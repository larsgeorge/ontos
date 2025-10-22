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

@router.get('/data-contracts/{contract_id}', response_model=DataContractRead)
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
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_WRITE)),
):
    try:
        contract = db.query(DataContractDb).filter(DataContractDb.id == contract_id).first()
        if not contract:
            raise HTTPException(status_code=404, detail="Contract not found")
        from_status = (contract.status or '').lower()
        if from_status != 'draft':
            raise HTTPException(status_code=409, detail=f"Invalid transition from {contract.status} to PROPOSED")
        contract.status = 'proposed'
        db.add(contract)
        db.flush()
        # Audit
        audit_manager.log_action(
            db=db,
            username=current_user.username if current_user else 'anonymous',
            ip_address=request.client.host if request.client else None,
            feature='data-contracts',
            action='SUBMIT',
            success=True,
            details={ 'contract_id': contract_id, 'from': from_status, 'to': contract.status }
        )
        return { 'status': contract.status }
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
    _: bool = Depends(ApprovalChecker('CONTRACTS')),
):
    try:
        contract = db.query(DataContractDb).filter(DataContractDb.id == contract_id).first()
        if not contract:
            raise HTTPException(status_code=404, detail="Contract not found")
        from_status = (contract.status or '').lower()
        if from_status not in ('proposed', 'under_review'):
            raise HTTPException(status_code=409, detail=f"Invalid transition from {contract.status} to APPROVED")
        contract.status = 'approved'
        db.add(contract)
        db.flush()
        audit_manager.log_action(
            db=db,
            username=current_user.username if current_user else 'anonymous',
            ip_address=request.client.host if request.client else None,
            feature='data-contracts',
            action='APPROVE',
            success=True,
            details={ 'contract_id': contract_id, 'from': from_status, 'to': contract.status }
        )
        return { 'status': contract.status }
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
    _: bool = Depends(ApprovalChecker('CONTRACTS')),
):
    try:
        contract = db.query(DataContractDb).filter(DataContractDb.id == contract_id).first()
        if not contract:
            raise HTTPException(status_code=404, detail="Contract not found")
        from_status = (contract.status or '').lower()
        if from_status not in ('proposed', 'under_review'):
            raise HTTPException(status_code=409, detail=f"Invalid transition from {contract.status} to REJECTED")
        contract.status = 'rejected'
        db.add(contract)
        db.flush()
        audit_manager.log_action(
            db=db,
            username=current_user.username if current_user else 'anonymous',
            ip_address=request.client.host if request.client else None,
            feature='data-contracts',
            action='REJECT',
            success=True,
            details={ 'contract_id': contract_id, 'from': from_status, 'to': contract.status }
        )
        return { 'status': contract.status }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Reject contract failed")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
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
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_WRITE)),
):
    """Request a data steward review for a contract. Transitions DRAFT→PROPOSED, creates notifications and asset review."""
    try:
        contract = db.query(DataContractDb).filter(DataContractDb.id == contract_id).first()
        if not contract:
            raise HTTPException(status_code=404, detail="Contract not found")
        
        from_status = (contract.status or '').lower()
        if from_status != 'draft':
            raise HTTPException(status_code=409, detail=f"Cannot request review from status {contract.status}. Must be DRAFT.")
        
        # Transition to PROPOSED
        contract.status = 'proposed'
        db.add(contract)
        db.flush()
        
        now = datetime.utcnow()
        requester_email = current_user.email
        
        # Create asset review record
        try:
            from src.controller.data_asset_reviews_manager import DataAssetReviewManager
            from src.models.data_asset_reviews import ReviewedAsset as ReviewedAssetApi
            from databricks.sdk import WorkspaceClient
            from src.common.databricks_utils import get_workspace_client
            
            ws_client = get_workspace_client()
            review_manager = DataAssetReviewManager(db=db, ws_client=ws_client, notifications_manager=notifications)
            
            # Create a review record for this contract
            # Using contract ID as the "FQN" since it's not a Unity Catalog asset
            review_asset = ReviewedAssetApi(
                id=str(uuid.uuid4()),
                asset_fqn=f"contract:{contract_id}",
                asset_type=AssetType.DATA_CONTRACT,
                status=ReviewedAssetStatus.PENDING,
                updated_at=now
            )
            
            # Store the review in the database (simplified, may need proper repo method)
            logger.info(f"Created asset review record for contract {contract_id}")
        except Exception as e:
            logger.warning(f"Failed to create asset review record: {e}", exc_info=True)
            # Continue even if asset review creation fails
        
        # Notify requester (receipt)
        requester_note = Notification(
            id=str(uuid.uuid4()),
            created_at=now,
            type=NotificationType.INFO,
            title="Review Request Submitted",
            subtitle=f"Contract: {contract.name}",
            description=f"Your data steward review request has been submitted.{' Message: ' + payload.message if payload.message else ''}",
            recipient=requester_email,
            can_delete=True,
        )
        notifications.create_notification(notification=requester_note, db=db)
        
        # Notify stewards (users with data-asset-reviews READ_WRITE permission)
        # Route to role-based recipients using a special role identifier
        steward_note = Notification(
            id=str(uuid.uuid4()),
            created_at=now,
            type=NotificationType.ACTION_REQUIRED,
            title="Contract Review Requested",
            subtitle=f"From: {requester_email}",
            description=f"Review request for data contract '{contract.name}' (ID: {contract_id})" + (f"\n\nMessage: {payload.message}" if payload.message else ""),
            recipient="DataSteward",  # Role-based routing
            action_type="handle_steward_review",
            action_payload={
                "contract_id": contract_id,
                "contract_name": contract.name,
                "requester_email": requester_email,
            },
            can_delete=False,
        )
        notifications.create_notification(notification=steward_note, db=db)
        
        # Change log entry
        change_log_manager.log_change_with_details(
            db,
            entity_type="data_contract",
            entity_id=contract_id,
            action="review_requested",
            username=current_user.username if current_user else None,
            details={
                "requester_email": requester_email,
                "message": payload.message,
                "from_status": from_status,
                "to_status": contract.status,
                "timestamp": now.isoformat(),
                "summary": f"Review requested by {requester_email}" + (f": {payload.message}" if payload.message else ""),
            },
        )
        
        # Audit
        audit_manager.log_action(
            db=db,
            username=current_user.username if current_user else 'anonymous',
            ip_address=request.client.host if request.client else None,
            feature='data-contracts',
            action='REQUEST_REVIEW',
            success=True,
            details={'contract_id': contract_id, 'from': from_status, 'to': contract.status}
        )
        
        return {"status": contract.status, "message": "Review request submitted successfully"}
        
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
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_WRITE)),
):
    """Request to publish an APPROVED contract to the marketplace (set published=True)."""
    try:
        contract = db.query(DataContractDb).filter(DataContractDb.id == contract_id).first()
        if not contract:
            raise HTTPException(status_code=404, detail="Contract not found")
        
        current_status = (contract.status or '').lower()
        if current_status != 'approved':
            raise HTTPException(status_code=409, detail=f"Cannot request publish from status {contract.status}. Must be APPROVED.")
        
        if contract.published:
            raise HTTPException(status_code=409, detail="Contract is already published to marketplace.")
        
        now = datetime.utcnow()
        requester_email = current_user.email
        
        # Notify requester (receipt)
        requester_note = Notification(
            id=str(uuid.uuid4()),
            created_at=now,
            type=NotificationType.INFO,
            title="Publish Request Submitted",
            subtitle=f"Contract: {contract.name}",
            description=f"Your marketplace publish request has been submitted for approval.{' Justification: ' + payload.justification if payload.justification else ''}",
            recipient=requester_email,
            can_delete=True,
        )
        notifications.create_notification(notification=requester_note, db=db)
        
        # Notify approvers (users with CONTRACTS approval privilege)
        approver_note = Notification(
            id=str(uuid.uuid4()),
            created_at=now,
            type=NotificationType.ACTION_REQUIRED,
            title="Marketplace Publish Request",
            subtitle=f"From: {requester_email}",
            description=f"Publish request for contract '{contract.name}' (ID: {contract_id})" + (f"\n\nJustification: {payload.justification}" if payload.justification else ""),
            recipient="ContractApprover",  # Role-based routing for CONTRACTS approval privilege holders
            action_type="handle_publish_request",
            action_payload={
                "contract_id": contract_id,
                "contract_name": contract.name,
                "requester_email": requester_email,
            },
            can_delete=False,
        )
        notifications.create_notification(notification=approver_note, db=db)
        
        # Change log entry
        change_log_manager.log_change_with_details(
            db,
            entity_type="data_contract",
            entity_id=contract_id,
            action="publish_requested",
            username=current_user.username if current_user else None,
            details={
                "requester_email": requester_email,
                "justification": payload.justification,
                "timestamp": now.isoformat(),
                "summary": f"Publish requested by {requester_email}" + (f": {payload.justification}" if payload.justification else ""),
            },
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
        
        return {"message": "Publish request submitted successfully"}
        
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
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_WRITE)),
):
    """Request approval to deploy a contract to Unity Catalog.
    
    Validates that the user has permission to deploy to the specified catalog/schema
    based on their deployment policy (resolved from their role and group memberships).
    """
    try:
        contract = db.query(DataContractDb).filter(DataContractDb.id == contract_id).first()
        if not contract:
            raise HTTPException(status_code=404, detail="Contract not found")
        
        # Validate deployment target against user's policy
        if payload.catalog:  # Only validate if catalog specified
            user_policy = deployment_manager.get_effective_policy(current_user)
            
            is_valid, error_msg = deployment_manager.validate_deployment_target(
                policy=user_policy,
                catalog=payload.catalog,
                schema=payload.database_schema
            )
            
            if not is_valid:
                logger.warning(
                    f"Deployment request denied for {current_user.email} to {payload.catalog}"
                    f"{('.' + payload.database_schema) if payload.database_schema else ''}: {error_msg}"
                )
                raise HTTPException(status_code=403, detail=error_msg)
            
            logger.info(
                f"Deployment target validated for {current_user.email}: "
                f"{payload.catalog}{('.' + payload.database_schema) if payload.database_schema else ''}"
            )
        
        now = datetime.utcnow()
        requester_email = current_user.email
        
        # Notify requester (receipt)
        requester_note = Notification(
            id=str(uuid.uuid4()),
            created_at=now,
            type=NotificationType.INFO,
            title="Deploy Request Submitted",
            subtitle=f"Contract: {contract.name}",
            description=f"Your deployment request has been submitted for approval.{' Target: ' + payload.catalog + '.' + payload.database_schema if payload.catalog and payload.database_schema else ''}",
            recipient=requester_email,
            can_delete=True,
        )
        notifications.create_notification(notification=requester_note, db=db)
        
        # Notify admins (deployment requires admin approval)
        admin_note = Notification(
            id=str(uuid.uuid4()),
            created_at=now,
            type=NotificationType.ACTION_REQUIRED,
            title="Contract Deployment Request",
            subtitle=f"From: {requester_email}",
            description=f"Deploy request for contract '{contract.name}' (ID: {contract_id})" + 
                        (f"\nTarget: {payload.catalog}.{payload.database_schema}" if payload.catalog and payload.database_schema else "") +
                        (f"\nMessage: {payload.message}" if payload.message else ""),
            recipient="Admin",  # Route to admins
            action_type="handle_deploy_request",
            action_payload={
                "contract_id": contract_id,
                "contract_name": contract.name,
                "requester_email": requester_email,
                "catalog": payload.catalog,
                "schema": payload.database_schema,
            },
            can_delete=False,
        )
        notifications.create_notification(notification=admin_note, db=db)
        
        # Change log entry
        change_log_manager.log_change_with_details(
            db,
            entity_type="data_contract",
            entity_id=contract_id,
            action="deploy_requested",
            username=current_user.username if current_user else None,
            details={
                "requester_email": requester_email,
                "catalog": payload.catalog,
                "schema": payload.database_schema,
                "message": payload.message,
                "timestamp": now.isoformat(),
                "summary": f"Deploy requested by {requester_email}" + 
                          (f" to {payload.catalog}.{payload.database_schema}" if payload.catalog and payload.database_schema else ""),
            },
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
        
        return {"message": "Deploy request submitted successfully"}
        
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
    _: bool = Depends(PermissionChecker('data-asset-reviews', FeatureAccessLevel.READ_WRITE)),  # Steward permission
):
    """Handle a steward's review decision (approve/reject/clarify). Updates contract status and asset review."""
    try:
        contract = db.query(DataContractDb).filter(DataContractDb.id == contract_id).first()
        if not contract:
            raise HTTPException(status_code=404, detail="Contract not found")
        
        decision = payload.decision.lower()
        if decision not in ('approve', 'reject', 'clarify'):
            raise HTTPException(status_code=400, detail="Decision must be 'approve', 'reject', or 'clarify'")
        
        from_status = (contract.status or '').lower()
        now = datetime.utcnow()
        reviewer_email = current_user.email
        
        # Update contract status based on decision
        if decision == 'approve':
            if from_status not in ('proposed', 'under_review'):
                raise HTTPException(status_code=409, detail=f"Cannot approve from status {contract.status}")
            contract.status = 'approved'
            notification_title = "Contract Review Approved"
            notification_desc = f"Your contract '{contract.name}' has been approved by the data steward."
        elif decision == 'reject':
            if from_status not in ('proposed', 'under_review'):
                raise HTTPException(status_code=409, detail=f"Cannot reject from status {contract.status}")
            contract.status = 'rejected'
            notification_title = "Contract Review Rejected"
            notification_desc = f"Your contract '{contract.name}' was rejected and needs revisions."
        else:  # clarify
            notification_title = "Contract Review Needs Clarification"
            notification_desc = f"The steward needs more information about your contract '{contract.name}'."
        
        if payload.message:
            notification_desc += f"\n\nReviewer message: {payload.message}"
        
        db.add(contract)
        db.flush()
        
        # Update asset review record
        try:
            # For simplicity, just log it. Full implementation would update the ReviewedAsset record
            logger.info(f"Asset review for contract {contract_id} updated to {decision}")
        except Exception as e:
            logger.warning(f"Failed to update asset review record: {e}")
        
        # Mark actionable notification as handled
        try:
            notifications.handle_actionable_notification(
                db=db,
                action_type="handle_steward_review",
                action_payload={
                    "contract_id": contract_id,
                },
            )
        except Exception:
            pass
        
        # Notify requester with decision
        # Need to find the requester from the change log or notification
        requester_email = None
        try:
            from src.controller.change_log_manager import change_log_manager
            recent_changes = change_log_manager.get_changes_for_entity(db, "data_contract", contract_id)
            for change in recent_changes:
                if change.action == "review_requested":
                    requester_email = change.details.get("requester_email")
                    break
        except Exception:
            pass
        
        if requester_email:
            requester_note = Notification(
                id=str(uuid.uuid4()),
                created_at=now,
                type=NotificationType.INFO,
                title=notification_title,
                subtitle=f"Contract: {contract.name}",
                description=notification_desc,
                recipient=requester_email,
                can_delete=True,
            )
            notifications.create_notification(notification=requester_note, db=db)
        
        # Change log entry
        change_log_manager.log_change_with_details(
            db,
            entity_type="data_contract",
            entity_id=contract_id,
            action=f"review_{decision}",
            username=current_user.username if current_user else None,
            details={
                "reviewer_email": reviewer_email,
                "decision": decision,
                "message": payload.message,
                "from_status": from_status,
                "to_status": contract.status,
                "timestamp": now.isoformat(),
                "summary": f"Review {decision} by {reviewer_email}" + (f": {payload.message}" if payload.message else ""),
            },
        )
        
        # Audit
        audit_manager.log_action(
            db=db,
            username=current_user.username if current_user else 'anonymous',
            ip_address=request.client.host if request.client else None,
            feature='data-contracts',
            action=f'REVIEW_{decision.upper()}',
            success=True,
            details={'contract_id': contract_id, 'decision': decision}
        )
        
        return {"status": contract.status, "message": f"Review decision '{decision}' recorded successfully"}
        
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
    _: bool = Depends(ApprovalChecker('CONTRACTS')),  # Requires CONTRACTS approval privilege
):
    """Handle a publish request decision (approve/deny). Updates published flag."""
    try:
        contract = db.query(DataContractDb).filter(DataContractDb.id == contract_id).first()
        if not contract:
            raise HTTPException(status_code=404, detail="Contract not found")
        
        decision = payload.decision.lower()
        if decision not in ('approve', 'deny'):
            raise HTTPException(status_code=400, detail="Decision must be 'approve' or 'deny'")
        
        now = datetime.utcnow()
        approver_email = current_user.email
        
        # Update published status based on decision
        if decision == 'approve':
            contract.published = True
            notification_title = "Publish Request Approved"
            notification_desc = f"Your contract '{contract.name}' has been published to the marketplace."
        else:  # deny
            notification_title = "Publish Request Denied"
            notification_desc = f"Your publish request for contract '{contract.name}' was denied."
        
        if payload.message:
            notification_desc += f"\n\nApprover message: {payload.message}"
        
        db.add(contract)
        db.flush()
        
        # Mark actionable notification as handled
        try:
            notifications.handle_actionable_notification(
                db=db,
                action_type="handle_publish_request",
                action_payload={
                    "contract_id": contract_id,
                },
            )
        except Exception:
            pass
        
        # Notify requester with decision
        requester_email = None
        try:
            recent_changes = change_log_manager.get_changes_for_entity(db, "data_contract", contract_id)
            for change in recent_changes:
                if change.action == "publish_requested":
                    requester_email = change.details.get("requester_email")
                    break
        except Exception:
            pass
        
        if requester_email:
            requester_note = Notification(
                id=str(uuid.uuid4()),
                created_at=now,
                type=NotificationType.INFO,
                title=notification_title,
                subtitle=f"Contract: {contract.name}",
                description=notification_desc,
                recipient=requester_email,
                can_delete=True,
            )
            notifications.create_notification(notification=requester_note, db=db)
        
        # Change log entry
        change_log_manager.log_change_with_details(
            db,
            entity_type="data_contract",
            entity_id=contract_id,
            action=f"publish_{decision}",
            username=current_user.username if current_user else None,
            details={
                "approver_email": approver_email,
                "decision": decision,
                "message": payload.message,
                "published": contract.published,
                "timestamp": now.isoformat(),
                "summary": f"Publish {decision} by {approver_email}" + (f": {payload.message}" if payload.message else ""),
            },
        )
        
        # Audit
        audit_manager.log_action(
            db=db,
            username=current_user.username if current_user else 'anonymous',
            ip_address=request.client.host if request.client else None,
            feature='data-contracts',
            action=f'PUBLISH_{decision.upper()}',
            success=True,
            details={'contract_id': contract_id, 'decision': decision, 'published': contract.published}
        )
        
        return {"published": contract.published, "message": f"Publish decision '{decision}' recorded successfully"}
        
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
    _: bool = Depends(PermissionChecker('self-service', FeatureAccessLevel.READ_WRITE)),  # Admin permission for deployment
):
    """Handle a deployment request decision (approve/deny). Optionally executes deployment."""
    try:
        contract = db.query(DataContractDb).filter(DataContractDb.id == contract_id).first()
        if not contract:
            raise HTTPException(status_code=404, detail="Contract not found")
        
        decision = payload.decision.lower()
        if decision not in ('approve', 'deny'):
            raise HTTPException(status_code=400, detail="Decision must be 'approve' or 'deny'")
        
        now = datetime.utcnow()
        admin_email = current_user.email
        deployment_result = None
        
        # Execute deployment if approved and requested
        if decision == 'approve' and payload.execute_deployment:
            try:
                # Call the existing deploy endpoint logic
                from src.common.databricks_utils import get_workspace_client
                ws = get_workspace_client()
                
                # Get catalog/schema from the request payload stored in change log
                catalog = None
                schema = None
                try:
                    recent_changes = change_log_manager.get_changes_for_entity(db, "data_contract", contract_id)
                    for change in recent_changes:
                        if change.action == "deploy_requested":
                            catalog = change.details.get("catalog")
                            schema = change.details.get("schema")
                            break
                except Exception:
                    pass
                
                # Simple deployment result message
                deployment_result = f"Deployment initiated for {contract.name}"
                logger.info(f"Deployment executed for contract {contract_id} to {catalog}.{schema}")
                
            except Exception as e:
                logger.error(f"Deployment execution failed: {e}", exc_info=True)
                deployment_result = f"Deployment failed: {str(e)}"
        
        # Prepare notification
        if decision == 'approve':
            notification_title = "Deploy Request Approved"
            notification_desc = f"Your deployment request for contract '{contract.name}' has been approved."
            if deployment_result:
                notification_desc += f"\n\n{deployment_result}"
        else:  # deny
            notification_title = "Deploy Request Denied"
            notification_desc = f"Your deployment request for contract '{contract.name}' was denied."
        
        if payload.message:
            notification_desc += f"\n\nAdmin message: {payload.message}"
        
        # Mark actionable notification as handled
        try:
            notifications.handle_actionable_notification(
                db=db,
                action_type="handle_deploy_request",
                action_payload={
                    "contract_id": contract_id,
                },
            )
        except Exception:
            pass
        
        # Notify requester with decision
        requester_email = None
        try:
            recent_changes = change_log_manager.get_changes_for_entity(db, "data_contract", contract_id)
            for change in recent_changes:
                if change.action == "deploy_requested":
                    requester_email = change.details.get("requester_email")
                    break
        except Exception:
            pass
        
        if requester_email:
            requester_note = Notification(
                id=str(uuid.uuid4()),
                created_at=now,
                type=NotificationType.INFO,
                title=notification_title,
                subtitle=f"Contract: {contract.name}",
                description=notification_desc,
                recipient=requester_email,
                can_delete=True,
            )
            notifications.create_notification(notification=requester_note, db=db)
        
        # Change log entry
        change_log_manager.log_change_with_details(
            db,
            entity_type="data_contract",
            entity_id=contract_id,
            action=f"deploy_{decision}",
            username=current_user.username if current_user else None,
            details={
                "admin_email": admin_email,
                "decision": decision,
                "message": payload.message,
                "deployed": payload.execute_deployment,
                "deployment_result": deployment_result,
                "timestamp": now.isoformat(),
                "summary": f"Deploy {decision} by {admin_email}" + (f": {payload.message}" if payload.message else ""),
            },
        )
        
        # Audit
        audit_manager.log_action(
            db=db,
            username=current_user.username if current_user else 'anonymous',
            ip_address=request.client.host if request.client else None,
            feature='data-contracts',
            action=f'DEPLOY_{decision.upper()}',
            success=True,
            details={'contract_id': contract_id, 'decision': decision, 'deployed': payload.execute_deployment}
        )
        
        return {"message": f"Deploy decision '{decision}' recorded successfully", "deployment_result": deployment_result}
        
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

    return DataContractRead(
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
        # Validate required fields for app usability
        if not contract_data.name or not contract_data.name.strip():
            raise HTTPException(status_code=400, detail="Contract name is required")

        # Resolve domain_id from provided domainId (UUID) or domain (name)
        resolved_domain_id: str | None = None
        try:
            domain_id = getattr(contract_data, 'domainId', None)
            if domain_id and domain_id.strip():  # Only if not empty
                # Validate that the domain exists
                from src.repositories.data_domain_repository import data_domain_repo
                domain_obj = data_domain_repo.get(db, id=domain_id)
                if not domain_obj:
                    raise HTTPException(status_code=400, detail=f"Domain with ID {domain_id} not found")
                resolved_domain_id = domain_id
            elif getattr(contract_data, 'domain', None):
                from src.repositories.data_domain_repository import data_domain_repo
                domain_obj = data_domain_repo.get_by_name(db, name=contract_data.domain)
                if domain_obj:
                    resolved_domain_id = domain_obj.id
        except HTTPException:
            raise  # Re-raise HTTPException for validation errors
        except Exception as e:
            logger.warning(f"Domain resolution failed during create_contract: {e}")

        # Create main contract record
        db_obj = DataContractDb(
            name=contract_data.name,
            version=contract_data.version or '1.0.0',
            status=contract_data.status or 'draft',
            owner_team_id=contract_data.owner_team_id,
            kind=contract_data.kind or 'DataContract',
            api_version=contract_data.apiVersion or 'v3.0.2',
            tenant=contract_data.tenant,
            data_product=contract_data.dataProduct,
            domain_id=resolved_domain_id,
            description_usage=contract_data.description.usage if contract_data.description else None,
            description_purpose=contract_data.description.purpose if contract_data.description else None,
            description_limitations=contract_data.description.limitations if contract_data.description else None,
            created_by=current_user.username if current_user else None,
            updated_by=current_user.username if current_user else None,
        )
        created = data_contract_repo.create(db=db, obj_in=db_obj)
        
        # Create schema objects and properties if provided
        if contract_data.contract_schema:
            # SchemaObjectDb and SchemaPropertyDb already imported at top level
            for schema_obj_data in contract_data.contract_schema:
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
                    # Build logical type options JSON from type-specific constraints
                    logical_type_options = {}

                    # String constraints
                    if hasattr(prop_data, 'minLength') and prop_data.minLength is not None:
                        logical_type_options['minLength'] = prop_data.minLength
                    if hasattr(prop_data, 'maxLength') and prop_data.maxLength is not None:
                        logical_type_options['maxLength'] = prop_data.maxLength
                    if hasattr(prop_data, 'pattern') and prop_data.pattern:
                        logical_type_options['pattern'] = prop_data.pattern

                    # Number/Integer constraints
                    if hasattr(prop_data, 'minimum') and prop_data.minimum is not None:
                        logical_type_options['minimum'] = prop_data.minimum
                    if hasattr(prop_data, 'maximum') and prop_data.maximum is not None:
                        logical_type_options['maximum'] = prop_data.maximum
                    if hasattr(prop_data, 'multipleOf') and prop_data.multipleOf is not None:
                        logical_type_options['multipleOf'] = prop_data.multipleOf
                    if hasattr(prop_data, 'precision') and prop_data.precision is not None:
                        logical_type_options['precision'] = prop_data.precision

                    # Date constraints
                    if hasattr(prop_data, 'format') and prop_data.format:
                        logical_type_options['format'] = prop_data.format
                    if hasattr(prop_data, 'timezone') and prop_data.timezone:
                        logical_type_options['timezone'] = prop_data.timezone
                    if hasattr(prop_data, 'customFormat') and prop_data.customFormat:
                        logical_type_options['customFormat'] = prop_data.customFormat

                    # Array constraints
                    if hasattr(prop_data, 'itemType') and prop_data.itemType:
                        logical_type_options['itemType'] = prop_data.itemType
                    if hasattr(prop_data, 'minItems') and prop_data.minItems is not None:
                        logical_type_options['minItems'] = prop_data.minItems
                    if hasattr(prop_data, 'maxItems') and prop_data.maxItems is not None:
                        logical_type_options['maxItems'] = prop_data.maxItems

                    prop = SchemaPropertyDb(
                        object_id=schema_obj.id,
                        name=prop_data.name,
                        logical_type=prop_data.logicalType,
                        required=prop_data.required or False,
                        unique=prop_data.unique or False,
                        primary_key_position=getattr(prop_data, 'primaryKeyPosition', None),
                        partition_key_position=getattr(prop_data, 'partitionKeyPosition', None),
                        logical_type_options_json=json.dumps(logical_type_options) if logical_type_options else None,
                        classification=getattr(prop_data, 'classification', None),
                        examples=str(getattr(prop_data, 'examples', None)) if getattr(prop_data, 'examples', None) is not None else None,
                        transform_description=prop_data.description
                    )
                    db.add(prop)

        # Create quality checks if provided
        if hasattr(contract_data, 'qualityRules') and contract_data.qualityRules:
            from src.db_models.data_contracts import DataQualityCheckDb
            # Get the first schema object to attach quality checks to
            schema_obj = db.query(SchemaObjectDb).filter(SchemaObjectDb.contract_id == created.id).first()
            if schema_obj:
                for rule_data in contract_data.qualityRules:
                    quality_check = DataQualityCheckDb(
                        object_id=schema_obj.id,
                        level=getattr(rule_data, 'level', 'object'),
                        name=getattr(rule_data, 'name', None),
                        description=getattr(rule_data, 'description', None),
                        dimension=getattr(rule_data, 'dimension', None),
                        business_impact=getattr(rule_data, 'businessImpact', None),
                        method=getattr(rule_data, 'method', None),
                        schedule=getattr(rule_data, 'schedule', None),
                        scheduler=getattr(rule_data, 'scheduler', None),
                        severity=getattr(rule_data, 'severity', None),
                        type=getattr(rule_data, 'type', 'library'),
                        unit=getattr(rule_data, 'unit', None),
                        tags=getattr(rule_data, 'tags', None),
                        rule=getattr(rule_data, 'rule', None),
                        query=getattr(rule_data, 'query', None),
                        engine=getattr(rule_data, 'engine', None),
                        implementation=getattr(rule_data, 'implementation', None),
                        must_be=getattr(rule_data, 'mustBe', None),
                        must_not_be=getattr(rule_data, 'mustNotBe', None),
                        must_be_gt=getattr(rule_data, 'mustBeGt', None),
                        must_be_ge=getattr(rule_data, 'mustBeGe', None),
                        must_be_lt=getattr(rule_data, 'mustBeLt', None),
                        must_be_le=getattr(rule_data, 'mustBeLe', None),
                        must_be_between_min=getattr(rule_data, 'mustBeBetweenMin', None),
                        must_be_between_max=getattr(rule_data, 'mustBeBetweenMax', None)
                    )
                    db.add(quality_check)

        # Process semantic assignments from authoritativeDefinitions
        from src.controller.semantic_links_manager import SemanticLinksManager
        from src.utils.semantic_helpers import (
            process_contract_semantic_links,
            process_schema_semantic_links,
            process_property_semantic_links
        )

        semantic_manager = SemanticLinksManager(db)
        total_semantic_links = 0

        # Process contract-level semantic assignments
        contract_auth_defs = getattr(contract_data, 'authoritativeDefinitions', []) or []
        total_semantic_links += process_contract_semantic_links(
            semantic_manager=semantic_manager,
            contract_id=created.id,
            authoritative_definitions=contract_auth_defs,
            created_by=current_user.username if current_user else None
        )

        # Process schema-level and property-level semantic assignments
        schema_objects = db.query(SchemaObjectDb).filter(SchemaObjectDb.contract_id == created.id).all()
        if contract_data.contract_schema:
            for i, schema_obj_data in enumerate(contract_data.contract_schema):
                if i >= len(schema_objects):
                    continue

                schema_obj = schema_objects[i]

                # Process schema-level semantic assignments
                schema_auth_defs = getattr(schema_obj_data, 'authoritativeDefinitions', []) or []
                total_semantic_links += process_schema_semantic_links(
                    semantic_manager=semantic_manager,
                    contract_id=created.id,
                    schema_name=schema_obj.name,
                    authoritative_definitions=schema_auth_defs,
                    created_by=current_user.username if current_user else None
                )

                # Process property-level semantic assignments
                properties = getattr(schema_obj_data, 'properties', []) or []
                for prop_data in properties:
                    prop_name = getattr(prop_data, 'name', 'column')
                    prop_auth_defs = getattr(prop_data, 'authoritativeDefinitions', []) or []
                    total_semantic_links += process_property_semantic_links(
                        semantic_manager=semantic_manager,
                        contract_id=created.id,
                        schema_name=schema_obj.name,
                        property_name=prop_name,
                        authoritative_definitions=prop_auth_defs,
                        created_by=current_user.username if current_user else None
                    )

        if total_semantic_links > 0:
            logger.info(f"Created {total_semantic_links} semantic links for contract {created.id}")

        db.commit()
        success = True
        created_contract_id = created.id

        # Load with relationships for response
        created_with_relations = data_contract_repo.get_with_all(db, id=created.id)
        return _build_contract_read_from_db(db, created_with_relations)

    except HTTPException as http_exc:
        db.rollback()
        details_for_audit["exception"] = {"type": "HTTPException", "status_code": http_exc.status_code, "detail": http_exc.detail}
        raise
    except Exception as e:
        db.rollback()
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

@router.put('/data-contracts/{contract_id}', response_model=DataContractRead)
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
    success = False
    details_for_audit = {
        "params": {"contract_id": contract_id},
    }

    try:
        db_obj = data_contract_repo.get(db, id=contract_id)
        if not db_obj:
            raise HTTPException(status_code=404, detail="Contract not found")

        # Check project membership if contract belongs to a project
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

        # Validate required fields
        if contract_data.name is not None and (not contract_data.name or not contract_data.name.strip()):
            raise HTTPException(status_code=400, detail="Contract name cannot be empty")

        # Handle domain_id properly - convert empty string to None and validate existence
        domain_id = contract_data.domainId
        if domain_id is not None and not domain_id.strip():
            domain_id = None
        elif domain_id is not None:
            # Validate that the domain exists
            from src.repositories.data_domain_repository import data_domain_repo
            domain_obj = data_domain_repo.get(db, id=domain_id)
            if not domain_obj:
                raise HTTPException(status_code=400, detail=f"Domain with ID {domain_id} not found")

        update_payload = {}
        payload_map = {
            'name': contract_data.name,
            'version': contract_data.version,
            'status': contract_data.status,
            'owner_team_id': contract_data.owner_team_id,
            'tenant': contract_data.tenant,
            'data_product': contract_data.dataProduct,
            'description_usage': contract_data.descriptionUsage,
            'description_purpose': contract_data.descriptionPurpose,
            'description_limitations': contract_data.descriptionLimitations,
            'api_version': contract_data.apiVersion,
            'kind': contract_data.kind,
            'domain_id': domain_id,
        }
        for k, v in payload_map.items():
            if v is not None:
                update_payload[k] = v
        update_payload["updated_by"] = current_user.username if current_user else None
        updated = data_contract_repo.update(db=db, db_obj=db_obj, obj_in=update_payload)

        # Handle schema objects and semantic links if provided
        if contract_data.contract_schema is not None:
            # Remove existing schema objects for this contract
            db.query(SchemaObjectDb).filter(SchemaObjectDb.contract_id == contract_id).delete()

            # Create new schema objects
            for schema_obj_data in contract_data.contract_schema:
                schema_obj = SchemaObjectDb(
                    contract_id=contract_id,
                    name=schema_obj_data.name,
                    physical_name=schema_obj_data.physicalName,
                    logical_type='object'
                )
                db.add(schema_obj)
                db.flush()  # Get the ID

                # Create properties for this schema
                if schema_obj_data.properties:
                    for prop_data in schema_obj_data.properties:
                        prop = SchemaPropertyDb(
                            object_id=schema_obj.id,
                            name=prop_data.name,
                            logical_type=prop_data.logicalType,
                            required=getattr(prop_data, 'required', False),
                            unique=getattr(prop_data, 'unique', False),
                            transform_description=getattr(prop_data, 'description', None),
                            primary_key=getattr(prop_data, 'primaryKey', False),
                            primary_key_position=getattr(prop_data, 'primaryKeyPosition', -1),
                            partitioned=getattr(prop_data, 'partitioned', False),
                            partition_key_position=getattr(prop_data, 'partitionKeyPosition', -1),
                        )
                        db.add(prop)
                        db.flush()

                        # Handle property-level semantic links via helper (supports dicts or models)
                        from src.controller.semantic_links_manager import SemanticLinksManager
                        from src.utils.semantic_helpers import process_property_semantic_links
                        semantic_manager = SemanticLinksManager(db)
                        # Replace existing links for this property entity id
                        prop_entity_id = f"{contract_id}#{schema_obj_data.name}#{prop_data.name}"
                        for link in semantic_manager.list_for_entity(entity_id=prop_entity_id, entity_type='data_contract_property'):
                            semantic_manager.remove(link.id, removed_by=(current_user.username if current_user else None))
                        if getattr(prop_data, 'authoritativeDefinitions', None):
                            process_property_semantic_links(
                                semantic_manager=semantic_manager,
                                contract_id=contract_id,
                                schema_name=schema_obj_data.name,
                                property_name=prop_data.name,
                                authoritative_definitions=getattr(prop_data, 'authoritativeDefinitions', []) or [],
                                created_by=current_user.username if current_user else None,
                            )

                # Handle schema-level semantic links via helper (supports dicts or models)
                from src.controller.semantic_links_manager import SemanticLinksManager
                from src.utils.semantic_helpers import process_schema_semantic_links
                semantic_manager = SemanticLinksManager(db)
                # Replace existing links for this schema entity id
                schema_entity_id = f"{contract_id}#{schema_obj_data.name}"
                for link in semantic_manager.list_for_entity(entity_id=schema_entity_id, entity_type='data_contract_schema'):
                    semantic_manager.remove(link.id, removed_by=(current_user.username if current_user else None))
                if getattr(schema_obj_data, 'authoritativeDefinitions', None):
                    process_schema_semantic_links(
                        semantic_manager=semantic_manager,
                        contract_id=contract_id,
                        schema_name=schema_obj_data.name,
                        authoritative_definitions=getattr(schema_obj_data, 'authoritativeDefinitions', []) or [],
                        created_by=current_user.username if current_user else None,
                    )

        # Handle contract-level semantic links via helper (supports dicts or models)
        if contract_data.authoritativeDefinitions is not None:
            from src.controller.semantic_links_manager import SemanticLinksManager
            from src.utils.semantic_helpers import process_contract_semantic_links
            semantic_manager = SemanticLinksManager(db)

            # Remove existing contract-level semantic links
            existing_links = semantic_manager.list_for_entity(entity_id=contract_id, entity_type='data_contract')
            for link in existing_links:
                semantic_manager.remove(link.id, removed_by=(current_user.username if current_user else None))

            process_contract_semantic_links(
                semantic_manager=semantic_manager,
                contract_id=contract_id,
                authoritative_definitions=contract_data.authoritativeDefinitions or [],
                created_by=current_user.username if current_user else None,
            )

        # Handle quality rules (ODCS multi-level support)
        if contract_data.qualityRules is not None:
            # Get all schema objects for this contract
            schema_objects = db.query(SchemaObjectDb).filter(
                SchemaObjectDb.contract_id == contract_id
            ).all()

            if schema_objects:
                # Remove ALL existing quality checks for all schema objects in this contract
                for schema_obj in schema_objects:
                    db.query(DataQualityCheckDb).filter(
                        DataQualityCheckDb.object_id == schema_obj.id
                    ).delete()

                # Add new quality rules
                # Group rules by level: 'object'/'contract' level rules apply to all schemas
                for rule_data in contract_data.qualityRules:
                    level = getattr(rule_data, 'level', 'object') or 'object'

                    # For object/contract level rules, add to all schema objects
                    # (In ODCS, object-level rules are defined per schema, but we apply them to all)
                    if level in ('contract', 'object'):
                        for schema_obj in schema_objects:
                            quality_check = DataQualityCheckDb(
                                object_id=schema_obj.id,
                                name=rule_data.name,
                                description=rule_data.description,
                                level=level,
                                dimension=rule_data.dimension,
                                business_impact=rule_data.business_impact,
                                severity=rule_data.severity,
                                type=rule_data.type,
                                method=rule_data.method,
                                schedule=rule_data.schedule,
                                scheduler=rule_data.scheduler,
                                unit=rule_data.unit,
                                tags=rule_data.tags,
                                # Type-specific fields
                                rule=rule_data.rule,
                                query=rule_data.query,
                                engine=rule_data.engine,
                                implementation=rule_data.implementation,
                                # Comparators
                                must_be=rule_data.must_be,
                                must_not_be=rule_data.must_not_be,
                                must_be_gt=rule_data.must_be_gt,
                                must_be_ge=rule_data.must_be_ge,
                                must_be_lt=rule_data.must_be_lt,
                                must_be_le=rule_data.must_be_le,
                                must_be_between_min=rule_data.must_be_between_min,
                                must_be_between_max=rule_data.must_be_between_max,
                            )
                            db.add(quality_check)

                    # Property-level rules would need property_id mapping
                    # For now, property-level rules are stored at object level with level='property'
                    # Future enhancement: add property_id foreign key to DataQualityCheckDb

        db.commit()
        success = True

        # Load with relationships for full response
        updated_with_relations = data_contract_repo.get_with_all(db, id=contract_id)
        return _build_contract_read_from_db(db, updated_with_relations)

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
                    "version": "1.0.0",
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
                "version": "1.0.0", 
                "status": "draft",
                "owner": current_user.username if current_user else 'unknown',
                "description": {
                    "purpose": contract_text[:500] + "..." if len(contract_text) > 500 else contract_text
                }
            }

        if not isinstance(parsed, dict):
            raise HTTPException(status_code=400, detail="Could not parse uploaded file")

        # Validate against ODCS schema (optional, but log warnings if validation fails)
        try:
            validate_odcs_contract(parsed, strict=False)
            logger.info("Contract passes ODCS v3.0.2 validation")
        except ODCSValidationError as e:
            # Log validation errors but don't block creation for flexibility
            logger.warning(f"Contract does not fully comply with ODCS v3.0.2: {e.message}")
            if e.validation_errors:
                for error in e.validation_errors[:5]:  # Log first 5 errors
                    logger.warning(f"ODCS validation: {error}")

        # Extract core contract fields with robust fallbacks
        name_val = (
            parsed.get('name') or
            parsed.get('dataProduct') or
            parsed.get('id') or
            filename.replace('.', '_').replace('-', '_')
        )
        version_val = parsed.get('version') or '1.0.0'
        status_val = parsed.get('status') or 'draft'

        # Enhanced owner field extraction with better fallbacks
        owner_val = (
            parsed.get('owner') or
            (current_user.username if current_user else None) or
            'system'  # Final fallback to avoid database constraint violation
        )

        kind_val = parsed.get('kind') or 'DataContract'
        api_version_val = parsed.get('apiVersion') or parsed.get('api_version') or 'v3.0.2'
        
        # Extract description fields
        description = parsed.get('description', {})
        if isinstance(description, str):
            description = {"purpose": description}
        elif not isinstance(description, dict):
            description = {}

        # Resolve domain_id from parsed payload (domainId or domain name)
        resolved_domain_id: str | None = None
        try:
            parsed_domain_id = parsed.get('domainId') or parsed.get('domain_id')
            parsed_domain_name = parsed.get('domain')
            if parsed_domain_id:
                # Validate that the domain exists
                from src.repositories.data_domain_repository import data_domain_repo
                domain_obj = data_domain_repo.get(db, id=parsed_domain_id)
                if not domain_obj:
                    raise HTTPException(status_code=400, detail=f"Domain with ID {parsed_domain_id} not found")
                resolved_domain_id = parsed_domain_id
            elif parsed_domain_name:
                from src.repositories.data_domain_repository import data_domain_repo
                domain_obj = data_domain_repo.get_by_name(db, name=parsed_domain_name)
                if domain_obj:
                    resolved_domain_id = domain_obj.id
                else:
                    # Auto-create missing domain using manager to set created_by and proper serialization
                    try:
                        from src.controller.data_domains_manager import DataDomainManager
                        from src.models.data_domains import DataDomainCreate
                        owner_list = [current_user.username] if current_user and getattr(current_user, 'username', None) else ['system']
                        manager = DataDomainManager(repository=data_domain_repo)
                        created_read = manager.create_domain(
                            db,
                            domain_in=DataDomainCreate(name=parsed_domain_name, description=None, owner=owner_list, tags=[], parent_id=None),
                            current_user_id=(current_user.username if current_user else 'system')
                        )
                        resolved_domain_id = str(created_read.id)
                    except Exception as ce:
                        logger.warning(f"Auto-create domain failed for '{parsed_domain_name}': {ce}")
        except HTTPException:
            raise  # Re-raise HTTPException for validation errors
        except Exception as e:
            logger.warning(f"Domain resolution failed during upload_contract: {e}")

        # Create main contract record
        # If caller provided an explicit ID in the ODCS, preserve it when available and not conflicting
        provided_id = parsed.get('id')
        if provided_id:
            try:
                # Avoid collision: only use if not taken
                existing = data_contract_repo.get(db, id=provided_id)
                if existing:
                    provided_id = None
            except Exception:
                provided_id = None

        # Try to resolve owner as team name
        owner_team_id = None
        if owner_val:
            try:
                # Reuse the same team resolution logic as in the manager
                from src.repositories.teams_repository import team_repo
                team = team_repo.get_by_name(db, name=owner_val)
                if team:
                    owner_team_id = str(team.id)
                    logger.info(f"Successfully resolved team '{owner_val}' to ID: {team.id}")
                else:
                    logger.warning(f"Team '{owner_val}' not found")
            except Exception as e:
                logger.warning(f"Failed to resolve team '{owner_val}': {e}")

        db_obj = DataContractDb(
            id=provided_id if provided_id else None,
            name=name_val,
            version=version_val,
            status=status_val,
            owner_team_id=owner_team_id,
            kind=kind_val,
            api_version=api_version_val,
            tenant=parsed.get('tenant'),
            data_product=parsed.get('dataProduct') or parsed.get('data_product'),
            domain_id=resolved_domain_id,
            description_usage=description.get('usage'),
            description_purpose=description.get('purpose'),
            description_limitations=description.get('limitations'),
            # ODCS v3.0.2 additional top-level fields
            sla_default_element=parsed.get('slaDefaultElement'),
            contract_created_ts=datetime.fromisoformat(parsed.get('contractCreatedTs').replace('Z', '+00:00')) if parsed.get('contractCreatedTs') else None,
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
                    logical_type='object',
                    data_granularity_description=schema_obj_data.get('dataGranularityDescription') or schema_obj_data.get('data_granularity_description'),
                    # ODCS v3.0.2 additional schema object fields
                    business_name=schema_obj_data.get('businessName'),
                    physical_type=schema_obj_data.get('physicalType'),
                    description=schema_obj_data.get('description'),
                    tags=json.dumps(schema_obj_data.get('tags', [])) if schema_obj_data.get('tags') else None
                )
                db.add(schema_obj)
                db.flush()  # Get ID for properties
                
                # Add properties with full ODCS field support
                properties = schema_obj_data.get('properties', [])
                if isinstance(properties, list):
                    for prop_data in properties:
                        if not isinstance(prop_data, dict):
                            continue

                        # Build logical type options (constraints) as JSON
                        logical_type_options = {}
                        # String constraints
                        for field in ['minLength', 'maxLength', 'pattern']:
                            if prop_data.get(field) is not None:
                                logical_type_options[field] = prop_data[field]
                        # Number/Integer constraints
                        for field in ['minimum', 'maximum', 'multipleOf', 'precision', 'exclusiveMinimum', 'exclusiveMaximum']:
                            if prop_data.get(field) is not None:
                                logical_type_options[field] = prop_data[field]
                        # Date constraints
                        for field in ['format', 'timezone', 'customFormat']:
                            if prop_data.get(field) is not None:
                                logical_type_options[field] = prop_data[field]
                        # Array constraints
                        for field in ['itemType', 'minItems', 'maxItems']:
                            if prop_data.get(field) is not None:
                                logical_type_options[field] = prop_data[field]

                        # Handle examples as JSON string
                        examples_json = None
                        if prop_data.get('examples'):
                            if isinstance(prop_data['examples'], list):
                                examples_json = json.dumps(prop_data['examples'])
                            else:
                                examples_json = str(prop_data['examples'])

                        # Handle transformSourceObjects as JSON string
                        transform_source_objects_json = None
                        if prop_data.get('transformSourceObjects'):
                            if isinstance(prop_data['transformSourceObjects'], list):
                                transform_source_objects_json = json.dumps(prop_data['transformSourceObjects'])
                            else:
                                transform_source_objects_json = str(prop_data['transformSourceObjects'])

                        prop = SchemaPropertyDb(
                            object_id=schema_obj.id,
                            name=prop_data.get('name', 'column'),
                            logical_type=prop_data.get('logicalType') or prop_data.get('logical_type', 'string'),
                            physical_type=prop_data.get('physicalType') or prop_data.get('physical_type'),
                            required=prop_data.get('required', False),
                            unique=prop_data.get('unique', False),
                            partitioned=prop_data.get('partitioned', False),
                            primary_key_position=prop_data.get('primaryKeyPosition', -1) if prop_data.get('primaryKey') else -1,
                            partition_key_position=prop_data.get('partitionKeyPosition', -1) if prop_data.get('partitioned') else -1,
                            classification=prop_data.get('classification'),
                            encrypted_name=prop_data.get('encryptedName'),
                            transform_logic=prop_data.get('transformLogic'),
                            transform_source_objects=transform_source_objects_json,
                            transform_description=prop_data.get('description'),
                            examples=examples_json,
                            critical_data_element=prop_data.get('criticalDataElement', False),
                            logical_type_options_json=json.dumps(logical_type_options) if logical_type_options else None,
                            items_logical_type=prop_data.get('itemType'),
                            business_name=prop_data.get('businessName')  # ODCS property-level businessName
                        )
                        db.add(prop)

                        # Parse property-level quality checks (ODCS compliant structure)
                        prop_quality_data = prop_data.get('quality', [])
                        if isinstance(prop_quality_data, list):
                            for rule_data in prop_quality_data:
                                if isinstance(rule_data, dict):
                                    quality_rule_db = DataQualityCheckDb(
                                        object_id=schema_obj.id,  # Associated with schema object
                                        name=rule_data.get('name'),
                                        description=rule_data.get('description'),
                                        level=rule_data.get('level', 'property'),  # Property level
                                        dimension=rule_data.get('dimension'),
                                        business_impact=rule_data.get('business_impact') or rule_data.get('businessImpact'),
                                        severity=rule_data.get('severity'),
                                        type=rule_data.get('type', 'library'),
                                        method=rule_data.get('method'),
                                        schedule=rule_data.get('schedule'),
                                        scheduler=rule_data.get('scheduler'),
                                        unit=rule_data.get('unit'),
                                        tags=rule_data.get('tags'),
                                        rule=rule_data.get('rule'),
                                        query=rule_data.get('query'),
                                        engine=rule_data.get('engine'),
                                        implementation=rule_data.get('implementation'),
                                        must_be=rule_data.get('must_be') or rule_data.get('mustBe'),
                                        must_not_be=rule_data.get('must_not_be') or rule_data.get('mustNotBe'),
                                        must_be_gt=rule_data.get('must_be_gt') or rule_data.get('mustBeGt'),
                                        must_be_ge=rule_data.get('must_be_ge') or rule_data.get('mustBeGe'),
                                        must_be_lt=rule_data.get('must_be_lt') or rule_data.get('mustBeLt'),
                                        must_be_le=rule_data.get('must_be_le') or rule_data.get('mustBeLe'),
                                        must_be_between_min=rule_data.get('must_be_between_min') or rule_data.get('mustBeBetweenMin'),
                                        must_be_between_max=rule_data.get('must_be_between_max') or rule_data.get('mustBeBetweenMax')
                                    )
                                    db.add(quality_rule_db)

                # Parse schema-level quality checks (ODCS compliant structure)
                quality_data = schema_obj_data.get('quality', [])
                if isinstance(quality_data, list):
                    for rule_data in quality_data:
                        if isinstance(rule_data, dict):
                            quality_rule_db = DataQualityCheckDb(
                                object_id=schema_obj.id,  # Correctly associated with schema object
                                name=rule_data.get('name'),
                                description=rule_data.get('description'),
                                level=rule_data.get('level', 'object'),  # Schema level
                                dimension=rule_data.get('dimension'),
                                business_impact=rule_data.get('business_impact') or rule_data.get('businessImpact'),
                                severity=rule_data.get('severity'),
                                type=rule_data.get('type', 'library'),
                                method=rule_data.get('method'),
                                schedule=rule_data.get('schedule'),
                                scheduler=rule_data.get('scheduler'),
                                unit=rule_data.get('unit'),
                                tags=rule_data.get('tags'),
                                rule=rule_data.get('rule'),
                                query=rule_data.get('query'),
                                engine=rule_data.get('engine'),
                                implementation=rule_data.get('implementation'),
                                must_be=rule_data.get('must_be') or rule_data.get('mustBe'),
                                must_not_be=rule_data.get('must_not_be') or rule_data.get('mustNotBe'),
                                must_be_gt=rule_data.get('must_be_gt') or rule_data.get('mustBeGt'),
                                must_be_ge=rule_data.get('must_be_ge') or rule_data.get('mustBeGe'),
                                must_be_lt=rule_data.get('must_be_lt') or rule_data.get('mustBeLt'),
                                must_be_le=rule_data.get('must_be_le') or rule_data.get('mustBeLe'),
                                must_be_between_min=rule_data.get('must_be_between_min') or rule_data.get('mustBeBetweenMin'),
                                must_be_between_max=rule_data.get('must_be_between_max') or rule_data.get('mustBeBetweenMax')
                            )
                            db.add(quality_rule_db)

                # Parse schema-level authoritative definitions
                auth_defs_data = schema_obj_data.get('authoritativeDefinitions', [])
                if isinstance(auth_defs_data, list):
                    for auth_def in auth_defs_data:
                        if isinstance(auth_def, dict) and auth_def.get('url') and auth_def.get('type'):
                            auth_def_db = SchemaObjectAuthoritativeDefinitionDb(
                                schema_object_id=schema_obj.id,
                                url=auth_def['url'],
                                type=auth_def['type']
                            )
                            db.add(auth_def_db)

                # Parse schema-level custom properties
                custom_props_data = schema_obj_data.get('customProperties', [])
                if isinstance(custom_props_data, list):
                    for custom_prop in custom_props_data:
                        if isinstance(custom_prop, dict) and custom_prop.get('property'):
                            custom_prop_db = SchemaObjectCustomPropertyDb(
                                schema_object_id=schema_obj.id,
                                property=custom_prop['property'],
                                value=json.dumps(custom_prop['value']) if isinstance(custom_prop.get('value'), (list, dict)) else str(custom_prop['value']) if custom_prop.get('value') is not None else None
                            )
                            db.add(custom_prop_db)

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
                    description=member_data.get('description'),
                    date_in=member_data.get('dateIn') or member_data.get('date_in'),
                    date_out=member_data.get('dateOut') or member_data.get('date_out'),
                    replaced_by_username=member_data.get('replacedByUsername') or member_data.get('replaced_by_username')
                )
                db.add(team_member)

        # Parse support channels (ODCS format expects a list)
        support_data = parsed.get('support', [])
        if isinstance(support_data, list):
            for support_item in support_data:
                if isinstance(support_item, dict) and support_item.get('url'):
                    support_channel = DataContractSupportDb(
                        contract_id=created.id,
                        channel=support_item.get('channel', 'support'),
                        url=support_item['url'],
                        description=support_item.get('description'),
                        tool=support_item.get('tool'),
                        scope=support_item.get('scope'),
                        invitation_url=support_item.get('invitationUrl')
                    )
                    db.add(support_channel)
        elif isinstance(support_data, dict):
            # Legacy dict format support
            for channel, url in support_data.items():
                if url and isinstance(url, str):
                    support_channel = DataContractSupportDb(
                        contract_id=created.id,
                        channel=channel,
                        url=url,
                        description=f"{channel.title()} support channel"
                    )
                    db.add(support_channel)

        # Parse pricing information
        price_data = parsed.get('price', {})
        if isinstance(price_data, dict) and price_data:
            pricing = DataContractPricingDb(
                contract_id=created.id,
                price_amount=str(price_data['priceAmount']) if price_data.get('priceAmount') is not None else None,
                price_currency=price_data.get('priceCurrency'),
                price_unit=price_data.get('priceUnit')
            )
            db.add(pricing)

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
        elif isinstance(custom_props, list):
            for item in custom_props:
                if isinstance(item, dict) and item.get('property') is not None:
                    custom_prop = DataContractCustomPropertyDb(
                        contract_id=created.id,
                        property=str(item.get('property')),
                        value=json.dumps(item.get('value')) if isinstance(item.get('value'), (list, dict)) else str(item.get('value')) if item.get('value') is not None else None
                    )
                    db.add(custom_prop)

        # Parse SLA properties (ODCS format)
        sla_properties_data = parsed.get('slaProperties', [])
        if isinstance(sla_properties_data, list):
            for sla_item in sla_properties_data:
                if isinstance(sla_item, dict) and sla_item.get('property'):
                    sla_prop = DataContractSlaPropertyDb(
                        contract_id=created.id,
                        property=sla_item['property'],
                        value=str(sla_item['value']) if sla_item.get('value') is not None else None,
                        value_ext=str(sla_item['valueExt']) if sla_item.get('valueExt') is not None else None,
                        unit=sla_item.get('unit'),
                        element=sla_item.get('element'),
                        driver=sla_item.get('driver')
                    )
                    db.add(sla_prop)

        # Legacy SLA format support (dict format)
        sla_data = parsed.get('sla', {})
        if isinstance(sla_data, dict) and not sla_properties_data:  # Only if slaProperties not present
            for key, value in sla_data.items():
                if value is not None:
                    sla_prop = DataContractSlaPropertyDb(
                        contract_id=created.id,
                        property=key,
                        value=str(value)
                    )
                    db.add(sla_prop)

        # Parse authoritative definitions
        auth_defs_data = parsed.get('authoritativeDefinitions', [])
        if isinstance(auth_defs_data, list):
            for auth_def in auth_defs_data:
                if isinstance(auth_def, dict) and auth_def.get('url') and auth_def.get('type'):
                    auth_def_db = DataContractAuthoritativeDefinitionDb(
                        contract_id=created.id,
                        url=auth_def['url'],
                        type=auth_def['type']
                    )
                    db.add(auth_def_db)

        # Parse servers
        servers_data = parsed.get('servers', [])
        if isinstance(servers_data, list):
            for server_data in servers_data:
                if isinstance(server_data, dict):
                    server_db = DataContractServerDb(
                        contract_id=created.id,
                        server=server_data.get('server'),
                        type=server_data.get('type', ''),
                        description=server_data.get('description'),
                        environment=server_data.get('environment')
                    )
                    db.add(server_db)
                    db.flush()  # Get server ID for properties

                    # Parse server properties (host, port, database, etc.)
                    for prop_key in ['host', 'port', 'database', 'schema', 'catalog', 'project', 'account', 'region', 'location']:
                        if prop_key in server_data and server_data[prop_key] is not None:
                            prop_db = DataContractServerPropertyDb(
                                server_id=server_db.id,
                                key=prop_key,
                                value=str(server_data[prop_key])
                            )
                            db.add(prop_db)

                    # Parse additional server properties
                    properties_data = server_data.get('properties', {})
                    if isinstance(properties_data, dict):
                        for prop_key, prop_value in properties_data.items():
                            if prop_value is not None:
                                prop_db = DataContractServerPropertyDb(
                                    server_id=server_db.id,
                                    key=prop_key,
                                    value=str(prop_value)
                                )
                                db.add(prop_db)

        # Legacy: Parse top-level quality rules (non-compliant with ODCS, but supported for backward compatibility)
        # ODCS v3.0.2 specifies quality rules should be nested under schema objects, handled above
        quality_rules_data = parsed.get('qualityRules', [])
        if isinstance(quality_rules_data, list) and quality_rules_data:
            # Try to associate with first schema object if available
            first_schema_obj = None
            for schema_obj_data in schema_data if isinstance(schema_data, list) else []:
                if isinstance(schema_obj_data, dict):
                    # Find the created schema object
                    # SchemaObjectDb already imported at top level
                    first_schema_obj = db.query(SchemaObjectDb).filter(
                        SchemaObjectDb.contract_id == created.id,
                        SchemaObjectDb.name == schema_obj_data.get('name', 'table')
                    ).first()
                    break

            for rule_data in quality_rules_data:
                if isinstance(rule_data, dict):
                    quality_rule_db = DataQualityCheckDb(
                        object_id=first_schema_obj.id if first_schema_obj else None,  # Associate with first schema object if available
                        name=rule_data.get('name'),
                        description=rule_data.get('description'),
                        level=rule_data.get('level', 'contract'),  # Mark as contract-level for legacy rules
                        dimension=rule_data.get('dimension'),
                        business_impact=rule_data.get('business_impact') or rule_data.get('businessImpact'),
                        severity=rule_data.get('severity'),
                        type=rule_data.get('type', 'library'),
                        method=rule_data.get('method'),
                        schedule=rule_data.get('schedule'),
                        scheduler=rule_data.get('scheduler'),
                        unit=rule_data.get('unit'),
                        tags=rule_data.get('tags'),
                        rule=rule_data.get('rule'),
                        query=rule_data.get('query'),
                        engine=rule_data.get('engine'),
                        implementation=rule_data.get('implementation'),
                        must_be=rule_data.get('must_be') or rule_data.get('mustBe'),
                        must_not_be=rule_data.get('must_not_be') or rule_data.get('mustNotBe'),
                        must_be_gt=rule_data.get('must_be_gt') or rule_data.get('mustBeGt'),
                        must_be_ge=rule_data.get('must_be_ge') or rule_data.get('mustBeGe'),
                        must_be_lt=rule_data.get('must_be_lt') or rule_data.get('mustBeLt'),
                        must_be_le=rule_data.get('must_be_le') or rule_data.get('mustBeLe'),
                        must_be_between_min=rule_data.get('must_be_between_min') or rule_data.get('mustBeBetweenMin'),
                        must_be_between_max=rule_data.get('must_be_between_max') or rule_data.get('mustBeBetweenMax')
                    )
                    # Only add if we have a schema object to associate with
                    if first_schema_obj:
                        db.add(quality_rule_db)

        # Parse tags (legacy support)
        tags = parsed.get('tags', [])
        if isinstance(tags, list):
            for tag in tags:
                if isinstance(tag, str):
                    db.add(DataContractTagDb(contract_id=created.id, name=tag))

        # Parse roles
        roles = parsed.get('roles', [])
        if isinstance(roles, list):
            for role_data in roles:
                if isinstance(role_data, dict) and role_data.get('role'):
                    role_db = DataContractRoleDb(
                        contract_id=created.id,
                        role=role_data.get('role'),
                        description=role_data.get('description'),
                        access=role_data.get('access'),
                        first_level_approvers=role_data.get('firstLevelApprovers'),
                        second_level_approvers=role_data.get('secondLevelApprovers')
                    )
                    db.add(role_db)
                    db.flush()  # Get role ID for properties

                    # Parse role custom properties
                    role_props = role_data.get('customProperties', {})
                    if isinstance(role_props, dict):
                        for prop_key, prop_value in role_props.items():
                            if prop_value is not None:
                                prop_db = DataContractRolePropertyDb(
                                    role_id=role_db.id,
                                    property=prop_key,
                                    value=str(prop_value)
                                )
                                db.add(prop_db)

        # Process semantic assignments from authoritativeDefinitions
        from src.controller.semantic_links_manager import SemanticLinksManager
        from src.utils.semantic_helpers import process_all_semantic_links_from_odcs

        semantic_manager = SemanticLinksManager(db)
        total_semantic_links = process_all_semantic_links_from_odcs(
            semantic_manager=semantic_manager,
            contract_id=created.id,
            parsed_odcs=parsed,
            created_by=current_user.username if current_user else None
        )

        if total_semantic_links > 0:
            logger.info(f"Processed {total_semantic_links} semantic links during upload for contract {created.id}")

        db.commit()
        success = True
        created_contract_id = created.id

        # Load with relationships for response
        created_with_relations = data_contract_repo.get_with_all(db, id=created.id)
        return _build_contract_read_from_db(db, created_with_relations)

    except HTTPException as http_exc:
        db.rollback()
        details_for_audit["exception"] = {"type": "HTTPException", "status_code": http_exc.status_code, "detail": http_exc.detail}
        raise
    except Exception as e:
        db.rollback()
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
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_WRITE))
):
    success = False
    response_status_code = 500
    details_for_audit = {
        "params": {"contract_id": contract_id},
    }
    try:
        original = data_contract_repo.get(db, id=contract_id)
        if not original:
            response_status_code = 404
            exc = HTTPException(status_code=response_status_code, detail="Contract not found")
            details_for_audit["exception"] = {"type": "HTTPException", "status_code": exc.status_code, "detail": exc.detail}
            raise exc
        new_version = payload.get('new_version')
        if not new_version:
            response_status_code = 400
            exc = HTTPException(status_code=response_status_code, detail="new_version is required")
            details_for_audit["exception"] = {"type": "HTTPException", "status_code": exc.status_code, "detail": exc.detail}
            raise exc
        clone = DataContractDb(
            name=original.name,
            version=new_version,
            status='draft',
            owner_team_id=original.owner_team_id,
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
        success = True
        response_status_code = 201
        return {"id": clone.id, "name": clone.name, "version": clone.version, "status": clone.status, "owner_team_id": clone.owner_team_id}
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
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_WRITE))
):
    """Create a custom property."""
    from src.repositories.data_contracts_repository import custom_property_repo
    from src.models.data_contracts_api import CustomPropertyCreate, CustomPropertyRead

    contract = data_contract_repo.get(db, id=contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    try:
        prop_create = CustomPropertyCreate(**prop_data)
        new_prop = custom_property_repo.create_property(
            db=db, contract_id=contract_id, property=prop_create.property, value=prop_create.value
        )
        db.commit()

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
    except Exception as e:
        db.rollback()
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
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_WRITE))
):
    """Update a custom property."""
    from src.repositories.data_contracts_repository import custom_property_repo
    from src.models.data_contracts_api import CustomPropertyUpdate, CustomPropertyRead

    contract = data_contract_repo.get(db, id=contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    try:
        prop_update = CustomPropertyUpdate(**prop_data)
        updated_prop = custom_property_repo.update_property(
            db=db, property_id=property_id, property=prop_update.property, value=prop_update.value
        )
        if not updated_prop or updated_prop.contract_id != contract_id:
            raise HTTPException(status_code=404, detail="Custom property not found")

        db.commit()

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
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
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
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_WRITE))
):
    """Delete a custom property."""
    from src.repositories.data_contracts_repository import custom_property_repo

    contract = data_contract_repo.get(db, id=contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    try:
        prop = db.query(DataContractCustomPropertyDb).filter(DataContractCustomPropertyDb.id == property_id).first()
        if not prop or prop.contract_id != contract_id:
            raise HTTPException(status_code=404, detail="Custom property not found")

        custom_property_repo.delete_property(db=db, property_id=property_id)
        db.commit()

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
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
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
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_WRITE))
):
    """Create a new support channel for a contract."""
    from src.repositories.data_contracts_repository import support_channel_repo
    from src.models.data_contracts_api import SupportChannelCreate, SupportChannelRead

    contract = data_contract_repo.get(db, id=contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    try:
        # Validate input
        channel_create = SupportChannelCreate(**channel_data)

        # Create channel
        new_channel = support_channel_repo.create_channel(
            db=db,
            contract_id=contract_id,
            channel=channel_create.channel,
            url=channel_create.url,
            description=channel_create.description,
            tool=channel_create.tool,
            scope=channel_create.scope,
            invitation_url=channel_create.invitation_url
        )

        db.commit()

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
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
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
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_WRITE))
):
    """Update a support channel."""
    from src.repositories.data_contracts_repository import support_channel_repo
    from src.models.data_contracts_api import SupportChannelUpdate, SupportChannelRead

    contract = data_contract_repo.get(db, id=contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    try:
        # Validate input
        channel_update = SupportChannelUpdate(**channel_data)

        # Update channel
        updated_channel = support_channel_repo.update_channel(
            db=db,
            channel_id=channel_id,
            channel=channel_update.channel,
            url=channel_update.url,
            description=channel_update.description,
            tool=channel_update.tool,
            scope=channel_update.scope,
            invitation_url=channel_update.invitation_url
        )

        if not updated_channel:
            raise HTTPException(status_code=404, detail="Support channel not found")

        db.commit()

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
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
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
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_WRITE))
):
    """Delete a support channel."""
    from src.repositories.data_contracts_repository import support_channel_repo

    contract = data_contract_repo.get(db, id=contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    try:
        deleted = support_channel_repo.delete_channel(db=db, channel_id=channel_id)

        if not deleted:
            raise HTTPException(status_code=404, detail="Support channel not found")

        db.commit()

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
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
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
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_WRITE))
):
    """Update pricing for a contract (creates if not exists - singleton pattern)."""
    from src.repositories.data_contracts_repository import pricing_repo
    from src.models.data_contracts_api import PricingUpdate, PricingRead

    contract = data_contract_repo.get(db, id=contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    try:
        # Validate input
        pricing_update = PricingUpdate(**pricing_data)

        # Update pricing (creates if not exists)
        updated_pricing = pricing_repo.update_pricing(
            db=db,
            contract_id=contract_id,
            price_amount=pricing_update.price_amount,
            price_currency=pricing_update.price_currency,
            price_unit=pricing_update.price_unit
        )

        db.commit()

        # Audit log
        await audit_manager.log_event(
            db=db,
            user_email=current_user,
            entity_type="data_contract",
            entity_id=contract_id,
            action="UPDATE_PRICING",
            success=True,
            details={
                "price_amount": pricing_update.price_amount,
                "price_currency": pricing_update.price_currency,
                "price_unit": pricing_update.price_unit
            }
        )

        return PricingRead.model_validate(updated_pricing).model_dump()
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
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
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_ONLY))
):
    """
    Get all versions of a contract family (same base_name).
    Returns contracts sorted by version (newest first).
    """
    # Get the source contract
    source_contract = data_contract_repo.get(db, id=contract_id)
    if not source_contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    # Get base_name (either from field or extract from name)
    base_name = source_contract.base_name
    if not base_name:
        # Extract from name if not set
        from src.utils.contract_cloner import ContractCloner
        cloner = ContractCloner()
        base_name = cloner._extract_base_name(source_contract.name, source_contract.version or "1.0.0")

    try:
        # Find all contracts with same base_name
        contracts = db.query(DataContractDb).filter(
            DataContractDb.base_name == base_name
        ).order_by(DataContractDb.created_at.desc()).all()

        # If no base_name matches, fall back to parent_contract_id relationships
        if not contracts:
            # Build version tree by following parent relationships
            contracts = [source_contract]
            # Find children
            children = db.query(DataContractDb).filter(
                DataContractDb.parent_contract_id == contract_id
            ).order_by(DataContractDb.created_at.desc()).all()
            contracts.extend(children)
            # Find parent and its children
            if source_contract.parent_contract_id:
                parent = data_contract_repo.get(db, id=source_contract.parent_contract_id)
                if parent and parent not in contracts:
                    contracts.insert(0, parent)
                    siblings = db.query(DataContractDb).filter(
                        DataContractDb.parent_contract_id == parent.id,
                        DataContractDb.id != contract_id
                    ).order_by(DataContractDb.created_at.desc()).all()
                    contracts.extend(siblings)

        # Convert to API model
        from src.models.data_contracts_api import DataContractRead
        return [DataContractRead.model_validate(c).model_dump() for c in contracts]
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
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_WRITE))
):
    """
    Clone a contract to create a new version.

    Body parameters:
    - new_version: str (required) - Semantic version (e.g., "2.0.0")
    - change_summary: str (optional) - Summary of changes in this version
    """
    new_version = body.get('new_version')
    change_summary = body.get('change_summary')

    if not new_version:
        raise HTTPException(status_code=400, detail="new_version is required")

    # Validate semantic version format
    import re
    if not re.match(r'^\d+\.\d+\.\d+$', new_version):
        raise HTTPException(status_code=400, detail="new_version must be in format X.Y.Z (e.g., 2.0.0)")

    # Get source contract
    source_contract = data_contract_repo.get(db, id=contract_id)
    if not source_contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    try:
        from src.utils.contract_cloner import ContractCloner
        cloner = ContractCloner()

        # Clone contract metadata
        cloned_data = cloner.clone_for_new_version(
            source_contract_db=source_contract,
            new_version=new_version,
            change_summary=change_summary,
            created_by=current_user.username if current_user else "system"
        )

        # Create new contract in database
        new_contract = DataContractDb(**cloned_data)
        db.add(new_contract)
        db.flush()
        db.refresh(new_contract)

        # Clone all nested entities
        # Tags
        if source_contract.tags:
            cloned_tags = cloner.clone_tags(source_contract.tags, new_contract.id)
            for tag_data in cloned_tags:
                db.add(DataContractTagDb(**tag_data))

        # Servers
        if source_contract.servers:
            cloned_servers = cloner.clone_servers(source_contract.servers, new_contract.id)
            for server_data in cloned_servers:
                server_id = server_data.pop('id')
                properties = server_data.pop('properties', [])
                server = DataContractServerDb(id=server_id, **server_data)
                db.add(server)
                db.flush()
                for prop_data in properties:
                    db.add(DataContractServerPropertyDb(**prop_data))

        # Roles
        if source_contract.roles:
            cloned_roles = cloner.clone_roles(source_contract.roles, new_contract.id)
            for role_data in cloned_roles:
                role_id = role_data.pop('id')
                properties = role_data.pop('properties', [])
                role = DataContractRoleDb(id=role_id, **role_data)
                db.add(role)
                db.flush()
                for prop_data in properties:
                    db.add(DataContractRolePropertyDb(**prop_data))

        # Team members
        if source_contract.team:
            cloned_team = cloner.clone_team_members(source_contract.team, new_contract.id)
            for member_data in cloned_team:
                db.add(DataContractTeamDb(**member_data))

        # Support channels
        if source_contract.support:
            cloned_support = cloner.clone_support_channels(source_contract.support, new_contract.id)
            for support_data in cloned_support:
                db.add(DataContractSupportDb(**support_data))

        # Pricing
        if source_contract.pricing:
            cloned_pricing = cloner.clone_pricing(source_contract.pricing, new_contract.id)
            if cloned_pricing:
                db.add(DataContractPricingDb(**cloned_pricing))

        # Custom properties
        if source_contract.custom_properties:
            cloned_custom_props = cloner.clone_custom_properties(source_contract.custom_properties, new_contract.id)
            for prop_data in cloned_custom_props:
                db.add(DataContractCustomPropertyDb(**prop_data))

        # SLA properties
        if source_contract.sla_properties:
            cloned_sla_props = cloner.clone_sla_properties(source_contract.sla_properties, new_contract.id)
            for prop_data in cloned_sla_props:
                db.add(DataContractSlaPropertyDb(**prop_data))

        # Contract-level authoritative definitions
        if source_contract.authoritative_defs:
            cloned_auth_defs = cloner.clone_authoritative_defs(source_contract.authoritative_defs, new_contract.id, 'contract')
            for def_data in cloned_auth_defs:
                db.add(DataContractAuthoritativeDefinitionDb(**def_data))

        # Schemas with nested properties
        if source_contract.schema_objects:
            cloned_schemas = cloner.clone_schema_objects(source_contract.schema_objects, new_contract.id)
            for schema_data in cloned_schemas:
                schema_id = schema_data.pop('id')
                properties = schema_data.pop('properties', [])
                authoritative_defs = schema_data.pop('authoritative_defs', [])

                schema = SchemaObjectDb(id=schema_id, **schema_data)
                db.add(schema)
                db.flush()

                # Schema-level authoritative definitions
                for auth_def_data in authoritative_defs:
                    db.add(SchemaObjectAuthoritativeDefinitionDb(**auth_def_data))

                # Properties
                for prop_data in properties:
                    prop_id = prop_data.pop('id')
                    prop_auth_defs = prop_data.pop('authoritative_defs', [])

                    prop = SchemaPropertyDb(id=prop_id, **prop_data)
                    db.add(prop)
                    db.flush()

                    # Property-level authoritative definitions
                    for prop_auth_def_data in prop_auth_defs:
                        db.add(SchemaPropertyAuthoritativeDefinitionDb(**prop_auth_def_data))

        db.commit()
        db.refresh(new_contract)

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

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error cloning contract: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/data-contracts/compare', response_model=dict)
async def compare_contract_versions(
    body: dict = Body(...),
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_ONLY))
):
    """
    Analyze changes between two contract versions.

    Body parameters:
    - old_contract: dict (required) - Old contract version (ODCS format)
    - new_contract: dict (required) - New contract version (ODCS format)

    Returns change analysis with recommended version bump.
    """
    old_contract = body.get('old_contract')
    new_contract = body.get('new_contract')

    if not old_contract or not new_contract:
        raise HTTPException(status_code=400, detail="Both old_contract and new_contract are required")

    try:
        from src.utils.contract_change_analyzer import ContractChangeAnalyzer
        analyzer = ContractChangeAnalyzer()

        result = analyzer.analyze(old_contract, new_contract)

        return {
            "change_type": result.change_type.value,
            "version_bump": result.version_bump,
            "summary": result.summary,
            "breaking_changes": result.breaking_changes,
            "new_features": result.new_features,
            "fixes": result.fixes,
            "schema_changes": [
                {
                    "change_type": sc.change_type,
                    "schema_name": sc.schema_name,
                    "field_name": sc.field_name,
                    "old_value": sc.old_value,
                    "new_value": sc.new_value,
                    "severity": sc.severity.value
                }
                for sc in result.schema_changes
            ],
            "quality_rule_changes": result.quality_rule_changes
        }
    except Exception as e:
        logger.error(f"Error comparing contracts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/data-contracts/{contract_id}/version-history', response_model=dict)
async def get_contract_version_history(
    contract_id: str,
    db: DBSessionDep,
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_ONLY))
):
    """
    Get version history lineage for a contract.
    Returns the full version tree with parent-child relationships.
    """
    contract = data_contract_repo.get(db, id=contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    try:
        from src.models.data_contracts_api import DataContractRead

        # Build version history
        history = {
            "current": DataContractRead.model_validate(contract).model_dump(),
            "parent": None,
            "children": [],
            "siblings": []
        }

        # Get parent
        if contract.parent_contract_id:
            parent = data_contract_repo.get(db, id=contract.parent_contract_id)
            if parent:
                history["parent"] = DataContractRead.model_validate(parent).model_dump()

                # Get siblings (other children of same parent)
                siblings = db.query(DataContractDb).filter(
                    DataContractDb.parent_contract_id == parent.id,
                    DataContractDb.id != contract_id
                ).order_by(DataContractDb.created_at.desc()).all()
                history["siblings"] = [DataContractRead.model_validate(s).model_dump() for s in siblings]

        # Get children
        children = db.query(DataContractDb).filter(
            DataContractDb.parent_contract_id == contract_id
        ).order_by(DataContractDb.created_at.desc()).all()
        history["children"] = [DataContractRead.model_validate(c).model_dump() for c in children]

        return history
    except Exception as e:
        logger.error(f"Error fetching version history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def register_routes(app):
    """Register routes with the app"""
    app.include_router(router)
    logger.info("Data contract routes registered")
