from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Body

from src.common.dependencies import (
    DBSessionDep,
    CurrentUserDep,
)
from src.common.features import FeatureAccessLevel
from src.common.authorization import PermissionChecker
from src.common.config import get_settings, get_config_manager
from src.common.workspace_client import get_workspace_client
from src.common.logging import get_logger
from src.db_models.compliance import CompliancePolicyDb
from src.repositories.teams_repository import team_repo
from src.repositories.projects_repository import project_repo
from src.db_models.teams import TeamDb
from src.db_models.projects import ProjectDb
from src.controller.catalog_commander_manager import CatalogCommanderManager
from src.controller.data_contracts_manager import DataContractsManager
from src.repositories.data_contracts_repository import data_contract_repo


logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["self-service"])

FEATURE_ID = "data-contracts"  # Reuse data-contracts feature for RW permission


def _username_slug(email: Optional[str]) -> str:
    if not email:
        return "user"
    local = email.split("@")[0].lower()
    # Allow only lowercase letters, digits and underscores
    safe = []
    for ch in local:
        if ch.isalnum() or ch == '_':
            safe.append(ch)
        elif ch in ('.', '-', ' '):
            safe.append('_')
    slug = ''.join(safe).strip('_')
    return slug or "user"


def _load_compliance_mapping() -> Dict[str, Any]:
    """Load compliance mapping from YAML via ConfigManager.

    Expected YAML structure (example):
      catalog:
        policies: ["naming-conventions"]
        auto_fix: true
        required_tags:
          owner: from_user
      schema:
        policies: ["naming-conventions"]
      table:
        policies: ["naming-conventions"]
        auto_fix: true
        required_tags:
          project: from_project
    """
    try:
        cfg = get_config_manager()
        return cfg.load_yaml('compliance_mapping.yaml')
    except Exception:
        return {}


def _apply_autofix(obj_type: str, obj: Dict[str, Any], mapping: Dict[str, Any], current_user_email: Optional[str], project: Optional[ProjectDb]) -> Dict[str, Any]:
    rules = mapping.get(obj_type, {}) if isinstance(mapping, dict) else {}
    required_tags = rules.get('required_tags', {}) if isinstance(rules, dict) else {}
    if not required_tags:
        return obj
    tags = dict(obj.get('tags') or {})
    for key, val in required_tags.items():
        if val == 'from_user' and current_user_email:
            tags.setdefault(key, current_user_email)
        elif val == 'from_project' and project is not None:
            tags.setdefault(key, getattr(project, 'name', None) or getattr(project, 'title', None) or project.id)
        elif isinstance(val, str):
            tags.setdefault(key, val)
    if tags:
        obj['tags'] = tags
    return obj


def _eval_policies(db, obj: Dict[str, Any], policy_ids_or_slugs: List[str]) -> Tuple[bool, List[Dict[str, Any]]]:
    """Evaluate a list of policies against an object.
    Returns (all_passed, results[])
    """
    from src.controller.compliance_manager import ComplianceManager
    from src.common.compliance_dsl import evaluate_rule_on_object

    results: List[Dict[str, Any]] = []
    all_passed = True

    # Map input identifiers to policies (try id first, then slug, then name)
    for pid in policy_ids_or_slugs:
        policy: Optional[CompliancePolicyDb] = None
        if not pid:
            continue
        # Try by primary key id
        policy = db.get(CompliancePolicyDb, pid)
        if policy is None:
            # Try by slug or name
            try:
                q = db.query(CompliancePolicyDb).filter((CompliancePolicyDb.slug == pid) | (CompliancePolicyDb.name == pid))
                policy = q.first()
            except Exception:
                policy = None
        if policy is None:
            results.append({"policy": pid, "passed": False, "message": "Policy not found"})
            all_passed = False
            continue

        passed, message = evaluate_rule_on_object(policy.rule, obj)  # type: ignore[name-defined]
        results.append({"policy": policy.slug or policy.id, "name": policy.name, "passed": bool(passed), "message": message})
        all_passed = all_passed and bool(passed)

    return all_passed, results


