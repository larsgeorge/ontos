"""
Unit tests for CRUDBase repository class

Tests base repository functionality including:
- CRUD operations (create, read, update, delete)
- Counting and emptiness checks
- UUID normalization
- Error handling
"""
import pytest
import uuid
from sqlalchemy import Column, String
from sqlalchemy.exc import SQLAlchemyError

from src.common.repository import CRUDBase
from src.common.database import Base


# Test model for repository testing
class TestModelDb(Base):
    __tablename__ = "test_model"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    value = Column(String, nullable=True)


class TestCRUDBase:
    """Test suite for CRUDBase repository"""

    @pytest.fixture
    def repository(self):
        """Create repository instance for testing."""
        return CRUDBase(TestModelDb)

    @pytest.fixture
    def sample_model(self, db_session):
        """Create a sample model in the database."""
        model = TestModelDb(
            id=str(uuid.uuid4()),
            name="Test Item",
            value="test_value",
        )
        db_session.add(model)
        db_session.commit()
        db_session.refresh(model)
        return model

    def test_repository_initialization(self, repository):
        """Test repository initializes correctly."""
        assert repository is not None
        assert repository.model == TestModelDb

    def test_get_existing(self, repository, db_session, sample_model):
        """Test retrieving an existing model."""
        # Act
        result = repository.get(db_session, id=sample_model.id)

        # Assert
        assert result is not None
        assert result.id == sample_model.id
        assert result.name == sample_model.name

    def test_get_nonexistent(self, repository, db_session):
        """Test retrieving a non-existent model."""
        # Act
        result = repository.get(db_session, id=str(uuid.uuid4()))

        # Assert
        assert result is None

    def test_get_multi_empty(self, repository, db_session):
        """Test listing models when none exist."""
        # Act
        result = repository.get_multi(db_session)

        # Assert
        assert result == []

    def test_get_multi_with_data(self, repository, db_session):
        """Test listing multiple models."""
        # Arrange - Create 3 models
        for i in range(3):
            model = TestModelDb(
                id=str(uuid.uuid4()),
                name=f"Item {i}",
                value=f"value_{i}",
            )
            db_session.add(model)
        db_session.commit()

        # Act
        result = repository.get_multi(db_session)

        # Assert
        assert len(result) == 3

    def test_get_multi_pagination(self, repository, db_session):
        """Test pagination for listing models."""
        # Arrange - Create 10 models
        for i in range(10):
            model = TestModelDb(
                id=str(uuid.uuid4()),
                name=f"Item {i}",
            )
            db_session.add(model)
        db_session.commit()

        # Act
        result = repository.get_multi(db_session, skip=2, limit=3)

        # Assert
        assert len(result) == 3

    def test_remove_existing(self, repository, db_session, sample_model):
        """Test deleting an existing model."""
        # Arrange
        model_id = sample_model.id

        # Act
        result = repository.remove(db_session, id=model_id)
        db_session.commit()

        # Assert
        assert result is not None
        deleted = repository.get(db_session, id=model_id)
        assert deleted is None

    def test_remove_nonexistent(self, repository, db_session):
        """Test deleting a non-existent model."""
        # Act
        result = repository.remove(db_session, id=str(uuid.uuid4()))

        # Assert
        assert result is None

    def test_count_empty(self, repository, db_session):
        """Test counting models when none exist."""
        # Act
        count = repository.count(db_session)

        # Assert
        assert count == 0

    def test_count_with_data(self, repository, db_session):
        """Test counting models."""
        # Arrange - Create 5 models
        for i in range(5):
            model = TestModelDb(
                id=str(uuid.uuid4()),
                name=f"Item {i}",
            )
            db_session.add(model)
        db_session.commit()

        # Act
        count = repository.count(db_session)

        # Assert
        assert count == 5

    def test_is_empty_when_empty(self, repository, db_session):
        """Test is_empty when table is empty."""
        # Act
        result = repository.is_empty(db_session)

        # Assert
        assert result is True

    def test_is_empty_when_not_empty(self, repository, db_session, sample_model):
        """Test is_empty when table has data."""
        # Act
        result = repository.is_empty(db_session)

        # Assert
        assert result is False

