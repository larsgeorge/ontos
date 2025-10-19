import os
import sys
import json
import argparse
import traceback
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from uuid import uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from pyspark.sql import SparkSession

# DQX imports
try:
    from databricks.labs.dqx.profiler.profiler import DQProfiler
    from databricks.labs.dqx.profiler.generator import DQGenerator
    from databricks.sdk import WorkspaceClient
except ImportError as e:
    print(f"WARNING: DQX imports failed: {e}")
    print("This workflow requires databricks-labs-dqx package to be installed")


# ============================================================================
# Database Connection Utilities (inlined to avoid import issues in Databricks)
# ============================================================================

def _parse_secret_ref(secret_ref: str) -> Tuple[str, str]:
    """Parse a secret reference in the form "scope:key" or "scope/key"."""
    if ":" in secret_ref:
        scope, key = secret_ref.split(":", 1)
    elif "/" in secret_ref:
        scope, key = secret_ref.split("/", 1)
    else:
        raise ValueError("Secret reference must be in the form 'scope:key' or 'scope/key'")
    
    scope = scope.strip()
    key = key.strip()
    if not scope or not key:
        raise ValueError("Secret scope and key must be non-empty")
    return scope, key


def get_secret_value(secret_ref: str) -> str:
    """Resolve a Databricks secret value using the Databricks runtime API."""
    scope, key = _parse_secret_ref(secret_ref)
    
    try:
        from databricks.sdk.runtime import dbutils  # type: ignore
    except Exception as e:
        raise RuntimeError("Databricks runtime is not available to resolve secrets.") from e
    
    try:
        value = dbutils.secrets.get(scope=scope, key=key)
    except Exception as e:
        raise RuntimeError(f"Failed to resolve Databricks secret for scope='{scope}' and key='{key}'") from e
    
    if value is None:
        raise RuntimeError(f"Databricks secret returned no value for scope='{scope}' and key='{key}'")
    
    return str(value)


def build_db_url(host: str, user: str, db: str, port: str, schema: str, password_secret: str) -> str:
    """Build PostgreSQL connection URL from provided parameters."""
    
    print(f"  POSTGRES_HOST: {host}")
    print(f"  POSTGRES_USER: {user}")
    print(f"  POSTGRES_DB: {db}")
    print(f"  POSTGRES_PORT: {port}")
    print(f"  POSTGRES_DB_SCHEMA: {schema}")
    print(f"  POSTGRES_PASSWORD_SECRET: {password_secret}")
    
    # Fetch password from Databricks secret
    print(f"  Fetching password from Databricks secret: {password_secret}")
    try:
        password = get_secret_value(password_secret)
        print(f"  ✓ Successfully retrieved password from secret")
    except Exception as e:
        print(f"  ✗ Failed to retrieve password from secret: {e}")
        raise
    
    if not all([host, user, password, db]):
        missing = []
        if not host: missing.append("host")
        if not user: missing.append("user")
        if not password: missing.append("password from secret")
        if not db: missing.append("db")
        raise RuntimeError(f"Missing required Postgres parameters: {', '.join(missing)}")
    
    query = f"?options=-csearch_path%3D{schema}" if schema else ""
    connection_url = f"postgresql+psycopg2://{user}:****@{host}:{port}/{db}{query}"
    print(f"  Connection URL (password redacted): {connection_url}")
    
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}{query}"


def create_engine(host: str, user: str, db: str, port: str, schema: str, password_secret: str) -> Engine:
    """Create SQLAlchemy engine from parameters."""
    from sqlalchemy import create_engine as create_sa_engine
    url = build_db_url(host, user, db, port, schema, password_secret)
    return create_sa_engine(url, pool_pre_ping=True)


