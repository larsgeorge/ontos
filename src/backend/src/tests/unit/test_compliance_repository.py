"""
Unit tests for Compliance Repositories

Tests database layer operations for compliance:
- CompliancePolicyRepository
- ComplianceRunRepository
- ComplianceResultRepository
"""
import pytest
import uuid
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from src.repositories.compliance_repository import (
    CompliancePolicyRepository,
    ComplianceRunRepository,
    ComplianceResultRepository,
)
from src.db_models.compliance import CompliancePolicyDb, ComplianceRunDb, ComplianceResultDb


class TestCompliancePolicyRepository:
    """Test suite for CompliancePolicyRepository"""

    @pytest.fixture
    def repository(self):
        """Create repository instance for testing."""
        return CompliancePolicyRepository()

    @pytest.fixture
    def sample_policy(self, db_session):
        """Create a sample policy in the database."""
        policy = CompliancePolicyDb(
            id=str(uuid.uuid4()),
            name="Test Policy",
            description="Test description",
            rule="hasProperty('test')",
            category="test",
            severity="medium",
            is_active=True,
        )
        db_session.add(policy)
        db_session.commit()
        db_session.refresh(policy)
        return policy

    def test_list_all_empty(self, repository, db_session):
        """Test listing all policies when none exist."""
        # Act
        result = repository.list_all(db_session)

        # Assert
        assert result == []

    def test_list_all_multiple(self, repository, db_session):
        """Test listing multiple policies."""
        # Arrange - Create 3 policies
        for i in range(3):
            policy = CompliancePolicyDb(
                id=str(uuid.uuid4()),
                name=f"Policy {i}",
                description=f"Description {i}",
                rule="hasProperty('test')",
                category="test",
                severity="low",
            )
            db_session.add(policy)
        db_session.commit()

        # Act
        result = repository.list_all(db_session)

        # Assert
        assert len(result) == 3
        assert all(isinstance(p, CompliancePolicyDb) for p in result)

    def test_list_all_ordered_by_updated_at(self, repository, db_session):
        """Test that list_all returns policies ordered by updated_at desc."""
        # Arrange - Create policies with different update times
        policy1 = CompliancePolicyDb(
            id=str(uuid.uuid4()),
            name="Policy 1",
            description="First",
            rule="test",
            updated_at=datetime.utcnow() - timedelta(hours=2),
        )
        policy2 = CompliancePolicyDb(
            id=str(uuid.uuid4()),
            name="Policy 2",
            description="Second",
            rule="test",
            updated_at=datetime.utcnow() - timedelta(hours=1),
        )
        policy3 = CompliancePolicyDb(
            id=str(uuid.uuid4()),
            name="Policy 3",
            description="Third",
            rule="test",
            updated_at=datetime.utcnow(),
        )
        db_session.add(policy1)
        db_session.add(policy2)
        db_session.add(policy3)
        db_session.commit()

        # Act
        result = repository.list_all(db_session)

        # Assert
        assert len(result) == 3
        assert result[0].name == "Policy 3"  # Most recently updated
        assert result[1].name == "Policy 2"
        assert result[2].name == "Policy 1"  # Oldest update


