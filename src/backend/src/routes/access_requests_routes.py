import uuid
from datetime import datetime
from typing import List, Optional, Literal

from fastapi import APIRouter, Body, Depends, HTTPException, status

from src.common.dependencies import (
    DBSessionDep,
    CurrentUserDep,
    NotificationsManagerDep,
)
from src.controller.change_log_manager import change_log_manager
from src.models.notifications import NotificationType, Notification
from src.models.comments import CommentCreate
from src.controller.comments_manager import CommentsManager
from src.common.manager_dependencies import get_comments_manager
from pydantic import BaseModel, Field


router = APIRouter(prefix="/api", tags=["access-requests"])


class CreateAccessRequest(BaseModel):
    entity_type: Literal["data_product", "data_contract"] = Field(...)
    entity_ids: List[str] = Field(..., min_length=1)
    message: Optional[str] = None


class HandleAccessRequest(BaseModel):
    entity_type: Literal["data_product", "data_contract"] = Field(...)
    entity_id: str = Field(...)
    requester_email: str = Field(...)
    decision: Literal["approve", "deny", "clarify"] = Field(...)
    message: Optional[str] = None


@router.post("/access-requests", status_code=status.HTTP_202_ACCEPTED)
async def create_access_request(
    db: DBSessionDep,
    current_user: CurrentUserDep,
    notifications: NotificationsManagerDep,
    payload: CreateAccessRequest = Body(...),
):
    """Create one or multiple access requests for a given entity type.
    Emits actionable notifications to Admin role and a receipt to the requester.
    Also records a change log entry per entity.
    """
    try:
        requester_email = current_user.email
        if not requester_email:
            raise HTTPException(status_code=400, detail="Requester email not found.")

        if len(payload.entity_ids) == 0:
            raise HTTPException(status_code=400, detail="No entity IDs provided")

        now = datetime.utcnow()

        # Notify requester (receipt)
        requester_note = Notification(
            id=str(uuid.uuid4()),
            created_at=now,
            type=NotificationType.INFO,
            title="Access Request Submitted",
            subtitle=f"{payload.entity_type} ({len(payload.entity_ids)} item(s))",
            description=f"Your access request has been submitted for review.{' Reason: ' + payload.message if payload.message else ''}",
            recipient=requester_email,
            can_delete=True,
        )
        notifications.create_notification(notification=requester_note, db=db)

        # Notify approvers (Admins or Stewards) via actionable notification
        # Use recipient as role name "Admin" to leverage role-based filtering
        for entity_id in payload.entity_ids:
            action_payload = {
                "entity_type": payload.entity_type,
                "entity_id": entity_id,
                "requester_email": requester_email,
            }
            admin_note = Notification(
                id=str(uuid.uuid4()),
                created_at=now,
                type=NotificationType.ACTION_REQUIRED,
                title="Access Request Received",
                subtitle=f"From: {requester_email}",
                description=f"Review access request for {payload.entity_type} {entity_id}" + (f"\n\nReason: {payload.message}" if payload.message else ""),
                recipient="Admin",
                action_type="handle_access_request",
                action_payload=action_payload,
                can_delete=False,
            )
            notifications.create_notification(notification=admin_note, db=db)

            # Change log entry so it appears in entity timeline
            change_log_manager.log_change_with_details(
                db,
                entity_type=payload.entity_type,
                entity_id=entity_id,
                action="access_request_created",
                username=current_user.username if current_user else None,
                details={
                    "requester_email": requester_email,
                    "message": payload.message,
                    "reason": payload.message,  # Add explicit reason field for better display
                    "timestamp": now.isoformat(),
                    "summary": f"Access request from {requester_email}" + (f": {payload.message}" if payload.message else ""),
                },
            )

        return {"message": "Access request submitted."}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/access-requests/handle", status_code=status.HTTP_200_OK)
async def handle_access_request(
    db: DBSessionDep,
    current_user: CurrentUserDep,
    notifications: NotificationsManagerDep,
    request_data: HandleAccessRequest = Body(...),
    comments_manager: CommentsManager = Depends(get_comments_manager),
):
    """Handle an access request decision by approvers (approve/deny/clarify)."""
    try:
        decision = request_data.decision
        requester = request_data.requester_email
        now = datetime.utcnow()
        # Mark any actionable notifications for this request as handled/read (best-effort)
        try:
            notifications.handle_actionable_notification(
                db=db,
                action_type="handle_access_request",
                action_payload={
                    "entity_type": request_data.entity_type,
                    "entity_id": request_data.entity_id,
                    "requester_email": requester,
                },
            )
        except Exception:
            pass

        # Notify requester with decision outcome
        decision_title = {
            "approve": "Access Request Approved",
            "deny": "Access Request Denied",
            "clarify": "Access Request Needs Clarification",
        }[decision]
        description = request_data.message or (
            "Your access request was approved." if decision == "approve"
            else "Your access request was denied." if decision == "deny"
            else "Please provide more information for your access request."
        )

        requester_note = Notification(
            id=str(uuid.uuid4()),
            created_at=now,
            type=NotificationType.INFO,
            title=decision_title,
            subtitle=f"{request_data.entity_type} {request_data.entity_id}",
            description=description,
            recipient=requester,
            can_delete=True,
        )
        notifications.create_notification(notification=requester_note, db=db)

        # Record change-log entry
        change_action = {
            "approve": "access_request_approved",
            "deny": "access_request_denied",
            "clarify": "access_request_clarification_requested",
        }[decision]

        change_log_manager.log_change_with_details(
            db,
            entity_type=request_data.entity_type,
            entity_id=request_data.entity_id,
            action=change_action,
            username=current_user.username if current_user else None,
            details={
                "requester_email": requester,
                "decision": decision,
                "message": request_data.message,
                "admin_response": request_data.message,  # Add explicit admin response field
                "summary": f"Access request {decision} for {requester}" + (f": {request_data.message}" if request_data.message else ""),
            },
        )

        # For clarification, also add a targeted comment visible only to the requester
        if decision == "clarify":
            comment_payload = CommentCreate(
                entity_id=request_data.entity_id,
                entity_type=request_data.entity_type,
                title="Clarification Requested",
                comment=request_data.message or "More information is required to review your access request.",
                audience=[f"user:{requester}"]
            )
            comments_manager.create_comment(db, data=comment_payload, user_email=current_user.email or current_user.username or "system")

        return {"message": "Decision recorded."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def register_routes(app):
    app.include_router(router)
    

