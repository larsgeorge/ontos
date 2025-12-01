"""
Genie Spaces Repository

This module implements the repository layer for Genie Spaces CRUD operations.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional

from src.common.repository import CRUDBase
from src.models.genie_spaces import GenieSpaceCreate, GenieSpaceUpdate
from src.db_models.genie_spaces import GenieSpaceDb
from src.common.logging import get_logger

logger = get_logger(__name__)


class GenieSpaceRepository(CRUDBase[GenieSpaceDb, GenieSpaceCreate, GenieSpaceUpdate]):
    """Repository for Genie Space CRUD operations."""

    def get_by_space_id(self, db: Session, space_id: str) -> Optional[GenieSpaceDb]:
        """
        Get Genie Space by Databricks space_id.

        Args:
            db: Database session
            space_id: Databricks space ID

        Returns:
            GenieSpaceDb object or None if not found
        """
        logger.debug(f"Fetching Genie Space with space_id: {space_id}")
        try:
            return db.query(GenieSpaceDb).filter(GenieSpaceDb.space_id == space_id).first()
        except Exception as e:
            logger.error(f"Error fetching Genie Space by space_id {space_id}: {e}", exc_info=True)
            db.rollback()
            raise

    def get_by_product_ids(self, db: Session, product_ids: List[str]) -> List[GenieSpaceDb]:
        """
        Get all Genie Spaces containing any of the given product IDs.

        Args:
            db: Database session
            product_ids: List of Data Product UUIDs

        Returns:
            List of GenieSpaceDb objects
        """
        logger.debug(f"Fetching Genie Spaces for product_ids: {product_ids}")
        try:
            # PostgreSQL array overlap operator
            return db.query(GenieSpaceDb).filter(
                func.jsonb_exists_any(GenieSpaceDb.product_ids, product_ids)
            ).all()
        except Exception as e:
            logger.error(f"Error fetching Genie Spaces by product_ids: {e}", exc_info=True)
            db.rollback()
            raise

    def get_by_created_by(self, db: Session, user_email: str, limit: int = 100) -> List[GenieSpaceDb]:
        """
        Get all Genie Spaces created by a user.

        Args:
            db: Database session
            user_email: User email address
            limit: Maximum number of results (default 100)

        Returns:
            List of GenieSpaceDb objects ordered by created_at desc
        """
        logger.debug(f"Fetching Genie Spaces created by: {user_email}")
        try:
            return db.query(GenieSpaceDb).filter(
                GenieSpaceDb.created_by == user_email
            ).order_by(GenieSpaceDb.created_at.desc()).limit(limit).all()
        except Exception as e:
            logger.error(f"Error fetching Genie Spaces by user {user_email}: {e}", exc_info=True)
            db.rollback()
            raise

    def get_active_spaces(self, db: Session, limit: int = 100) -> List[GenieSpaceDb]:
        """
        Get all active Genie Spaces.

        Args:
            db: Database session
            limit: Maximum number of results (default 100)

        Returns:
            List of active GenieSpaceDb objects
        """
        logger.debug("Fetching active Genie Spaces")
        try:
            return db.query(GenieSpaceDb).filter(
                GenieSpaceDb.status == "active"
            ).order_by(GenieSpaceDb.created_at.desc()).limit(limit).all()
        except Exception as e:
            logger.error(f"Error fetching active Genie Spaces: {e}", exc_info=True)
            db.rollback()
            raise


# Create singleton instance
genie_space_repo = GenieSpaceRepository(GenieSpaceDb)