class TestComplianceRunRepository:
    """Test suite for ComplianceRunRepository"""

    @pytest.fixture
    def repository(self):
        """Create repository instance for testing."""
        return ComplianceRunRepository()

    @pytest.fixture
    def sample_policy(self, db_session):
        """Create a sample policy for runs."""
        policy = CompliancePolicyDb(
            id=str(uuid.uuid4()),
            name="Test Policy",
            description="Test",
            rule="test",
        )
        db_session.add(policy)
        db_session.commit()
        db_session.refresh(policy)
        return policy

    @pytest.fixture
    def sample_run(self, db_session, sample_policy):
        """Create a sample run in the database."""
        run = ComplianceRunDb(
            id=str(uuid.uuid4()),
            policy_id=sample_policy.id,
            status="succeeded",
            started_at=datetime.utcnow(),
            finished_at=datetime.utcnow(),
            success_count=10,
            failure_count=2,
            score=83.33,
        )
        db_session.add(run)
        db_session.commit()
        db_session.refresh(run)
        return run

    def test_list_for_policy_empty(self, repository, db_session, sample_policy):
        """Test listing runs for policy with no runs."""
        # Act
        result = repository.list_for_policy(db_session, policy_id=sample_policy.id)

        # Assert
        assert result == []

    def test_list_for_policy_multiple(self, repository, db_session, sample_policy):
        """Test listing multiple runs for a policy."""
        # Arrange - Create 3 runs
        for i in range(3):
            run = ComplianceRunDb(
                id=str(uuid.uuid4()),
                policy_id=sample_policy.id,
                status="succeeded",
                started_at=datetime.utcnow() - timedelta(hours=i),
                finished_at=datetime.utcnow() - timedelta(hours=i),
                success_count=10,
                failure_count=0,
                score=100.0,
            )
            db_session.add(run)
        db_session.commit()

        # Act
        result = repository.list_for_policy(db_session, policy_id=sample_policy.id)

        # Assert
        assert len(result) == 3
        assert all(isinstance(r, ComplianceRunDb) for r in result)
        assert all(r.policy_id == sample_policy.id for r in result)

    def test_list_for_policy_ordered_by_started_at_desc(
        self, repository, db_session, sample_policy
    ):
        """Test that runs are ordered by started_at descending (newest first)."""
        # Arrange
        run1 = ComplianceRunDb(
            id=str(uuid.uuid4()),
            policy_id=sample_policy.id,
            status="succeeded",
            started_at=datetime.utcnow() - timedelta(hours=3),
            success_count=10,
            failure_count=0,
            score=100.0,
        )
        run2 = ComplianceRunDb(
            id=str(uuid.uuid4()),
            policy_id=sample_policy.id,
            status="succeeded",
            started_at=datetime.utcnow() - timedelta(hours=1),
            success_count=10,
            failure_count=0,
            score=100.0,
        )
        run3 = ComplianceRunDb(
            id=str(uuid.uuid4()),
            policy_id=sample_policy.id,
            status="succeeded",
            started_at=datetime.utcnow(),
            success_count=10,
            failure_count=0,
            score=100.0,
        )
        db_session.add(run1)
        db_session.add(run2)
        db_session.add(run3)
        db_session.commit()

        # Act
        result = repository.list_for_policy(db_session, policy_id=sample_policy.id)

        # Assert
        assert len(result) == 3
        assert result[0].id == run3.id  # Most recent
        assert result[1].id == run2.id
        assert result[2].id == run1.id  # Oldest

    def test_list_for_policy_with_limit(self, repository, db_session, sample_policy):
        """Test limiting the number of runs returned."""
        # Arrange - Create 10 runs
        for i in range(10):
            run = ComplianceRunDb(
                id=str(uuid.uuid4()),
                policy_id=sample_policy.id,
                status="succeeded",
                started_at=datetime.utcnow() - timedelta(hours=i),
                success_count=10,
                failure_count=0,
                score=100.0,
            )
            db_session.add(run)
        db_session.commit()

        # Act
        result = repository.list_for_policy(
            db_session, policy_id=sample_policy.id, limit=5
        )

        # Assert
        assert len(result) == 5


