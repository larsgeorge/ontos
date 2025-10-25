import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile, Depends, Request, Body
from fastapi.responses import JSONResponse

from src.controller.data_contracts_manager import DataContractsManager
from src.common.dependencies import (
    DBSessionDep,
    AuditManagerDep,
    CurrentUserDep,
    AuditCurrentUserDep,
    NotificationsManagerDep,
)
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
    DataQualityCheckDb,
    DataContractServerDb,
    DataContractServerPropertyDb,
    DataContractAuthoritativeDefinitionDb,
    SchemaObjectAuthoritativeDefinitionDb,
    SchemaObjectCustomPropertyDb,
    DataContractPricingDb,
    DataContractRolePropertyDb,
    DataProfilingRunDb,
    SuggestedQualityCheckDb
)
from src.models.data_contracts_api import (
    DataContractCreate,
    DataContractUpdate,
    DataContractRead,
    DataContractCommentCreate,
    DataContractCommentRead,
)
from src.common.odcs_validation import validate_odcs_contract, ODCSValidationError
from src.common.authorization import PermissionChecker, ApprovalChecker
from src.common.features import FeatureAccessLevel
from src.controller.change_log_manager import change_log_manager
from src.models.notifications import NotificationType, Notification
from src.models.data_asset_reviews import AssetType, ReviewedAssetStatus
from src.common.deployment_dependencies import get_deployment_policy_manager
from src.controller.deployment_policy_manager import DeploymentPolicyManager
from pydantic import BaseModel, Field
import uuid
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

def get_jobs_manager(request: Request):
    """Retrieves the JobsManager instance from app.state."""
    return getattr(request.app.state, 'jobs_manager', None)

 

@router.get('/data-contracts', response_model=list[DataContractRead])
async def get_contracts(
    db: DBSessionDep,
    domain_id: Optional[str] = None,
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_ONLY))
):
    """Get all data contracts with basic ODCS structure"""
    try:
        if domain_id:
            # Filter by domain ID
            contracts = db.query(DataContractDb).filter(DataContractDb.domain_id == domain_id).all()
        else:
            # Get all contracts
            contracts = data_contract_repo.get_multi(db)

        return [
            DataContractRead(
                id=c.id,
                name=c.name,
                version=c.version,
                status=c.status,
                owner_team_id=c.owner_team_id,
                kind=c.kind,
                apiVersion=c.api_version,
                tenant=c.tenant,
                domainId=c.domain_id,  # Include domainId for frontend resolution
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

@router.get('/data-contracts/{contract_id}', response_model=DataContractRead, response_model_by_alias=False)
async def get_contract(contract_id: str, db: DBSessionDep, _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_ONLY))):
    """Get a specific data contract with full ODCS structure"""
    contract = data_contract_repo.get_with_all(db, id=contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    return _build_contract_read_from_db(db, contract)


# --- Lifecycle Transition Endpoints (minimal) ---

@router.post('/data-contracts/{contract_id}/submit')
async def submit_contract(
    contract_id: str,
    request: Request,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: AuditCurrentUserDep,
    manager: DataContractsManager = Depends(get_data_contracts_manager),
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_WRITE)),
):
    try:
        contract = data_contract_repo.get(db, id=contract_id)
        if not contract:
            raise HTTPException(status_code=404, detail="Contract not found")
        from_status = (contract.status or '').lower()
        if from_status != 'draft':
            raise HTTPException(status_code=409, detail=f"Invalid transition from {contract.status} to PROPOSED")
        
        # Business logic now in manager
        updated = manager.transition_status(
            db=db,
            contract_id=contract_id,
            new_status='proposed',
            current_user=current_user.username if current_user else None
        )
        
        # Audit
        audit_manager.log_action(
            db=db,
            username=current_user.username if current_user else 'anonymous',
            ip_address=request.client.host if request.client else None,
            feature='data-contracts',
            action='SUBMIT',
            success=True,
            details={ 'contract_id': contract_id, 'from': from_status, 'to': updated.status }
        )
        return { 'status': updated.status }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Submit contract failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/data-contracts/{contract_id}/approve')
async def approve_contract(
    contract_id: str,
    request: Request,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: AuditCurrentUserDep,
    manager: DataContractsManager = Depends(get_data_contracts_manager),
    _: bool = Depends(ApprovalChecker('CONTRACTS')),
):
    """Approve a contract (PROPOSED/UNDER_REVIEW → APPROVED)."""
    try:
        # Check valid source status
        contract = data_contract_repo.get(db, id=contract_id)
        if not contract:
            raise HTTPException(status_code=404, detail="Contract not found")
        from_status = (contract.status or '').lower()
        if from_status not in ('proposed', 'under_review'):
            raise HTTPException(status_code=409, detail=f"Invalid transition from {contract.status} to APPROVED")
        
        # Business logic now in manager
        updated = manager.transition_status(
            db=db,
            contract_id=contract_id,
            new_status='approved',
            current_user=current_user.username if current_user else None
        )
        
        # Audit
        audit_manager.log_action(
            db=db,
            username=current_user.username if current_user else 'anonymous',
            ip_address=request.client.host if request.client else None,
            feature='data-contracts',
            action='APPROVE',
            success=True,
            details={'contract_id': contract_id, 'from': from_status, 'to': updated.status}
        )
        return {'status': updated.status}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Approve contract failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/data-contracts/{contract_id}/reject')
async def reject_contract(
    contract_id: str,
    request: Request,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: AuditCurrentUserDep,
    manager: DataContractsManager = Depends(get_data_contracts_manager),
    _: bool = Depends(ApprovalChecker('CONTRACTS')),
):
    """Reject a contract (PROPOSED/UNDER_REVIEW → REJECTED)."""
    try:
        # Check valid source status
        contract = data_contract_repo.get(db, id=contract_id)
        if not contract:
            raise HTTPException(status_code=404, detail="Contract not found")
        from_status = (contract.status or '').lower()
        if from_status not in ('proposed', 'under_review'):
            raise HTTPException(status_code=409, detail=f"Invalid transition from {contract.status} to REJECTED")
        
        # Business logic now in manager
        updated = manager.transition_status(
            db=db,
            contract_id=contract_id,
            new_status='rejected',
            current_user=current_user.username if current_user else None
        )
        
        # Audit
        audit_manager.log_action(
            db=db,
            username=current_user.username if current_user else 'anonymous',
            ip_address=request.client.host if request.client else None,
            feature='data-contracts',
            action='REJECT',
            success=True,
            details={'contract_id': contract_id, 'from': from_status, 'to': updated.status}
        )
        return {'status': updated.status}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Reject contract failed")
        raise HTTPException(status_code=500, detail=str(e))


# --- Request Endpoints (for review, publish, deploy) ---

class RequestReviewPayload(BaseModel):
    message: Optional[str] = None

class RequestPublishPayload(BaseModel):
    justification: Optional[str] = None

class RequestDeployPayload(BaseModel):
    catalog: Optional[str] = None
    database_schema: Optional[str] = Field(None, alias="schema")
    message: Optional[str] = None
    
    class Config:
        populate_by_name = True


