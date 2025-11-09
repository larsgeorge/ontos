"""
Unit tests for ApprovalsManager

Tests approval queue management including:
- Getting approvals queue
- Filtering by entity type
"""
import pytest
import uuid

from src.controller.approvals_manager import ApprovalsManager
from src.db_models.data_contracts import DataContractDb
from src.db_models.data_products import DataProductDb


class TestApprovalsManager:
    """Test suite for ApprovalsManager"""

    @pytest.fixture
    def manager(self):
        """Create ApprovalsManager instance for testing."""
        return ApprovalsManager()

    def test_manager_initialization(self, manager):
        """Test manager initializes successfully."""
        assert manager is not None

    def test_get_approvals_queue_empty(self, manager, db_session):
        """Test getting approvals queue when none exist."""
        # Act
        result = manager.get_approvals_queue(db=db_session)

        # Assert
        assert result is not None
        assert 'contracts' in result
        assert 'products' in result
        assert result['contracts'] == []
        assert result['products'] == []

    def test_get_approvals_queue_with_contracts(self, manager, db_session):
        """Test getting approvals queue with pending contracts."""
        # Arrange - Create contracts with different statuses
        contract1 = DataContractDb(
            id=str(uuid.uuid4()),
            name="Proposed Contract",
            version="1.0.0",
            status="proposed",
            created_by="user@example.com",
        )
        contract2 = DataContractDb(
            id=str(uuid.uuid4()),
            name="Under Review Contract",
            version="1.0.0",
            status="under_review",
            created_by="user@example.com",
        )
        contract3 = DataContractDb(
            id=str(uuid.uuid4()),
            name="Active Contract",
            version="1.0.0",
            status="active",
            created_by="user@example.com",
        )
        db_session.add_all([contract1, contract2, contract3])
        db_session.commit()

        # Act
        result = manager.get_approvals_queue(db=db_session)

        # Assert
        assert len(result['contracts']) == 2
        contract_ids = [c['id'] for c in result['contracts']]
        assert contract1.id in contract_ids
        assert contract2.id in contract_ids
        assert contract3.id not in contract_ids

    def test_get_approvals_queue_with_products(self, manager, db_session):
        """Test getting approvals queue with draft products."""
        # Arrange - Create products with different statuses
        product1 = DataProductDb(
            id=str(uuid.uuid4()),
            name="Draft Product",
            version="1.0.0",
            status="draft",
        )
        product2 = DataProductDb(
            id=str(uuid.uuid4()),
            name="Active Product",
            version="1.0.0",
            status="active",
        )
        db_session.add_all([product1, product2])
        db_session.commit()

        # Act
        result = manager.get_approvals_queue(db=db_session)

        # Assert
        assert len(result['products']) == 1
        assert result['products'][0]['id'] == product1.id
        assert result['products'][0]['title'] == "Draft Product"

    def test_get_approvals_queue_mixed(self, manager, db_session):
        """Test getting approvals queue with both contracts and products."""
        # Arrange
        contract = DataContractDb(
            id=str(uuid.uuid4()),
            name="Proposed Contract",
            version="1.0.0",
            status="proposed",
            created_by="user@example.com",
        )
        product = DataProductDb(
            id=str(uuid.uuid4()),
            name="Draft Product",
            version="1.0.0",
            status="draft",
        )
        db_session.add_all([contract, product])
        db_session.commit()

        # Act
        result = manager.get_approvals_queue(db=db_session)

        # Assert
        assert len(result['contracts']) == 1
        assert len(result['products']) == 1
        assert result['contracts'][0]['name'] == "Proposed Contract"
        assert result['products'][0]['title'] == "Draft Product"

