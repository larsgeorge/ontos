from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, TypeVar

from .logging import get_logger
from sqlalchemy import create_engine, Index # Need Index for type checking
from sqlalchemy.orm import sessionmaker, Session as SQLAlchemySession
from sqlalchemy.ext.declarative import declarative_base
import os
from sqlalchemy.schema import CreateTable
from sqlalchemy import pool

from alembic import command
# Rename the Alembic Config import to avoid collision
from alembic.config import Config as AlembicConfig
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext
from sqlalchemy.engine import Connection

from .config import get_settings, Settings
from .logging import get_logger
# Import SDK components
from api.common.workspace_client import get_workspace_client
from databricks.sdk.errors import NotFound, DatabricksError 
from databricks.sdk.core import Config, oauth_service_principal

logger = get_logger(__name__)

T = TypeVar('T')

# Define the base class for SQLAlchemy models
Base = declarative_base()

# --- Explicitly import all model modules HERE to register them with Base --- #
# This ensures Base.metadata is populated before init_db needs it.
logger.debug("Importing all DB model modules to register with Base...")
try:
    from api.db_models import settings as settings_db
    from api.db_models import audit_log
    from api.db_models import data_asset_reviews
    from api.db_models import data_products
    from api.db_models import notifications
    from api.db_models import data_domains
    # Add imports for any other future model modules here
    logger.debug("DB model modules imported successfully.")
except ImportError as e:
    logger.critical(f"Failed to import a DB model module during initial registration: {e}", exc_info=True)
    # This is likely a fatal error, consider raising or exiting
    raise
# ------------------------------------------------------------------------- #

# Singleton engine instance
_engine = None
_SessionLocal = None
# Public engine instance (will be assigned after creation)
engine = None

@dataclass
class InMemorySession:
    """In-memory session for managing transactions."""
    changes: List[Dict[str, Any]]

    def __init__(self):
        self.changes = []

    def commit(self):
        """Commit changes to the global store."""

    def rollback(self):
        """Discard changes."""
        self.changes = []