@router.post('/data-contracts/{contract_id}/request-review')
async def request_steward_review(
    contract_id: str,
    request: Request,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: AuditCurrentUserDep,
    notifications: NotificationsManagerDep,
    payload: RequestReviewPayload = Body(default=RequestReviewPayload()),
    manager: DataContractsManager = Depends(get_data_contracts_manager),
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_WRITE)),
):
    """Request a data steward review for a contract."""
    try:
        # Business logic now in manager
        result = manager.request_steward_review(
            db=db,
            notifications_manager=notifications,
            contract_id=contract_id,
            requester_email=current_user.email,
            message=payload.message,
            current_user=current_user.username if current_user else None
        )
        
        # Audit
        audit_manager.log_action(
            db=db,
            username=current_user.username if current_user else 'anonymous',
            ip_address=request.client.host if request.client else None,
            feature='data-contracts',
            action='REQUEST_REVIEW',
            success=True,
            details={'contract_id': contract_id, 'status': result.get('status')}
        )
        
        return result
        
    except ValueError as e:
        error_status = 404 if "not found" in str(e).lower() else 409
        raise HTTPException(status_code=error_status, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Request review failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/data-contracts/{contract_id}/request-publish')
async def request_publish_to_marketplace(
    contract_id: str,
    request: Request,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: AuditCurrentUserDep,
    notifications: NotificationsManagerDep,
    payload: RequestPublishPayload = Body(default=RequestPublishPayload()),
    manager: DataContractsManager = Depends(get_data_contracts_manager),
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_WRITE)),
):
    """Request to publish an APPROVED contract to the marketplace."""
    try:
        # Business logic now in manager
        result = manager.request_publish(
            db=db,
            notifications_manager=notifications,
            contract_id=contract_id,
            requester_email=current_user.email,
            justification=payload.justification,
            current_user=current_user.username if current_user else None
        )
        
        # Audit
        audit_manager.log_action(
            db=db,
            username=current_user.username if current_user else 'anonymous',
            ip_address=request.client.host if request.client else None,
            feature='data-contracts',
            action='REQUEST_PUBLISH',
            success=True,
            details={'contract_id': contract_id}
        )
        
        return result
        
    except ValueError as e:
        error_status = 404 if "not found" in str(e).lower() else 409
        raise HTTPException(status_code=error_status, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Request publish failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/data-contracts/{contract_id}/request-deploy')
async def request_deploy_to_catalog(
    contract_id: str,
    request: Request,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: AuditCurrentUserDep,
    notifications: NotificationsManagerDep,
    deployment_manager: DeploymentPolicyManager = Depends(get_deployment_policy_manager),
    payload: RequestDeployPayload = Body(default=RequestDeployPayload()),
    manager: DataContractsManager = Depends(get_data_contracts_manager),
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_WRITE)),
):
    """Request approval to deploy a contract to Unity Catalog."""
    try:
        # Business logic now in manager
        result = manager.request_deploy(
            db=db,
            notifications_manager=notifications,
            deployment_manager=deployment_manager,
            current_user_obj=current_user,
            contract_id=contract_id,
            requester_email=current_user.email,
            catalog=payload.catalog,
            database_schema=payload.database_schema,
            message=payload.message,
            current_user=current_user.username if current_user else None
        )
        
        # Audit
        audit_manager.log_action(
            db=db,
            username=current_user.username if current_user else 'anonymous',
            ip_address=request.client.host if request.client else None,
            feature='data-contracts',
            action='REQUEST_DEPLOY',
            success=True,
            details={'contract_id': contract_id, 'catalog': payload.catalog, 'schema': payload.database_schema}
        )
        
        return result
        
    except ValueError as e:
        error_status = 404 if "not found" in str(e).lower() else (403 if "denied" in str(e).lower() or "permission" in str(e).lower() else 409)
        raise HTTPException(status_code=error_status, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Request deploy failed")
        raise HTTPException(status_code=500, detail=str(e))


# --- Handle Request Endpoints (for approvers to respond) ---

class HandleReviewPayload(BaseModel):
    decision: str  # 'approve', 'reject', 'clarify'
    message: Optional[str] = None

class HandlePublishPayload(BaseModel):
    decision: str  # 'approve', 'deny'
    message: Optional[str] = None

class HandleDeployPayload(BaseModel):
    decision: str  # 'approve', 'deny'
    message: Optional[str] = None
    execute_deployment: bool = False  # If true, actually trigger deployment


@router.post('/data-contracts/{contract_id}/handle-review')
async def handle_steward_review_response(
    contract_id: str,
    request: Request,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: AuditCurrentUserDep,
    notifications: NotificationsManagerDep,
    payload: HandleReviewPayload = Body(...),
    manager: DataContractsManager = Depends(get_data_contracts_manager),
    _: bool = Depends(PermissionChecker('data-asset-reviews', FeatureAccessLevel.READ_WRITE)),
):
    """Handle a steward's review decision (approve/reject/clarify)."""
    try:
        # Business logic now in manager
        result = manager.handle_review_response(
            db=db,
            notifications_manager=notifications,
            contract_id=contract_id,
            reviewer_email=current_user.email,
            decision=payload.decision,
            message=payload.message,
            current_user=current_user.username if current_user else None
        )
        
        # Audit
        audit_manager.log_action(
            db=db,
            username=current_user.username if current_user else 'anonymous',
            ip_address=request.client.host if request.client else None,
            feature='data-contracts',
            action=f'REVIEW_{payload.decision.upper()}',
            success=True,
            details={'contract_id': contract_id, 'decision': payload.decision}
        )
        
        return result
        
    except ValueError as e:
        error_status = 404 if "not found" in str(e).lower() else (400 if "must be" in str(e).lower() else 409)
        raise HTTPException(status_code=error_status, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Handle review failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/data-contracts/{contract_id}/handle-publish')
async def handle_publish_request_response(
    contract_id: str,
    request: Request,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: AuditCurrentUserDep,
    notifications: NotificationsManagerDep,
    payload: HandlePublishPayload = Body(...),
    manager: DataContractsManager = Depends(get_data_contracts_manager),
    _: bool = Depends(ApprovalChecker('CONTRACTS')),
):
    """Handle a publish request decision (approve/deny)."""
    try:
        # Business logic now in manager
        result = manager.handle_publish_response(
            db=db,
            notifications_manager=notifications,
            contract_id=contract_id,
            approver_email=current_user.email,
            decision=payload.decision,
            message=payload.message,
            current_user=current_user.username if current_user else None
        )
        
        # Get contract to check published status for audit
        contract = data_contract_repo.get(db, id=contract_id)
        published_status = contract.published if contract else None
        
        # Audit
        audit_manager.log_action(
            db=db,
            username=current_user.username if current_user else 'anonymous',
            ip_address=request.client.host if request.client else None,
            feature='data-contracts',
            action=f'PUBLISH_{payload.decision.upper()}',
            success=True,
            details={'contract_id': contract_id, 'decision': payload.decision, 'published': published_status}
        )
        
        # Add published status to result for backward compatibility
        result["published"] = published_status
        return result
        
    except ValueError as e:
        error_status = 404 if "not found" in str(e).lower() else (400 if "must be" in str(e).lower() else 409)
        raise HTTPException(status_code=error_status, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Handle publish failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/data-contracts/{contract_id}/handle-deploy')
async def handle_deploy_request_response(
    contract_id: str,
    request: Request,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: AuditCurrentUserDep,
    notifications: NotificationsManagerDep,
    payload: HandleDeployPayload = Body(...),
    manager: DataContractsManager = Depends(get_data_contracts_manager),
    _: bool = Depends(PermissionChecker('self-service', FeatureAccessLevel.READ_WRITE)),
):
    """Handle a deployment request decision (approve/deny). Optionally executes deployment."""
    try:
        # Get jobs manager for deployment execution
        jobs_manager = None
        try:
            from src.common.dependencies import get_jobs_manager
            jobs_manager = request.app.state.jobs_manager
        except Exception:
            logger.warning("Jobs manager not available")
        
        # Business logic now in manager
        result = manager.handle_deploy_response(
            db=db,
            notifications_manager=notifications,
            jobs_manager=jobs_manager,
            contract_id=contract_id,
            approver_email=current_user.email,
            decision=payload.decision,
            execute_deployment=payload.execute_deployment,
            message=payload.message,
            current_user=current_user.username if current_user else None
        )
        
        # Audit
        audit_manager.log_action(
            db=db,
            username=current_user.username if current_user else 'anonymous',
            ip_address=request.client.host if request.client else None,
            feature='data-contracts',
            action=f'DEPLOY_{payload.decision.upper()}',
            success=True,
            details={'contract_id': contract_id, 'decision': payload.decision, 'deployed': payload.execute_deployment}
        )
        
        return result
        
    except ValueError as e:
        error_status = 404 if "not found" in str(e).lower() else (400 if "must be" in str(e).lower() else 409)
        raise HTTPException(status_code=error_status, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Handle deploy failed")
        raise HTTPException(status_code=500, detail=str(e))


def _build_contract_read_from_db(db, db_contract) -> DataContractRead:
    """Build DataContractRead from normalized database models"""
    from src.models.data_contracts_api import ContractDescription, SchemaObject, ColumnProperty

    # Resolve domain name from domain_id if available
    domain_name = None
    if db_contract.domain_id:
        try:
            from src.repositories.data_domain_repository import data_domain_repo
            domain = data_domain_repo.get(db, id=db_contract.domain_id)
            if domain:
                domain_name = domain.name
        except Exception as e:
            logger.warning(f"Failed to resolve domain name for domain_id {db_contract.domain_id}: {e}")

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
            # Parse logical type options if available
            options = {}
            if prop.logical_type_options_json:
                try:
                    options = json.loads(prop.logical_type_options_json)
                except:
                    pass

            prop_dict = {
                'name': prop.name,
                'logicalType': prop.logical_type or 'string',
                'required': prop.required,
                'unique': prop.unique,
                'description': prop.transform_description,
                'primaryKeyPosition': prop.primary_key_position,
                'partitionKeyPosition': prop.partition_key_position,
            }

            # Add logical type options to property
            prop_dict.update(options)

            properties.append(ColumnProperty(**prop_dict))

        schema_objects.append(SchemaObject(
            name=schema_obj.name,
            physicalName=schema_obj.physical_name,
            properties=properties
        ))

    # Build team (legacy minimal)
    team = []
    if getattr(db_contract, 'team', None):
        for member in db_contract.team:
            entry = {
                'role': member.role or 'member',
                'email': member.username,
                'name': None,
            }
            if getattr(member, 'description', None):
                entry['description'] = member.description
            team.append(entry)

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

    # Servers (full ODCS mapping)
    servers = []
    if getattr(db_contract, 'servers', None):
        from src.models.data_contracts_api import ServerConfig
        for s in db_contract.servers:
            # Build properties dict from server properties
            properties = {}
            if getattr(s, 'properties', None):
                for prop in s.properties:
                    properties[prop.key] = prop.value

            # Create ServerConfig object
            server_config = ServerConfig(
                server=s.server,
                type=s.type,
                description=s.description,
                environment=s.environment,
                host=properties.get('host'),
                port=int(properties.get('port')) if properties.get('port') else None,
                database=properties.get('database'),
                schema=properties.get('schema'),
                catalog=properties.get('catalog'),
                project=properties.get('project'),
                account=properties.get('account'),
                region=properties.get('region'),
                location=properties.get('location'),
                properties={k: v for k, v in properties.items() if k not in ['host', 'port', 'database', 'schema', 'catalog', 'project', 'account', 'region', 'location']}
            )
            servers.append(server_config)

    # Authoritative definitions
    authoritative_definitions = []
    if getattr(db_contract, 'authoritative_defs', None):
        from src.models.data_contracts_api import AuthoritativeDefinition
        for auth_def in db_contract.authoritative_defs:
            authoritative_definitions.append(AuthoritativeDefinition(
                url=auth_def.url,
                type=auth_def.type
            ))

    # Quality rules
    quality_rules = []
    if hasattr(db_contract, 'schema_objects') and db_contract.schema_objects:
        from src.models.data_contracts_api import QualityRule
        for schema_obj in db_contract.schema_objects:
            if hasattr(schema_obj, 'quality_checks') and schema_obj.quality_checks:
                for check in schema_obj.quality_checks:
                    quality_rules.append(QualityRule(
                        name=check.name,
                        description=check.description,
                        level=check.level,
                        dimension=check.dimension,
                        business_impact=check.business_impact,
                        severity=check.severity,
                        type=check.type,
                        method=check.method,
                        schedule=check.schedule,
                        scheduler=check.scheduler,
                        unit=check.unit,
                        tags=check.tags,
                        rule=check.rule,
                        query=check.query,
                        engine=check.engine,
                        implementation=check.implementation,
                        must_be=check.must_be,
                        must_not_be=check.must_not_be,
                        must_be_gt=check.must_be_gt,
                        must_be_ge=check.must_be_ge,
                        must_be_lt=check.must_be_lt,
                        must_be_le=check.must_be_le,
                        must_be_between_min=check.must_be_between_min,
                        must_be_between_max=check.must_be_between_max
                    ))

    logger.info(f"[DEBUG SERIALIZE] Building response for contract {db_contract.id}")
    logger.info(f"[DEBUG SERIALIZE] db_contract.owner_team_id = {db_contract.owner_team_id}")
    
    result = DataContractRead(
        id=db_contract.id,
        name=db_contract.name,
        version=db_contract.version,
        status=db_contract.status,
        published=db_contract.published if hasattr(db_contract, 'published') else False,
        owner_team_id=db_contract.owner_team_id,
        kind=db_contract.kind,
        apiVersion=db_contract.api_version,
        tenant=db_contract.tenant,
        domain=domain_name,  # Resolved domain name
        domainId=db_contract.domain_id,  # Provide domain ID for frontend resolution
        dataProduct=db_contract.data_product,
        description=description,
        schema=schema_objects,
        team=team,
        support=support,
        customProperties=custom_properties,
        sla=sla,
        servers=servers,
        authoritativeDefinitions=authoritative_definitions,
        qualityRules=quality_rules,
        created=db_contract.created_at.isoformat() if db_contract.created_at else None,
        updated=db_contract.updated_at.isoformat() if db_contract.updated_at else None,
    )
    
    logger.info(f"[DEBUG SERIALIZE] result.owner_team_id = {result.owner_team_id}")
    logger.info(f"[DEBUG SERIALIZE] result.model_dump() owner_team_id = {result.model_dump().get('owner_team_id')}")
    
    return result


@router.post('/data-contracts', response_model=DataContractRead)
async def create_contract(
    request: Request,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: AuditCurrentUserDep,
    contract_data: DataContractCreate = Body(...),
    manager: DataContractsManager = Depends(get_data_contracts_manager),
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_WRITE)),
):
    """Create a new data contract with normalized ODCS structure"""
    success = False
    details_for_audit = {
        "params": {"contract_name": contract_data.name if contract_data.name else "N/A"},
    }
    created_contract_id = None

    try:
        # Business logic now in manager
        created = manager.create_contract_with_relations(
            db=db,
            contract_data=contract_data,
            current_user=current_user.username if current_user else None
        )
        
        success = True
        created_contract_id = created.id

        # Load with relationships for response
        created_with_relations = data_contract_repo.get_with_all(db, id=created.id)
        return _build_contract_read_from_db(db, created_with_relations)

    except ValueError as e:
        details_for_audit["exception"] = {"type": "ValueError", "message": str(e)}
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException as http_exc:
        details_for_audit["exception"] = {"type": "HTTPException", "status_code": http_exc.status_code, "detail": http_exc.detail}
        raise
    except Exception as e:
        details_for_audit["exception"] = {"type": type(e).__name__, "message": str(e)}
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if created_contract_id:
            details_for_audit["created_resource_id"] = created_contract_id
        audit_manager.log_action(
            db=db,
            username=current_user.username if current_user else "anonymous",
            ip_address=request.client.host if request.client else None,
            feature="data-contracts",
            action="CREATE",
            success=success,
            details=details_for_audit
        )

@router.put('/data-contracts/{contract_id}', response_model=DataContractRead, response_model_by_alias=False)
async def update_contract(
    contract_id: str,
    request: Request,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: AuditCurrentUserDep,
    contract_data: DataContractUpdate = Body(...),
    manager: DataContractsManager = Depends(get_data_contracts_manager),
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_WRITE))
):
    """Update a data contract"""
    logger.info(f"[DEBUG UPDATE] Received update for contract {contract_id}")
    logger.info(f"[DEBUG UPDATE] contract_data.owner_team_id = {contract_data.owner_team_id}")
    logger.info(f"[DEBUG UPDATE] contract_data dict = {contract_data.model_dump()}")
    success = False
    details_for_audit = {
        "params": {"contract_id": contract_id},
    }

    try:
        # Check project membership if contract belongs to a project
        db_obj = data_contract_repo.get(db, id=contract_id)
        if not db_obj:
            raise HTTPException(status_code=404, detail="Contract not found")
            
        if db_obj.project_id:
            from src.controller.projects_manager import projects_manager
            from src.common.config import get_settings
            user_groups = current_user.groups or []
            settings = get_settings()
            is_member = projects_manager.is_user_project_member(
                db=db,
                user_identifier=current_user.email,
                user_groups=user_groups,
                project_id=db_obj.project_id,
                settings=settings
            )
            if not is_member:
                raise HTTPException(
                    status_code=403, 
                    detail="You must be a member of the project to edit this contract"
                )

        # Business logic now in manager
        updated = manager.update_contract_with_relations(
            db=db,
            contract_id=contract_id,
            contract_data=contract_data,
            current_user=current_user.username if current_user else None
        )

        success = True

        # Load with relationships for full response
        updated_with_relations = data_contract_repo.get_with_all(db, id=contract_id)
        return _build_contract_read_from_db(db, updated_with_relations)

    except ValueError as e:
        details_for_audit["exception"] = {"type": "ValueError", "message": str(e)}
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException as http_exc:
        details_for_audit["exception"] = {"type": "HTTPException", "status_code": http_exc.status_code, "detail": http_exc.detail}
        raise
    except Exception as e:
        error_msg = f"Error updating data contract {contract_id}: {e!s}"
        logger.error(error_msg)
        details_for_audit["exception"] = {"type": type(e).__name__, "message": str(e)}
        raise HTTPException(status_code=500, detail=error_msg)
    finally:
        if success:
            details_for_audit["updated_resource_id"] = contract_id
        audit_manager.log_action(
            db=db,
            username=current_user.username if current_user else "anonymous",
            ip_address=request.client.host if request.client else None,
            feature="data-contracts",
            action="UPDATE",
            success=success,
            details=details_for_audit
        )

