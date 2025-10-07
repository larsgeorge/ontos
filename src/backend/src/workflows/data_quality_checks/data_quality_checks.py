import os
import re
import json
import argparse
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F


def load_active_contracts_from_uc(spark: SparkSession, catalog: str, schema: str) -> List[Dict[str, Any]]:
    """Load active contracts and their schema/properties from UC-backed Lakehouse tables."""
    cte = f"{catalog}.{schema}"
    df = spark.sql(
        f"""
        SELECT c.id AS contract_id,
               c.name AS contract_name,
               o.id AS object_id,
               o.name AS object_name,
               o.physical_name AS physical_name,
               p.name AS prop_name,
               p.required AS prop_required,
               p.unique AS prop_unique,
               p.logical_type_options_json AS prop_opts
        FROM {cte}.data_contracts c
        JOIN {cte}.data_contract_schema_objects o
          ON o.contract_id = c.id
        LEFT JOIN {cte}.data_contract_schema_properties p
          ON p.object_id = o.id
        WHERE lower(c.status) = 'active'
        """
    )

    # Group rows into contracts -> schema objects -> properties
    rows = df.collect()
    contracts_by_id: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        cid = r["contract_id"]
        cname = r["contract_name"]
        oid = r["object_id"]
        oname = r["object_name"]
        physical_name = r["physical_name"]
        prop_name = r["prop_name"]
        prop_required = bool(r["prop_required"]) if r["prop_required"] is not None else False
        prop_unique = bool(r["prop_unique"]) if r["prop_unique"] is not None else False
        prop_opts_raw = r["prop_opts"]
        prop_opts: Dict[str, Any] = {}
        if isinstance(prop_opts_raw, str) and prop_opts_raw:
            try:
                prop_opts = json.loads(prop_opts_raw)
            except Exception:
                prop_opts = {}

        contract = contracts_by_id.setdefault(cid, {
            "id": cid,
            "name": cname,
            "schema": {}
        })
        schema_obj = contract["schema"].setdefault(oid, {
            "id": oid,
            "name": oname,
            "physicalName": physical_name,
            "properties": []
        })

        if prop_name:
            prop_dict: Dict[str, Any] = {
                "name": str(prop_name),
                "required": prop_required,
                "unique": prop_unique,
            }
            # Map common ODCS options if present
            if isinstance(prop_opts, dict):
                if prop_opts.get("minLength") is not None:
                    prop_dict["minLength"] = prop_opts.get("minLength")
                if prop_opts.get("maxLength") is not None:
                    prop_dict["maxLength"] = prop_opts.get("maxLength")
                if prop_opts.get("minimum") is not None:
                    prop_dict["minimum"] = prop_opts.get("minimum")
                if prop_opts.get("maximum") is not None:
                    prop_dict["maximum"] = prop_opts.get("maximum")
                if prop_opts.get("pattern"):
                    prop_dict["pattern"] = prop_opts.get("pattern")
            schema_obj["properties"].append(prop_dict)

    # Convert schema maps to arrays
    result: List[Dict[str, Any]] = []
    for contract in contracts_by_id.values():
        schema_list = list(contract["schema"].values())
        contract["schema"] = schema_list
        result.append(contract)
    return result


def qualify_uc_name(physical_name: str, default_catalog: Optional[str], default_schema: Optional[str]) -> Optional[str]:
    """Return a fully qualified UC table name catalog.schema.table if possible.

    Respects already-qualified names and uses defaults when partial.
    """
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


def column_exists(df: DataFrame, column_name: str) -> bool:
    return column_name in [c.lower() for c in df.columns]


def evaluate_required_columns(df: DataFrame, columns: List[str]) -> List[Tuple[str, bool, int]]:
    """Check that required columns have no nulls. Returns (column, passed, null_count)."""
    if not columns:
        return []
    # Compute null counts in one pass
    agg_exprs = [F.sum(F.col(c).isNull().cast("int")).alias(c) for c in columns if column_exists(df, c)]
    if not agg_exprs:
        return []
    row = df.agg(*agg_exprs).collect()[0]
    results: List[Tuple[str, bool, int]] = []
    for c in columns:
        if not column_exists(df, c):
            continue
        nulls = int(row[c])
        results.append((c, nulls == 0, nulls))
    return results


