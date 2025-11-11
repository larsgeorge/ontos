import os
import re
import sys
import argparse
from typing import Any, Dict, Iterable, List, Optional, Tuple
from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from pyspark.sql import SparkSession

from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import NotFound


# ============================================================================
# OAuth Token Generation & Database Connection (for Lakebase Postgres)
# ============================================================================

def get_oauth_token(ws_client: WorkspaceClient, instance_name: str) -> Tuple[str, str]:
    """Generate OAuth token for the service principal to access Lakebase Postgres."""
    if not instance_name or instance_name == 'None' or instance_name == '':
        raise RuntimeError(
            "Lakebase instance name is required but was not provided.\n"
            "This is auto-detected from the Databricks App resources.\n"
            "Ensure your app has a Lakebase database resource configured."
        )
    
    print(f"  Generating OAuth token for instance: {instance_name}")
    
    # Get current service principal
    current_user = ws_client.current_user.me().user_name
    print(f"  Service Principal: {current_user}")
    
    # Generate token
    try:
        cred = ws_client.database.generate_database_credential(
            request_id=str(uuid4()),
            instance_names=[instance_name],
        )
    except AttributeError as e:
        raise RuntimeError(
            f"Failed to generate OAuth token: {e}\n"
            "This may indicate that the Databricks SDK version doesn't support database OAuth,\n"
            "or that the workspace client is not properly initialized.\n"
            "Please ensure you're using a recent version of the databricks-sdk package."
        )
    
    print(f"  ✓ Successfully generated OAuth token")
    return current_user, cred.token


def build_db_url(
    host: str,
    db: str, 
    port: str, 
    schema: str,
    instance_name: str,
    ws_client: WorkspaceClient
) -> Tuple[str, str]:
    """Build PostgreSQL connection URL using OAuth authentication.
    
    Returns: (connection_url, auth_user)
    """
    
    print(f"  POSTGRES_HOST: {host}")
    print(f"  POSTGRES_DB: {db}")
    print(f"  POSTGRES_PORT: {port}")
    print(f"  POSTGRES_DB_SCHEMA: {schema}")
    print(f"  LAKEBASE_INSTANCE_NAME: {instance_name}")
    print(f"  Authentication: OAuth (Lakebase Postgres)")
    
    # Generate OAuth token
    oauth_user, oauth_token = get_oauth_token(ws_client, instance_name)
    print(f"  Using OAuth user: {oauth_user}")
    
    if not all([host, oauth_user, oauth_token, db]):
        missing = []
        if not host: missing.append("host")
        if not oauth_user: missing.append("oauth_user")
        if not oauth_token: missing.append("oauth_token")
        if not db: missing.append("db")
        raise RuntimeError(f"Missing required Postgres parameters: {', '.join(missing)}")
    
    query = f"?options=-csearch_path%3D{schema}" if schema else ""
    connection_url = f"postgresql+psycopg2://{oauth_user}:****@{host}:{port}/{db}{query}"
    print(f"  Connection URL (token redacted): {connection_url}")
    
    actual_url = f"postgresql+psycopg2://{oauth_user}:{oauth_token}@{host}:{port}/{db}{query}"
    return actual_url, oauth_user


def create_engine_from_params(
    ws_client: WorkspaceClient,
    host: str,
    db: str,
    port: str,
    schema: str,
    instance_name: str
) -> Engine:
    """Create SQLAlchemy engine using OAuth authentication."""
    if not instance_name:
        raise RuntimeError("lakebase_instance_name parameter is required")
    
    url, auth_user = build_db_url(host, db, port, schema, instance_name, ws_client)
    return create_engine(url, pool_pre_ping=True)


# --- Helpers -----------------------------------------------------------------


def slugify_iri(iri: str) -> str:
    last = iri.rstrip('/').split('/')[-1]
    last = last.split('#')[-1]
    return re.sub(r"[^a-z0-9-]", "-", last.lower()).strip('-')