class InMemoryStore:
    """In-memory storage system."""

    def __init__(self):
        """Initialize the in-memory store."""
        self._data: Dict[str, List[Dict[str, Any]]] = {}
        self._metadata: Dict[str, Dict[str, Any]] = {}

    def create_table(self, table_name: str, metadata: Dict[str, Any] = None) -> None:
        """Create a new table in the store.
        
        Args:
            table_name: Name of the table
            metadata: Optional metadata for the table
        """
        if table_name not in self._data:
            self._data[table_name] = []
            if metadata:
                self._metadata[table_name] = metadata

    def insert(self, table_name: str, data: Dict[str, Any]) -> None:
        """Insert a record into a table.
        
        Args:
            table_name: Name of the table
            data: Record to insert
        """
        if table_name not in self._data:
            self.create_table(table_name)

        # Add timestamp and id if not present
        if 'id' not in data:
            data['id'] = str(len(self._data[table_name]) + 1)
        if 'created_at' not in data:
            data['created_at'] = datetime.utcnow().isoformat()
        if 'updated_at' not in data:
            data['updated_at'] = data['created_at']

        self._data[table_name].append(data)

    def get(self, table_name: str, id: str) -> Optional[Dict[str, Any]]:
        """Get a record by ID.
        
        Args:
            table_name: Name of the table
            id: Record ID
            
        Returns:
            Record if found, None otherwise
        """
        if table_name not in self._data:
            return None
        return next((item for item in self._data[table_name] if item['id'] == id), None)

    def get_all(self, table_name: str) -> List[Dict[str, Any]]:
        """Get all records from a table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            List of records
        """
        return self._data.get(table_name, [])

    def update(self, table_name: str, id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a record.
        
        Args:
            table_name: Name of the table
            id: Record ID
            data: Updated data
            
        Returns:
            Updated record if found, None otherwise
        """
        if table_name not in self._data:
            return None

        for item in self._data[table_name]:
            if item['id'] == id:
                item.update(data)
                item['updated_at'] = datetime.utcnow().isoformat()
                return item
        return None

    def delete(self, table_name: str, id: str) -> bool:
        """Delete a record.
        
        Args:
            table_name: Name of the table
            id: Record ID
            
        Returns:
            True if deleted, False otherwise
        """
        if table_name not in self._data:
            return False

        initial_length = len(self._data[table_name])
        self._data[table_name] = [item for item in self._data[table_name] if item['id'] != id]
        return len(self._data[table_name]) < initial_length

    def clear(self, table_name: str) -> None:
        """Clear all records from a table.
        
        Args:
            table_name: Name of the table
        """
        if table_name in self._data:
            self._data[table_name] = []

class DatabaseManager:
    """Manages in-memory database operations."""

    def __init__(self) -> None:
        """Initialize the database manager."""
        self.store = InMemoryStore()

    @contextmanager
    def get_session(self) -> InMemorySession:
        """Get a database session.
        
        Yields:
            In-memory session
            
        Raises:
            Exception: If session operations fail
        """
        session = InMemorySession()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e!s}")
            raise

    def dispose(self) -> None:
        """Clear all data from the store."""
        self.store = InMemoryStore()

# Global database manager instance
db_manager: Optional[DatabaseManager] = None

def get_db_url(settings: Settings) -> str:
    """Constructs the Databricks SQLAlchemy URL."""
    token = os.getenv("DATABRICKS_TOKEN") # Prefer token from env for security
    if not token:
        logger.warning("DATABRICKS_TOKEN environment variable not set. Relying on SDK default credential provider.")
        # databricks-sqlalchemy uses default creds if token is None
    
    if not settings.DATABRICKS_HOST or not settings.DATABRICKS_HTTP_PATH:
         raise ValueError("DATABRICKS_HOST and DATABRICKS_HTTP_PATH must be configured in settings.")

    # Ensure host doesn't have https:// prefix
    host = settings.DATABRICKS_HOST.replace("https://", "")

    # Construct the URL for databricks-sqlalchemy dialect
    # See: https://github.com/databricks/databricks-sqlalchemy
    # Example: databricks://token:{token}@{host}?http_path={http_path}&catalog={catalog}&schema={schema}
    url = (
        f"databricks://token:{token}@{host}"
        f"?http_path={settings.DATABRICKS_HTTP_PATH}"
        f"&catalog={settings.DATABRICKS_CATALOG}"
        f"&schema={settings.DATABRICKS_SCHEMA}"
    )
    logger.debug(f"Constructed Databricks SQLAlchemy URL (token redacted)")
    return url

def ensure_catalog_schema_exists(settings: Settings):
    """Checks if the configured catalog and schema exist, creates them if not."""
    logger.info("Ensuring required catalog and schema exist...")
    try:
        # Get a workspace client instance (use the underlying client to bypass caching)
        caching_ws_client = get_workspace_client(settings)
        ws_client = caching_ws_client._client # Access raw client
        
        catalog_name = settings.DATABRICKS_CATALOG
        schema_name = settings.DATABRICKS_SCHEMA
        full_schema_name = f"{catalog_name}.{schema_name}"

        # 1. Check/Create Catalog
        try:
            logger.debug(f"Checking existence of catalog: {catalog_name}")
            ws_client.catalogs.get(catalog_name)
            logger.info(f"Catalog '{catalog_name}' already exists.")
        except NotFound:
            logger.warning(f"Catalog '{catalog_name}' not found. Attempting to create...")
            try:
                ws_client.catalogs.create(name=catalog_name)
                logger.info(f"Successfully created catalog: {catalog_name}")
            except DatabricksError as e:
                logger.critical(f"Failed to create catalog '{catalog_name}': {e}. Check permissions.", exc_info=True)
                raise ConnectionError(f"Failed to create required catalog '{catalog_name}': {e}") from e
        except DatabricksError as e:
            logger.error(f"Error checking catalog '{catalog_name}': {e}", exc_info=True)
            raise ConnectionError(f"Failed to check catalog '{catalog_name}': {e}") from e

        # 2. Check/Create Schema
        try:
            logger.debug(f"Checking existence of schema: {full_schema_name}")
            ws_client.schemas.get(full_schema_name)
            logger.info(f"Schema '{full_schema_name}' already exists.")
        except NotFound:
            logger.warning(f"Schema '{full_schema_name}' not found. Attempting to create...")
            try:
                ws_client.schemas.create(name=schema_name, catalog_name=catalog_name)
                logger.info(f"Successfully created schema: {full_schema_name}")
            except DatabricksError as e:
                logger.critical(f"Failed to create schema '{full_schema_name}': {e}. Check permissions.", exc_info=True)
                raise ConnectionError(f"Failed to create required schema '{full_schema_name}': {e}") from e
        except DatabricksError as e:
            logger.error(f"Error checking schema '{full_schema_name}': {e}", exc_info=True)
            raise ConnectionError(f"Failed to check schema '{full_schema_name}': {e}") from e
            
    except Exception as e:
        logger.critical(f"An unexpected error occurred during catalog/schema check/creation: {e}", exc_info=True)
        raise ConnectionError(f"Failed during catalog/schema setup: {e}") from e

def get_current_db_revision(engine_connection: Connection, alembic_cfg: AlembicConfig) -> str | None:
    """Gets the current revision of the database."""
    context = MigrationContext.configure(engine_connection)
    return context.get_current_revision()

def init_db() -> None:
    """Initializes the database connection, checks/creates catalog/schema, and runs migrations."""
    global _engine, _SessionLocal, engine
    settings = get_settings()

    if _engine is not None:
        logger.debug("Database engine already initialized.")
        return

    logger.info("Initializing database engine and session factory...")

    try:
        # Ensure target catalog and schema exist before connecting engine
        ensure_catalog_schema_exists(settings)

        db_url = get_db_url(settings)
        logger.info("Connecting to database...")
        _engine = create_engine(db_url, echo=settings.DB_ECHO, poolclass=pool.QueuePool, pool_size=5, max_overflow=10)
        engine = _engine # Assign to public variable

        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
        logger.info("Database engine and session factory initialized.")

        # --- Alembic Migration Logic --- #
        alembic_cfg_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..' , 'alembic.ini'))
        logger.info(f"Loading Alembic configuration from: {alembic_cfg_path}")
        alembic_cfg = AlembicConfig(alembic_cfg_path)
        alembic_cfg.set_main_option("sqlalchemy.url", db_url) # Ensure Alembic uses the same URL
        script = ScriptDirectory.from_config(alembic_cfg)
        head_revision = script.get_current_head()
        logger.info(f"Alembic Head Revision: {head_revision}")

        # Create a connection for Alembic context
        with engine.connect() as connection:
            logger.info("Getting current database revision...")
            db_revision = get_current_db_revision(connection, alembic_cfg)
            logger.info(f"Current Database Revision: {db_revision}")

            if db_revision != head_revision:
                logger.warning(f"Database revision '{db_revision}' differs from head revision '{head_revision}'.")
                if settings.APP_DEMO_MODE:
                    # WARNING: This wipes data in managed tables!
                    border = "=" * 50
                    logger.warning(border)
                    logger.warning("APP_DEMO_MODE: Database revision differs from head revision.")
                    logger.warning(f"DB: {db_revision}, Head: {head_revision}")
                    logger.warning("Performing Alembic downgrade to base and upgrade to head...")
                    logger.warning("THIS WILL WIPE ALL DATA IN MANAGED TABLES!")
                    logger.warning(border)
                    try:
                        # Remove logging around downgrade/upgrade
                        command.downgrade(alembic_cfg, "base")
                        command.upgrade(alembic_cfg, "head")
                        logger.info("Alembic downgrade/upgrade completed successfully.") # Keep completion message
                    except Exception as alembic_err:
                        logger.critical("Alembic downgrade/upgrade failed during demo mode reset!", exc_info=True)
                        raise RuntimeError("Failed to reset database schema for demo mode.") from alembic_err
                else:
                    logger.info("Attempting Alembic upgrade to head...")
                    try:
                        command.upgrade(alembic_cfg, "head")
                        logger.info("Alembic upgrade to head COMPLETED.")
                    except Exception as alembic_err:
                        logger.critical("Alembic upgrade failed! Manual intervention may be required.", exc_info=True)
                        raise RuntimeError("Failed to upgrade database schema.") from alembic_err
            else:
                logger.info("Database schema is up to date according to Alembic.")

        # Ensure all tables defined in Base metadata exist
        logger.info("Verifying/creating tables based on SQLAlchemy models...")
        try:
            dialect_name = engine.dialect.name
            logger.info(f"Detected database dialect: {dialect_name}")

            # Use a connection and explicit transaction for DDL
            with engine.connect() as connection:
                with connection.begin(): # Start a transaction
                    # Log all tables found in metadata
                    table_names = [t.name for t in Base.metadata.sorted_tables]
                    logger.info(f"Tables found in Base.metadata.sorted_tables: {table_names}")
                    all_meta_tables = list(Base.metadata.tables.values())
                    logger.info(f"Tables found directly in Base.metadata.tables: {[t.name for t in all_meta_tables]}")

                    if dialect_name == 'databricks':
                        logger.warning("Databricks dialect detected. Creating tables individually.")
                        logger.info("Processing remaining tables from sorted_tables...")
                        for table in Base.metadata.sorted_tables:
                            logger.info(f"Processing table object: {table}")
                            try:
                                logger.debug(f"Attempting to create table (if not exists): {table.name}")
                                table.create(bind=connection, checkfirst=True)
                                logger.info(f"Finished attempting create for table: {table.name}")
                            except Exception as table_create_err:
                                logger.error(f"Failed to create table '{table.name}' for Databricks: {table_create_err}", exc_info=True)
                                raise RuntimeError(f"Failed to create table '{table.name}'") from table_create_err
                    else:
                        # Non-databricks: Keep using create_all
                        logger.info(f"Dialect is not Databricks ({dialect_name}). Creating all tables and indexes.")
                        Base.metadata.create_all(bind=connection)

                # Transaction is committed automatically upon exiting the 'with connection.begin()' block
                logger.info("Table creation transaction committed (if any DDL was executed).")

            logger.info("Table existence check/creation completed.")
        except Exception as create_err:
            logger.critical(f"Error during table creation/check phase: {create_err}", exc_info=True)
            raise RuntimeError("Failed to ensure database tables exist.") from create_err

    except Exception as e:
        logger.critical(f"Database initialization failed: {e}", exc_info=True)
        _engine = None
        _SessionLocal = None
        engine = None # Reset public engine on failure
        raise ConnectionError("Failed to initialize database connection or run migrations.") from e

def get_db():
    global _SessionLocal
    if _SessionLocal is None:
        logger.error("Database not initialized. Cannot get session.")
        raise RuntimeError("Database session factory is not available.")
    
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_engine():
    global _engine
    if _engine is None:
        raise RuntimeError("Database engine not initialized.")
    return _engine

def get_session_factory():
    global _SessionLocal
    if _SessionLocal is None:
        raise RuntimeError("Database session factory not initialized.")
    return _SessionLocal
