import os
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, TypeVar

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session as SQLAlchemySession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import pool
from sqlalchemy.engine import Connection, URL

from alembic.config import Config as AlembicConfig
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext

from .config import get_settings, Settings
from .logging import get_logger
from src.common.workspace_client import get_workspace_client
# Import SDK components
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
    from src.db_models import settings as settings_db
    from src.db_models import audit_log
    from src.db_models import data_asset_reviews
    from src.db_models import data_products
    from src.db_models import notifications
    from src.db_models import data_domains
    from src.db_models import semantic_links
    from src.db_models import metadata as metadata_db
    from src.db_models import semantic_models
    from src.db_models.data_products import DataProductDb, InfoDb, InputPortDb, OutputPortDb
    from src.db_models.settings import AppRoleDb
    # from src.db_models.users import UserActivityDb, UserSearchHistoryDb # Commented out due to missing file
    from src.db_models.audit_log import AuditLogDb
    from src.db_models.notifications import NotificationDb
    # from src.db_models.business_glossary import GlossaryDb, TermDb, CategoryDb, term_category_association, term_related_terms, term_asset_association # Commented out due to missing file
    # Add new tag models
    from src.db_models.tags import TagDb, TagNamespaceDb, TagNamespacePermissionDb, EntityTagAssociationDb
    # Add imports for any other future model modules here
    logger.debug("DB model modules imported successfully.")
except ImportError as e:
    logger.critical(
        f"Failed to import a DB model module during initial registration: {e}", exc_info=True)
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
        self._data[table_name] = [
            item for item in self._data[table_name] if item['id'] != id]
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
    """Construct the PostgreSQL SQLAlchemy URL."""
    if not all([settings.POSTGRES_HOST, settings.POSTGRES_USER, settings.POSTGRES_PASSWORD, settings.POSTGRES_DB]):
        raise ValueError("PostgreSQL connection details (Host, User, Password, DB) are missing in settings.")

    query_params = {}
    if settings.POSTGRES_DB_SCHEMA:
        query_params["options"] = f"-csearch_path={settings.POSTGRES_DB_SCHEMA},public"
        logger.info(f"PostgreSQL schema will be set via options: {settings.POSTGRES_DB_SCHEMA}")
    else:
        logger.info("No specific PostgreSQL schema configured, using default (public).")

    db_url_obj = URL.create(
        drivername="postgresql+psycopg2",
        username=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        database=settings.POSTGRES_DB,
        query=query_params if query_params else None
    )
    url_str = db_url_obj.render_as_string(hide_password=False)
    logger.debug(
        f"Constructed PostgreSQL SQLAlchemy URL using URL.create (credentials redacted in log): "
        f"{db_url_obj.render_as_string(hide_password=True)}"
    )
    return url_str