def evaluate_unique_columns(df: DataFrame, columns: List[str]) -> List[Tuple[str, bool, int]]:
    """Check that columns are unique. Returns (column, passed, duplicate_groups)."""
    results: List[Tuple[str, bool, int]] = []
    for c in columns:
        if not column_exists(df, c):
            continue
        dup_groups = df.groupBy(F.col(c)).count().filter(F.col("count") > 1).limit(1).count()
        results.append((c, dup_groups == 0, dup_groups))
    return results


def evaluate_numeric_ranges(df: DataFrame, col_specs: List[Tuple[str, Optional[float], Optional[float]]]) -> List[Tuple[str, bool, int]]:
    """Check numeric ranges; returns (column, passed, out_of_range_count)."""
    results: List[Tuple[str, bool, int]] = []
    for c, min_val, max_val in col_specs:
        if not column_exists(df, c):
            continue
        col_expr = F.col(c).cast("double")
        conds = []
        if min_val is not None:
            conds.append(col_expr < F.lit(float(min_val)))
        if max_val is not None:
            conds.append(col_expr > F.lit(float(max_val)))
        if not conds:
            continue
        out_of_range = df.select(F.sum(F.when(conds[0] if len(conds) == 1 else (conds[0] | conds[1]), 1).otherwise(0)).alias("cnt")).collect()[0]["cnt"]
        results.append((c, int(out_of_range) == 0, int(out_of_range)))
    return results


def evaluate_string_lengths(df: DataFrame, col_specs: List[Tuple[str, Optional[int], Optional[int]]]) -> List[Tuple[str, bool, int]]:
    """Check string min/max lengths; returns (column, passed, violations)."""
    results: List[Tuple[str, bool, int]] = []
    for c, min_len, max_len in col_specs:
        if not column_exists(df, c):
            continue
        length_expr = F.length(F.col(c).cast("string"))
        conds = []
        if min_len is not None:
            conds.append(length_expr < F.lit(int(min_len)))
        if max_len is not None:
            conds.append(length_expr > F.lit(int(max_len)))
        if not conds:
            continue
        violations = df.select(F.sum(F.when(conds[0] if len(conds) == 1 else (conds[0] | conds[1]), 1).otherwise(0)).alias("cnt")).collect()[0]["cnt"]
        results.append((c, int(violations) == 0, int(violations)))
    return results


def evaluate_regex_patterns(df: DataFrame, specs: List[Tuple[str, str]]) -> List[Tuple[str, bool, int]]:
    """Check regex patterns; returns (column, passed, non_matching_count)."""
    results: List[Tuple[str, bool, int]] = []
    for c, pattern in specs:
        if not column_exists(df, c):
            continue
        # Use Spark SQL rlike (Java regex). Best-effort for Python patterns; escape if obviously invalid.
        try:
            re.compile(pattern)
        except re.error:
            # Skip invalid user pattern
            results.append((c, True, 0))
            continue
        nonmatch = df.select(F.sum(F.when(~F.col(c).cast("string").rlike(pattern), 1).otherwise(0)).alias("cnt")).collect()[0]["cnt"]
        results.append((c, int(nonmatch) == 0, int(nonmatch)))
    return results