@router.post('/self-service/bootstrap')
async def bootstrap_self_service(
    db: DBSessionDep,
    current_user: CurrentUserDep,
    _: bool = Depends(PermissionChecker(FEATURE_ID, FeatureAccessLevel.READ_WRITE)),
):
    """Ensure user's personal Team and Project exist and return defaults including sandbox names.

    - Creates a team and project if missing
    - Returns suggested default UC catalog/schema
    """
    try:
        username_slug = _username_slug(current_user.email if current_user else None)
        team_name = f"team_{username_slug}"
        project_name = f"project_{username_slug}"

        # Ensure Team
        team: Optional[TeamDb] = team_repo.get_by_name(db, name=team_name)
        if not team:
            team = team_repo.create(db=db, obj_in={
                'name': team_name,
                'title': f"Personal Team for {current_user.email}",
                'description': "Auto-created personal team",
                'created_by': current_user.email,
                'updated_by': current_user.email,
            })

        # Ensure Project
        project: Optional[ProjectDb] = project_repo.get_by_name(db, name=project_name)
        if not project:
            project = project_repo.create(db=db, obj_in={
                'name': project_name,
                'title': f"Personal Project for {current_user.email}",
                'description': "Auto-created personal project",
                'owner_team_id': team.id if team else None,
                'created_by': current_user.email,
                'updated_by': current_user.email,
            })

        # Suggest default UC sandbox names
        settings = get_settings()
        default_catalog = f"user_{username_slug}"
        default_schema = "sandbox"

        return {
            'team': {'id': team.id, 'name': team.name} if team else None,
            'project': {'id': project.id, 'name': project.name} if project else None,
            'defaults': {
                'catalog': default_catalog,
                'schema': default_schema,
            }
        }
    except Exception as e:
        logger.exception("Failed bootstrapping self-service")
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/self-service/create')
async def self_service_create(
    db: DBSessionDep,
    current_user: CurrentUserDep,
    payload: Dict[str, Any] = Body(...),
    _: bool = Depends(PermissionChecker(FEATURE_ID, FeatureAccessLevel.READ_WRITE)),
):
    """Create catalog/schema/table with parent auto-creation, apply compliance mapping, optionally create a contract and assign to project.

    Payload:
      type: 'catalog'|'schema'|'table'
      catalog: string (optional if type=catalog)
      schema: string (optional; defaults to 'sandbox')
      table: { name: string, columns?: [{ name, logicalType }], physicalType?: 'managed_table'|'streaming_table' }
      projectId: string (optional)
      autoFix: boolean (default true)
      createContract: boolean (default true when type='table')
      defaultToUserCatalog: boolean (default true)
    """
    try:
        ws = get_workspace_client()
        catalog_manager = CatalogCommanderManager(ws)
        dc_manager = DataContractsManager()

        obj_type = (payload.get('type') or '').lower()
        if obj_type not in ('catalog', 'schema', 'table'):
            raise HTTPException(status_code=400, detail="Invalid type; expected catalog|schema|table")

        username_slug = _username_slug(current_user.email if current_user else None)
        mapping = _load_compliance_mapping()

        auto_fix = bool(payload.get('autoFix', True))
        default_to_user_catalog = bool(payload.get('defaultToUserCatalog', True))
        requested_catalog = (payload.get('catalog') or '').strip()
        requested_schema = (payload.get('schema') or '').strip() or 'sandbox'
        if not requested_catalog and default_to_user_catalog:
            requested_catalog = f"user_{username_slug}"

        project: Optional[ProjectDb] = None
        project_id = payload.get('projectId')
        if project_id:
            try:
                project = project_repo.get(db, id=project_id)
            except Exception:
                project = None

        # Prepare object skeleton for compliance
        compliance_results: List[Dict[str, Any]] = []

        if obj_type == 'catalog':
            obj: Dict[str, Any] = {'type': 'catalog', 'name': requested_catalog, 'tags': payload.get('tags') or {}}
            if auto_fix:
                obj = _apply_autofix('catalog', obj, mapping, getattr(current_user, 'email', None), project)
            all_passed, res = _eval_policies(db, obj, list(mapping.get('catalog', {}).get('policies', [])) if isinstance(mapping.get('catalog'), dict) else [])
            compliance_results.extend(res)
            # Create catalog (idempotent)
            try:
                ws.catalogs.get(requested_catalog)
            except Exception:
                ws.catalogs.create(name=requested_catalog, comment=obj.get('tags', {}).get('description'))
            return { 'created': {'catalog': requested_catalog}, 'compliance': compliance_results }

        if obj_type == 'schema':
            if not requested_catalog:
                raise HTTPException(status_code=400, detail="catalog is required for schema creation")
            obj = {'type': 'schema', 'name': requested_schema, 'catalog': requested_catalog, 'tags': payload.get('tags') or {}}
            if auto_fix:
                obj = _apply_autofix('schema', obj, mapping, getattr(current_user, 'email', None), project)
            all_passed, res = _eval_policies(db, obj, list(mapping.get('schema', {}).get('policies', [])) if isinstance(mapping.get('schema'), dict) else [])
            compliance_results.extend(res)
            # Ensure catalog then schema
            try:
                try:
                    ws.catalogs.get(requested_catalog)
                except Exception:
                    ws.catalogs.create(name=requested_catalog)
                try:
                    ws.schemas.get(f"{requested_catalog}.{requested_schema}")
                except Exception:
                    ws.schemas.create(name=requested_schema, catalog_name=requested_catalog)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Schema creation failed: {e}")
            return { 'created': {'catalog': requested_catalog, 'schema': requested_schema}, 'compliance': compliance_results }

        # table
        table_spec = payload.get('table') or {}
        table_name = (table_spec.get('name') or '').strip()
        if not requested_catalog or not requested_schema or not table_name:
            raise HTTPException(status_code=400, detail="catalog, schema, and table.name are required for table creation")

        # Compliance for table
        obj = {'type': 'table', 'name': table_name, 'catalog': requested_catalog, 'schema': requested_schema, 'tags': (table_spec.get('tags') or {})}
        if auto_fix:
            obj = _apply_autofix('table', obj, mapping, getattr(current_user, 'email', None), project)
        all_passed, res = _eval_policies(db, obj, list(mapping.get('table', {}).get('policies', [])) if isinstance(mapping.get('table'), dict) else [])
        compliance_results.extend(res)

        # Ensure parents
        try:
            try:
                ws.catalogs.get(requested_catalog)
            except Exception:
                ws.catalogs.create(name=requested_catalog)
            try:
                ws.schemas.get(f"{requested_catalog}.{requested_schema}")
            except Exception:
                ws.schemas.create(name=requested_schema, catalog_name=requested_catalog)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Parent creation failed: {e}")

        # Create table via SQL (map logicalType -> DB type)
        columns: List[Dict[str, Any]] = table_spec.get('columns') or []
        def map_type(logical: str) -> str:
            l = (logical or '').lower()
            if l in ('integer', 'int', 'long', 'smallint', 'tinyint'): return 'BIGINT'
            if l in ('number', 'double', 'float', 'decimal', 'numeric'): return 'DOUBLE'
            if l in ('string', 'text'): return 'STRING'
            if l in ('boolean', 'bool'): return 'BOOLEAN'
            if l in ('date', 'datetime', 'timestamp', 'time'): return 'TIMESTAMP'
            if l in ('array',): return 'ARRAY<STRING>'
            if l in ('object', 'struct', 'map'): return 'STRING'
            return 'STRING'
        column_sql_parts: List[str] = []
        for c in columns:
            cname = c.get('name')
            ltype = c.get('logicalType') or c.get('logical_type') or 'string'
            if not cname:
                continue
            column_sql_parts.append(f"`{cname}` {map_type(ltype)}")
        columns_sql = ', '.join(column_sql_parts) or '`id` STRING'
        full_name = f"{requested_catalog}.{requested_schema}.{table_name}"
        try:
            # Use SQL endpoint for creation
            ws.sql.execute(f"CREATE TABLE IF NOT EXISTS {full_name} ({columns_sql})")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Table creation failed: {e}")

        created_contract_id: Optional[str] = None
        if bool(payload.get('createContract', True)):
            # Build minimal ODCS contract dict and create
            odcs = {
                'name': table_name,
                'version': '1.0.0',
                'status': 'draft',
                'owner': getattr(current_user, 'username', None) or getattr(current_user, 'email', None),
                'schema': [
                    {
                        'name': table_name,
                        'physicalName': full_name,
                        'physicalType': 'managed_table',
                        'properties': [
                            {
                                'name': c.get('name'),
                                'logicalType': c.get('logicalType') or c.get('logical_type') or 'string',
                                'required': False,
                            } for c in columns if c.get('name')
                        ]
                    }
                ]
            }
            try:
                created_db = dc_manager.create_from_odcs_dict(db, odcs, getattr(current_user, 'username', None))
                created_contract_id = created_db.id
                # Assign to project if provided
                if project_id and created_db:
                    try:
                        created_db.project_id = project_id
                        db.add(created_db)
                        db.flush()
                    except Exception:
                        logger.warning("Failed to assign project_id to created contract", exc_info=True)
                db.commit()
            except Exception as e:
                logger.warning(f"Failed to create data contract for table: {e}", exc_info=True)

        return {
            'created': {
                'catalog': requested_catalog,
                'schema': requested_schema,
                'table': table_name,
                'full_name': full_name,
            },
            'contractId': created_contract_id,
            'compliance': compliance_results,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Self-service create failed")
        raise HTTPException(status_code=500, detail=str(e))


def register_routes(app):
    app.include_router(router)
    logger.info("Self-service routes registered")


@router.post('/self-service/deploy/{contract_id}')
async def deploy_contract(
    contract_id: str,
    db: DBSessionDep,
    current_user: CurrentUserDep,
    body: Dict[str, Any] = Body(default={}),
    _: bool = Depends(PermissionChecker(FEATURE_ID, FeatureAccessLevel.READ_WRITE)),
):
    """Deploy a data contract to Unity Catalog by creating its physical dataset(s).

    Optional body keys:
      defaultCatalog: string
      defaultSchema: string
    """
    try:
        ws = get_workspace_client()
        contract = data_contract_repo.get_with_all(db, id=contract_id)
        if not contract:
            raise HTTPException(status_code=404, detail="Contract not found")

        default_catalog = (body.get('defaultCatalog') or '').strip()
        default_schema = (body.get('defaultSchema') or '').strip()

        created: List[str] = []
        for sobj in (contract.schema_objects or []):
            # Resolve physical name or build from defaults
            physical_name = getattr(sobj, 'physical_name', None) or ''
            if not physical_name:
                if not default_catalog or not default_schema:
                    # Cannot build full name
                    raise HTTPException(status_code=400, detail="Missing physicalName and defaults for deployment")
                physical_name = f"{default_catalog}.{default_schema}.{sobj.name}"

            parts = physical_name.split('.')
            if len(parts) != 3:
                raise HTTPException(status_code=400, detail=f"Invalid physical name: {physical_name}")
            catalog_name, schema_name, table_name = parts

            # Ensure parents
            try:
                try:
                    ws.catalogs.get(catalog_name)
                except Exception:
                    ws.catalogs.create(name=catalog_name)
                try:
                    ws.schemas.get(f"{catalog_name}.{schema_name}")
                except Exception:
                    ws.schemas.create(name=schema_name, catalog_name=catalog_name)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed ensuring parents: {e}")

            # Prepare column DDL from properties
            props = getattr(sobj, 'properties', []) or []
            def map_type(logical: str) -> str:
                l = (logical or '').lower()
                if l in ('integer', 'int', 'long', 'smallint', 'tinyint'): return 'BIGINT'
                if l in ('number', 'double', 'float', 'decimal', 'numeric'): return 'DOUBLE'
                if l in ('string', 'text'): return 'STRING'
                if l in ('boolean', 'bool'): return 'BOOLEAN'
                if l in ('date', 'datetime', 'timestamp', 'time'): return 'TIMESTAMP'
                if l in ('array',): return 'ARRAY<STRING>'
                if l in ('object', 'struct', 'map'): return 'STRING'
                return 'STRING'
            cols = []
            for p in props:
                try:
                    pname = getattr(p, 'name', None) or p.get('name')
                    ltype = getattr(p, 'logical_type', None) or getattr(p, 'logicalType', None) or p.get('logicalType') or 'string'
                except Exception:
                    pname = None
                    ltype = 'string'
                if pname:
                    cols.append(f"`{pname}` {map_type(str(ltype))}")
            cols_sql = ', '.join(cols) or '`id` STRING'

            try:
                ws.sql.execute(f"CREATE TABLE IF NOT EXISTS {catalog_name}.{schema_name}.{table_name} ({cols_sql})")
                created.append(f"{catalog_name}.{schema_name}.{table_name}")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed creating table {table_name}: {e}")

        return { 'created': created }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Deploy contract failed")
        raise HTTPException(status_code=500, detail=str(e))


