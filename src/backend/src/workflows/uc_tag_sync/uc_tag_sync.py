import os
import re
import sys
import time
import argparse
from typing import Any, Dict, Iterable, List, Optional, Tuple

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.engine import Engine

from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import NotFound

# Make 'workflows/shared' helper directory importable when running as a script on Databricks
_BASE_DIR = os.path.dirname(__file__) if '__file__' in globals() else os.getcwd()
_WF_ROOT = os.path.dirname(_BASE_DIR)
_SHARED_DIR = os.path.join(_WF_ROOT, 'shared')
if _SHARED_DIR not in sys.path:
    sys.path.insert(0, _SHARED_DIR)
from db import create_engine_from_env  # type: ignore


# --- Helpers -----------------------------------------------------------------

def build_db_url_from_env() -> str:
    # Kept for backward compatibility; use create_engine_from_env directly where possible
    from db import build_db_url_from_env as _impl  # type: ignore
    return _impl()


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


def get_existing_prefixed_tags(ws: WorkspaceClient, object_type: str, object_name: str, prefix: str) -> Dict[str, Optional[str]]:
    # Fallback to SQL SHOW TAGS if direct API not available
    # object_type in {CATALOG, SCHEMA, TABLE}
    q = f"SHOW TAGS ON {object_type} {object_name}"
    rows = list(ws.sql.statements.execute(statement=q))
    existing: Dict[str, Optional[str]] = {}
    # Rows typically have columns: key, value, inheritable, applied_by
    for r in rows:
        key = str(r.get("key") or r.get("KEY") or "")
        if key.startswith(prefix):
            existing[key] = r.get("value") or r.get("VALUE")
    return existing


def assign_tag(ws: WorkspaceClient, object_type: str, object_name: str, key: str, value: Optional[str]) -> None:
    v = value if value is not None else ""
    ws.sql.statements.execute(statement=f"ALTER {object_type} {object_name} SET TAGS ('{key}' = '{v.replace("'","''")}')")


def unassign_tag(ws: WorkspaceClient, object_type: str, object_name: str, key: str) -> None:
    ws.sql.statements.execute(statement=f"ALTER {object_type} {object_name} UNSET TAGS ('{key}')")


def reconcile_tags(ws: WorkspaceClient, object_type: str, object_name: str, desired: Dict[str, Optional[str]], prefix: str, dry_run: bool = False) -> Tuple[int, int]:
    existing = get_existing_prefixed_tags(ws, object_type, object_name, prefix)
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
            unassign_tag(ws, object_type, object_name, k)
            removed += 1
        except Exception as e:
            print(f"[WARN] Failed to remove tag {k} from {object_type} {object_name}: {e}")

    for k, v in to_upsert.items():
        try:
            ensure_tag_key(ws, k)
            assign_tag(ws, object_type, object_name, k, v)
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
    parser.add_argument("--prefix", type=str, default=os.environ.get("ONTOS_TAG_PREFIX", "x_ontos_"))
    parser.add_argument("--dry-run", dest="dry_run", action="store_true")
    parser.add_argument("--catalog", type=str, default=os.environ.get("DATABRICKS_CATALOG"))
    parser.add_argument("--schema", type=str, default=os.environ.get("DATABRICKS_SCHEMA"))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--verbose", action="store_true")
    args, _ = parser.parse_known_args()

    prefix: str = args.prefix
    dry_run: bool = bool(args.dry_run)
    default_catalog = args.catalog
    default_schema = args.schema

    # DB engine
    engine = create_engine_from_env()

    # Workspace client (host/token from env)
    ws = WorkspaceClient()

    rows = read_contracts_and_links(engine, limit=args.limit)
    datasets = build_dataset_tag_infos(rows, default_catalog, default_schema)

    updated_total = removed_total = 0

    # Dataset-level
    for d in datasets:
        desired = build_desired_for_dataset(d, prefix)
        if not desired:
            continue
        u, r = reconcile_tags(ws, "TABLE", d.fqn, desired, prefix, dry_run=dry_run)
        updated_total += u
        removed_total += r
        if args.verbose:
            print(f"Dataset {d.fqn}: updated={u} removed={r}")

    # Aggregate parent desired values
    schema_desired, catalog_desired = aggregate_parent_desired(datasets, prefix)

    # Schema-level
    for schema_fqn, desired in schema_desired.items():
        if not desired:
            continue
        u, r = reconcile_tags(ws, "SCHEMA", schema_fqn, desired, prefix, dry_run=dry_run)
        updated_total += u
        removed_total += r

    # Catalog-level
    for catalog_name, desired in catalog_desired.items():
        if not desired:
            continue
        u, r = reconcile_tags(ws, "CATALOG", catalog_name, desired, prefix, dry_run=dry_run)
        updated_total += u
        removed_total += r

    print(f"Tag sync complete. updated={updated_total} removed={removed_total}")


if __name__ == "__main__":
    main()


