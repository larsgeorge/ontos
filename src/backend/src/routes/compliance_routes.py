import logging
import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, FastAPI, HTTPException, Depends, Body, Query, Request

from src.common.dependencies import DBSessionDep, AuditManagerDep, AuditCurrentUserDep
from src.common.features import FeatureAccessLevel
from src.common.authorization import PermissionChecker
from src.controller.compliance_manager import ComplianceManager
from src.controller.change_log_manager import change_log_manager
from src.models.compliance import (
    CompliancePolicy,
    ComplianceRun,
    ComplianceResult,
    ComplianceRunRequest,
    ComplianceResultsResponse,
)
from src.db_models.compliance import CompliancePolicyDb, ComplianceRunDb, ComplianceResultDb
from src.common.compliance_dsl import evaluate_rule_on_object as eval_dsl


router = APIRouter(prefix="/api", tags=["compliance"])
manager = ComplianceManager()

FEATURE_ID = 'compliance'


@router.on_event("startup")
def _load_yaml_on_startup():
    try:
        yaml_path = Path(__file__).parent.parent / 'data' / 'compliance.yaml'
        if os.path.exists(yaml_path):
            # Defer DB provision via dependency in endpoints; here we just note file exists
            logging.info(f"Compliance YAML available at {yaml_path}")
    except Exception:
        logging.exception("Compliance YAML detection failed")


@router.get("/compliance/policies")
async def get_policies(
    db: DBSessionDep,
    _: bool = Depends(PermissionChecker(FEATURE_ID, FeatureAccessLevel.READ_ONLY)),
):
    # Lazy-load YAML into DB if DB has no policies yet
    yaml_path = Path(__file__).parent.parent / 'data' / 'compliance.yaml'
    try:
        from sqlalchemy import func
        count = db.query(CompliancePolicyDb).count()
        if count == 0 and os.path.exists(yaml_path):
            manager.load_from_yaml(db, str(yaml_path))
    except Exception:
        logging.exception("Failed preloading compliance YAML")

    rows = manager.list_policies(db)
    stats = manager.get_compliance_stats(db)
    # No heavy projection here; return minimal fields akin to Pydantic model
    return {
        "policies": [
            {
                'id': r.id,
                'name': r.name,
                'description': r.description,
                'rule': r.rule,
                'created_at': r.created_at,
                'updated_at': r.updated_at,
                'is_active': r.is_active,
                'severity': r.severity,
                'category': r.category,
                # compliance field resolved from latest run if present
                'compliance': (manager.list_runs(db, policy_id=r.id, limit=1)[0].score if manager.list_runs(db, policy_id=r.id, limit=1) else 0.0),
                'history': [],
            } for r in rows
        ],
        "stats": stats
    }


@router.get("/compliance/policies/{policy_id}")
async def get_policy(
    policy_id: str,
    db: DBSessionDep,
    _: bool = Depends(PermissionChecker(FEATURE_ID, FeatureAccessLevel.READ_ONLY)),
):
    r = manager.get_policy(db, policy_id)
    if not r:
        raise HTTPException(status_code=404, detail="Policy not found")
    # Try reading examples from YAML for this policy
    examples = None
    try:
        yaml_path = Path(__file__).parent.parent / 'data' / 'compliance.yaml'
        if os.path.exists(yaml_path):
            import yaml as _yaml
            with open(yaml_path) as _f:
                _data = _yaml.safe_load(_f) or []
                if isinstance(_data, list):
                    for _item in _data:
                        if isinstance(_item, dict) and str(_item.get('id')) == r.id:
                            ex = _item.get('examples')
                            if isinstance(ex, dict):
                                examples = ex
                            break
    except Exception:
        # Non-fatal; just omit examples on error
        pass
    return {
        'id': r.id,
        'name': r.name,
        'description': r.description,
        'rule': r.rule,
        'created_at': r.created_at,
        'updated_at': r.updated_at,
        'is_active': r.is_active,
        'severity': r.severity,
        'category': r.category,
        'examples': examples,
    }


@router.post("/compliance/policies")
async def create_policy(
    request: Request,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: AuditCurrentUserDep,
    policy: CompliancePolicy = Body(...),
    _: bool = Depends(PermissionChecker(FEATURE_ID, FeatureAccessLevel.READ_WRITE)),
):
    created = manager.create_policy(db, policy)
    change_log_manager.log_change_with_details(
        db,
        entity_type='compliance_policy',
        entity_id=created.id,
        action='CREATE',
        username=current_user.username if current_user else None,
        details={"name": created.name}
    )
    return {
        'id': created.id,
        'name': created.name,
        'description': created.description,
        'rule': created.rule,
        'created_at': created.created_at,
        'updated_at': created.updated_at,
        'is_active': created.is_active,
        'severity': created.severity,
        'category': created.category,
        'compliance': 0.0,
        'history': [],
    }