def qualify_uc_name(physical_name: str, default_catalog: Optional[str], default_schema: Optional[str]) -> Optional[str]:
    if not physical_name:
        return None
    parts = physical_name.split(".")
    if len(parts) == 3:
        return physical_name
    if len(parts) == 2 and default_catalog:
        return f"{default_catalog}.{physical_name}"
    if len(parts) == 1 and default_catalog and default_schema:
        return f"{default_catalog}.{default_schema}.{physical_name}"
    return None


@dataclass
class DatasetTagInfo:
    fqn: str
    catalog: str
    schema: str
    table: str
    contract_name: Optional[str]
    product_name: Optional[str]
    semantic_slugs: List[str]


def read_contracts_and_links(engine: Engine, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    sql = (
        """
        SELECT c.id AS contract_id,
               c.name AS contract_name,
               c.data_product AS product_name,
               o.id   AS object_id,
               o.name AS schema_name,
               o.physical_name,
               el.iri AS schema_semantic_iri
        FROM data_contracts c
        JOIN data_contract_schema_objects o ON o.contract_id = c.id
        LEFT JOIN entity_semantic_links el
          ON el.entity_type = 'data_contract_schema'
         AND el.entity_id = c.id || '#' || o.name
        """
        + (" LIMIT :limit" if limit else "")
    )
    params = {"limit": int(limit)} if limit else {}
    with engine.connect() as conn:
        rows = [dict(r._mapping) for r in conn.execute(text(sql), params)]
    return rows


def build_dataset_tag_infos(rows: List[Dict[str, Any]], default_catalog: Optional[str], default_schema: Optional[str]) -> List[DatasetTagInfo]:
    # Aggregate semantic IRIs per object
    by_object: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        key = r["object_id"]
        obj = by_object.setdefault(
            key,
            {
                "contract_name": r.get("contract_name"),
                "product_name": r.get("product_name"),
                "physical_name": r.get("physical_name"),
                "sem_iris": set(),
            },
        )
        iri = r.get("schema_semantic_iri")
        if iri:
            obj["sem_iris"].add(str(iri))

    out: List[DatasetTagInfo] = []
    for _obj_id, data in by_object.items():
        qualified = qualify_uc_name(str(data.get("physical_name") or ""), default_catalog, default_schema)
        if not qualified:
            continue
        parts = qualified.split(".")
        if len(parts) != 3:
            continue
        cat, sch, tbl = parts
        slugs = sorted({slugify_iri(iri) for iri in data["sem_iris"]})
        out.append(
            DatasetTagInfo(
                fqn=qualified,
                catalog=cat,
                schema=sch,
                table=tbl,
                contract_name=str(data.get("contract_name") or "") or None,
                product_name=str(data.get("product_name") or "") or None,
                semantic_slugs=slugs,
            )
        )
    return out


# Databricks governed tags helpers ------------------------------------------------

def ensure_tag_key(ws: WorkspaceClient, key: str) -> None:
    # SDK doesn't yet expose create-if-missing uniformly for all backends; attempt idempotent create.
    try:
        ws.tags.create(key=key)
    except Exception:
        # Assume it exists already or creation is not required in this workspace
        pass


def get_existing_prefixed_tags(spark: SparkSession, object_type: str, object_name: str, prefix: str) -> Dict[str, Optional[str]]:
    # Use SparkSQL to query Unity Catalog tags
    # object_type in {CATALOG, SCHEMA, TABLE}
    q = f"SHOW TAGS ON {object_type} {object_name}"
    rows = spark.sql(q).collect()
    existing: Dict[str, Optional[str]] = {}
    # Rows typically have columns: key, value, inheritable, applied_by
    for r in rows:
        key = str(r.get("key") or r.get("KEY") or "")
        if key.startswith(prefix):
            existing[key] = r.get("value") or r.get("VALUE")
    return existing


def assign_tag(spark: SparkSession, object_type: str, object_name: str, key: str, value: Optional[str]) -> None:
    v = value if value is not None else ""
    spark.sql(f"ALTER {object_type} {object_name} SET TAGS ('{key}' = '{v.replace(\"'\",\"''\")}')")


def unassign_tag(spark: SparkSession, object_type: str, object_name: str, key: str) -> None:
    spark.sql(f"ALTER {object_type} {object_name} UNSET TAGS ('{key}')")


def reconcile_tags(ws: WorkspaceClient, spark: SparkSession, object_type: str, object_name: str, desired: Dict[str, Optional[str]], prefix: str, dry_run: bool = False) -> Tuple[int, int]:
    existing = get_existing_prefixed_tags(spark, object_type, object_name, prefix)
    to_remove = [k for k in existing.keys() if k not in desired]
    to_upsert = {k: v for k, v in desired.items() if existing.get(k) != v}

    updated = 0
    removed = 0
    if dry_run:
        if to_remove or to_upsert:
            print(f"[DRY-RUN] {object_type} {object_name} remove={to_remove} upsert={to_upsert}")
        return (0, 0)

    for k in to_remove:
        try:
            unassign_tag(spark, object_type, object_name, k)
            removed += 1
        except Exception as e:
            print(f"[WARN] Failed to remove tag {k} from {object_type} {object_name}: {e}")

    for k, v in to_upsert.items():
        try:
            ensure_tag_key(ws, k)
            assign_tag(spark, object_type, object_name, k, v)
            updated += 1
        except Exception as e:
            print(f"[WARN] Failed to assign tag {k}={v} to {object_type} {object_name}: {e}")

    return (updated, removed)


def aggregate_parent_desired(dataset_items: List[DatasetTagInfo], prefix: str) -> Tuple[Dict[str, Dict[str, Optional[str]]], Dict[str, Dict[str, Optional[str]]]]:
    # schema FQN -> desired tags, catalog name -> desired tags
    schema_to_values: Dict[str, Dict[str, Optional[str]]] = {}
    catalog_to_values: Dict[str, Dict[str, Optional[str]]] = {}

    for d in dataset_items:
        schema_fqn = f"{d.catalog}.{d.schema}"
        # Aggregate product names
        if d.product_name:
            schema_vals = schema_to_values.setdefault(schema_fqn, {})
            catalog_vals = catalog_to_values.setdefault(d.catalog, {})
            schema_vals.setdefault(f"{prefix}product_name:list", set()).add(d.product_name)
            catalog_vals.setdefault(f"{prefix}product_name:list", set()).add(d.product_name)

        # Aggregate semantic links
        if d.semantic_slugs:
            schema_vals = schema_to_values.setdefault(schema_fqn, {})
            catalog_vals = catalog_to_values.setdefault(d.catalog, {})
            for slug in d.semantic_slugs:
                schema_vals.setdefault(f"{prefix}semantic_link:list", set()).add(slug)
                catalog_vals.setdefault(f"{prefix}semantic_link:list", set()).add(slug)

    # Collapse sets to comma strings and map keys
    def collapse(map_in: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Optional[str]]]:
        out: Dict[str, Dict[str, Optional[str]]] = {}
        for res, vals in map_in.items():
            m: Dict[str, Optional[str]] = {}
            for k, v in vals.items():
                if k.endswith(":list") and isinstance(v, set):
                    base = k[:-5]
                    m[base] = ",".join(sorted(v)) if v else None
            out[res] = m
        return out

    return collapse(schema_to_values), collapse(catalog_to_values)