class TestComplianceResultRepository:
    """Test suite for ComplianceResultRepository"""

    @pytest.fixture
    def repository(self):
        """Create repository instance for testing."""
        return ComplianceResultRepository()

    @pytest.fixture
    def sample_policy(self, db_session):
        """Create a sample policy."""
        policy = CompliancePolicyDb(
            id=str(uuid.uuid4()),
            name="Test Policy",
            description="Test",
            rule="test",
        )
        db_session.add(policy)
        db_session.commit()
        db_session.refresh(policy)
        return policy

    @pytest.fixture
    def sample_run(self, db_session, sample_policy):
        """Create a sample run."""
        run = ComplianceRunDb(
            id=str(uuid.uuid4()),
            policy_id=sample_policy.id,
            status="succeeded",
            started_at=datetime.utcnow(),
            success_count=10,
            failure_count=0,
            score=100.0,
        )
        db_session.add(run)
        db_session.commit()
        db_session.refresh(run)
        return run

    def test_list_for_run_empty(self, repository, db_session, sample_run):
        """Test listing results for run with no results."""
        # Act
        result = repository.list_for_run(db_session, run_id=sample_run.id)

        # Assert
        assert result == []

    def test_list_for_run_multiple(self, repository, db_session, sample_run):
        """Test listing multiple results for a run."""
        # Arrange - Create 5 results
        for i in range(5):
            result = ComplianceResultDb(
                id=str(uuid.uuid4()),
                run_id=sample_run.id,
                object_type="table",
                object_id=f"table_{i}",
                object_name=f"Table {i}",
                passed=i % 2 == 0,  # Alternate pass/fail
                message=f"Result {i}",
            )
            db_session.add(result)
        db_session.commit()

        # Act
        result = repository.list_for_run(db_session, run_id=sample_run.id)

        # Assert
        assert len(result) == 5
        assert all(isinstance(r, ComplianceResultDb) for r in result)
        assert all(r.run_id == sample_run.id for r in result)

    def test_list_for_run_only_failed(self, repository, db_session, sample_run):
        """Test filtering to only failed results."""
        # Arrange - Create passing and failing results
        result1 = ComplianceResultDb(
            id=str(uuid.uuid4()),
            run_id=sample_run.id,
            object_type="table",
            object_id="table_pass",
            passed=True,
            message="Passed",
        )
        result2 = ComplianceResultDb(
            id=str(uuid.uuid4()),
            run_id=sample_run.id,
            object_type="table",
            object_id="table_fail",
            passed=False,
            message="Failed",
        )
        result3 = ComplianceResultDb(
            id=str(uuid.uuid4()),
            run_id=sample_run.id,
            object_type="table",
            object_id="table_fail2",
            passed=False,
            message="Failed",
        )
        db_session.add(result1)
        db_session.add(result2)
        db_session.add(result3)
        db_session.commit()

        # Act
        result = repository.list_for_run(
            db_session, run_id=sample_run.id, only_failed=True
        )

        # Assert
        assert len(result) == 2
        assert all(r.passed is False for r in result)

    def test_list_for_run_ordered_by_created_at_desc(
        self, repository, db_session, sample_run
    ):
        """Test that results are ordered by created_at descending."""
        # Arrange
        result1 = ComplianceResultDb(
            id=str(uuid.uuid4()),
            run_id=sample_run.id,
            object_type="table",
            object_id="table_1",
            passed=True,
            created_at=datetime.utcnow() - timedelta(seconds=3),
        )
        result2 = ComplianceResultDb(
            id=str(uuid.uuid4()),
            run_id=sample_run.id,
            object_type="table",
            object_id="table_2",
            passed=True,
            created_at=datetime.utcnow() - timedelta(seconds=1),
        )
        result3 = ComplianceResultDb(
            id=str(uuid.uuid4()),
            run_id=sample_run.id,
            object_type="table",
            object_id="table_3",
            passed=True,
            created_at=datetime.utcnow(),
        )
        db_session.add(result1)
        db_session.add(result2)
        db_session.add(result3)
        db_session.commit()

        # Act
        result = repository.list_for_run(db_session, run_id=sample_run.id)

        # Assert
        assert len(result) == 3
        assert result[0].object_id == "table_3"  # Most recent
        assert result[1].object_id == "table_2"
        assert result[2].object_id == "table_1"  # Oldest

    def test_list_for_run_with_limit(self, repository, db_session, sample_run):
        """Test limiting the number of results returned."""
        # Arrange - Create 20 results
        for i in range(20):
            result = ComplianceResultDb(
                id=str(uuid.uuid4()),
                run_id=sample_run.id,
                object_type="table",
                object_id=f"table_{i}",
                passed=True,
            )
            db_session.add(result)
        db_session.commit()

        # Act
        result = repository.list_for_run(db_session, run_id=sample_run.id, limit=10)

        # Assert
        assert len(result) == 10

