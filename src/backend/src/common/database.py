import os
import uuid
import time
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, TypeVar

from sqlalchemy import create_engine, text, event
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
    from src.db_models import comments
    from src.db_models import costs
    from src.db_models import change_log
    # from src.db_models.data_products import DataProductDb, InfoDb, InputPortDb, OutputPortDb  # Already imported via module import above
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

# OAuth token state for Lakebase connections
_oauth_token: Optional[str] = None
_token_last_refresh: float = 0
_token_refresh_lock = threading.Lock()
_token_refresh_thread: Optional[threading.Thread] = None
_token_refresh_stop_event = threading.Event()


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


def refresh_oauth_token(settings: Settings) -> str:
    """Generate fresh OAuth token from Databricks for Lakebase connection."""
    global _oauth_token, _token_last_refresh
    
    with _token_refresh_lock:
        ws_client = get_workspace_client(settings)
        instance_name = settings.LAKEBASE_INSTANCE_NAME
        
        if not instance_name:
            raise ValueError("LAKEBASE_INSTANCE_NAME required for OAuth mode")
        
        logger.info(f"Generating OAuth token for Lakebase instance: {instance_name}")
        cred = ws_client.database.generate_database_credential(
            request_id=str(uuid.uuid4()),
            instance_names=[instance_name],
        )
        
        _oauth_token = cred.token
        _token_last_refresh = time.time()
        logger.info("OAuth token refreshed successfully")
        
        return _oauth_token


def start_token_refresh_background(settings: Settings):
    """Start background thread to refresh OAuth tokens every 50 minutes."""
    global _token_refresh_thread, _token_refresh_stop_event
    
    def refresh_loop():
        while not _token_refresh_stop_event.is_set():
            _token_refresh_stop_event.wait(50 * 60)  # 50 minutes
            if not _token_refresh_stop_event.is_set():
                try:
                    refresh_oauth_token(settings)
                except Exception as e:
                    logger.error(f"Background token refresh failed: {e}", exc_info=True)
    
    _token_refresh_stop_event.clear()
    _token_refresh_thread = threading.Thread(target=refresh_loop, daemon=True)
    _token_refresh_thread.start()
    logger.info("OAuth token refresh background thread started")


def stop_token_refresh_background():
    """Stop the background token refresh thread."""
    global _token_refresh_stop_event, _token_refresh_thread
    if _token_refresh_thread and _token_refresh_thread.is_alive():
        _token_refresh_stop_event.set()
        _token_refresh_thread.join(timeout=2)
        logger.info("OAuth token refresh background thread stopped")