def build_desired_for_dataset(d: DatasetTagInfo, prefix: str) -> Dict[str, Optional[str]]:
    desired: Dict[str, Optional[str]] = {}
    if d.contract_name:
        desired[f"{prefix}contract_name"] = d.contract_name
    if d.product_name:
        desired[f"{prefix}product_name"] = d.product_name
    if d.semantic_slugs:
        desired[f"{prefix}semantic_link"] = ",".join(sorted(d.semantic_slugs))
    return desired


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync Ontos metadata to UC governed tags")
    parser.add_argument("--prefix", type=str, default="x_ontos_")
    parser.add_argument("--dry_run", type=str, default="false")
    parser.add_argument("--default_catalog", type=str, default="")
    parser.add_argument("--default_schema", type=str, default="")
    parser.add_argument("--limit", type=str, default="")
    parser.add_argument("--verbose", type=str, default="false")
    parser.add_argument("--lakebase_instance_name", type=str, required=True)
    parser.add_argument("--postgres_host", type=str, required=True)
    parser.add_argument("--postgres_db", type=str, required=True)
    parser.add_argument("--postgres_port", type=str, default="5432")
    parser.add_argument("--postgres_schema", type=str, default="public")
    args, _ = parser.parse_known_args()

    prefix: str = args.prefix
    dry_run: bool = args.dry_run.lower() in ("true", "1", "yes")
    default_catalog = args.default_catalog if args.default_catalog else None
    default_schema = args.default_schema if args.default_schema else None
    limit = int(args.limit) if args.limit and args.limit.isdigit() else None
    verbose = args.verbose.lower() in ("true", "1", "yes")

    print("=" * 80)
    print("UC Tag Sync workflow started")
    print("=" * 80)
    print(f"\nJob Parameters:")
    print(f"  Prefix: {prefix}")
    print(f"  Dry run: {dry_run}")
    print(f"  Default catalog: {default_catalog}")
    print(f"  Default schema: {default_schema}")
    print(f"  Limit: {limit}")
    print(f"  Verbose: {verbose}")
    print(f"  Lakebase instance name: {args.lakebase_instance_name}")

    # Initialize Workspace Client (needed for OAuth authentication)
    print("\nInitializing Databricks Workspace Client...")
    ws = WorkspaceClient()
    print("✓ Workspace client initialized")

    # Connect to database using OAuth
    print("\nConnecting to database...")
    engine = create_engine_from_params(
        ws_client=ws,
        host=args.postgres_host,
        db=args.postgres_db,
        port=args.postgres_port,
        schema=args.postgres_schema,
        instance_name=args.lakebase_instance_name
    )
    print("✓ Database connection established successfully")

    # Initialize Spark
    print("\nInitializing Spark Session...")
    spark = SparkSession.builder.appName("UC-Tag-Sync").getOrCreate()
    print("✓ Spark session initialized")

    rows = read_contracts_and_links(engine, limit=limit)
    datasets = build_dataset_tag_infos(rows, default_catalog, default_schema)

    updated_total = removed_total = 0

    print(f"\nProcessing {len(datasets)} datasets...")

    # Dataset-level
    for d in datasets:
        desired = build_desired_for_dataset(d, prefix)
        if not desired:
            continue
        u, r = reconcile_tags(ws, spark, "TABLE", d.fqn, desired, prefix, dry_run=dry_run)
        updated_total += u
        removed_total += r
        if verbose:
            print(f"Dataset {d.fqn}: updated={u} removed={r}")

    # Aggregate parent desired values
    schema_desired, catalog_desired = aggregate_parent_desired(datasets, prefix)

    # Schema-level
    for schema_fqn, desired in schema_desired.items():
        if not desired:
            continue
        u, r = reconcile_tags(ws, spark, "SCHEMA", schema_fqn, desired, prefix, dry_run=dry_run)
        updated_total += u
        removed_total += r

    # Catalog-level
    for catalog_name, desired in catalog_desired.items():
        if not desired:
            continue
        u, r = reconcile_tags(ws, spark, "CATALOG", catalog_name, desired, prefix, dry_run=dry_run)
        updated_total += u
        removed_total += r

    print("\n" + "=" * 80)
    print("✓ UC Tag Sync workflow completed successfully!")
    print("=" * 80)
    print(f"Summary: updated={updated_total} removed={removed_total}")


if __name__ == "__main__":
    main()