@router.put("/compliance/policies/{policy_id}")
async def update_policy(
    policy_id: str,
    request: Request,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: AuditCurrentUserDep,
    policy: CompliancePolicy = Body(...),
    _: bool = Depends(PermissionChecker(FEATURE_ID, FeatureAccessLevel.READ_WRITE)),
):
    updated = manager.update_policy(db, policy_id, policy)
    if not updated:
        raise HTTPException(status_code=404, detail="Policy not found")
    change_log_manager.log_change_with_details(
        db,
        entity_type='compliance_policy',
        entity_id=policy_id,
        action='UPDATE',
        username=current_user.username if current_user else None,
        details={"name": updated.name}
    )
    return {
        'id': updated.id,
        'name': updated.name,
        'description': updated.description,
        'rule': updated.rule,
        'created_at': updated.created_at,
        'updated_at': updated.updated_at,
        'is_active': updated.is_active,
        'severity': updated.severity,
        'category': updated.category,
    }


@router.delete("/compliance/policies/{policy_id}")
async def delete_policy(
    policy_id: str,
    db: DBSessionDep,
    current_user: AuditCurrentUserDep,
    _: bool = Depends(PermissionChecker(FEATURE_ID, FeatureAccessLevel.READ_WRITE)),
):
    ok = manager.delete_policy(db, policy_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Policy not found")
    change_log_manager.log_change_with_details(
        db,
        entity_type='compliance_policy',
        entity_id=policy_id,
        action='DELETE',
        username=current_user.username if current_user else None,
        details=None,
    )
    return {"status": "success"}


@router.post("/compliance/policies/{policy_id}/runs")
async def run_policy(
    policy_id: str,
    db: DBSessionDep,
    current_user: AuditCurrentUserDep,
    payload: ComplianceRunRequest = Body(default=ComplianceRunRequest()),
    _: bool = Depends(PermissionChecker(FEATURE_ID, FeatureAccessLevel.READ_WRITE)),
):
    policy = manager.get_policy(db, policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    # For now, implement inline only; async can be backed by Databricks job later
    run = manager.run_policy_inline(db, policy=policy, limit=payload.limit)
    change_log_manager.log_change_with_details(
        db,
        entity_type='compliance_policy',
        entity_id=policy_id,
        action='RUN',
        username=current_user.username if current_user else None,
        details={"run_id": run.id, "status": run.status, "score": run.score}
    )
    return {
        'id': run.id,
        'policy_id': run.policy_id,
        'status': run.status,
        'started_at': run.started_at,
        'finished_at': run.finished_at,
        'success_count': run.success_count,
        'failure_count': run.failure_count,
        'score': run.score,
        'error_message': run.error_message,
    }


@router.get("/compliance/policies/{policy_id}/runs")
async def list_runs(
    policy_id: str,
    db: DBSessionDep,
    _: bool = Depends(PermissionChecker(FEATURE_ID, FeatureAccessLevel.READ_ONLY)),
):
    policy = manager.get_policy(db, policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    runs = manager.list_runs(db, policy_id=policy_id, limit=50)
    return [
        {
            'id': r.id,
            'policy_id': r.policy_id,
            'status': r.status,
            'started_at': r.started_at,
            'finished_at': r.finished_at,
            'success_count': r.success_count,
            'failure_count': r.failure_count,
            'score': r.score,
            'error_message': r.error_message,
        } for r in runs
    ]


@router.get("/compliance/runs/{run_id}/results")
async def get_run_results(
    run_id: str,
    db: DBSessionDep,
    only_failed: Optional[bool] = Query(default=False),
    _: bool = Depends(PermissionChecker(FEATURE_ID, FeatureAccessLevel.READ_ONLY)),
):
    run = db.get(ComplianceRunDb, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    results = manager.list_results(db, run_id=run_id, only_failed=bool(only_failed), limit=2000)
    return {
        'run': {
            'id': run.id,
            'policy_id': run.policy_id,
            'status': run.status,
            'started_at': run.started_at,
            'finished_at': run.finished_at,
            'success_count': run.success_count,
            'failure_count': run.failure_count,
            'score': run.score,
            'error_message': run.error_message,
        },
        'results': [
            {
                'id': r.id,
                'run_id': r.run_id,
                'object_type': r.object_type,
                'object_id': r.object_id,
                'object_name': r.object_name,
                'passed': r.passed,
                'message': r.message,
                'details_json': r.details_json,
                'created_at': r.created_at,
            } for r in results
        ],
        'only_failed': bool(only_failed),
        'total': len(results),
    }


@router.get("/compliance/stats")
async def get_stats(
    db: DBSessionDep,
    _: bool = Depends(PermissionChecker(FEATURE_ID, FeatureAccessLevel.READ_ONLY)),
):
    return manager.get_compliance_stats(db)


@router.get("/compliance/trend")
async def get_compliance_trend(
    db: DBSessionDep,
    _: bool = Depends(PermissionChecker(FEATURE_ID, FeatureAccessLevel.READ_ONLY)),
):
    return manager.get_compliance_trend(db)


def register_routes(app: FastAPI) -> None:
    app.include_router(router)


@router.post("/compliance/validate-inline")
async def validate_inline(
    body: dict = Body(...),
    _: bool = Depends(PermissionChecker(FEATURE_ID, FeatureAccessLevel.READ_ONLY)),
):
    """Validate a single object against a DSL rule inline (no DB writes)."""
    try:
        rule = body.get('rule') or ''
        obj = body.get('object') or {}
        passed, msg = eval_dsl(rule, obj)
        return {"passed": passed, "message": msg}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
