import json
import logging
import os
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, Depends, Request, Body
from fastapi.responses import JSONResponse

from src.controller.data_contracts_manager import DataContractsManager
from src.common.dependencies import (
    DBSessionDep,
    AuditManagerDep,
    CurrentUserDep,
)
from src.common.audit_logging import audit_action
from src.repositories.data_contracts_repository import data_contract_repo
from src.db_models.data_contracts import DataContractDb, DataContractCommentDb, DataContractTagDb, DataContractRoleDb
from src.models.data_contracts_api import (
    DataContractCreate,
    DataContractUpdate,
    DataContractRead,
    DataContractCommentCreate,
    DataContractCommentRead,
)
from src.common.authorization import PermissionChecker
from src.common.features import FeatureAccessLevel
import yaml

# Configure logging
from src.common.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["data-contracts"])

def get_data_contracts_manager(request: Request) -> DataContractsManager:
    """Retrieves the DataContractsManager singleton from app.state."""
    manager = getattr(request.app.state, 'data_contracts_manager', None)
    if manager is None:
        logger.critical("DataContractsManager instance not found in app.state!")
        raise HTTPException(status_code=500, detail="Data Contracts service is not available.")
    if not isinstance(manager, DataContractsManager):
        logger.critical(f"Object found at app.state.data_contracts_manager is not a DataContractsManager instance (Type: {type(manager)})!")
        raise HTTPException(status_code=500, detail="Data Contracts service configuration error.")
    return manager

@router.get('/data-contracts', response_model=list[DataContractRead])
async def get_contracts(db: DBSessionDep, _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_ONLY))):
    """Get all data contracts"""
    try:
        contracts = data_contract_repo.get_multi(db)
        return [
            DataContractRead(
                id=c.id,
                name=c.name,
                version=c.version,
                status=c.status,
                owner=c.owner,
                format=c.raw_format,
                created=c.created_at.isoformat() if c.created_at else None,
                updated=c.updated_at.isoformat() if c.updated_at else None,
            )
            for c in contracts
        ]
    except Exception as e:
        error_msg = f"Error retrieving data contracts: {e!s}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@router.get('/data-contracts/{contract_id}', response_model=DataContractRead)
async def get_contract(contract_id: str, db: DBSessionDep, _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_ONLY))):
    """Get a specific data contract"""
    try:
        contract = data_contract_repo.get_with_all(db, id=contract_id)
        if not contract:
            raise HTTPException(status_code=404, detail="Contract not found")

        return DataContractRead(
            id=contract.id,
            name=contract.name,
            version=contract.version,
            status=contract.status,
            owner=contract.owner,
            format=contract.raw_format,
            contract_text=contract.raw_text,
            created=contract.created_at.isoformat() if contract.created_at else None,
            updated=contract.updated_at.isoformat() if contract.updated_at else None,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post('/data-contracts', response_model=DataContractRead)
@audit_action(feature="data-contracts", action="CREATE")
async def create_contract(
    request: Request,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: CurrentUserDep,
    contract_data: DataContractCreate = Body(...),
    manager: DataContractsManager = Depends(get_data_contracts_manager),
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_WRITE))
):
    """Create a new data contract"""
    try:
        # Persist as DB entity (normalized fields minimal for now)
        db_obj = DataContractDb(
            name=contract_data.name,
            version=contract_data.version or 'v1.0',
            status=contract_data.status or 'draft',
            owner=contract_data.owner or (current_user.username if current_user else 'unknown'),
            kind=contract_data.kind or 'DataContract',
            api_version=contract_data.apiVersion or 'v3.0.1',
            raw_format=contract_data.format or 'json',
            raw_text=contract_data.contract_text or '',
            created_by=current_user.username if current_user else None,
            updated_by=current_user.username if current_user else None,
        )
        created = data_contract_repo.create(db=db, obj_in=db_obj)  # type: ignore[arg-type]
        db.commit()
        return DataContractRead(
            id=created.id,
            name=created.name,
            version=created.version,
            status=created.status,
            owner=created.owner,
            format=created.raw_format,
            created=created.created_at.isoformat() if created.created_at else None,
            updated=created.updated_at.isoformat() if created.updated_at else None,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put('/data-contracts/{contract_id}', response_model=DataContractRead)
@audit_action(feature="data-contracts", action="UPDATE")
async def update_contract(
    contract_id: str,
    request: Request,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: CurrentUserDep,
    contract_data: DataContractUpdate = Body(...),
    manager: DataContractsManager = Depends(get_data_contracts_manager),
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_WRITE))
):
    """Update a data contract"""
    try:
        db_obj = data_contract_repo.get(db, id=contract_id)
        if not db_obj:
            raise HTTPException(status_code=404, detail="Contract not found")
        update_payload = {}
        payload_map = {
            'name': contract_data.name,
            'version': contract_data.version,
            'status': contract_data.status,
            'owner': contract_data.owner,
            'tenant': contract_data.tenant,
            'data_product': contract_data.dataProduct,
            'description_usage': contract_data.descriptionUsage,
            'description_purpose': contract_data.descriptionPurpose,
            'description_limitations': contract_data.descriptionLimitations,
            'raw_format': contract_data.format,
            'raw_text': contract_data.contract_text,
            'api_version': contract_data.apiVersion,
            'kind': contract_data.kind,
            'domain_id': contract_data.domainId,
        }
        for k, v in payload_map.items():
            if v is not None:
                update_payload[k] = v
        update_payload["updated_by"] = current_user.username if current_user else None
        updated = data_contract_repo.update(db=db, db_obj=db_obj, obj_in=update_payload)
        db.commit()
        return DataContractRead(
            id=updated.id,
            name=updated.name,
            version=updated.version,
            status=updated.status,
            owner=updated.owner,
            format=updated.raw_format,
            created=updated.created_at.isoformat() if updated.created_at else None,
            updated=updated.updated_at.isoformat() if updated.updated_at else None,
        )
    except Exception as e:
        error_msg = f"Error updating data contract {contract_id}: {e!s}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@router.delete('/data-contracts/{contract_id}')