def get_db_url(settings: Settings) -> str:
    """Construct the PostgreSQL SQLAlchemy URL with appropriate auth method."""
    
    # Validate required settings
    if not all([settings.POSTGRES_HOST, settings.POSTGRES_DB]):
        raise ValueError("PostgreSQL connection details (Host, DB) are missing in settings.")
    
    # Determine authentication mode based on ENV
    use_password_auth = settings.ENV.upper().startswith("LOCAL")
    
    if use_password_auth:
        logger.info("Database: Using password authentication (LOCAL mode)")
        if not settings.POSTGRES_PASSWORD or not settings.POSTGRES_USER:
            raise ValueError("POSTGRES_PASSWORD and POSTGRES_USER required for LOCAL mode")
        username = settings.POSTGRES_USER
        password = settings.POSTGRES_PASSWORD
    else:
        logger.info("Database: Using OAuth authentication (Lakebase mode)")
        # Dynamically determine username from authenticated principal
        ws_client = get_workspace_client(settings)
        username = (
            os.getenv("DATABRICKS_CLIENT_ID")
            or ws_client.current_user.me().user_name
        )
        if not username:
            raise ValueError("Could not determine database username from authenticated principal")
        
        logger.info(f"🔑 Detected service principal username: {username}")
        password = ""  # Will be set via event handler
    
    # Build URL with schema options
    query_params = {}
    if settings.POSTGRES_DB_SCHEMA:
        query_params["options"] = f"-csearch_path={settings.POSTGRES_DB_SCHEMA}"
        logger.info(f"PostgreSQL schema will be set via options: {settings.POSTGRES_DB_SCHEMA}")
    else:
        logger.info("No specific PostgreSQL schema configured, using default (public).")
    
    db_url_obj = URL.create(
        drivername="postgresql+psycopg2",
        username=username,
        password=password,
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


def log_database_setup_info(settings: Settings):
    """Log complete database setup information for Lakebase configuration."""
    if not settings.ENV.upper().startswith("LOCAL"):
        try:
            ws_client = get_workspace_client(settings)
            username = (
                os.getenv("DATABRICKS_CLIENT_ID")
                or ws_client.current_user.me().user_name
            )
            if not username:
                logger.warning("Could not determine service principal username for setup info")
                return
            
            db_name = settings.POSTGRES_DB
            schema_name = settings.POSTGRES_DB_SCHEMA or "public"
            
            logger.info("")
            logger.info("=" * 80)
            logger.info("LAKEBASE DATABASE SETUP INSTRUCTIONS")
            logger.info("=" * 80)
            logger.info(f"Service Principal: {username}")
            logger.info(f"Database: {db_name}")
            logger.info(f"Schema: {schema_name}")
            logger.info("")
            logger.info("Connect to Lakebase with your OAuth token, then run these commands:")
            logger.info("")
            logger.info(f"-- 1. Create the database")
            logger.info(f"CREATE DATABASE {db_name};")
            logger.info("")
            logger.info(f"-- 2. Connect to the new database")
            logger.info(f"\\c {db_name}")
            logger.info("")
            logger.info(f"-- 3. Create the schema")
            logger.info(f"CREATE SCHEMA {schema_name};")
            logger.info("")
            logger.info(f"-- 4. Create the role for service principal (forces it to exist)")
            logger.info(f'CREATE ROLE "{username}" WITH LOGIN;')
            logger.info("")
            logger.info(f"-- 5. Grant all permissions")
            logger.info(f'GRANT ALL PRIVILEGES ON DATABASE {db_name} TO "{username}";')
            logger.info(f'GRANT ALL PRIVILEGES ON SCHEMA {schema_name} TO "{username}";')
            logger.info(f'GRANT ALL ON ALL TABLES IN SCHEMA {schema_name} TO "{username}";')
            logger.info("")
            logger.info(f"-- 6. Make service principal the owner")
            logger.info(f'ALTER DATABASE {db_name} OWNER TO "{username}";')
            logger.info(f'ALTER SCHEMA {schema_name} OWNER TO "{username}";')
            logger.info("")
            logger.info(f"-- 7. Set default privileges for future objects")
            logger.info(f'ALTER DEFAULT PRIVILEGES IN SCHEMA {schema_name} GRANT ALL ON TABLES TO "{username}";')
            logger.info(f'ALTER DEFAULT PRIVILEGES IN SCHEMA {schema_name} GRANT ALL ON SEQUENCES TO "{username}";')
            logger.info("")
            logger.info("=" * 80)
            logger.info("")
        except Exception as e:
            logger.warning(f"Could not generate database setup info: {e}", exc_info=True)


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
    
    # Log database setup information for OAuth mode
    log_database_setup_info(settings)

    try:
        db_url = get_db_url(settings)

        # PostgreSQL connect args are typically empty; URL contains necessary options
        connect_args = {}

        logger.info("Connecting to database...")
        logger.info(f"> Database URL: {db_url}")
        logger.info(f"> Connect args: {connect_args}")
        logger.info(f"> Pool settings: size={settings.DB_POOL_SIZE}, max_overflow={settings.DB_MAX_OVERFLOW}, "
                   f"timeout={settings.DB_POOL_TIMEOUT}s, recycle={settings.DB_POOL_RECYCLE}s")
        
        _engine = create_engine(db_url,
                                connect_args=connect_args, 
                                echo=settings.DB_ECHO, 
                                poolclass=pool.QueuePool, 
                                pool_size=settings.DB_POOL_SIZE, 
                                max_overflow=settings.DB_MAX_OVERFLOW,
                                pool_timeout=settings.DB_POOL_TIMEOUT,
                                pool_recycle=settings.DB_POOL_RECYCLE,
                                pool_pre_ping=True)
        engine = _engine # Assign to public variable

        # Add OAuth token injection if not in LOCAL mode
        if not settings.ENV.upper().startswith("LOCAL"):
            logger.info("Setting up OAuth token injection for Lakebase...")
            
            # Generate initial token
            refresh_oauth_token(settings)
            
            # Register event handler to inject tokens for new connections
            # Use 'do_connect' event to inject password at connection creation time
            @event.listens_for(_engine, "do_connect")
            def inject_token_on_connect(dialect, conn_rec, cargs, cparams):
                global _oauth_token
                if _oauth_token:
                    cparams["password"] = _oauth_token
                    logger.debug("Injected OAuth token into new database connection")
            
            # Start background refresh thread
            start_token_refresh_background(settings)
            logger.info("OAuth authentication configured successfully")
        else:
            logger.info("Password authentication configured for LOCAL mode")

        # Explicitly enforce search_path at connection time to ensure correct schema usage in environments
        # where connection options may be ignored.
        if settings.POSTGRES_DB_SCHEMA:
            target_schema = settings.POSTGRES_DB_SCHEMA

            @event.listens_for(_engine, "connect")
            def set_search_path(dbapi_connection, connection_record):
                try:
                    with dbapi_connection.cursor() as cursor:
                        cursor.execute(f'SET search_path TO "{target_schema}"')
                except Exception as e:
                    # Log and continue; the app can still operate using default schema if necessary
                    logger.warning(f"Failed to set search_path to '{target_schema}': {e}")

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

@contextmanager
def get_db_session():
    """Context manager that yields a SQLAlchemy session.

    Ensures the session is committed on success and rolled back on error,
    and that the session is always closed. If the session factory is not
    initialized yet, it attempts to initialize the database first.
    """
    global _SessionLocal
    if _SessionLocal is None:
        try:
            init_db()
        except Exception as e:
            logger.critical(f"Failed to initialize database session factory: {e}", exc_info=True)
            raise RuntimeError("Database session factory not available and initialization failed.") from e

    session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        logger.error(f"Error during database session, rolling back: {e}", exc_info=True)
        session.rollback()
        raise
    finally:
        session.close()

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

def cleanup_db():
    """Cleanup database resources including OAuth token refresh."""
    global _engine, _SessionLocal, engine
    
    # Stop token refresh if running
    stop_token_refresh_background()
    
    # Dispose engine
    if _engine:
        _engine.dispose()
        logger.info("Database engine disposed")
    
    _engine = None
    _SessionLocal = None
    engine = None
