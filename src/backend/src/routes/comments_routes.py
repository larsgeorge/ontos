from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from src.common.dependencies import DBSessionDep, CurrentUserDep
from src.common.features import FeatureAccessLevel
from src.common.authorization import PermissionChecker, get_user_groups
from src.common.logging import get_logger
from src.controller.comments_manager import CommentsManager
from src.controller.change_log_manager import change_log_manager
from src.common.manager_dependencies import get_comments_manager
from src.models.comments import Comment, CommentCreate, CommentUpdate, CommentListResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["Comments"])

# Comments can be created on any object, so we use a generic feature for now
FEATURE_ID = "data-domains"  # Use domain feature for now; can widen later


@router.post("/entities/{entity_type}/{entity_id}/comments", response_model=Comment, status_code=status.HTTP_201_CREATED)
async def create_comment(
    entity_type: str,
    entity_id: str,
    payload: CommentCreate,
    db: DBSessionDep,
    current_user: CurrentUserDep,
    manager: CommentsManager = Depends(get_comments_manager),
    _: bool = Depends(PermissionChecker(FEATURE_ID, FeatureAccessLevel.READ_WRITE)),
):
    """Create a comment on an entity."""
    try:
        # Validate that path matches payload
        if payload.entity_type != entity_type or payload.entity_id != entity_id:
            raise HTTPException(
                status_code=400, 
                detail="Entity path does not match request body"
            )
        
        return manager.create_comment(db, data=payload, user_email=current_user.email)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed creating comment")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/entities/{entity_type}/{entity_id}/comments", response_model=CommentListResponse)