@audit_action(feature="data-contracts", action="DELETE")
async def delete_contract(
    contract_id: str,
    request: Request,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: CurrentUserDep,
    manager: DataContractsManager = Depends(get_data_contracts_manager),
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_WRITE))
):
    """Delete a data contract"""
    try:
        db_obj = data_contract_repo.get(db, id=contract_id)
        if not db_obj:
            raise HTTPException(status_code=404, detail="Contract not found")
        data_contract_repo.remove(db=db, id=contract_id)
        db.commit()
        return {"deleted": True}
    except Exception as e:
        error_msg = f"Error deleting data contract {contract_id}: {e!s}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@router.post('/data-contracts/upload')
@audit_action(feature="data-contracts", action="UPLOAD")
async def upload_contract(
    request: Request,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: CurrentUserDep,
    file: UploadFile = File(...),
    manager: DataContractsManager = Depends(get_data_contracts_manager),
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_WRITE))
):
    """Upload a contract file"""
    try:
        content_type = file.content_type
        filename = file.filename or ''

        # Determine format from content type or extension
        format = 'json'  # default
        if content_type == 'application/x-yaml' or filename.endswith(('.yaml', '.yml')):
            format = 'yaml'
        elif content_type.startswith('text/'):
            format = 'text'

        # Read file content
        contract_text = (await file.read()).decode('utf-8')

        # Parse if JSON/YAML to extract name/version/tags/roles when possible
        parsed: dict | None = None
        try:
            if format == 'yaml':
                parsed = yaml.safe_load(contract_text) or None
            elif format == 'json':
                parsed = json.loads(contract_text) or None
        except Exception:
            parsed = None

        name_val = (parsed.get('name') if isinstance(parsed, dict) else None) or filename
        version_val = (parsed.get('version') if isinstance(parsed, dict) else None) or 'v1.0'
        owner_val = (parsed.get('owner') if isinstance(parsed, dict) else None) or (current_user.username if current_user else 'unknown')
        api_version_val = (parsed.get('apiVersion') if isinstance(parsed, dict) else None) or 'v3.0.1'
        kind_val = (parsed.get('kind') if isinstance(parsed, dict) else None) or 'DataContract'

        created = data_contract_repo.create(db=db, obj_in=DataContractDb(
            name=name_val,
            version=version_val,
            status='draft',
            owner=owner_val,
            kind=kind_val,
            api_version=api_version_val,
            raw_format=format,
            raw_text=contract_text,
            created_by=current_user.username if current_user else None,
            updated_by=current_user.username if current_user else None,
        ))

        # Extract simple arrays
        if isinstance(parsed, dict):
            tags = parsed.get('tags')
            if isinstance(tags, list):
                for t in tags:
                    if isinstance(t, str):
                        db.add(DataContractTagDb(contract_id=created.id, name=t))
            roles = parsed.get('roles')
            if isinstance(roles, list):
                for r in roles:
                    if isinstance(r, dict) and r.get('role'):
                        db.add(DataContractRoleDb(contract_id=created.id, role=r.get('role'), description=r.get('description'), access=r.get('access'), first_level_approvers=r.get('firstLevelApprovers'), second_level_approvers=r.get('secondLevelApprovers')))

        db.commit()
        return {"id": created.id, "name": created.name, "version": created.version, "status": created.status, "owner": created.owner, "format": created.raw_format, "created": str(created.created_at), "updated": str(created.updated_at)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get('/data-contracts/{contract_id}/export')
async def export_contract(contract_id: str, db: DBSessionDep, manager: DataContractsManager = Depends(get_data_contracts_manager), _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_ONLY))):
    """Export a contract as JSON"""
    try:
        db_obj = data_contract_repo.get(db, id=contract_id)
        if not db_obj:
            raise HTTPException(status_code=404, detail="Contract not found")
        media = 'application/json' if (db_obj.raw_format or 'json') == 'json' else 'text/plain'
        content = db_obj.raw_text or ''
        if (db_obj.raw_format or 'json') == 'json':
            try:
                content = json.loads(content)
            except Exception:
                # keep as string if not valid JSON
                media = 'text/plain'
        return JSONResponse(content=content, media_type=media, headers={'Content-Disposition': f'attachment; filename="{(db_obj.name or "contract").lower().replace(" ", "_")}.{db_obj.raw_format or "json"}"'})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/data-contracts/schema/odcs')