def load_contract_schemas(engine: Engine, contract_id: str, schema_names: List[str]) -> List[Dict[str, Any]]:
    """Load schema details for a contract from the database."""
    print(f"Loading contract schemas from database for contract: {contract_id}")
    schema_names_sql = ",".join([f"'{name}'" for name in schema_names])
    
    sql = text(f"""
        SELECT o.id AS object_id,
               o.name AS schema_name,
               o.physical_name,
               c.name AS contract_name
        FROM data_contract_schema_objects o
        JOIN data_contracts c ON c.id = o.contract_id
        WHERE o.contract_id = :contract_id
          AND o.name IN ({schema_names_sql})
    """)
    
    with engine.connect() as conn:
        result = conn.execute(sql, {"contract_id": contract_id})
        rows = result.fetchall()
        
    schemas = []
    for row in rows:
        schemas.append({
            "object_id": row[0],
            "schema_name": row[1],
            "physical_name": row[2],
            "contract_name": row[3]
        })
    
    print(f"Found {len(schemas)} schemas: {[s['schema_name'] for s in schemas]}")
    return schemas


def update_profiling_run_status(
    engine: Engine,
    profile_run_id: str,
    status: str,
    summary_stats: Optional[str] = None,
    error_message: Optional[str] = None
):
    """Update the status of a profiling run."""
    print(f"Updating profiling run status to: {status}")
    updates = {"status": status, "completed_at": datetime.utcnow()}
    
    if summary_stats:
        updates["summary_stats"] = summary_stats
    if error_message:
        updates["error_message"] = error_message
    
    set_clause = ", ".join([f"{k} = :{k}" for k in updates.keys()])
    sql = text(f"UPDATE data_profiling_runs SET {set_clause} WHERE id = :profile_run_id")
    
    with engine.connect() as conn:
        conn.execute(sql, {**updates, "profile_run_id": profile_run_id})
        conn.commit()
    print(f"Successfully updated profiling run status to: {status}")


def insert_suggestion(
    engine: Engine,
    profile_run_id: str,
    contract_id: str,
    schema_name: str,
    property_name: Optional[str],
    dq_profile: Any,
    source: str = "dqx"
) -> str:
    """Insert a quality check suggestion into the database."""
    suggestion_id = str(uuid4())
    
    # Map DQX profile to our schema
    # DQProfile has: name, column, description, parameters
    rule_name = dq_profile.name
    column_name = dq_profile.column
    description = dq_profile.description or ""
    params = dq_profile.parameters or {}
    
    # Determine level
    level = "property" if property_name else "object"
    
    # Map DQX rule types to ODCS dimensions and our rule format
    dimension_map = {
        "is_not_null": "completeness",
        "is_not_null_or_empty": "completeness",
        "min_max": "conformity",
        "is_in": "conformity",
        "pattern": "conformity",
        "is_unique": "uniqueness"
    }
    
    dimension = dimension_map.get(rule_name, "accuracy")
    severity = "error"  # DQX generates error-level rules by default
    
    # Build the rule string based on DQX rule type
    rule_str = None
    must_be = None
    must_be_gt = None
    must_be_lt = None
    
    if rule_name == "is_not_null":
        rule_str = f"{column_name} IS NOT NULL"
    elif rule_name == "is_not_null_or_empty":
        rule_str = f"{column_name} IS NOT NULL AND {column_name} != ''"
    elif rule_name == "min_max":
        min_val = params.get("min")
        max_val = params.get("max")
        if min_val is not None:
            must_be_gt = str(min_val)
        if max_val is not None:
            must_be_lt = str(max_val)
        rule_str = f"{column_name} BETWEEN {min_val} AND {max_val}"
    elif rule_name == "is_in":
        values = params.get("values", [])
        values_str = ", ".join([f"'{v}'" for v in values])
        rule_str = f"{column_name} IN ({values_str})"
    elif rule_name == "pattern":
        pattern = params.get("pattern", "")
        rule_str = f"{column_name} MATCHES '{pattern}'"
    elif rule_name == "is_unique":
        rule_str = f"{column_name} IS UNIQUE"
    
    sql = text("""
        INSERT INTO suggested_quality_checks (
            id, profile_run_id, contract_id, source, schema_name, property_name,
            status, name, description, level, dimension, severity, type, rule,
            must_be, must_be_gt, must_be_lt, created_at
        ) VALUES (
            :id, :profile_run_id, :contract_id, :source, :schema_name, :property_name,
            :status, :name, :description, :level, :dimension, :severity, :type, :rule,
            :must_be, :must_be_gt, :must_be_lt, :created_at
        )
    """)
    
    with engine.connect() as conn:
        conn.execute(sql, {
            "id": suggestion_id,
            "profile_run_id": profile_run_id,
            "contract_id": contract_id,
            "source": source,
            "schema_name": schema_name,
            "property_name": property_name,
            "status": "pending",
            "name": rule_name,
            "description": description,
            "level": level,
            "dimension": dimension,
            "severity": severity,
            "type": "library",
            "rule": rule_str,
            "must_be": must_be,
            "must_be_gt": must_be_gt,
            "must_be_lt": must_be_lt,
            "created_at": datetime.utcnow()
        })
        conn.commit()
    
    return suggestion_id