@router.delete('/data-contracts/{contract_id}', status_code=204)
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
    success = False
    response_status_code = 500
    details_for_audit = {
        "params": {"contract_id": contract_id}
    }
    try:
        db_obj = data_contract_repo.get(db, id=contract_id)
        if not db_obj:
            response_status_code = 404
            exc = HTTPException(status_code=response_status_code, detail="Contract not found")
            details_for_audit["exception"] = {"type": "HTTPException", "status_code": exc.status_code, "detail": exc.detail}
            raise exc
        data_contract_repo.remove(db=db, id=contract_id)
        db.commit()
        success = True
        response_status_code = 204
        return None
    except HTTPException:
        raise
    except Exception as e:
        success = False
        response_status_code = 500
        error_msg = f"Error deleting data contract {contract_id}: {e!s}"
        details_for_audit["exception"] = {"type": type(e).__name__, "message": str(e)}
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)
    finally:
        if "exception" not in details_for_audit:
            details_for_audit["response_status_code"] = response_status_code
        details_for_audit["deleted_resource_id_attempted"] = contract_id
        audit_manager.log_action(
            db=db,
            username=current_user.username if current_user else "anonymous",
            ip_address=request.client.host if request.client else None,
            feature="data-contracts",
            action="DELETE",
            success=success,
            details=details_for_audit,
        )

