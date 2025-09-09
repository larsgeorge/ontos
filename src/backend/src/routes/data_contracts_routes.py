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
    AuditCurrentUserDep,
)
from src.common.audit_logging import audit_action
from src.repositories.data_contracts_repository import data_contract_repo
from src.db_models.data_contracts import (
    DataContractDb, 
    DataContractCommentDb, 
    DataContractTagDb, 
    DataContractRoleDb,
    SchemaObjectDb,
    SchemaPropertyDb,
    DataContractTeamDb,
    DataContractSupportDb,
    DataContractCustomPropertyDb,
    DataContractSlaPropertyDb,
    DataQualityCheckDb
)
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
    """Get all data contracts with basic ODCS structure"""
    try:
        contracts = data_contract_repo.get_multi(db)
        return [
            DataContractRead(
                id=c.id,
                name=c.name,
                version=c.version,
                status=c.status,
                owner=c.owner,
                kind=c.kind,
                apiVersion=c.api_version,
                tenant=c.tenant,
                dataProduct=c.data_product,
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
    """Get a specific data contract with full ODCS structure"""
    try:
        contract = data_contract_repo.get_with_all(db, id=contract_id)
        if not contract:
            raise HTTPException(status_code=404, detail="Contract not found")

        return _build_contract_read_from_db(contract)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def _build_contract_read_from_db(db_contract) -> DataContractRead:
    """Build DataContractRead from normalized database models"""
    from src.models.data_contracts_api import ContractDescription, SchemaObject, ColumnProperty
    
    # Build description
    description = None
    if db_contract.description_usage or db_contract.description_purpose or db_contract.description_limitations:
        description = ContractDescription(
            usage=db_contract.description_usage,
            purpose=db_contract.description_purpose,
            limitations=db_contract.description_limitations
        )
    
    # Build schema objects
    schema_objects = []
    for schema_obj in db_contract.schema_objects:
        properties = []
        for prop in schema_obj.properties:
            properties.append(ColumnProperty(
                name=prop.name,
                logical_type=prop.logical_type or 'string',
                required=prop.required,
                unique=prop.unique,
                description=prop.transform_description
            ))
        
        schema_objects.append(SchemaObject(
            name=schema_obj.name,
            physicalName=schema_obj.physical_name,
            properties=properties
        ))

    # Build team (legacy minimal)
    team = []
    if getattr(db_contract, 'team', None):
        for member in db_contract.team:
            team.append({
                'role': member.role or 'member',
                'email': member.username,
                'name': None,
            })

    # Build support channels (legacy minimal)
    support = None
    if getattr(db_contract, 'support', None):
        support = {}
        for ch in db_contract.support:
            if ch.channel and ch.url:
                support[ch.channel] = ch.url

    # Custom properties
    custom_properties = {}
    if getattr(db_contract, 'custom_properties', None):
        for cp in db_contract.custom_properties:
            custom_properties[cp.property] = cp.value

    # SLA properties (flatten basic key/value)
    sla = None
    if getattr(db_contract, 'sla_properties', None):
        sla = {}
        for sp in db_contract.sla_properties:
            if sp.property and sp.value is not None:
                sla[sp.property] = sp.value

    # Servers (minimal mapping)
    servers = None
    if getattr(db_contract, 'servers', None):
        servers = []
        for s in db_contract.servers:
            servers.append({
                'serverType': s.type,
                'connectionString': s.server,
                'environment': s.environment,
            })

    return DataContractRead(
        id=db_contract.id,
        name=db_contract.name,
        version=db_contract.version,
        status=db_contract.status,
        owner=db_contract.owner,
        kind=db_contract.kind,
        apiVersion=db_contract.api_version,
        tenant=db_contract.tenant,
        domain=db_contract.domain_id,  # Include domain_id as domain
        dataProduct=db_contract.data_product,
        description=description,
        schema=schema_objects,
        team=team,
        support=support,
        customProperties=custom_properties,
        sla=sla,
        servers=servers,
        created=db_contract.created_at.isoformat() if db_contract.created_at else None,
        updated=db_contract.updated_at.isoformat() if db_contract.updated_at else None,
    )


@router.post('/data-contracts', response_model=DataContractRead)
async def create_contract(
    db: DBSessionDep,
    current_user: CurrentUserDep,
    contract_data: DataContractCreate = Body(...),
    manager: DataContractsManager = Depends(get_data_contracts_manager),
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_WRITE)),
):
    """Create a new data contract with normalized ODCS structure"""
    try:
        # Create main contract record
        db_obj = DataContractDb(
            name=contract_data.name,
            version=contract_data.version or 'v1.0',
            status=contract_data.status or 'draft',
            owner=contract_data.owner or (current_user.username if current_user else 'unknown'),
            kind=contract_data.kind or 'DataContract',
            api_version=contract_data.apiVersion or 'v3.0.2',
            tenant=contract_data.tenant,
            data_product=contract_data.dataProduct,
            description_usage=contract_data.description.usage if contract_data.description else None,
            description_purpose=contract_data.description.purpose if contract_data.description else None,
            description_limitations=contract_data.description.limitations if contract_data.description else None,
            created_by=current_user.username if current_user else None,
            updated_by=current_user.username if current_user else None,
        )
        created = data_contract_repo.create(db=db, obj_in=db_obj)
        
        # Create schema objects and properties if provided
        if contract_data.schema:
            from src.db_models.data_contracts import SchemaObjectDb, SchemaPropertyDb
            for schema_obj_data in contract_data.schema:
                schema_obj = SchemaObjectDb(
                    contract_id=created.id,
                    name=schema_obj_data.name,
                    physical_name=schema_obj_data.physicalName,
                    logical_type='object'
                )
                db.add(schema_obj)
                db.flush()  # Get ID for properties
                
                # Add properties
                for prop_data in schema_obj_data.properties:
                    prop = SchemaPropertyDb(
                        object_id=schema_obj.id,
                        name=prop_data.name,
                        logical_type=prop_data.logicalType,
                        required=prop_data.required or False,
                        unique=prop_data.unique or False,
                        transform_description=prop_data.description
                    )
                    db.add(prop)
        
        db.commit()
        
        # Load with relationships for response
        created_with_relations = data_contract_repo.get_with_all(db, id=created.id)
        return _build_contract_read_from_db(created_with_relations)
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.put('/data-contracts/{contract_id}', response_model=DataContractRead)
async def update_contract(
    contract_id: str,
    db: DBSessionDep,
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
        
        # Load with relationships for full response
        updated_with_relations = data_contract_repo.get_with_all(db, id=contract_id)
        return _build_contract_read_from_db(updated_with_relations)
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
    current_user: AuditCurrentUserDep,
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
    current_user: AuditCurrentUserDep,
    file: UploadFile = File(...),
    manager: DataContractsManager = Depends(get_data_contracts_manager),
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_WRITE)),
):
    """Upload a contract file and parse it into normalized ODCS structure"""
    try:
        content_type = file.content_type
        filename = file.filename or 'uploaded_contract'

        # Determine format from content type or extension
        format = 'json'  # default
        if content_type == 'application/x-yaml' or filename.endswith(('.yaml', '.yml')):
            format = 'yaml'
        elif content_type.startswith('text/'):
            format = 'text'

        # Read file content
        contract_text = (await file.read()).decode('utf-8')

        # Parse structured content (JSON/YAML) or handle text
        parsed: dict | None = None
        try:
            if format == 'yaml':
                parsed = yaml.safe_load(contract_text) or None
            elif format == 'json':
                parsed = json.loads(contract_text) or None
            elif format == 'text':
                # For text format, create a minimal structure
                parsed = {
                    "name": filename.replace('.txt', '').replace('.', '_'),
                    "version": "v1.0",
                    "status": "draft", 
                    "owner": current_user.username if current_user else 'unknown',
                    "description": {
                        "purpose": contract_text[:500] + "..." if len(contract_text) > 500 else contract_text
                    }
                }
        except Exception:
            # If parsing fails, treat as text
            parsed = {
                "name": filename.replace('.', '_'),
                "version": "v1.0", 
                "status": "draft",
                "owner": current_user.username if current_user else 'unknown',
                "description": {
                    "purpose": contract_text[:500] + "..." if len(contract_text) > 500 else contract_text
                }
            }

        if not isinstance(parsed, dict):
            raise HTTPException(status_code=400, detail="Could not parse uploaded file")

        # Extract core contract fields
        name_val = parsed.get('name') or filename.replace('.', '_')
        version_val = parsed.get('version') or 'v1.0'
        status_val = parsed.get('status') or 'draft'
        owner_val = parsed.get('owner') or (current_user.username if current_user else 'unknown')
        kind_val = parsed.get('kind') or 'DataContract'
        api_version_val = parsed.get('apiVersion') or parsed.get('api_version') or 'v3.0.2'
        
        # Extract description fields
        description = parsed.get('description', {})
        if isinstance(description, str):
            description = {"purpose": description}
        elif not isinstance(description, dict):
            description = {}

        # Create main contract record
        db_obj = DataContractDb(
            name=name_val,
            version=version_val,
            status=status_val,
            owner=owner_val,
            kind=kind_val,
            api_version=api_version_val,
            tenant=parsed.get('tenant'),
            data_product=parsed.get('dataProduct') or parsed.get('data_product'),
            description_usage=description.get('usage'),
            description_purpose=description.get('purpose'),
            description_limitations=description.get('limitations'),
            created_by=current_user.username if current_user else None,
            updated_by=current_user.username if current_user else None,
        )
        created = data_contract_repo.create(db=db, obj_in=db_obj)
        
        # Parse and create schema objects if present
        schema_data = parsed.get('schema', [])
        if isinstance(schema_data, list):
            for schema_obj_data in schema_data:
                if not isinstance(schema_obj_data, dict):
                    continue
                    
                schema_obj = SchemaObjectDb(
                    contract_id=created.id,
                    name=schema_obj_data.get('name', 'table'),
                    physical_name=schema_obj_data.get('physicalName') or schema_obj_data.get('physical_name'),
                    logical_type='object'
                )
                db.add(schema_obj)
                db.flush()  # Get ID for properties
                
                # Add properties
                properties = schema_obj_data.get('properties', [])
                if isinstance(properties, list):
                    for prop_data in properties:
                        if not isinstance(prop_data, dict):
                            continue
                        prop = SchemaPropertyDb(
                            object_id=schema_obj.id,
                            name=prop_data.get('name', 'column'),
                            logical_type=prop_data.get('logicalType') or prop_data.get('logical_type', 'string'),
                            required=prop_data.get('required', False),
                            unique=prop_data.get('unique', False),
                            transform_description=prop_data.get('description')
                        )
                        db.add(prop)

        # Parse team members
        team_data = parsed.get('team', [])
        if isinstance(team_data, list):
            for member_data in team_data:
                if not isinstance(member_data, dict):
                    continue
                team_member = DataContractTeamDb(
                    contract_id=created.id,
                    username=member_data.get('email', member_data.get('username', 'unknown')),
                    role=member_data.get('role', 'member'),
                    date_in=member_data.get('dateIn') or member_data.get('date_in'),
                    date_out=member_data.get('dateOut') or member_data.get('date_out'),
                )
                db.add(team_member)

        # Parse support channels
        support_data = parsed.get('support', {})
        if isinstance(support_data, dict):
            for channel, url in support_data.items():
                if url and isinstance(url, str):
                    support_channel = DataContractSupportDb(
                        contract_id=created.id,
                        channel=channel,
                        url=url,
                        description=f"{channel.title()} support channel"
                    )
                    db.add(support_channel)

        # Parse custom properties
        custom_props = parsed.get('customProperties') or parsed.get('custom_properties', {})
        if isinstance(custom_props, dict):
            for key, value in custom_props.items():
                custom_prop = DataContractCustomPropertyDb(
                    contract_id=created.id,
                    property=key,
                    value=str(value) if value is not None else None
                )
                db.add(custom_prop)

        # Parse SLA properties
        sla_data = parsed.get('sla', {})
        if isinstance(sla_data, dict):
            for key, value in sla_data.items():
                if value is not None:
                    sla_prop = DataContractSlaPropertyDb(
                        contract_id=created.id,
                        property=key,
                        value=str(value)
                    )
                    db.add(sla_prop)

        # Parse tags (legacy support)
        tags = parsed.get('tags', [])
        if isinstance(tags, list):
            for tag in tags:
                if isinstance(tag, str):
                    db.add(DataContractTagDb(contract_id=created.id, name=tag))

        # Parse roles (legacy support)
        roles = parsed.get('roles', [])
        if isinstance(roles, list):
            for role_data in roles:
                if isinstance(role_data, dict) and role_data.get('role'):
                    db.add(DataContractRoleDb(
                        contract_id=created.id,
                        role=role_data.get('role'),
                        description=role_data.get('description'),
                        access=role_data.get('access'),
                        first_level_approvers=role_data.get('firstLevelApprovers'),
                        second_level_approvers=role_data.get('secondLevelApprovers')
                    ))

        db.commit()
        
        # Load with relationships for response
        created_with_relations = data_contract_repo.get_with_all(db, id=created.id)
        return _build_contract_read_from_db(created_with_relations)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

# Old document-based export removed - use /data-contracts/{contract_id}/odcs/export instead


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


# ODCS import functionality now handled by /data-contracts/upload endpoint


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
    current_user: AuditCurrentUserDep,
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
    current_user: AuditCurrentUserDep,
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
            tenant=original.tenant,
            data_product=original.data_product,
            description_usage=original.description_usage,
            description_purpose=original.description_purpose,
            description_limitations=original.description_limitations,
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
