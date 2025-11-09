"""
Unit tests for SuggestedQualityChecksRepository

Tests suggested quality checks repository including:
- CRUD operations
- Filtering by profile run and contract
- Bulk accept/reject operations
- Status management
"""
import pytest
import uuid

from src.repositories.suggested_quality_checks_repository import SuggestedQualityChecksRepository
from src.db_models.data_contracts import SuggestedQualityCheckDb


class TestSuggestedQualityChecksRepository:
    """Test suite for SuggestedQualityChecksRepository"""

    @pytest.fixture
    def repository(self):
        """Create repository instance for testing."""
        return SuggestedQualityChecksRepository(SuggestedQualityCheckDb)

    @pytest.fixture
    def sample_suggestion(self, db_session):
        """Create a sample quality check suggestion."""
        suggestion = SuggestedQualityCheckDb(
            id=str(uuid.uuid4()),
            profile_run_id="run-123",
            contract_id="contract-456",
            source="dqx",
            schema_name="customers",
            property_name="email",
            status="pending",
            name="Email format check",
            description="Validate email format",
            level="property",
            dimension="conformity",
            severity="warning",
            type="library",
        )
        db_session.add(suggestion)
        db_session.commit()
        db_session.refresh(suggestion)
        return suggestion

    def test_repository_initialization(self, repository):
        """Test repository initializes correctly."""
        assert repository is not None
        assert repository.model == SuggestedQualityCheckDb

    def test_get_by_profile_run_id_empty(self, repository, db_session):
        """Test getting suggestions for profile run with no suggestions."""
        # Act
        result = repository.get_by_profile_run_id(db_session, "nonexistent-run")

        # Assert
        assert result == []

    def test_get_by_profile_run_id_with_data(self, repository, db_session):
        """Test getting suggestions for profile run."""
        # Arrange - Create suggestions for two different runs
        run1_id = "run-001"
        run2_id = "run-002"
        
        suggestion1 = SuggestedQualityCheckDb(
            id=str(uuid.uuid4()),
            profile_run_id=run1_id,
            contract_id="contract-1",
            source="dqx",
            schema_name="users",
            property_name="name",
            status="pending",
            type="library",
        )
        suggestion2 = SuggestedQualityCheckDb(
            id=str(uuid.uuid4()),
            profile_run_id=run1_id,
            contract_id="contract-1",
            source="llm",
            schema_name="users",
            property_name="email",
            status="pending",
            type="library",
        )
        suggestion3 = SuggestedQualityCheckDb(
            id=str(uuid.uuid4()),
            profile_run_id=run2_id,
            contract_id="contract-2",
            source="dqx",
            schema_name="products",
            property_name="price",
            status="pending",
            type="library",
        )
        db_session.add_all([suggestion1, suggestion2, suggestion3])
        db_session.commit()

        # Act
        result = repository.get_by_profile_run_id(db_session, run1_id)

        # Assert
        assert len(result) == 2
        assert all(s.profile_run_id == run1_id for s in result)

    def test_get_by_profile_run_id_ordering(self, repository, db_session):
        """Test suggestions are ordered by schema and property."""
        # Arrange
        run_id = "run-123"
        
        # Create suggestions in non-alphabetical order
        s1 = SuggestedQualityCheckDb(
            id=str(uuid.uuid4()),
            profile_run_id=run_id,
            contract_id="contract-1",
            source="dqx",
            schema_name="users",
            property_name="zfield",
            status="pending",
            type="library",
        )
        s2 = SuggestedQualityCheckDb(
            id=str(uuid.uuid4()),
            profile_run_id=run_id,
            contract_id="contract-1",
            source="dqx",
            schema_name="users",
            property_name="afield",
            status="pending",
            type="library",
        )
        s3 = SuggestedQualityCheckDb(
            id=str(uuid.uuid4()),
            profile_run_id=run_id,
            contract_id="contract-1",
            source="dqx",
            schema_name="products",
            property_name="name",
            status="pending",
            type="library",
        )
        db_session.add_all([s1, s2, s3])
        db_session.commit()

        # Act
        result = repository.get_by_profile_run_id(db_session, run_id)

        # Assert
        assert len(result) == 3
        # Should be ordered by schema_name, then property_name
        assert result[0].schema_name == "products"
        assert result[1].schema_name == "users"
        assert result[1].property_name == "afield"
        assert result[2].schema_name == "users"
        assert result[2].property_name == "zfield"

    def test_get_pending_for_contract_empty(self, repository, db_session):
        """Test getting pending suggestions for contract with none."""
        # Act
        result = repository.get_pending_for_contract(db_session, "nonexistent-contract")

        # Assert
        assert result == []

    def test_get_pending_for_contract_with_data(self, repository, db_session):
        """Test getting pending suggestions for contract."""
        # Arrange
        contract_id = "contract-123"
        
        pending = SuggestedQualityCheckDb(
            id=str(uuid.uuid4()),
            profile_run_id="run-1",
            contract_id=contract_id,
            source="dqx",
            schema_name="users",
            status="pending",
            type="library",
        )
        accepted = SuggestedQualityCheckDb(
            id=str(uuid.uuid4()),
            profile_run_id="run-1",
            contract_id=contract_id,
            source="dqx",
            schema_name="users",
            status="accepted",
            type="library",
        )
        rejected = SuggestedQualityCheckDb(
            id=str(uuid.uuid4()),
            profile_run_id="run-1",
            contract_id=contract_id,
            source="dqx",
            schema_name="users",
            status="rejected",
            type="library",
        )
        db_session.add_all([pending, accepted, rejected])
        db_session.commit()

        # Act
        result = repository.get_pending_for_contract(db_session, contract_id)

        # Assert
        assert len(result) == 1
        assert result[0].status == "pending"

    def test_bulk_accept_empty(self, repository, db_session):
        """Test bulk accepting with no IDs."""
        # Act
        count = repository.bulk_accept(db_session, [])

        # Assert
        assert count == 0

    def test_bulk_accept_with_data(self, repository, db_session):
        """Test bulk accepting suggestions."""
        # Arrange
        s1 = SuggestedQualityCheckDb(
            id=str(uuid.uuid4()),
            profile_run_id="run-1",
            contract_id="contract-1",
            source="dqx",
            schema_name="users",
            status="pending",
            type="library",
        )
        s2 = SuggestedQualityCheckDb(
            id=str(uuid.uuid4()),
            profile_run_id="run-1",
            contract_id="contract-1",
            source="dqx",
            schema_name="users",
            status="pending",
            type="library",
        )
        s3 = SuggestedQualityCheckDb(
            id=str(uuid.uuid4()),
            profile_run_id="run-1",
            contract_id="contract-1",
            source="dqx",
            schema_name="users",
            status="pending",
            type="library",
        )
        db_session.add_all([s1, s2, s3])
        db_session.commit()

        # Act
        count = repository.bulk_accept(db_session, [s1.id, s2.id])

        # Assert
        assert count == 2
        
        # Verify status changes
        db_session.refresh(s1)
        db_session.refresh(s2)
        db_session.refresh(s3)
        assert s1.status == "accepted"
        assert s2.status == "accepted"
        assert s3.status == "pending"  # Unchanged

    def test_bulk_reject_with_data(self, repository, db_session):
        """Test bulk rejecting suggestions."""
        # Arrange
        s1 = SuggestedQualityCheckDb(
            id=str(uuid.uuid4()),
            profile_run_id="run-1",
            contract_id="contract-1",
            source="dqx",
            schema_name="users",
            status="pending",
            type="library",
        )
        s2 = SuggestedQualityCheckDb(
            id=str(uuid.uuid4()),
            profile_run_id="run-1",
            contract_id="contract-1",
            source="dqx",
            schema_name="users",
            status="pending",
            type="library",
        )
        db_session.add_all([s1, s2])
        db_session.commit()

        # Act
        count = repository.bulk_reject(db_session, [s1.id, s2.id])

        # Assert
        assert count == 2
        
        # Verify status changes
        db_session.refresh(s1)
        db_session.refresh(s2)
        assert s1.status == "rejected"
        assert s2.status == "rejected"

    def test_bulk_accept_nonexistent_ids(self, repository, db_session):
        """Test bulk accepting with nonexistent IDs."""
        # Act
        count = repository.bulk_accept(db_session, ["nonexistent-1", "nonexistent-2"])

        # Assert
        assert count == 0

    def test_bulk_reject_nonexistent_ids(self, repository, db_session):
        """Test bulk rejecting with nonexistent IDs."""
        # Act
        count = repository.bulk_reject(db_session, ["nonexistent-1", "nonexistent-2"])

        # Assert
        assert count == 0

    def test_get_pending_for_contract_multiple_contracts(self, repository, db_session):
        """Test filtering pending suggestions by specific contract."""
        # Arrange
        contract1_id = "contract-001"
        contract2_id = "contract-002"
        
        s1 = SuggestedQualityCheckDb(
            id=str(uuid.uuid4()),
            profile_run_id="run-1",
            contract_id=contract1_id,
            source="dqx",
            schema_name="users",
            status="pending",
            type="library",
        )
        s2 = SuggestedQualityCheckDb(
            id=str(uuid.uuid4()),
            profile_run_id="run-1",
            contract_id=contract2_id,
            source="dqx",
            schema_name="users",
            status="pending",
            type="library",
        )
        db_session.add_all([s1, s2])
        db_session.commit()

        # Act
        result = repository.get_pending_for_contract(db_session, contract1_id)

        # Assert
        assert len(result) == 1
        assert result[0].contract_id == contract1_id