@router.post('/data-contracts/upload')
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
    success = False
    details_for_audit = {
        "params": {"filename": file.filename if file.filename else "N/A"},
    }
    created_contract_id = None

    try:
        # Read file content
        contract_text = (await file.read()).decode('utf-8')
        
        # Parse file using manager
        parsed = manager.parse_uploaded_file(
            file_content=contract_text,
            filename=file.filename or 'uploaded_contract',
            content_type=file.content_type or 'application/json'
        )
        
        # Validate ODCS (optional, log warnings)
        validation_warnings = manager.validate_odcs(parsed, strict=False)
        for warning in validation_warnings[:5]:
            logger.warning(warning)
        
        # Create contract with all nested entities using manager
        created = manager.create_from_upload(
            db=db,
            parsed_odcs=parsed,
            current_user=current_user.username if current_user else None
        )
        
        success = True
        created_contract_id = created.id

        # Load with relationships for response
        created_with_relations = data_contract_repo.get_with_all(db, id=created.id)
        return _build_contract_read_from_db(db, created_with_relations)

    except ValueError as e:
        details_for_audit["exception"] = {"type": "ValueError", "message": str(e)}
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException as http_exc:
        details_for_audit["exception"] = {"type": "HTTPException", "status_code": http_exc.status_code, "detail": http_exc.detail}
        raise
    except Exception as e:
        details_for_audit["exception"] = {"type": type(e).__name__, "message": str(e)}
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
    finally:
        if created_contract_id:
            details_for_audit["created_resource_id"] = created_contract_id
        audit_manager.log_action(
            db=db,
            username=current_user.username if current_user else "anonymous",
            ip_address=request.client.host if request.client else None,
            feature="data-contracts",
            action="UPLOAD",
            success=success,
            details=details_for_audit
        )

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
        from fastapi.responses import Response

        db_obj = data_contract_repo.get_with_all(db, id=contract_id)
        if not db_obj:
            raise HTTPException(status_code=404, detail="Contract not found")
        odcs = manager.build_odcs_from_db(db_obj, db)

        # Convert to YAML format for ODCS compliance
        yaml_content = yaml.dump(odcs, default_flow_style=False, allow_unicode=True, sort_keys=False)
        filename = f"{(db_obj.name or 'contract').lower().replace(' ', '_')}-odcs.yaml"

        return Response(
            content=yaml_content,
            media_type='application/x-yaml',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Content-Type': 'application/x-yaml; charset=utf-8'
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post('/data-contracts/{contract_id}/comments', response_model=dict)
async def add_comment(
    contract_id: str,
    request: Request,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: AuditCurrentUserDep,
    payload: DataContractCommentCreate = Body(...),
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_WRITE))
):
    success = False
    response_status_code = 500
    details_for_audit = {
        "params": {"contract_id": contract_id},
    }
    try:
        if not data_contract_repo.get(db, id=contract_id):
            response_status_code = 404
            exc = HTTPException(status_code=response_status_code, detail="Contract not found")
            details_for_audit["exception"] = {"type": "HTTPException", "status_code": exc.status_code, "detail": exc.detail}
            raise exc
        message = payload.message
        if not message:
            response_status_code = 400
            exc = HTTPException(status_code=response_status_code, detail="message is required")
            details_for_audit["exception"] = {"type": "HTTPException", "status_code": exc.status_code, "detail": exc.detail}
            raise exc
        db.add(DataContractCommentDb(contract_id=contract_id, author=current_user.username if current_user else 'anonymous', message=message))
        db.commit()
        success = True
        response_status_code = 200
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        success = False
        response_status_code = 500
        details_for_audit["exception"] = {"type": type(e).__name__, "message": str(e)}
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if "exception" not in details_for_audit:
            details_for_audit["response_status_code"] = response_status_code
        audit_manager.log_action(
            db=db,
            username=current_user.username if current_user else "anonymous",
            ip_address=request.client.host if request.client else None,
            feature="data-contracts",
            action="COMMENT",
            success=success,
            details=details_for_audit,
        )


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
async def create_version(
    contract_id: str,
    request: Request,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: AuditCurrentUserDep,
    payload: dict = Body(...),
    manager: DataContractsManager = Depends(get_data_contracts_manager),
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_WRITE))
):
    """Create a new version of a contract (lightweight, metadata only)."""
    success = False
    response_status_code = 500
    details_for_audit = {"params": {"contract_id": contract_id}}
    
    try:
        new_version = payload.get('new_version')
        if not new_version:
            response_status_code = 400
            raise HTTPException(status_code=400, detail="new_version is required")
        
        # Business logic now in manager
        clone = manager.create_new_version(
            db=db,
            contract_id=contract_id,
            new_version=new_version,
            current_user=current_user.username if current_user else None
        )
        
        success = True
        response_status_code = 201
        return {
            "id": clone.id,
            "name": clone.name,
            "version": clone.version,
            "status": clone.status,
            "owner_team_id": clone.owner_team_id
        }
    except ValueError as e:
        response_status_code = 404 if "not found" in str(e).lower() else 400
        details_for_audit["exception"] = {"type": "ValueError", "message": str(e)}
        raise HTTPException(status_code=response_status_code, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        response_status_code = 500
        details_for_audit["exception"] = {"type": type(e).__name__, "message": str(e)}
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if "exception" not in details_for_audit:
            details_for_audit["response_status_code"] = response_status_code
        if success:
            details_for_audit["created_version_for_contract_id"] = contract_id
        audit_manager.log_action(
            db=db,
            username=current_user.username if current_user else "anonymous",
            ip_address=request.client.host if request.client else None,
            feature="data-contracts",
            action="VERSION",
            success=success,
            details=details_for_audit,
        )

# DQX Profiling endpoints

@router.post('/data-contracts/{contract_id}/profile')
async def start_profiling(
    contract_id: str,
    request: Request,
    db: DBSessionDep,
    current_user: AuditCurrentUserDep,
    payload: dict = Body(...),
    manager: DataContractsManager = Depends(get_data_contracts_manager),
    jobs_manager = Depends(get_jobs_manager),
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_WRITE))
):
    """Start DQX profiling for selected schemas in a contract."""
    try:
        result = manager.start_profiling(
            db=db,
            contract_id=contract_id,
            schema_names=payload.get('schema_names', []),
            triggered_by=current_user.username if current_user else 'unknown',
            jobs_manager=jobs_manager
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to start profiling: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/data-contracts/{contract_id}/profile-runs')
async def get_profile_runs(
    contract_id: str,
    db: DBSessionDep,
    manager: DataContractsManager = Depends(get_data_contracts_manager),
    jobs_manager = Depends(get_jobs_manager),
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_ONLY))
):
    """Get profiling runs for a contract with suggestion counts."""
    try:
        result = manager.get_profile_runs(
            db=db,
            contract_id=contract_id,
            jobs_manager=jobs_manager
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get profile runs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/data-contracts/{contract_id}/profile-runs/{run_id}/suggestions')
async def get_suggestions(
    contract_id: str,
    run_id: str,
    db: DBSessionDep,
    manager: DataContractsManager = Depends(get_data_contracts_manager),
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_ONLY))
):
    """Get quality check suggestions for a profiling run."""
    try:
        result = manager.get_profile_suggestions(
            db=db,
            contract_id=contract_id,
            run_id=run_id
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get suggestions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/data-contracts/{contract_id}/suggestions/accept')
async def accept_suggestions(
    contract_id: str,
    request: Request,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: AuditCurrentUserDep,
    payload: dict = Body(...),
    manager: DataContractsManager = Depends(get_data_contracts_manager),
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_WRITE))
):
    """Accept quality check suggestions and add them to the contract."""
    try:
        result = manager.accept_suggestions(
            db=db,
            contract_id=contract_id,
            suggestion_ids=payload.get('suggestion_ids', []),
            bump_version=payload.get('bump_version'),
            current_user=current_user.username if current_user else 'anonymous',
            audit_manager=audit_manager
        )
        
        # Update audit log with IP address (manager doesn't have access to request)
        if audit_manager and request.client:
            # The audit log was already created in the manager, just noting this for future reference
            pass
        
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to accept suggestions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put('/data-contracts/{contract_id}/suggestions/{suggestion_id}')
async def update_suggestion(
    contract_id: str,
    suggestion_id: str,
    db: DBSessionDep,
    payload: dict = Body(...),
    manager: DataContractsManager = Depends(get_data_contracts_manager),
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_WRITE))
):
    """Update a quality check suggestion (for editing before acceptance)."""
    try:
        result = manager.update_suggestion(
            db=db,
            contract_id=contract_id,
            suggestion_id=suggestion_id,
            updates=payload
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update suggestion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/data-contracts/{contract_id}/suggestions/reject')
async def reject_suggestions(
    contract_id: str,
    request: Request,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: AuditCurrentUserDep,
    payload: dict = Body(...),
    manager: DataContractsManager = Depends(get_data_contracts_manager),
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_WRITE))
):
    """Reject quality check suggestions."""
    try:
        result = manager.reject_suggestions(
            db=db,
            contract_id=contract_id,
            suggestion_ids=payload.get('suggestion_ids', []),
            current_user=current_user.username if current_user else 'anonymous',
            audit_manager=audit_manager
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to reject suggestions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ===== Custom Properties CRUD Endpoints =====

@router.get('/data-contracts/{contract_id}/custom-properties', response_model=List[dict])
async def get_custom_properties(
    contract_id: str,
    db: DBSessionDep,
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_ONLY))
):
    """Get all custom properties for a contract."""
    from src.repositories.data_contracts_repository import custom_property_repo
    from src.models.data_contracts_api import CustomPropertyRead

    contract = data_contract_repo.get(db, id=contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    try:
        properties = custom_property_repo.get_by_contract(db=db, contract_id=contract_id)
        return [CustomPropertyRead.model_validate(prop).model_dump() for prop in properties]
    except Exception as e:
        logger.error(f"Error fetching custom properties: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/data-contracts/{contract_id}/custom-properties', response_model=dict, status_code=201)
async def create_custom_property(
    contract_id: str,
    request: Request,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: AuditCurrentUserDep,
    prop_data: dict = Body(...),
    manager: DataContractsManager = Depends(get_data_contracts_manager),
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_WRITE))
):
    """Create a custom property."""
    from src.models.data_contracts_api import CustomPropertyCreate, CustomPropertyRead

    try:
        prop_create = CustomPropertyCreate(**prop_data)
        
        # Business logic now in manager
        new_prop = manager.create_custom_property(
            db=db,
            contract_id=contract_id,
            property_data={"property": prop_create.property, "value": prop_create.value}
        )

        audit_manager.log_action(
            db=db,
            username=current_user.username if current_user else "anonymous",
            ip_address=request.client.host if request.client else None,
            feature="data-contracts",
            action="CREATE_CUSTOM_PROPERTY",
            success=True,
            details={"contract_id": contract_id, "property": prop_create.property}
        )

        return CustomPropertyRead.model_validate(new_prop).model_dump()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating custom property: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put('/data-contracts/{contract_id}/custom-properties/{property_id}', response_model=dict)