async def get_odcs_schema(_perm: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_ONLY))):
    try:
        from pathlib import Path
        schema_path = Path(__file__).parent.parent / 'schemas' / 'odcs_v3.json'
        with open(schema_path, 'r') as f:
            data = json.load(f)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/data-contracts/odcs/import')
@audit_action(feature="data-contracts", action="IMPORT")
async def import_odcs(
    request: Request,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: CurrentUserDep,
    payload: dict = Body(...),
    manager: DataContractsManager = Depends(get_data_contracts_manager),
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_WRITE))
):
    try:
        created = manager.create_from_odcs_dict(db, payload, current_user.username if current_user else None)
        db.commit()
        return DataContractRead(
            id=created.id,
            name=created.name,
            version=created.version,
            status=created.status,
            owner=created.owner,
            format=created.raw_format,
            created=created.created_at.isoformat() if created.created_at else None,
            updated=created.updated_at.isoformat() if created.updated_at else None,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/data-contracts/{contract_id}/odcs/export')
async def export_odcs(contract_id: str, db: DBSessionDep, manager: DataContractsManager = Depends(get_data_contracts_manager), _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_ONLY))):
    try:
        db_obj = data_contract_repo.get_with_all(db, id=contract_id)
        if not db_obj:
            raise HTTPException(status_code=404, detail="Contract not found")
        odcs = manager.build_odcs_from_db(db_obj)
        return JSONResponse(content=odcs, media_type='application/json', headers={'Content-Disposition': f'attachment; filename="{(db_obj.name or "contract").lower().replace(" ", "_")}-odcs.json"'})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post('/data-contracts/{contract_id}/comments', response_model=dict)
@audit_action(feature="data-contracts", action="COMMENT")
async def add_comment(
    contract_id: str,
    request: Request,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: CurrentUserDep,
    payload: DataContractCommentCreate = Body(...),
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_WRITE))
):
    try:
        if not data_contract_repo.get(db, id=contract_id):
            raise HTTPException(status_code=404, detail="Contract not found")
        message = payload.message
        if not message:
            raise HTTPException(status_code=400, detail="message is required")
        db.add(DataContractCommentDb(contract_id=contract_id, author=current_user.username if current_user else 'anonymous', message=message))
        db.commit()
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/data-contracts/{contract_id}/comments', response_model=list[DataContractCommentRead])
async def list_comments(contract_id: str, db: DBSessionDep, _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_ONLY))):
    try:
        comments = db.query(DataContractCommentDb).filter(DataContractCommentDb.contract_id == contract_id).order_by(DataContractCommentDb.created_at.asc()).all()
        return [
            DataContractCommentRead(
                id=c.id,
                author=c.author,
                message=c.message,
                created_at=c.created_at.isoformat() if c.created_at else None,
            )
            for c in comments
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/data-contracts/{contract_id}/versions')
@audit_action(feature="data-contracts", action="VERSION")
async def create_version(
    contract_id: str,
    request: Request,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: CurrentUserDep,
    payload: dict = Body(...),
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_WRITE))
):
    try:
        original = data_contract_repo.get(db, id=contract_id)
        if not original:
            raise HTTPException(status_code=404, detail="Contract not found")
        new_version = payload.get('new_version')
        if not new_version:
            raise HTTPException(status_code=400, detail="new_version is required")
        clone = DataContractDb(
            name=original.name,
            version=new_version,
            status='draft',
            owner=original.owner,
            kind=original.kind,
            api_version=original.api_version,
            raw_format=original.raw_format,
            raw_text=original.raw_text,
            domain_id=original.domain_id,
            created_by=current_user.username if current_user else None,
            updated_by=current_user.username if current_user else None,
        )
        db.add(clone)
        db.flush()
        db.commit()
        return {"id": clone.id, "name": clone.name, "version": clone.version, "status": clone.status, "owner": clone.owner}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def register_routes(app):
    """Register routes with the app"""
    app.include_router(router)
    logger.info("Data contract routes registered")