def profile_and_generate_suggestions(
    spark: SparkSession,
    ws: WorkspaceClient,
    engine: Engine,
    profile_run_id: str,
    contract_id: str,
    schemas: List[Dict[str, Any]]
):
    """Profile tables and generate quality check suggestions using DQX."""
    print(f"Initializing DQX profiler and generator")
    profiler = DQProfiler(ws)
    generator = DQGenerator(ws)
    
    summary_data = {"tables": {}}
    total_suggestions = 0
    
    print(f"Starting profiling for {len(schemas)} schemas...")
    
    for idx, schema_info in enumerate(schemas, 1):
        schema_name = schema_info["schema_name"]
        physical_name = schema_info["physical_name"]
        
        print(f"\n[{idx}/{len(schemas)}] Profiling table: {physical_name} (schema: {schema_name})")
        
        try:
            # Profile the table
            # Use moderate sampling for reasonable performance
            profile_options = {
                "sample_fraction": 0.1,  # 10% sample
                "limit": 5000,  # Max 5000 rows
                "sample_seed": 42,  # Reproducible
            }
            
            print(f"  Running profiler with options: sample_fraction=0.1, limit=5000")
            summary_stats, profiles = profiler.profile_table(
                table=physical_name,
                options=profile_options
            )
            
            print(f"  Profiler completed. Generated {len(profiles)} column profiles")
            
            # Store summary stats
            summary_data["tables"][schema_name] = {
                "physical_name": physical_name,
                "summary_stats": summary_stats,
                "profile_count": len(profiles)
            }
            
            # Generate DQ rules from profiles
            print(f"  Generating quality check rules...")
            checks = generator.generate_dq_rules(profiles, level="error")
            
            print(f"  Generated {len(checks)} quality check suggestions")
            
            # Insert suggestions into database
            print(f"  Inserting {len(checks)} suggestions into database...")
            for check_idx, check in enumerate(checks, 1):
                property_name = check.column if hasattr(check, 'column') else None
                insert_suggestion(
                    engine=engine,
                    profile_run_id=profile_run_id,
                    contract_id=contract_id,
                    schema_name=schema_name,
                    property_name=property_name,
                    dq_profile=check,
                    source="dqx"
                )
                total_suggestions += 1
            print(f"  Successfully inserted {len(checks)} suggestions")
            
        except Exception as e:
            print(f"  ERROR profiling {physical_name}: {e}")
            traceback.print_exc()
            summary_data["tables"][schema_name] = {
                "physical_name": physical_name,
                "error": str(e)
            }
    
    print(f"\nProfiling complete. Total suggestions generated: {total_suggestions}")
    summary_data["total_suggestions"] = total_suggestions
    return json.dumps(summary_data)