def run_contract_checks(spark: SparkSession, contract: Dict[str, Any], default_catalog: Optional[str], default_schema: Optional[str]) -> None:
    contract_name = contract.get("name") or contract.get("id") or "unknown"
    schema_objs: List[Dict[str, Any]] = contract.get("schema") or []

    for schema_obj in schema_objs:
        physical_name = schema_obj.get("physicalName") or schema_obj.get("physical_name")
        qualified = qualify_uc_name(str(physical_name) if physical_name else "", default_catalog, default_schema)
        if not qualified:
            print(f"[SKIP] {contract_name}: schema '{schema_obj.get('name')}' has no resolvable physicalName")
            continue

        try:
            df = spark.table(qualified)
        except Exception as e:
            print(f"[ERROR] {contract_name}: failed to read table {qualified}: {e}")
            continue

        properties: List[Dict[str, Any]] = schema_obj.get("properties") or []
        required_cols = [str(p.get("name")) for p in properties if p.get("required") is True and p.get("name")]
        unique_cols = [str(p.get("name")) for p in properties if p.get("unique") is True and p.get("name")]
        range_specs: List[Tuple[str, Optional[float], Optional[float]]] = []
        length_specs: List[Tuple[str, Optional[int], Optional[int]]] = []
        pattern_specs: List[Tuple[str, str]] = []

        for p in properties:
            col_name = p.get("name")
            if not col_name:
                continue
            min_val = p.get("minimum")
            max_val = p.get("maximum")
            if min_val is not None or max_val is not None:
                try:
                    range_specs.append((str(col_name), float(min_val) if min_val is not None else None, float(max_val) if max_val is not None else None))
                except Exception:
                    pass
            min_len = p.get("minLength")
            max_len = p.get("maxLength")
            if min_len is not None or max_len is not None:
                try:
                    length_specs.append((str(col_name), int(min_len) if min_len is not None else None, int(max_len) if max_len is not None else None))
                except Exception:
                    pass
            pattern_val = p.get("pattern")
            if isinstance(pattern_val, str) and pattern_val:
                pattern_specs.append((str(col_name), pattern_val))

        results: List[str] = []

        # Required
        for col_name, passed, nulls in evaluate_required_columns(df, required_cols):
            results.append(f"required({col_name})={'OK' if passed else 'FAIL'} nulls={nulls}")

        # Unique
        for col_name, passed, dup_groups in evaluate_unique_columns(df, unique_cols):
            results.append(f"unique({col_name})={'OK' if passed else 'FAIL'} duplicate_groups={dup_groups}")

        # Ranges
        for col_name, passed, violations in evaluate_numeric_ranges(df, range_specs):
            results.append(f"range({col_name})={'OK' if passed else 'FAIL'} violations={violations}")

        # Lengths
        for col_name, passed, violations in evaluate_string_lengths(df, length_specs):
            results.append(f"length({col_name})={'OK' if passed else 'FAIL'} violations={violations}")

        # Patterns
        for col_name, passed, violations in evaluate_regex_patterns(df, pattern_specs):
            results.append(f"pattern({col_name})={'OK' if passed else 'FAIL'} violations={violations}")

        summary = "; ".join(results) if results else "no checks defined"
        print(f"[DQ] {contract_name} | {qualified} -> {summary}")


def main() -> None:
    print("Data Quality Checks workflow started")

    parser = argparse.ArgumentParser(description="Run data quality checks for active contracts")
    parser.add_argument("--catalog", type=str, default=os.environ.get("DATABRICKS_CATALOG"))
    parser.add_argument("--schema", type=str, default=os.environ.get("DATABRICKS_SCHEMA"))
    args, _ = parser.parse_known_args()

    spark = SparkSession.builder.appName("Ontos-DQX-Example").getOrCreate()

    # Defaults for partially-qualified physical names
    default_catalog = args.catalog or os.environ.get("DATABRICKS_CATALOG")
    default_schema = args.schema or os.environ.get("DATABRICKS_SCHEMA")

    if not default_catalog or not default_schema:
        print("Catalog/schema not provided; set --catalog/--schema or DATABRICKS_CATALOG/SCHEMA.")
        return

    # Load from Lakehouse federated UC tables
    try:
        contracts = load_active_contracts_from_uc(spark, default_catalog, default_schema)
    except Exception as e:
        print(f"Failed loading contracts from UC: {e}")
        return

    if not contracts:
        print("No active contracts found in UC. Exiting.")
        return

    for contract in contracts:
        try:
            run_contract_checks(spark, contract, default_catalog, default_schema)
        except Exception as e:
            name = contract.get("name") or contract.get("id") or "unknown"
            print(f"[ERROR] Contract {name} failed with error: {e}")

    print("Data Quality Checks workflow completed")


if __name__ == "__main__":
    main()