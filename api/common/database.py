from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, TypeVar

from .logging import get_logger
from sqlalchemy import create_engine, Index # Need Index for type checking
from sqlalchemy.orm import sessionmaker, Session as SQLAlchemySession
from sqlalchemy.ext.declarative import declarative_base
import os
from sqlalchemy.schema import CreateTable, CreateIndex # Import DDL elements

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

# Singleton engine instance
_engine = None
_SessionLocal = None

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
                ws_client.schemas.create(catalog_name=catalog_name, name=schema_name)
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

def init_db(run_create_all: bool = True) -> None:
    """Initializes the database engine and sessionmaker."""
    global _engine, _SessionLocal
    if _engine:
        logger.warning("Database engine already initialized.")
        return

    settings = get_settings()
    
    if not all([settings.DATABRICKS_HOST, settings.DATABRICKS_HTTP_PATH, settings.DATABRICKS_CATALOG, settings.DATABRICKS_SCHEMA]):
         logger.error("Cannot initialize database: Missing required Databricks settings.")
         raise ConnectionError("Missing required Databricks connection settings.")

    try:
        # Ensure Catalog and Schema exist
        ensure_catalog_schema_exists(settings)

        def get_credentials():
            config = Config(
                host=os.getenv("DATABRICKS_HOST"),
                client_id=os.getenv("DATABRICKS_CLIENT_ID"),
                client_secret=os.getenv("DATABRICKS_CLIENT_SECRET")
            )
            return oauth_service_principal(config)
        
        logger.info(f"Environment for DB connection: {settings.ENV}")
        if settings.ENV.startswith('LOCAL'):
            connect_args = {
                "server_hostname": settings.DATABRICKS_HOST,
                "http_path": settings.DATABRICKS_HTTP_PATH,
                "access_token": settings.DATABRICKS_TOKEN,
            }
        else:
            cfg = Config() # Hands in SQL host and OAuth function when run in Databricks
            connect_args = {
                "server_hostname": cfg.host,
                "http_path": settings.DATABRICKS_HTTP_PATH,
                "credentials_provider": lambda: cfg.authenticate,
                "auth_type": "databricks-oauth",
            }

        # Create SQLAlchemy engine
        db_url = get_db_url(settings)
        logger.info(f"Database URL: {db_url}")
        logger.info(f"Connect args: {connect_args}")
        _engine = create_engine(
            db_url, 
            connect_args=connect_args,
            echo=settings.DEBUG,
            pool_pre_ping=True,
            pool_recycle=3600
        )
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
        logger.info(f"Database engine initialized for: {settings.DATABRICKS_HOST}")

        if run_create_all:
            # Import all models here so Base knows about them
            from api.db_models import data_products 
            logger.info("Checking/creating database tables (conditional indexes)...")
            
            # --- Conditionally Modify Metadata BEFORE DDL Generation ---
            is_databricks = _engine.dialect.name == 'databricks'
            if is_databricks:
                logger.info("Databricks dialect detected. Removing Index objects from metadata before DDL generation.")
                # Iterate through tables and remove associated Index objects
                # This prevents create_all from attempting to create them
                indexes_to_remove = []
                for table in Base.metadata.tables.values():
                    # Find indexes associated directly with this table via Column(index=True)
                    # We check the column's index attribute, not just table.indexes 
                    # as table.indexes might include functional indexes etc.
                    for col in table.columns:
                         if col.index:
                             # Find the actual Index object SQLAlchemy created for this column
                             # This is a bit involved as Index name isn't guaranteed
                             # Let's try removing ALL indexes associated with the table for simplicity
                             # as UC doesn't support any CREATE INDEX.
                             logger.debug(f"Preparing to remove indexes associated with table: {table.name}")
                             # Collect indexes associated with the table to avoid modifying while iterating
                             for idx in list(table.indexes): # Iterate over a copy
                                  if idx not in indexes_to_remove:
                                       indexes_to_remove.append(idx)
                                       logger.debug(f"Marked index {idx.name} for removal from metadata.")
                
                # Actually remove them from the metadata's central index collection if necessary
                # In newer SQLAlchemy, removing from table.indexes might be sufficient
                for idx in indexes_to_remove:
                     try:
                         # Attempt removal from the table's collection first
                         if hasattr(idx, 'table') and idx in idx.table.indexes:
                              idx.table.indexes.remove(idx)
                         # Attempt removal from metadata collection (less common needed)
                         # if idx in Base.metadata.indexes:
                         #     Base.metadata.indexes.remove(idx)
                         logger.info(f"Successfully removed index {idx.name} from metadata for DDL generation.")
                     except Exception as remove_err:
                         logger.warning(f"Could not fully remove index {idx.name} from metadata: {remove_err}")
            # --- End Conditional Metadata Modification --- 

            # Now, call create_all. It will operate on the potentially modified metadata.
            logger.info("Executing Base.metadata.create_all()...")
            Base.metadata.create_all(bind=_engine)
            logger.info("Database tables checked/created by create_all.")

    except Exception as e:
        logger.error(f"Failed to initialize database: {e}", exc_info=True)
        _engine = None
        _SessionLocal = None
        # Simplify error propagation
        raise ConnectionError(f"Failed to initialize database connection: {e}") from e

def get_db():
    global _SessionLocal
    if _SessionLocal is None:
        logger.error("Database session factory not initialized! Call init_db() first.")
        raise RuntimeError("Database session factory not available.")

    db = _SessionLocal()
    try:
        yield db
        db.commit() # Commit transaction if no exceptions occurred
        logger.debug("Database transaction committed.")
    except Exception as e:
        logger.error(f"Database transaction failed, rolling back: {e}", exc_info=False) # Avoid logging full trace unless needed
        db.rollback()
        raise # Re-raise the exception to be handled by FastAPI error handlers
    finally:
        db.close()
        logger.debug("Database session closed.")

def get_engine():
    """Returns the SQLAlchemy engine instance."""
    if not _engine:
         raise RuntimeError("Database engine not initialized.")
    return _engine

def get_session_factory():
    """Returns the initialized SQLAlchemy session factory (_SessionLocal)."""
    if not _SessionLocal:
        # This case should ideally not be hit if init_db was called successfully
        # But added as a safeguard.
        logger.error("get_session_factory called before database initialization or after failure.")
        raise RuntimeError("Database session factory not available.")
    return _SessionLocal