def main():
    print("=" * 80)
    print("DQX Profile Datasets workflow started")
    print("=" * 80)
    
    parser = argparse.ArgumentParser(description="Profile datasets using DQX")
    parser.add_argument("--contract_id", type=str, required=True)
    parser.add_argument("--schema_names", type=str, required=True)  # JSON array
    parser.add_argument("--profile_run_id", type=str, required=True)
    parser.add_argument("--postgres_host", type=str, required=True)
    parser.add_argument("--postgres_user", type=str, required=True)
    parser.add_argument("--postgres_db", type=str, required=True)
    parser.add_argument("--postgres_port", type=str, default="5432")
    parser.add_argument("--postgres_schema", type=str, default="public")
    parser.add_argument("--postgres_password_secret", type=str, required=True)
    args, _ = parser.parse_known_args()
    
    contract_id = args.contract_id
    schema_names = json.loads(args.schema_names)
    profile_run_id = args.profile_run_id
    
    print(f"\nJob Parameters:")
    print(f"  Contract ID: {contract_id}")
    print(f"  Schema names: {schema_names}")
    print(f"  Profile run ID: {profile_run_id}")
    
    print(f"\nEnvironment Info:")
    print(f"  Python version: {sys.version}")
    
    # Connect to database
    print("\nConnecting to database...")
    try:
        engine = create_engine(
            host=args.postgres_host,
            user=args.postgres_user,
            db=args.postgres_db,
            port=args.postgres_port,
            schema=args.postgres_schema,
            password_secret=args.postgres_password_secret
        )
        print("✓ Database connection established successfully")
    except Exception as e:
        print(f"✗ Failed to connect to database: {e}")
        traceback.print_exc()
        return
    
    # Update run status to 'running'
    try:
        update_profiling_run_status(engine, profile_run_id, "running")
    except Exception as e:
        print(f"Warning: Failed to update run status to 'running': {e}")
    
    try:
        # Load contract schemas
        print("\n" + "=" * 80)
        print("Phase 1: Loading Contract Schemas")
        print("=" * 80)
        schemas = load_contract_schemas(engine, contract_id, schema_names)
        
        if not schemas:
            raise ValueError(f"No schemas found for contract {contract_id} with names {schema_names}")
        
        print(f"✓ Loaded {len(schemas)} schemas to profile")
        for schema in schemas:
            print(f"  - {schema['schema_name']} ({schema['physical_name']})")
        
        # Initialize Spark and Databricks client
        print("\n" + "=" * 80)
        print("Phase 2: Initializing Spark and Databricks Client")
        print("=" * 80)
        spark = SparkSession.builder.appName("DQX-Profile-Datasets").getOrCreate()
        print("✓ Spark session initialized")
        ws = WorkspaceClient()
        print("✓ Workspace client initialized")
        
        # Profile and generate suggestions
        print("\n" + "=" * 80)
        print("Phase 3: Profiling Tables and Generating Suggestions")
        print("=" * 80)
        summary_stats = profile_and_generate_suggestions(
            spark=spark,
            ws=ws,
            engine=engine,
            profile_run_id=profile_run_id,
            contract_id=contract_id,
            schemas=schemas
        )
        
        # Update run status to 'completed'
        print("\n" + "=" * 80)
        print("Phase 4: Finalizing")
        print("=" * 80)
        update_profiling_run_status(
            engine,
            profile_run_id,
            "completed",
            summary_stats=summary_stats
        )
        
        print("\n" + "=" * 80)
        print("✓ DQX Profile Datasets workflow completed successfully!")
        print("=" * 80)
        
    except Exception as e:
        print("\n" + "=" * 80)
        print(f"✗ Workflow failed with error: {e}")
        print("=" * 80)
        traceback.print_exc()
        
        # Update run status to 'failed'
        try:
            update_profiling_run_status(
                engine,
                profile_run_id,
                "failed",
                error_message=str(e)
            )
        except Exception as update_error:
            print(f"Warning: Failed to update run status to 'failed': {update_error}")


if __name__ == "__main__":
    main()