async def update_custom_property(
    contract_id: str,
    property_id: str,
    request: Request,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: AuditCurrentUserDep,
    prop_data: dict = Body(...),
    manager: DataContractsManager = Depends(get_data_contracts_manager),
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_WRITE))
):
    """Update a custom property."""
    from src.models.data_contracts_api import CustomPropertyRead

    try:
        # Business logic now in manager
        updated_prop = manager.update_custom_property(
            db=db,
            contract_id=contract_id,
            property_id=property_id,
            property_data=prop_data
        )

        audit_manager.log_action(
            db=db,
            username=current_user.username if current_user else "anonymous",
            ip_address=request.client.host if request.client else None,
            feature="data-contracts",
            action="UPDATE_CUSTOM_PROPERTY",
            success=True,
            details={"contract_id": contract_id, "property_id": property_id}
        )

        return CustomPropertyRead.model_validate(updated_prop).model_dump()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating custom property: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete('/data-contracts/{contract_id}/custom-properties/{property_id}', status_code=204)
async def delete_custom_property(
    contract_id: str,
    property_id: str,
    request: Request,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: AuditCurrentUserDep,
    manager: DataContractsManager = Depends(get_data_contracts_manager),
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_WRITE))
):
    """Delete a custom property."""
    try:
        # Business logic now in manager
        manager.delete_custom_property(
            db=db,
            contract_id=contract_id,
            property_id=property_id
        )

        audit_manager.log_action(
            db=db,
            username=current_user.username if current_user else "anonymous",
            ip_address=request.client.host if request.client else None,
            feature="data-contracts",
            action="DELETE_CUSTOM_PROPERTY",
            success=True,
            details={"contract_id": contract_id, "property_id": property_id}
        )

        return None
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting custom property: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ===== Support Channels CRUD Endpoints (ODCS support[]) =====

@router.get('/data-contracts/{contract_id}/support', response_model=List[dict])
async def get_support_channels(
    contract_id: str,
    db: DBSessionDep,
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_ONLY))
):
    """Get all support channels for a contract."""
    from src.repositories.data_contracts_repository import support_channel_repo
    from src.models.data_contracts_api import SupportChannelRead

    contract = data_contract_repo.get(db, id=contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    try:
        channels = support_channel_repo.get_by_contract(db=db, contract_id=contract_id)
        return [SupportChannelRead.model_validate(ch).model_dump() for ch in channels]
    except Exception as e:
        logger.error(f"Error fetching support channels: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/data-contracts/{contract_id}/support', response_model=dict, status_code=201)
async def create_support_channel(
    contract_id: str,
    request: Request,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: AuditCurrentUserDep,
    channel_data: dict = Body(...),
    manager: DataContractsManager = Depends(get_data_contracts_manager),
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_WRITE))
):
    """Create a new support channel for a contract."""
    from src.models.data_contracts_api import SupportChannelRead

    try:
        # Business logic now in manager
        new_channel = manager.create_support_channel(
            db=db,
            contract_id=contract_id,
            channel_data=channel_data
        )

        # Audit log
        await audit_manager.log_event(
            db=db,
            user_email=current_user,
            entity_type="data_contract",
            entity_id=contract_id,
            action="CREATE_SUPPORT_CHANNEL",
            success=True,
            details={"channel_id": new_channel.id, "channel": new_channel.channel}
        )

        return SupportChannelRead.model_validate(new_channel).model_dump()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating support channel: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put('/data-contracts/{contract_id}/support/{channel_id}', response_model=dict)
async def update_support_channel(
    contract_id: str,
    channel_id: str,
    request: Request,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: AuditCurrentUserDep,
    channel_data: dict = Body(...),
    manager: DataContractsManager = Depends(get_data_contracts_manager),
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_WRITE))
):
    """Update a support channel."""
    from src.models.data_contracts_api import SupportChannelRead

    try:
        # Business logic now in manager
        updated_channel = manager.update_support_channel(
            db=db,
            contract_id=contract_id,
            channel_id=channel_id,
            channel_data=channel_data
        )

        # Audit log
        await audit_manager.log_event(
            db=db,
            user_email=current_user,
            entity_type="data_contract",
            entity_id=contract_id,
            action="UPDATE_SUPPORT_CHANNEL",
            success=True,
            details={"channel_id": channel_id}
        )

        return SupportChannelRead.model_validate(updated_channel).model_dump()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating support channel: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete('/data-contracts/{contract_id}/support/{channel_id}', status_code=204)
async def delete_support_channel(
    contract_id: str,
    channel_id: str,
    request: Request,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: AuditCurrentUserDep,
    manager: DataContractsManager = Depends(get_data_contracts_manager),
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_WRITE))
):
    """Delete a support channel."""
    try:
        # Business logic now in manager
        manager.delete_support_channel(
            db=db,
            contract_id=contract_id,
            channel_id=channel_id
        )

        # Audit log
        await audit_manager.log_event(
            db=db,
            user_email=current_user,
            entity_type="data_contract",
            entity_id=contract_id,
            action="DELETE_SUPPORT_CHANNEL",
            success=True,
            details={"contract_id": contract_id, "channel_id": channel_id}
        )

        return None
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting support channel: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ===== Pricing Endpoints (ODCS price) - Singleton Pattern =====

@router.get('/data-contracts/{contract_id}/pricing', response_model=dict)
async def get_pricing(
    contract_id: str,
    db: DBSessionDep,
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_ONLY))
):
    """Get pricing for a contract (returns empty object if not set)."""
    from src.repositories.data_contracts_repository import pricing_repo
    from src.models.data_contracts_api import PricingRead

    contract = data_contract_repo.get(db, id=contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    try:
        pricing = pricing_repo.get_pricing(db=db, contract_id=contract_id)
        if pricing:
            return PricingRead.model_validate(pricing).model_dump()
        else:
            # Return empty pricing structure
            return {
                "id": None,
                "contract_id": contract_id,
                "price_amount": None,
                "price_currency": None,
                "price_unit": None
            }
    except Exception as e:
        logger.error(f"Error fetching pricing: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put('/data-contracts/{contract_id}/pricing', response_model=dict)
async def update_pricing(
    contract_id: str,
    request: Request,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: AuditCurrentUserDep,
    pricing_data: dict = Body(...),
    manager: DataContractsManager = Depends(get_data_contracts_manager),
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_WRITE))
):
    """Update pricing for a contract (creates if not exists - singleton pattern)."""
    from src.models.data_contracts_api import PricingRead

    try:
        # Business logic now in manager
        updated_pricing = manager.update_pricing(
            db=db,
            contract_id=contract_id,
            pricing_data=pricing_data
        )

        # Audit log
        await audit_manager.log_event(
            db=db,
            user_email=current_user,
            entity_type="data_contract",
            entity_id=contract_id,
            action="UPDATE_PRICING",
            success=True,
            details={
                "price_amount": pricing_data.get("price_amount"),
                "price_currency": pricing_data.get("price_currency"),
                "price_unit": pricing_data.get("price_unit")
            }
        )

        return PricingRead.model_validate(updated_pricing).model_dump()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating pricing: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ===== Roles CRUD Endpoints (ODCS roles[]) - With Nested Properties =====

