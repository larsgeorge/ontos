from typing import List, Optional
import json

from sqlalchemy.orm import Session

from src.common.logging import get_logger
from src.models.comments import Comment, CommentCreate, CommentUpdate, CommentListResponse
from src.repositories.comments_repository import comments_repo, CommentsRepository
from src.db_models.comments import CommentStatus

logger = get_logger(__name__)


class CommentsManager:
    def __init__(self, comments_repository: CommentsRepository = comments_repo):
        self._comments_repo = comments_repository


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
            "project_id": comment_db.project_id,
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
        user_email: str,
        user_teams: Optional[List[str]] = None,
        is_admin: bool = False
    ) -> Comment:
        """Create a new comment.
        
        Args:
            db: Database session
            data: Comment creation data
            user_email: Email of the user creating the comment
            user_teams: List of team IDs the user belongs to (for validation)
            is_admin: Whether the user is an admin
            
        Returns:
            Created comment
            
        Raises:
            ValueError: If project_id is None and user is not admin or member of owning team
        """
        logger.info(f"Creating comment for {data.entity_type}:{data.entity_id} by {user_email}, project_id={data.project_id}")
        
        # Validate global comment creation (project_id is None)
        if data.project_id is None and not is_admin:
            # For now, allow global comments only for admins
            # In the future, could check if user is member of entity's owning team
            logger.warning(f"User {user_email} attempted to create global comment without admin privileges")
            raise ValueError("Only administrators or entity owners can create global comments")
        
        db_obj = self._comments_repo.create_with_audience(
            db, obj_in=data, created_by=user_email
        )
        db.commit()
        db.refresh(db_obj)
        
        return self._db_to_api_model(db_obj)

    def list_comments(
        self, 
        db: Session, 
        *, 
        entity_type: str, 
        entity_id: str,
        project_id: Optional[str] = None,
        user_groups: Optional[List[str]] = None,
        user_teams: Optional[List[str]] = None,
        user_app_role: Optional[str] = None,
        user_email: Optional[str] = None,
        include_deleted: bool = False
    ) -> CommentListResponse:
        """List comments for an entity, filtered by project and user's audience visibility.
        
        Args:
            db: Database session
            entity_type: Type of entity
            entity_id: ID of entity
            project_id: Filter by project context
            user_groups: User's group memberships
            user_teams: User's team memberships (IDs)
            user_app_role: User's app role name
            user_email: User's email (for direct targeting)
            include_deleted: Include soft-deleted comments
        """
        logger.debug(f"Listing comments for {entity_type}:{entity_id}, project_id={project_id}")
        
        # Get all comments (for total count) - without project filter for admin view
        all_comments = self._comments_repo.list_for_entity(
            db, 
            entity_type=entity_type, 
            entity_id=entity_id,
            project_id=None,  # Get all for count
            user_groups=None,
            user_teams=None,
            user_app_role=None,
            include_deleted=include_deleted
        )
        total_count = len(all_comments)
        
        # Get visible comments filtered by project and audience
        visible_comments = self._comments_repo.list_for_entity(
            db,
            entity_type=entity_type,
            entity_id=entity_id,
            project_id=project_id,
            user_groups=user_groups,
            user_teams=user_teams,
            user_app_role=user_app_role,
            include_deleted=include_deleted
        )

        # Additionally include comments targeted directly to the user's email via audience token
        if user_email:
            try:
                email_token = f"user:{user_email}"
                for c in all_comments:
                    aud = getattr(c, 'audience', None)
                    if aud and email_token in aud and c not in visible_comments:
                        # Also check project_id matches
                        if project_id is None or c.project_id is None or c.project_id == project_id:
                            visible_comments.append(c)
            except Exception:
                pass
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
                return True
        else:
            # Soft delete - mark as deleted
            soft_deleted = self._comments_repo.soft_delete(
                db, comment_id=comment_id, deleted_by=user_email
            )
            if soft_deleted:
                db.commit()
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