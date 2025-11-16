"""Debug routes for troubleshooting database connectivity."""

from fastapi import APIRouter, Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.common.dependencies import get_db
from src.common.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/debug", tags=["debug"])


def register_routes(app: FastAPI):
    """Register debug routes with the FastAPI app."""
    app.include_router(router)


@router.get("/db-info")
def get_database_info(db: Session = Depends(get_db)):
    """Get information about the current database connection."""
    try:
        # Get current database name
        result = db.execute(text("SELECT current_database()"))
        current_db = result.scalar()
        
        # Get current schema
        result = db.execute(text("SHOW search_path"))
        search_path = result.scalar()
        
        # Count tables in current schema
        result = db.execute(text("""
            SELECT table_schema, COUNT(*) as table_count
            FROM information_schema.tables
            WHERE table_type = 'BASE TABLE'
            GROUP BY table_schema
            ORDER BY table_schema
        """))
        schema_counts = [{"schema": row[0], "count": row[1]} for row in result]
        
        # Check if alembic_version exists
        result = db.execute(text("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = 'alembic_version'
            )
        """))
        alembic_exists = result.scalar()
        
        # Get alembic version if it exists
        alembic_version = None
        if alembic_exists:
            result = db.execute(text("SELECT version_num FROM alembic_version"))
            alembic_version = result.scalar()
        
        return {
            "current_database": current_db,
            "search_path": search_path,
            "schema_table_counts": schema_counts,
            "alembic_version_exists": alembic_exists,
            "alembic_version": alembic_version,
        }
    except Exception as e:
        logger.error(f"Error getting database info: {e}", exc_info=True)
        return {"error": str(e)}

