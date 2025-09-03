from typing import List, Optional
import json

from sqlalchemy.orm import Session

from src.common.logging import get_logger
from src.models.comments import Comment, CommentCreate, CommentUpdate, CommentListResponse
from src.repositories.comments_repository import comments_repo, CommentsRepository
from src.repositories.change_log_repository import change_log_repo
from src.db_models.change_log import ChangeLogDb
from src.db_models.comments import CommentStatus

logger = get_logger(__name__)


class CommentsManager:
    def __init__(self, comments_repository: CommentsRepository = comments_repo):
        self._comments_repo = comments_repository

    def _log_change(
        self, 
        db: Session, 
        *, 
        entity_type: str, 
        entity_id: str, 
        action: str, 
        username: Optional[str], 
        details_json: Optional[str] = None
    ) -> None:
        """Log changes to the change log."""
        entry = ChangeLogDb(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            username=username,
            details_json=details_json,
        )
        db.add(entry)
        db.commit()

    def _convert_audience_from_json(self, comment_db) -> Optional[List[str]]:
        """Convert JSON audience string back to list."""
        if comment_db.audience is None:
            return None
        try:
            return json.loads(comment_db.audience)
        except (json.JSONDecodeError, TypeError):
            logger.warning(f"Invalid JSON in comment audience: {comment_db.audience}")
            return None

    def _db_to_api_model(self, comment_db) -> Comment:
        """Convert database model to API model with proper audience handling."""
        # Create the base comment data
        comment_data = {
            "id": comment_db.id,
            "entity_id": comment_db.entity_id,
            "entity_type": comment_db.entity_type,
            "title": comment_db.title,
            "comment": comment_db.comment,
            "audience": self._convert_audience_from_json(comment_db),
            "status": comment_db.status,
            "created_by": comment_db.created_by,
            "updated_by": comment_db.updated_by,
            "created_at": comment_db.created_at,
            "updated_at": comment_db.updated_at,
        }
        return Comment(**comment_data)

    def create_comment(
        self, 
        db: Session, 
        *, 
        data: CommentCreate, 
        user_email: str
    ) -> Comment:
        """Create a new comment."""
        logger.info(f"Creating comment for {data.entity_type}:{data.entity_id} by {user_email}")
        
        db_obj = self._comments_repo.create_with_audience(
            db, obj_in=data, created_by=user_email
        )
        db.commit()
        db.refresh(db_obj)
        
        # Log the action
        self._log_change(
            db, 
            entity_type=f"{data.entity_type}:comment", 
            entity_id=data.entity_id, 
            action="CREATE", 
            username=user_email
        )
        
        return self._db_to_api_model(db_obj)

    def list_comments(
        self, 
        db: Session, 
        *, 
        entity_type: str, 
        entity_id: str,
        user_groups: Optional[List[str]] = None,
        include_deleted: bool = False
    ) -> CommentListResponse:
        """List comments for an entity, filtered by user's group membership."""
        logger.debug(f"Listing comments for {entity_type}:{entity_id}, user_groups: {user_groups}")
        
        # Get all comments (for total count)
        all_comments = self._comments_repo.list_for_entity(
            db, 
            entity_type=entity_type, 
            entity_id=entity_id,
            user_groups=None,  # Get all for count
            include_deleted=include_deleted
        )
        total_count = len(all_comments)
        
        # Get visible comments
        visible_comments = self._comments_repo.list_for_entity(
            db,
            entity_type=entity_type,
            entity_id=entity_id,
            user_groups=user_groups,
            include_deleted=include_deleted
        )
        visible_count = len(visible_comments)
        
        # Convert to API models
        api_comments = [self._db_to_api_model(comment) for comment in visible_comments]
        
        return CommentListResponse(
            comments=api_comments,
            total_count=total_count,
            visible_count=visible_count
        )

    def update_comment(
        self, 
        db: Session, 
        *, 
        comment_id: str, 
        data: CommentUpdate, 
        user_email: str,
        is_admin: bool = False
    ) -> Optional[Comment]:
        """Update a comment if user has permission."""
        logger.info(f"Updating comment {comment_id} by {user_email}")
        
        db_obj = self._comments_repo.get(db, comment_id)
        if not db_obj:
            logger.warning(f"Comment {comment_id} not found")
            return None
        
        # Check permissions
        if not self._comments_repo.can_user_modify(db_obj, user_email, is_admin):
            logger.warning(f"User {user_email} not authorized to modify comment {comment_id}")
            return None
        
        updated = self._comments_repo.update_with_audience(
            db, db_obj=db_obj, obj_in=data, updated_by=user_email
        )
        db.commit()
        db.refresh(updated)
        
        # Log the action
        self._log_change(
            db, 
            entity_type=f"{updated.entity_type}:comment", 
            entity_id=updated.entity_id, 
            action="UPDATE", 
            username=user_email
        )
        
        return self._db_to_api_model(updated)

    def delete_comment(
        self, 
        db: Session, 
        *, 
        comment_id: str, 
        user_email: str,
        is_admin: bool = False,
        hard_delete: bool = False
    ) -> bool:
        """Delete a comment if user has permission. Soft delete by default."""
        logger.info(f"Deleting comment {comment_id} by {user_email}, hard_delete={hard_delete}")
        
        db_obj = self._comments_repo.get(db, comment_id)
        if not db_obj:
            logger.warning(f"Comment {comment_id} not found")
            return False
        
        # Check permissions
        if not self._comments_repo.can_user_modify(db_obj, user_email, is_admin):
            logger.warning(f"User {user_email} not authorized to delete comment {comment_id}")
            return False
        
        entity_type, entity_id = db_obj.entity_type, db_obj.entity_id
        
        if hard_delete:
            # Permanently remove from database
            removed = self._comments_repo.remove(db, id=comment_id)
            if removed:
                db.commit()
                self._log_change(
                    db, 
                    entity_type=f"{entity_type}:comment", 
                    entity_id=entity_id, 
                    action="HARD_DELETE", 
                    username=user_email
                )
                return True
        else:
            # Soft delete - mark as deleted
            soft_deleted = self._comments_repo.soft_delete(
                db, comment_id=comment_id, deleted_by=user_email
            )
            if soft_deleted:
                db.commit()
                self._log_change(
                    db, 
                    entity_type=f"{entity_type}:comment", 
                    entity_id=entity_id, 
                    action="SOFT_DELETE", 
                    username=user_email
                )
                return True
        
        return False

    def get_comment(self, db: Session, *, comment_id: str) -> Optional[Comment]:
        """Get a single comment by ID."""
        db_obj = self._comments_repo.get(db, comment_id)
        if not db_obj:
            return None
        return self._db_to_api_model(db_obj)

    def can_user_modify_comment(
        self, 
        db: Session, 
        *, 
        comment_id: str, 
        user_email: str, 
        is_admin: bool = False
    ) -> bool:
        """Check if user can modify a specific comment."""
        db_obj = self._comments_repo.get(db, comment_id)
        if not db_obj:
            return False
        return self._comments_repo.can_user_modify(db_obj, user_email, is_admin)