def ensure_catalog_schema_exists(settings: Settings):
    """Checks if the configured catalog and schema exist, creates them if not."""
    logger.info("Ensuring required catalog and schema exist...")
    try:
        # Get a workspace client instance (use the underlying client to bypass caching)
        caching_ws_client = get_workspace_client(settings)
        ws_client = caching_ws_client._client  # Access raw client

        catalog_name = settings.DATABRICKS_CATALOG
        schema_name = settings.DATABRICKS_SCHEMA
        full_schema_name = f"{catalog_name}.{schema_name}"

        # 1. Check/Create Catalog
        try:
            logger.debug(f"Checking existence of catalog: {catalog_name}")
            ws_client.catalogs.get(catalog_name)
            logger.info(f"Catalog '{catalog_name}' already exists.")
        except NotFound:
            logger.warning(
                f"Catalog '{catalog_name}' not found. Attempting to create...")
            try:
                ws_client.catalogs.create(name=catalog_name)
                logger.info(f"Successfully created catalog: {catalog_name}")
            except DatabricksError as e:
                logger.critical(
                    f"Failed to create catalog '{catalog_name}': {e}. Check permissions.", exc_info=True)
                raise ConnectionError(
                    f"Failed to create required catalog '{catalog_name}': {e}") from e
        except DatabricksError as e:
            logger.error(
                f"Error checking catalog '{catalog_name}': {e}", exc_info=True)
            raise ConnectionError(
                f"Failed to check catalog '{catalog_name}': {e}") from e

        # 2. Check/Create Schema
        try:
            logger.debug(f"Checking existence of schema: {full_schema_name}")
            ws_client.schemas.get(full_schema_name)
            logger.info(f"Schema '{full_schema_name}' already exists.")
        except NotFound:
            logger.warning(
                f"Schema '{full_schema_name}' not found. Attempting to create...")
            try:
                ws_client.schemas.create(
                    name=schema_name, catalog_name=catalog_name)
                logger.info(f"Successfully created schema: {full_schema_name}")
            except DatabricksError as e:
                logger.critical(
                    f"Failed to create schema '{full_schema_name}': {e}. Check permissions.", exc_info=True)
                raise ConnectionError(
                    f"Failed to create required schema '{full_schema_name}': {e}") from e
        except DatabricksError as e:
            logger.error(
                f"Error checking schema '{full_schema_name}': {e}", exc_info=True)
            raise ConnectionError(
                f"Failed to check schema '{full_schema_name}': {e}") from e

    except Exception as e:
        logger.critical(
            f"An unexpected error occurred during catalog/schema check/creation: {e}", exc_info=True)
        raise ConnectionError(
            f"Failed during catalog/schema setup: {e}") from e


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
        db_url = get_db_url(settings)

        # PostgreSQL connect args are typically empty; URL contains necessary options
        connect_args = {}

        logger.info("Connecting to database...")
        logger.info(f"> Database URL: {db_url}")
        logger.info(f"> Connect args: {connect_args}")
        _engine = create_engine(db_url,
                                connect_args=connect_args, 
                                echo=settings.DB_ECHO, 
                                poolclass=pool.QueuePool, 
                                pool_size=5, 
                                max_overflow=10,
                                pool_recycle=840,
                                pool_pre_ping=True)
        engine = _engine # Assign to public variable

        # def refresh_connection(dbapi_connection, connection_record):
        #     if dbapi_connection.is_closed() or not dbapi_connection.is_valid():
        #         connection_record.invalidate()

        # event.listen(engine, "engine_connect", refresh_connection)

        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
        logger.info("Database engine and session factory initialized.")

        # --- Alembic Migration Logic --- #
        alembic_cfg_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..' , 'alembic.ini'))
        logger.info(f"Loading Alembic configuration from: {alembic_cfg_path}")
        alembic_cfg = AlembicConfig(alembic_cfg_path)
        alembic_cfg.set_main_option("sqlalchemy.url", db_url.replace("%", "%%")) # Ensure Alembic uses the same URL
        script = ScriptDirectory.from_config(alembic_cfg)
        head_revision = script.get_current_head()
        logger.info(f"Alembic Head Revision: {head_revision}")

        # Create a connection for Alembic context
        with engine.connect() as connection:
            logger.info("Getting current database revision...")
            db_revision = get_current_db_revision(connection, alembic_cfg)
            logger.info(f"Current Database Revision: {db_revision}")

            # if db_revision != head_revision:
            #     logger.warning(f"Database revision '{db_revision}' differs from head revision '{head_revision}'.")
            #     if settings.APP_DEMO_MODE:
            #         # WARNING: This wipes data in managed tables!
            #         border = "=" * 50
            #         logger.warning(border)
            #         logger.warning("APP_DEMO_MODE: Database revision differs from head revision.")
            #         logger.warning(f"DB: {db_revision}, Head: {head_revision}")
            #         logger.warning("Performing Alembic downgrade to base and upgrade to head...")
            #         logger.warning("THIS WILL WIPE ALL DATA IN MANAGED TABLES!")
            #         logger.warning(border)
            #         try:
            #             # Remove logging around downgrade/upgrade
            #             logger.info("Downgrading database to base version...")
            #             command.downgrade(alembic_cfg, "base")
            #             logger.info("Upgrading database to head version...")
            #             command.upgrade(alembic_cfg, "head")
            #             logger.info("Alembic downgrade/upgrade completed successfully.") # Keep completion message
            #         except Exception as alembic_err:
            #             logger.critical("Alembic downgrade/upgrade failed during demo mode reset!", exc_info=True)
            #             raise RuntimeError("Failed to reset database schema for demo mode.") from alembic_err
            #     else:
            #         logger.info("Attempting Alembic upgrade to head...")
            #         try:
            #             command.upgrade(alembic_cfg, "head")
            #             logger.info("Alembic upgrade to head COMPLETED.")
            #         except Exception as alembic_err:
            #             logger.critical("Alembic upgrade failed! Manual intervention may be required.", exc_info=True)
            #             raise RuntimeError("Failed to upgrade database schema.") from alembic_err
            # else:
            #     logger.info("Database schema is up to date according to Alembic.")

        # Ensure all tables defined in Base metadata exist
        logger.info("Verifying/creating tables based on SQLAlchemy models...")
        # Schema for create_all if PostgreSQL
        schema_to_create_in = None
        if settings.POSTGRES_DB_SCHEMA:
            schema_to_create_in = settings.POSTGRES_DB_SCHEMA
            # We need to ensure this schema exists before calling create_all if it's not 'public'
            # and if tables don't explicitly define their schema.
            # SQLAlchemy create_all does not create schemas.
            # The search_path option in the URL handles where tables are looked for and created if no schema is specified on the Table object.
            # However, for explicit control, ensuring schema existence might be needed.
            # For now, relying on search_path. If schema needs explicit creation:
            # with engine.connect() as connection:
            # connection.execute(sqlalchemy.text(f"CREATE SCHEMA IF NOT EXISTS {schema_to_create_in}"))
            # connection.commit()
            logger.info(f"PostgreSQL: Tables will be targeted for schema '{schema_to_create_in}' via search_path or model definitions.")

        # No Databricks-specific metadata modifications required

        # Check if we should drop all tables first (for development)
        if settings.APP_DB_DROP_ON_START:
            logger.warning("APP_DB_DROP_ON_START=true: Dropping all existing tables with CASCADE...")
            with _engine.connect() as connection:
                # Use raw SQL to drop schema and recreate it
                schema_name = settings.POSTGRES_DB_SCHEMA or 'public'
                logger.warning(f"Dropping schema '{schema_name}' CASCADE and recreating...")
                connection.execute(text(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE"))
                connection.execute(text(f"CREATE SCHEMA {schema_name}"))
                connection.commit()
            logger.warning("Schema dropped and recreated. This will recreate all tables from scratch.")

        # Now, call create_all. It will operate on the potentially modified metadata.
        logger.info("Executing Base.metadata.create_all()...")
        Base.metadata.create_all(bind=_engine) # schema argument is not directly used here if search_path is set.
                                               # If tables have schema set in their definition, that's used.
                                               # Otherwise, the first schema in search_path is used.
        logger.info("Database tables checked/created by create_all.")
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
        # Consider raising HTTPException for FastAPI to handle gracefully if this occurs at runtime
        raise RuntimeError("Database session factory is not available. Database might not have been initialized correctly.")
    
    db = _SessionLocal()
    try:
        yield db
        db.commit()  # Commit the transaction on successful completion of the request
    except Exception as e: # Catch all exceptions to ensure rollback
        logger.error(f"Error during database session for request, rolling back: {e}", exc_info=True)
        db.rollback()
        # Re-raise the exception so FastAPI can handle it appropriately
        # (e.g., return a 500 error or specific HTTPException if e is one)
        raise
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
