import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from unittest.mock import MagicMock
import tempfile
import shutil

# Adjust the import path according to your project structure
# This assumes your FastAPI app instance is named `app` in `api.app`
from api.app import app
from api.common.database import Base, get_db # Removed engine import from here
from api.common.dependencies import get_settings_manager
from api.common.config import Settings # Import the main Settings model
from api.controller.settings_manager import SettingsManager
from databricks.sdk import WorkspaceClient # For mocking


# In-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

# Create a new engine for SQLite
test_engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False} # check_same_thread is needed for SQLite
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session")
def temp_audit_log_dir():
    # Create a temporary directory for audit logs
    d = tempfile.mkdtemp()
    yield d
    # Clean up the directory after tests
    shutil.rmtree(d)


@pytest.fixture(scope="session", autouse=True)
def setup_test_database(temp_audit_log_dir): # Add temp_audit_log_dir dependency if needed for settings
    """
    Fixture to create all tables in the in-memory SQLite database once per test session.
    """
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine) # Clean up after tests


@pytest.fixture(scope="function")
def db_session(setup_test_database): # Depends on the session-scoped setup
    """
    Provides a database session for each test function, with transaction rollback.
    """
    connection = test_engine.connect()
    transaction = connection.begin()
    db = TestingSessionLocal(bind=connection)

    original_get_db = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = lambda: db

    yield db

    db.close()
    transaction.rollback()
    connection.close()

    if original_get_db:
        app.dependency_overrides[get_db] = original_get_db
    else:
        del app.dependency_overrides[get_db]


@pytest.fixture(scope="function")
def mock_workspace_client():
    mock_client = MagicMock(spec=WorkspaceClient)
    # Configure default return values for methods that might be called during setup or basic tests
    # For example, if settings_manager.get_job_clusters() is called via settings_manager.get_settings()
    mock_client.clusters.list.return_value = [] # No clusters by default
    # Add more mock configurations as needed for other WorkspaceClient interactions
    return mock_client


@pytest.fixture(scope="function")
def test_settings(temp_audit_log_dir: str) -> Settings:
    # Create a Settings instance with minimal viable test data
    # Adjust these values as necessary for your application's needs
    return Settings(
        DATABRICKS_HOST="https://test-databricks.com",
        DATABRICKS_WAREHOUSE_ID="test_warehouse_id",
        DATABRICKS_CATALOG="test_catalog",
        DATABRICKS_SCHEMA="test_schema",
        DATABRICKS_VOLUME="test_volume",
        DATABRICKS_TOKEN="test_token_val", # Even if optional, good to have a mock value
        APP_AUDIT_LOG_DIR=temp_audit_log_dir, # Use temp dir for tests
        APP_ADMIN_DEFAULT_GROUPS='["test_admins"]', # JSON string
        ENV="TEST",
        DEBUG=True,
        # Provide other required fields from your Settings model or ones with impactful defaults
        # For example, if POSTGRES_HOST is used conditionally, provide it or ensure logic handles its absence
        POSTGRES_HOST="localhost_test_db", # Or None if that's handled
        # Ensure all fields without defaults in Pydantic Settings model are covered
    )


@pytest.fixture(scope="function")
def client(db_session: Session, test_settings: Settings, mock_workspace_client: MagicMock):
    """
    Provides a TestClient instance.
    Overrides get_settings_manager to use test_settings and a mock_workspace_client.
    Ensures default roles are created by SettingsManager.
    """
    
    # This is the actual SettingsManager instance that will be used by the app during tests
    # when get_settings_manager is called.
    settings_manager_instance = SettingsManager(
        db=db_session, 
        settings=test_settings, 
        workspace_client=mock_workspace_client
    )

    # Call ensure_default_roles_exist to populate necessary roles for tests
    # This needs to happen after the SettingsManager is configured with test_settings
    # as it might use settings like APP_ADMIN_DEFAULT_GROUPS
    try:
        settings_manager_instance.ensure_default_roles_exist()
        db_session.commit() # Commit role creation if successful
    except Exception as e:
        db_session.rollback() # Rollback on error
        print(f"Error ensuring default roles in test setup: {e}")
        # Depending on test needs, you might want to raise this exception
        # or log it and proceed if roles are not critical for all tests.
        # For now, we'll print and proceed.
        # raise # Uncomment to make test setup fail if role creation fails


    def override_get_settings_manager():
        return settings_manager_instance

    original_get_settings_manager = app.dependency_overrides.get(get_settings_manager)
    app.dependency_overrides[get_settings_manager] = override_get_settings_manager

    with TestClient(app) as c:
        yield c
    
    if original_get_settings_manager:
        app.dependency_overrides[get_settings_manager] = original_get_settings_manager
    else:
        del app.dependency_overrides[get_settings_manager] 