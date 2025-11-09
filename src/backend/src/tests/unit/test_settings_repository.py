"""
Unit tests for AppRoleRepository

Tests database operations for app role management including:
- CRUD operations (create, read, update, delete)
- Querying by name
- Role counting
"""
import pytest
import uuid
import json

from src.repositories.settings_repository import AppRoleRepository
from src.models.settings import AppRole, AppRoleCreate
from src.db_models.settings import AppRoleDb
from src.common.features import FeatureAccessLevel


class TestAppRoleRepository:
    """Test suite for AppRoleRepository"""

    @pytest.fixture
    def repository(self):
        """Create repository instance for testing."""
        return AppRoleRepository(AppRoleDb)

    @pytest.fixture
    def sample_role_data(self):
        """Sample role data for testing."""
        return AppRoleCreate(
            name="Test Role",
            description="A test role",
            feature_permissions={
                "data-products": FeatureAccessLevel.READ_WRITE,
                "data-contracts": FeatureAccessLevel.READ_ONLY,
            },
            assigned_groups=["test-group"],
        )

    # =====================================================================
    # Create Tests
    # =====================================================================

    def test_create_role(self, repository, db_session, sample_role_data):
        """Test creating a role."""
        # Act
        role = repository.create(db_session, obj_in=sample_role_data)
        db_session.commit()

        # Assert
        assert role is not None
        assert role.name == sample_role_data.name
        assert role.description == sample_role_data.description
        # Verify JSON serialization
        assert isinstance(role.feature_permissions, str)
        assert isinstance(role.assigned_groups, str)

    def test_create_role_with_empty_permissions(self, repository, db_session):
        """Test creating role with empty permissions."""
        # Arrange
        role_data = AppRoleCreate(
            name="Empty Permissions Role",
            description="Test",
            feature_permissions={},
        )

        # Act
        role = repository.create(db_session, obj_in=role_data)
        db_session.commit()

        # Assert
        assert role.feature_permissions == '{}'

    # =====================================================================
    # Get Tests
    # =====================================================================

    def test_get_role_by_id(self, repository, db_session, sample_role_data):
        """Test retrieving a role by ID."""
        # Arrange
        created_role = repository.create(db_session, obj_in=sample_role_data)
        db_session.commit()

        # Act
        retrieved_role = repository.get(db_session, id=created_role.id)

        # Assert
        assert retrieved_role is not None
        assert retrieved_role.id == created_role.id
        assert retrieved_role.name == created_role.name

    def test_get_role_not_found(self, repository, db_session):
        """Test retrieving non-existent role."""
        # Act
        result = repository.get(db_session, id="nonexistent-id")

        # Assert
        assert result is None

    def test_get_role_by_name(self, repository, db_session, sample_role_data):
        """Test retrieving a role by name."""
        # Arrange
        created_role = repository.create(db_session, obj_in=sample_role_data)
        db_session.commit()

        # Act
        retrieved_role = repository.get_by_name(db_session, name=sample_role_data.name)

        # Assert
        assert retrieved_role is not None
        assert retrieved_role.name == sample_role_data.name

    def test_get_role_by_name_not_found(self, repository, db_session):
        """Test retrieving role by non-existent name."""
        # Act
        result = repository.get_by_name(db_session, name="Nonexistent Role")

        # Assert
        assert result is None

    # =====================================================================
    # List Tests
    # =====================================================================

    def test_get_multi_empty(self, repository, db_session):
        """Test listing roles when none exist."""
        # Act
        roles = repository.get_multi(db_session)

        # Assert
        assert roles == []

    def test_get_multi_roles(self, repository, db_session):
        """Test listing multiple roles."""
        # Arrange - Create 3 roles
        for i in range(3):
            role_data = AppRoleCreate(
                name=f"Role {i}",
                description=f"Description {i}",
                feature_permissions={},
            )
            repository.create(db_session, obj_in=role_data)
        db_session.commit()

        # Act
        roles = repository.get_multi(db_session)

        # Assert
        assert len(roles) == 3

    def test_get_all_roles(self, repository, db_session):
        """Test get_all_roles method."""
        # Arrange - Create 2 roles
        for i in range(2):
            role_data = AppRoleCreate(
                name=f"Role {i}",
                description=f"Description {i}",
                feature_permissions={},
            )
            repository.create(db_session, obj_in=role_data)
        db_session.commit()

        # Act
        roles = repository.get_all_roles(db_session)

        # Assert
        assert len(roles) == 2

    # =====================================================================
    # Update Tests
    # =====================================================================

    def test_update_role(self, repository, db_session, sample_role_data):
        """Test updating a role."""
        # Arrange
        created_role = repository.create(db_session, obj_in=sample_role_data)
        db_session.commit()

        # Act
        update_data = {"name": "Updated Name", "description": "Updated description"}
        updated_role = repository.update(db_session, db_obj=created_role, obj_in=update_data)
        db_session.commit()

        # Assert
        assert updated_role.name == "Updated Name"
        assert updated_role.description == "Updated description"

    def test_update_role_permissions(self, repository, db_session, sample_role_data):
        """Test updating role permissions."""
        # Arrange
        created_role = repository.create(db_session, obj_in=sample_role_data)
        db_session.commit()

        # Act
        new_permissions = {
            "compliance": FeatureAccessLevel.ADMIN,
        }
        update_data = {"feature_permissions": new_permissions}
        updated_role = repository.update(db_session, db_obj=created_role, obj_in=update_data)
        db_session.commit()

        # Assert
        # Permissions should be JSON serialized
        permissions_json = json.loads(updated_role.feature_permissions)
        assert "compliance" in permissions_json

    # =====================================================================
    # Delete Tests
    # =====================================================================

    def test_delete_role(self, repository, db_session, sample_role_data):
        """Test deleting a role."""
        # Arrange
        created_role = repository.create(db_session, obj_in=sample_role_data)
        db_session.commit()
        role_id = created_role.id

        # Act
        repository.remove(db_session, id=role_id)
        db_session.commit()

        # Assert
        deleted_role = repository.get(db_session, id=role_id)
        assert deleted_role is None

    # =====================================================================
    # Count Tests
    # =====================================================================

    def test_get_roles_count_empty(self, repository, db_session):
        """Test role count when none exist."""
        # Act
        count = repository.get_roles_count(db_session)

        # Assert
        assert count == 0

    def test_get_roles_count(self, repository, db_session):
        """Test role count with multiple roles."""
        # Arrange - Create 5 roles
        for i in range(5):
            role_data = AppRoleCreate(
                name=f"Role {i}",
                description=f"Description {i}",
                feature_permissions={},
            )
            repository.create(db_session, obj_in=role_data)
        db_session.commit()

        # Act
        count = repository.get_roles_count(db_session)

        # Assert
        assert count == 5