async def list_comments(
    entity_type: str,
    entity_id: str,
    db: DBSessionDep,
    current_user: CurrentUserDep,
    include_deleted: bool = Query(False, description="Include soft-deleted comments (admin only)"),
    manager: CommentsManager = Depends(get_comments_manager),
    _: bool = Depends(PermissionChecker(FEATURE_ID, FeatureAccessLevel.READ_ONLY)),
):
    """List comments for an entity, filtered by user's visibility permissions."""
    try:
        # Get user's groups for audience filtering
        user_groups = await get_user_groups(current_user.email)
        
        # Only admins can see deleted comments
        if include_deleted:
            # Check if user is admin (simplified - in production you'd check permissions properly)
            is_admin = "admin" in [group.lower() for group in user_groups] if user_groups else False
            if not is_admin:
                include_deleted = False
        
        return manager.list_comments(
            db,
            entity_type=entity_type,
            entity_id=entity_id,
            user_groups=user_groups,
            include_deleted=include_deleted
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed listing comments")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/entities/{entity_type}/{entity_id}/timeline/count")
async def get_entity_timeline_count(
    entity_type: str,
    entity_id: str,
    db: DBSessionDep,
    current_user: CurrentUserDep,
    include_deleted: bool = Query(False, description="Include soft-deleted comments (admin only)"),
    filter_type: str = Query("all", description="Filter type: 'all', 'comments', 'changes'"),
    manager: CommentsManager = Depends(get_comments_manager),
    _: bool = Depends(PermissionChecker(FEATURE_ID, FeatureAccessLevel.READ_ONLY)),
):
    """Get count of timeline entries for an entity without fetching full data."""
    try:
        total_count = 0

        # Get user's groups for audience filtering
        user_groups = await get_user_groups(current_user.email)
        is_admin = "admin" in [group.lower() for group in user_groups] if user_groups else False

        if filter_type in ("all", "comments"):
            # Get comments count
            if include_deleted and not is_admin:
                include_deleted = False

            comments_response = manager.list_comments(
                db,
                entity_type=entity_type,
                entity_id=entity_id,
                user_groups=user_groups,
                include_deleted=include_deleted
            )
            total_count += len(comments_response.comments)

        if filter_type in ("all", "changes"):
            # Get change log entries count
            change_entries = change_log_manager.list_changes_for_entity(
                db,
                entity_type=entity_type,
                entity_id=entity_id,
                limit=10000  # High limit to get actual count
            )
            total_count += len(change_entries)

        return {
            "total_count": total_count,
            "filter_type": filter_type
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed getting entity timeline count")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/entities/{entity_type}/{entity_id}/timeline")
async def get_entity_timeline(
    entity_type: str,
    entity_id: str,
    db: DBSessionDep,
    current_user: CurrentUserDep,
    include_deleted: bool = Query(False, description="Include soft-deleted comments (admin only)"),
    filter_type: str = Query("all", description="Filter type: 'all', 'comments', 'changes'"),
    limit: int = Query(100, ge=1, le=1000, description="Max number of entries"),
    manager: CommentsManager = Depends(get_comments_manager),
    _: bool = Depends(PermissionChecker(FEATURE_ID, FeatureAccessLevel.READ_ONLY)),
):
    """Get a unified timeline of comments and change log entries for an entity."""
    try:
        timeline_entries = []
        
        # Get user's groups for audience filtering
        user_groups = await get_user_groups(current_user.email)
        is_admin = "admin" in [group.lower() for group in user_groups] if user_groups else False
        
        if filter_type in ("all", "comments"):
            # Get comments
            if include_deleted and not is_admin:
                include_deleted = False
                
            comments_response = manager.list_comments(
                db,
                entity_type=entity_type,
                entity_id=entity_id,
                user_groups=user_groups,
                include_deleted=include_deleted
            )
            
            # Convert comments to timeline format
            for comment in comments_response.comments:
                timeline_entries.append({
                    "id": comment.id,
                    "type": "comment",
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "title": comment.title,
                    "content": comment.comment,
                    "username": comment.created_by,
                    "timestamp": comment.created_at.isoformat(),
                    "updated_at": comment.updated_at.isoformat() if comment.updated_at != comment.created_at else None,
                    "audience": comment.audience,
                    "status": comment.status,
                    "metadata": {
                        "updated_by": comment.updated_by if comment.updated_by != comment.created_by else None
                    }
                })
        
        if filter_type in ("all", "changes"):
            # Get change log entries
            change_entries = change_log_manager.list_changes_for_entity(
                db,
                entity_type=entity_type,
                entity_id=entity_id,
                limit=limit
            )
            
            # Convert change log entries to timeline format
            for change in change_entries:
                timeline_entries.append({
                    "id": change.id,
                    "type": "change",
                    "entity_type": change.entity_type,
                    "entity_id": change.entity_id,
                    "title": f"{change.action.replace('_', ' ').title()}",
                    "content": change.details_json or f"{change.action} performed on {change.entity_type}",
                    "username": change.username,
                    "timestamp": change.timestamp.isoformat(),
                    "updated_at": None,
                    "audience": None,
                    "status": None,
                    "metadata": {
                        "action": change.action
                    }
                })
        
        # Sort by timestamp (newest first)
        timeline_entries.sort(key=lambda x: x["timestamp"], reverse=True)

        # Calculate total count before applying limit
        total_count = len(timeline_entries)

        # Apply limit
        if len(timeline_entries) > limit:
            timeline_entries = timeline_entries[:limit]

        return {
            "timeline": timeline_entries,
            "total_count": total_count,
            "filter_type": filter_type
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed getting entity timeline")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/comments/{comment_id}", response_model=Comment)
async def get_comment(
    comment_id: str,
    db: DBSessionDep,
    manager: CommentsManager = Depends(get_comments_manager),
    _: bool = Depends(PermissionChecker(FEATURE_ID, FeatureAccessLevel.READ_ONLY)),
):
    """Get a single comment by ID."""
    comment = manager.get_comment(db, comment_id=comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    return comment


@router.put("/comments/{comment_id}", response_model=Comment)
async def update_comment(
    comment_id: str,
    payload: CommentUpdate,
    db: DBSessionDep,
    current_user: CurrentUserDep,
    manager: CommentsManager = Depends(get_comments_manager),
    _: bool = Depends(PermissionChecker(FEATURE_ID, FeatureAccessLevel.READ_WRITE)),
):
    """Update a comment. Only the comment author or admins can update."""
    try:
        # Get user's groups to check for admin status
        user_groups = await get_user_groups(current_user.email)
        is_admin = "admin" in [group.lower() for group in user_groups] if user_groups else False
        
        updated = manager.update_comment(
            db,
            comment_id=comment_id,
            data=payload,
            user_email=current_user.email,
            is_admin=is_admin
        )
        
        if not updated:
            raise HTTPException(
                status_code=404, 
                detail="Comment not found or you don't have permission to update it"
            )
        
        return updated
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed updating comment")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: str,
    db: DBSessionDep,
    current_user: CurrentUserDep,
    hard_delete: bool = Query(False, description="Permanently delete comment (admin only)"),
    manager: CommentsManager = Depends(get_comments_manager),
    _: bool = Depends(PermissionChecker(FEATURE_ID, FeatureAccessLevel.READ_WRITE)),
):
    """Delete a comment. Only the comment author or admins can delete."""
    try:
        # Get user's groups to check for admin status
        user_groups = await get_user_groups(current_user.email)
        is_admin = "admin" in [group.lower() for group in user_groups] if user_groups else False
        
        # Only admins can hard delete
        if hard_delete and not is_admin:
            hard_delete = False
        
        success = manager.delete_comment(
            db,
            comment_id=comment_id,
            user_email=current_user.email,
            is_admin=is_admin,
            hard_delete=hard_delete
        )
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail="Comment not found or you don't have permission to delete it"
            )
        
        return  # 204 No Content
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed deleting comment")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/comments/{comment_id}/permissions")
async def check_comment_permissions(
    comment_id: str,
    db: DBSessionDep,
    current_user: CurrentUserDep,
    manager: CommentsManager = Depends(get_comments_manager),
    _: bool = Depends(PermissionChecker(FEATURE_ID, FeatureAccessLevel.READ_ONLY)),
):
    """Check if current user can modify a specific comment."""
    try:
        # Get user's groups to check for admin status
        user_groups = await get_user_groups(current_user.email)
        is_admin = "admin" in [group.lower() for group in user_groups] if user_groups else False
        
        can_modify = manager.can_user_modify_comment(
            db,
            comment_id=comment_id,
            user_email=current_user.email,
            is_admin=is_admin
        )
        
        return {
            "can_modify": can_modify,
            "is_admin": is_admin
        }
    except Exception as e:
        logger.exception("Failed checking comment permissions")
        raise HTTPException(status_code=500, detail=str(e))


def register_routes(app):
    """Register comment routes with the FastAPI app."""
    app.include_router(router)
    logger.info("Comments routes registered with prefix /api")