@router.get('/data-contracts/{contract_id}/roles', response_model=List[dict])
async def get_roles(
    contract_id: str,
    db: DBSessionDep,
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_ONLY))
):
    """Get all roles for a contract (with nested properties)."""
    from src.repositories.data_contracts_repository import role_repo
    from src.models.data_contracts_api import RoleRead

    contract = data_contract_repo.get(db, id=contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    try:
        roles = role_repo.get_by_contract(db=db, contract_id=contract_id)
        return [RoleRead.model_validate(r).model_dump() for r in roles]
    except Exception as e:
        logger.error(f"Error fetching roles: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/data-contracts/{contract_id}/roles', response_model=dict, status_code=201)
async def create_role(
    contract_id: str,
    request: Request,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: AuditCurrentUserDep,
    role_data: dict = Body(...),
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_WRITE))
):
    """Create a new role for a contract (with optional nested properties)."""
    from src.repositories.data_contracts_repository import role_repo
    from src.models.data_contracts_api import RoleCreate, RoleRead

    contract = data_contract_repo.get(db, id=contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    try:
        # Validate input
        role_create = RoleCreate(**role_data)

        # Convert nested properties to dict format
        custom_props = None
        if role_create.custom_properties:
            custom_props = [prop.model_dump() for prop in role_create.custom_properties]

        # Create role with nested properties
        new_role = role_repo.create_role(
            db=db,
            contract_id=contract_id,
            role=role_create.role,
            description=role_create.description,
            access=role_create.access,
            first_level_approvers=role_create.first_level_approvers,
            second_level_approvers=role_create.second_level_approvers,
            custom_properties=custom_props
        )

        db.commit()

        # Audit log
        await audit_manager.log_event(
            db=db,
            user_email=current_user,
            entity_type="data_contract",
            entity_id=contract_id,
            action="CREATE_ROLE",
            success=True,
            details={"role_id": new_role.id, "role": new_role.role}
        )

        return RoleRead.model_validate(new_role).model_dump()
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating role: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put('/data-contracts/{contract_id}/roles/{role_id}', response_model=dict)
async def update_role(
    contract_id: str,
    role_id: str,
    request: Request,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: AuditCurrentUserDep,
    role_data: dict = Body(...),
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_WRITE))
):
    """Update a role (replaces nested properties if provided)."""
    from src.repositories.data_contracts_repository import role_repo
    from src.models.data_contracts_api import RoleUpdate, RoleRead

    contract = data_contract_repo.get(db, id=contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    try:
        # Validate input
        role_update = RoleUpdate(**role_data)

        # Convert nested properties to dict format
        custom_props = None
        if role_update.custom_properties is not None:
            custom_props = [prop.model_dump() for prop in role_update.custom_properties]

        # Update role
        updated_role = role_repo.update_role(
            db=db,
            role_id=role_id,
            role=role_update.role,
            description=role_update.description,
            access=role_update.access,
            first_level_approvers=role_update.first_level_approvers,
            second_level_approvers=role_update.second_level_approvers,
            custom_properties=custom_props
        )

        if not updated_role:
            raise HTTPException(status_code=404, detail="Role not found")

        db.commit()

        # Audit log
        await audit_manager.log_event(
            db=db,
            user_email=current_user,
            entity_type="data_contract",
            entity_id=contract_id,
            action="UPDATE_ROLE",
            success=True,
            details={"role_id": role_id}
        )

        return RoleRead.model_validate(updated_role).model_dump()
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating role: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete('/data-contracts/{contract_id}/roles/{role_id}', status_code=204)
async def delete_role(
    contract_id: str,
    role_id: str,
    request: Request,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: AuditCurrentUserDep,
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_WRITE))
):
    """Delete a role (cascade deletes nested properties)."""
    from src.repositories.data_contracts_repository import role_repo

    contract = data_contract_repo.get(db, id=contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    try:
        deleted = role_repo.delete_role(db=db, role_id=role_id)

        if not deleted:
            raise HTTPException(status_code=404, detail="Role not found")

        db.commit()

        # Audit log
        await audit_manager.log_event(
            db=db,
            user_email=current_user,
            entity_type="data_contract",
            entity_id=contract_id,
            action="DELETE_ROLE",
            success=True,
            details={"contract_id": contract_id, "role_id": role_id}
        )

        return None
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting role: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ===== Contract-Level Authoritative Definitions CRUD (ODCS authoritativeDefinitions[]) =====

@router.get('/data-contracts/{contract_id}/authoritative-definitions', response_model=List[dict])
async def get_contract_authoritative_definitions(
    contract_id: str,
    db: DBSessionDep,
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_ONLY))
):
    """Get all authoritative definitions for a contract."""
    from src.repositories.data_contracts_repository import contract_authoritative_definition_repo
    from src.models.data_contracts_api import AuthoritativeDefinitionRead

    contract = data_contract_repo.get(db, id=contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    try:
        definitions = contract_authoritative_definition_repo.get_by_contract(db=db, contract_id=contract_id)
        return [AuthoritativeDefinitionRead.model_validate(d).model_dump() for d in definitions]
    except Exception as e:
        logger.error(f"Error fetching contract authoritative definitions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/data-contracts/{contract_id}/authoritative-definitions', response_model=dict, status_code=201)
async def create_contract_authoritative_definition(
    contract_id: str,
    request: Request,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: AuditCurrentUserDep,
    definition_data: dict = Body(...),
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_WRITE))
):
    """Create an authoritative definition for a contract."""
    from src.repositories.data_contracts_repository import contract_authoritative_definition_repo
    from src.models.data_contracts_api import AuthoritativeDefinitionCreate, AuthoritativeDefinitionRead

    contract = data_contract_repo.get(db, id=contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    try:
        definition_create = AuthoritativeDefinitionCreate(**definition_data)
        new_definition = contract_authoritative_definition_repo.create_definition(
            db=db, contract_id=contract_id, url=definition_create.url, type=definition_create.type
        )
        db.commit()

        await audit_manager.log_event(
            db=db, user_email=current_user, entity_type="data_contract", entity_id=contract_id,
            action="CREATE_AUTHORITATIVE_DEFINITION", success=True,
            details={"definition_id": new_definition.id, "url": new_definition.url}
        )

        return AuthoritativeDefinitionRead.model_validate(new_definition).model_dump()
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating contract authoritative definition: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put('/data-contracts/{contract_id}/authoritative-definitions/{definition_id}', response_model=dict)
async def update_contract_authoritative_definition(
    contract_id: str,
    definition_id: str,
    request: Request,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: AuditCurrentUserDep,
    definition_data: dict = Body(...),
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_WRITE))
):
    """Update an authoritative definition."""
    from src.repositories.data_contracts_repository import contract_authoritative_definition_repo
    from src.models.data_contracts_api import AuthoritativeDefinitionUpdate, AuthoritativeDefinitionRead

    contract = data_contract_repo.get(db, id=contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    try:
        definition_update = AuthoritativeDefinitionUpdate(**definition_data)
        updated_definition = contract_authoritative_definition_repo.update_definition(
            db=db, definition_id=definition_id, url=definition_update.url, type=definition_update.type
        )

        if not updated_definition:
            raise HTTPException(status_code=404, detail="Authoritative definition not found")

        db.commit()

        await audit_manager.log_event(
            db=db, user_email=current_user, entity_type="data_contract", entity_id=contract_id,
            action="UPDATE_AUTHORITATIVE_DEFINITION", success=True,
            details={"definition_id": definition_id}
        )

        return AuthoritativeDefinitionRead.model_validate(updated_definition).model_dump()
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating contract authoritative definition: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete('/data-contracts/{contract_id}/authoritative-definitions/{definition_id}', status_code=204)
async def delete_contract_authoritative_definition(
    contract_id: str,
    definition_id: str,
    request: Request,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: AuditCurrentUserDep,
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_WRITE))
):
    """Delete an authoritative definition."""
    from src.repositories.data_contracts_repository import contract_authoritative_definition_repo

    contract = data_contract_repo.get(db, id=contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    try:
        deleted = contract_authoritative_definition_repo.delete_definition(db=db, definition_id=definition_id)

        if not deleted:
            raise HTTPException(status_code=404, detail="Authoritative definition not found")

        db.commit()

        await audit_manager.log_event(
            db=db, user_email=current_user, entity_type="data_contract", entity_id=contract_id,
            action="DELETE_AUTHORITATIVE_DEFINITION", success=True,
            details={"contract_id": contract_id, "definition_id": definition_id}
        )

        return None
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting contract authoritative definition: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ===== Schema-Level Authoritative Definitions CRUD =====

@router.get('/data-contracts/{contract_id}/schemas/{schema_id}/authoritative-definitions', response_model=List[dict])
async def get_schema_authoritative_definitions(
    contract_id: str,
    schema_id: str,
    db: DBSessionDep,
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_ONLY))
):
    """Get all authoritative definitions for a schema object."""
    from src.repositories.data_contracts_repository import schema_authoritative_definition_repo
    from src.models.data_contracts_api import AuthoritativeDefinitionRead

    contract = data_contract_repo.get(db, id=contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    try:
        definitions = schema_authoritative_definition_repo.get_by_schema(db=db, schema_id=schema_id)
        return [AuthoritativeDefinitionRead.model_validate(d).model_dump() for d in definitions]
    except Exception as e:
        logger.error(f"Error fetching schema authoritative definitions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/data-contracts/{contract_id}/schemas/{schema_id}/authoritative-definitions', response_model=dict, status_code=201)
async def create_schema_authoritative_definition(
    contract_id: str,
    schema_id: str,
    request: Request,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: AuditCurrentUserDep,
    definition_data: dict = Body(...),
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_WRITE))
):
    """Create an authoritative definition for a schema object."""
    from src.repositories.data_contracts_repository import schema_authoritative_definition_repo
    from src.models.data_contracts_api import AuthoritativeDefinitionCreate, AuthoritativeDefinitionRead

    contract = data_contract_repo.get(db, id=contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    try:
        definition_create = AuthoritativeDefinitionCreate(**definition_data)
        new_definition = schema_authoritative_definition_repo.create_definition(
            db=db, schema_id=schema_id, url=definition_create.url, type=definition_create.type
        )
        db.commit()

        await audit_manager.log_event(
            db=db, user_email=current_user, entity_type="data_contract", entity_id=contract_id,
            action="CREATE_SCHEMA_AUTHORITATIVE_DEFINITION", success=True,
            details={"schema_id": schema_id, "definition_id": new_definition.id}
        )

        return AuthoritativeDefinitionRead.model_validate(new_definition).model_dump()
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating schema authoritative definition: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put('/data-contracts/{contract_id}/schemas/{schema_id}/authoritative-definitions/{definition_id}', response_model=dict)
async def update_schema_authoritative_definition(
    contract_id: str,
    schema_id: str,
    definition_id: str,
    request: Request,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: AuditCurrentUserDep,
    definition_data: dict = Body(...),
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_WRITE))
):
    """Update a schema-level authoritative definition."""
    from src.repositories.data_contracts_repository import schema_authoritative_definition_repo
    from src.models.data_contracts_api import AuthoritativeDefinitionUpdate, AuthoritativeDefinitionRead

    contract = data_contract_repo.get(db, id=contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    try:
        definition_update = AuthoritativeDefinitionUpdate(**definition_data)
        updated_definition = schema_authoritative_definition_repo.update_definition(
            db=db, definition_id=definition_id, url=definition_update.url, type=definition_update.type
        )

        if not updated_definition:
            raise HTTPException(status_code=404, detail="Authoritative definition not found")

        db.commit()

        await audit_manager.log_event(
            db=db, user_email=current_user, entity_type="data_contract", entity_id=contract_id,
            action="UPDATE_SCHEMA_AUTHORITATIVE_DEFINITION", success=True,
            details={"schema_id": schema_id, "definition_id": definition_id}
        )

        return AuthoritativeDefinitionRead.model_validate(updated_definition).model_dump()
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating schema authoritative definition: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete('/data-contracts/{contract_id}/schemas/{schema_id}/authoritative-definitions/{definition_id}', status_code=204)
async def delete_schema_authoritative_definition(
    contract_id: str,
    schema_id: str,
    definition_id: str,
    request: Request,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: AuditCurrentUserDep,
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_WRITE))
):
    """Delete a schema-level authoritative definition."""
    from src.repositories.data_contracts_repository import schema_authoritative_definition_repo

    contract = data_contract_repo.get(db, id=contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    try:
        deleted = schema_authoritative_definition_repo.delete_definition(db=db, definition_id=definition_id)

        if not deleted:
            raise HTTPException(status_code=404, detail="Authoritative definition not found")

        db.commit()

        await audit_manager.log_event(
            db=db, user_email=current_user, entity_type="data_contract", entity_id=contract_id,
            action="DELETE_SCHEMA_AUTHORITATIVE_DEFINITION", success=True,
            details={"schema_id": schema_id, "definition_id": definition_id}
        )

        return None
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting schema authoritative definition: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ===== Property-Level Authoritative Definitions CRUD =====

@router.get('/data-contracts/{contract_id}/schemas/{schema_id}/properties/{property_id}/authoritative-definitions', response_model=List[dict])
async def get_property_authoritative_definitions(
    contract_id: str,
    schema_id: str,
    property_id: str,
    db: DBSessionDep,
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_ONLY))
):
    """Get all authoritative definitions for a schema property."""
    from src.repositories.data_contracts_repository import property_authoritative_definition_repo
    from src.models.data_contracts_api import AuthoritativeDefinitionRead

    contract = data_contract_repo.get(db, id=contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    try:
        definitions = property_authoritative_definition_repo.get_by_property(db=db, property_id=property_id)
        return [AuthoritativeDefinitionRead.model_validate(d).model_dump() for d in definitions]
    except Exception as e:
        logger.error(f"Error fetching property authoritative definitions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/data-contracts/{contract_id}/schemas/{schema_id}/properties/{property_id}/authoritative-definitions', response_model=dict, status_code=201)
async def create_property_authoritative_definition(
    contract_id: str,
    schema_id: str,
    property_id: str,
    request: Request,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: AuditCurrentUserDep,
    definition_data: dict = Body(...),
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_WRITE))
):
    """Create an authoritative definition for a schema property."""
    from src.repositories.data_contracts_repository import property_authoritative_definition_repo
    from src.models.data_contracts_api import AuthoritativeDefinitionCreate, AuthoritativeDefinitionRead

    contract = data_contract_repo.get(db, id=contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    try:
        definition_create = AuthoritativeDefinitionCreate(**definition_data)
        new_definition = property_authoritative_definition_repo.create_definition(
            db=db, property_id=property_id, url=definition_create.url, type=definition_create.type
        )
        db.commit()

        await audit_manager.log_event(
            db=db, user_email=current_user, entity_type="data_contract", entity_id=contract_id,
            action="CREATE_PROPERTY_AUTHORITATIVE_DEFINITION", success=True,
            details={"property_id": property_id, "definition_id": new_definition.id}
        )

        return AuthoritativeDefinitionRead.model_validate(new_definition).model_dump()
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating property authoritative definition: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put('/data-contracts/{contract_id}/schemas/{schema_id}/properties/{property_id}/authoritative-definitions/{definition_id}', response_model=dict)
async def update_property_authoritative_definition(
    contract_id: str,
    schema_id: str,
    property_id: str,
    definition_id: str,
    request: Request,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: AuditCurrentUserDep,
    definition_data: dict = Body(...),
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_WRITE))
):
    """Update a property-level authoritative definition."""
    from src.repositories.data_contracts_repository import property_authoritative_definition_repo
    from src.models.data_contracts_api import AuthoritativeDefinitionUpdate, AuthoritativeDefinitionRead

    contract = data_contract_repo.get(db, id=contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    try:
        definition_update = AuthoritativeDefinitionUpdate(**definition_data)
        updated_definition = property_authoritative_definition_repo.update_definition(
            db=db, definition_id=definition_id, url=definition_update.url, type=definition_update.type
        )

        if not updated_definition:
            raise HTTPException(status_code=404, detail="Authoritative definition not found")

        db.commit()

        await audit_manager.log_event(
            db=db, user_email=current_user, entity_type="data_contract", entity_id=contract_id,
            action="UPDATE_PROPERTY_AUTHORITATIVE_DEFINITION", success=True,
            details={"property_id": property_id, "definition_id": definition_id}
        )

        return AuthoritativeDefinitionRead.model_validate(updated_definition).model_dump()
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating property authoritative definition: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete('/data-contracts/{contract_id}/schemas/{schema_id}/properties/{property_id}/authoritative-definitions/{definition_id}', status_code=204)
async def delete_property_authoritative_definition(
    contract_id: str,
    schema_id: str,
    property_id: str,
    definition_id: str,
    request: Request,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: AuditCurrentUserDep,
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_WRITE))
):
    """Delete a property-level authoritative definition."""
    from src.repositories.data_contracts_repository import property_authoritative_definition_repo

    contract = data_contract_repo.get(db, id=contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    try:
        deleted = property_authoritative_definition_repo.delete_definition(db=db, definition_id=definition_id)

        if not deleted:
            raise HTTPException(status_code=404, detail="Authoritative definition not found")

        db.commit()

        await audit_manager.log_event(
            db=db, user_email=current_user, entity_type="data_contract", entity_id=contract_id,
            action="DELETE_PROPERTY_AUTHORITATIVE_DEFINITION", success=True,
            details={"property_id": property_id, "definition_id": definition_id}
        )

        return None
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting property authoritative definition: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ===== Contract Tags CRUD Endpoints =====

@router.get('/data-contracts/{contract_id}/tags', response_model=List[dict])
async def get_contract_tags(
    contract_id: str,
    db: DBSessionDep,
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_ONLY))
):
    """Get all tags for a specific contract."""
    from src.repositories.data_contracts_repository import contract_tag_repo
    from src.models.data_contracts_api import ContractTagRead

    # Verify contract exists
    contract = data_contract_repo.get(db, id=contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    try:
        tags = contract_tag_repo.get_by_contract(db=db, contract_id=contract_id)
        return [ContractTagRead.model_validate(tag).model_dump() for tag in tags]
    except Exception as e:
        logger.error(f"Error fetching tags for contract {contract_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/data-contracts/{contract_id}/tags', response_model=dict, status_code=201)
async def create_contract_tag(
    contract_id: str,
    request: Request,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: AuditCurrentUserDep,
    tag_data: dict = Body(...),
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_WRITE))
):
    """Create a new tag for a contract."""
    from src.repositories.data_contracts_repository import contract_tag_repo
    from src.models.data_contracts_api import ContractTagCreate, ContractTagRead

    # Verify contract exists
    contract = data_contract_repo.get(db, id=contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    try:
        # Validate input
        tag_create = ContractTagCreate(**tag_data)

        # Create tag
        new_tag = contract_tag_repo.create_tag(db=db, contract_id=contract_id, name=tag_create.name)
        db.commit()

        # Audit log
        audit_manager.log_action(
            db=db,
            username=current_user.username if current_user else "anonymous",
            ip_address=request.client.host if request.client else None,
            feature="data-contracts",
            action="CREATE_TAG",
            success=True,
            details={"contract_id": contract_id, "tag_name": tag_create.name}
        )

        return ContractTagRead.model_validate(new_tag).model_dump()

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating tag for contract {contract_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put('/data-contracts/{contract_id}/tags/{tag_id}', response_model=dict)
async def update_contract_tag(
    contract_id: str,
    tag_id: str,
    request: Request,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: AuditCurrentUserDep,
    tag_data: dict = Body(...),
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_WRITE))
):
    """Update a contract tag."""
    from src.repositories.data_contracts_repository import contract_tag_repo
    from src.models.data_contracts_api import ContractTagUpdate, ContractTagRead

    # Verify contract exists
    contract = data_contract_repo.get(db, id=contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    try:
        # Validate input
        tag_update = ContractTagUpdate(**tag_data)

        if tag_update.name is None:
            raise HTTPException(status_code=400, detail="Tag name is required for update")

        # Update tag
        updated_tag = contract_tag_repo.update_tag(db=db, tag_id=tag_id, name=tag_update.name)
        if not updated_tag:
            raise HTTPException(status_code=404, detail="Tag not found")

        # Verify tag belongs to the contract
        if updated_tag.contract_id != contract_id:
            raise HTTPException(status_code=400, detail="Tag does not belong to this contract")

        db.commit()

        # Audit log
        audit_manager.log_action(
            db=db,
            username=current_user.username if current_user else "anonymous",
            ip_address=request.client.host if request.client else None,
            feature="data-contracts",
            action="UPDATE_TAG",
            success=True,
            details={"contract_id": contract_id, "tag_id": tag_id, "new_name": tag_update.name}
        )

        return ContractTagRead.model_validate(updated_tag).model_dump()

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating tag {tag_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete('/data-contracts/{contract_id}/tags/{tag_id}', status_code=204)
async def delete_contract_tag(
    contract_id: str,
    tag_id: str,
    request: Request,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: AuditCurrentUserDep,
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_WRITE))
):
    """Delete a contract tag."""
    from src.repositories.data_contracts_repository import contract_tag_repo

    # Verify contract exists
    contract = data_contract_repo.get(db, id=contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    try:
        # Get tag first to verify it belongs to this contract
        tag = db.query(DataContractTagDb).filter(DataContractTagDb.id == tag_id).first()
        if not tag:
            raise HTTPException(status_code=404, detail="Tag not found")

        if tag.contract_id != contract_id:
            raise HTTPException(status_code=400, detail="Tag does not belong to this contract")

        # Delete tag
        success = contract_tag_repo.delete_tag(db=db, tag_id=tag_id)
        if not success:
            raise HTTPException(status_code=404, detail="Tag not found")

        db.commit()

        # Audit log
        audit_manager.log_action(
            db=db,
            username=current_user.username if current_user else "anonymous",
            ip_address=request.client.host if request.client else None,
            feature="data-contracts",
            action="DELETE_TAG",
            success=True,
            details={"contract_id": contract_id, "tag_id": tag_id}
        )

        return None

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting tag {tag_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ===== Semantic Versioning Endpoints =====

@router.get('/data-contracts/{contract_id}/versions', response_model=List[dict])
async def get_contract_versions(
    contract_id: str,
    db: DBSessionDep,
    manager: DataContractsManager = Depends(get_data_contracts_manager),
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_ONLY))
):
    """Get all versions of a contract family (same base_name), sorted newest first."""
    try:
        # Business logic now in manager
        contracts = manager.get_contract_versions(db=db, contract_id=contract_id)

        # Convert to API model
        from src.models.data_contracts_api import DataContractRead
        return [DataContractRead.model_validate(c).model_dump() for c in contracts]
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching contract versions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/data-contracts/{contract_id}/clone', response_model=dict, status_code=201)
async def clone_contract_for_new_version(
    contract_id: str,
    request: Request,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: AuditCurrentUserDep,
    body: dict = Body(...),
    manager: DataContractsManager = Depends(get_data_contracts_manager),
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_WRITE))
):
    """Clone a contract to create a new version with all nested entities."""
    new_version = body.get('new_version')
    change_summary = body.get('change_summary')

    if not new_version:
        raise HTTPException(status_code=400, detail="new_version is required")

    try:
        # Business logic now in manager
        new_contract = manager.clone_contract_for_new_version(
            db=db,
            contract_id=contract_id,
            new_version=new_version,
            change_summary=change_summary,
            current_user=current_user.username if current_user else None
        )

        # Audit log
        audit_manager.log_action(
            db=db,
            username=current_user.username if current_user else "anonymous",
            ip_address=request.client.host if request.client else None,
            feature="data-contracts",
            action="CLONE_VERSION",
            success=True,
            details={
                "source_contract_id": contract_id,
                "new_contract_id": new_contract.id,
                "new_version": new_version,
                "change_summary": change_summary
            }
        )

        # Return new contract
        from src.models.data_contracts_api import DataContractRead
        return DataContractRead.model_validate(new_contract).model_dump()

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cloning contract: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/data-contracts/compare', response_model=dict)
async def compare_contract_versions(
    body: dict = Body(...),
    manager: DataContractsManager = Depends(get_data_contracts_manager),
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_ONLY))
):
    """Analyze changes between two contract versions and recommend version bump."""
    old_contract = body.get('old_contract')
    new_contract = body.get('new_contract')

    if not old_contract or not new_contract:
        raise HTTPException(status_code=400, detail="Both old_contract and new_contract are required")

    try:
        # Business logic now in manager
        return manager.compare_contracts(
            old_contract=old_contract,
            new_contract=new_contract
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error comparing contracts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/data-contracts/{contract_id}/version-history', response_model=dict)
async def get_contract_version_history(
    contract_id: str,
    db: DBSessionDep,
    manager: DataContractsManager = Depends(get_data_contracts_manager),
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_ONLY))
):
    """Get version history lineage for a contract with parent-child relationships."""
    try:
        from src.models.data_contracts_api import DataContractRead

        # Business logic now in manager
        history = manager.get_version_history(db=db, contract_id=contract_id)

        # Convert database objects to API models
        return {
            "current": DataContractRead.model_validate(history["current"]).model_dump(),
            "parent": DataContractRead.model_validate(history["parent"]).model_dump() if history["parent"] else None,
            "children": [DataContractRead.model_validate(c).model_dump() for c in history["children"]],
            "siblings": [DataContractRead.model_validate(s).model_dump() for s in history["siblings"]]
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching version history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/data-contracts/{contract_id}/import-team-members', response_model=list)
async def get_team_members_for_import(
    contract_id: str,
    team_id: str,
    request: Request,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: AuditCurrentUserDep,
    manager: DataContractsManager = Depends(get_data_contracts_manager),
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_WRITE))
):
    """Get team members formatted for import into contract ODCS team array.
    
    Route handler: parses parameters, audits request, delegates to manager, returns response.
    All business logic is in the manager.
    """
    success = False
    members = []
    try:
        # Delegate business logic to manager
        members = manager.get_team_members_for_import(
            db=db,
            contract_id=contract_id,
            team_id=team_id,
            current_user=current_user.username if current_user else None
        )
        
        success = True
        return members
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching team members for import: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Audit the action
        audit_manager.log_action(
            db=db,
            username=current_user.username if current_user else 'anonymous',
            ip_address=request.client.host if request.client else None,
            feature='data-contracts',
            action='GET_TEAM_MEMBERS_FOR_IMPORT',
            success=success,
            details={"contract_id": contract_id, "team_id": team_id, "member_count": len(members)}
        )


def register_routes(app):
    """Register routes with the app"""
    app.include_router(router)
    logger.info("Data contract routes registered")
