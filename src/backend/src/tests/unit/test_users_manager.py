"""
Unit tests for UsersManager
"""
import pytest
from unittest.mock import Mock, MagicMock
from databricks.sdk.errors import NotFound, DatabricksError
from src.controller.users_manager import UsersManager
from src.models.users import UserInfo


class TestUsersManager:
    """Test suite for UsersManager."""

    @pytest.fixture
    def mock_ws_client(self):
        """Create mock workspace client."""
        return Mock()

    @pytest.fixture
    def manager(self, mock_ws_client):
        """Create UsersManager instance for testing."""
        return UsersManager(ws_client=mock_ws_client)

    @pytest.fixture
    def mock_databricks_user(self):
        """Create mock Databricks user object."""
        user = Mock()
        user.user_name = "test@example.com"
        user.display_name = "Test User"
        user.active = True
        
        # Mock email
        email = Mock()
        email.value = "test@example.com"
        user.emails = [email]
        
        # Mock groups
        group1 = Mock()
        group1.display = "data_engineers"
        group2 = Mock()
        group2.display = "admins"
        user.groups = [group1, group2]
        
        return user

    # Initialization Tests

    def test_manager_initialization_with_client(self, mock_ws_client):
        """Test manager initializes with workspace client."""
        manager = UsersManager(ws_client=mock_ws_client)
        assert manager._ws_client == mock_ws_client

    def test_manager_initialization_without_client(self):
        """Test manager initializes without workspace client (logs warning)."""
        manager = UsersManager(ws_client=None)
        assert manager._ws_client is None

    # Get User Details Tests

    def test_get_user_details_by_email_success(
        self, manager, mock_ws_client, mock_databricks_user
    ):
        """Test successfully getting user details by email."""
        mock_ws_client.users.list.return_value = iter([mock_databricks_user])

        result = manager.get_user_details_by_email("test@example.com", "192.168.1.1")

        assert isinstance(result, UserInfo)
        assert result.email == "test@example.com"
        assert result.username == "test@example.com"
        assert result.user == "Test User"
        assert result.ip == "192.168.1.1"
        assert result.groups == ["data_engineers", "admins"]

    def test_get_user_details_by_email_no_groups(
        self, manager, mock_ws_client, mock_databricks_user
    ):
        """Test getting user details when user has no groups."""
        mock_databricks_user.groups = []
        mock_ws_client.users.list.return_value = iter([mock_databricks_user])

        result = manager.get_user_details_by_email("test@example.com", "192.168.1.1")

        # Empty groups returns None (not []) based on the code logic
        assert result.groups is None

    def test_get_user_details_by_email_none_groups(
        self, manager, mock_ws_client, mock_databricks_user
    ):
        """Test getting user details when user has None groups."""
        mock_databricks_user.groups = None
        mock_ws_client.users.list.return_value = iter([mock_databricks_user])

        result = manager.get_user_details_by_email("test@example.com", "192.168.1.1")

        assert result.groups is None

    def test_get_user_details_by_email_no_email(
        self, manager, mock_ws_client, mock_databricks_user
    ):
        """Test getting user details when user has no email (uses username)."""
        mock_databricks_user.emails = []
        mock_ws_client.users.list.return_value = iter([mock_databricks_user])

        result = manager.get_user_details_by_email("test@example.com", "192.168.1.1")

        # Should fall back to username
        assert result.email == "test@example.com"

    def test_get_user_details_by_email_user_not_found(self, manager, mock_ws_client):
        """Test getting user details when user not found."""
        mock_ws_client.users.list.return_value = iter([])

        with pytest.raises(NotFound, match="not found via SDK"):
            manager.get_user_details_by_email("nonexistent@example.com", "192.168.1.1")

    def test_get_user_details_by_email_multiple_users(
        self, manager, mock_ws_client, mock_databricks_user
    ):
        """Test getting user details when multiple users found (uses first)."""
        user2 = Mock()
        user2.user_name = "test@example.com"
        user2.display_name = "Test User 2"
        user2.active = True
        email2 = Mock()
        email2.value = "test@example.com"
        user2.emails = [email2]
        user2.groups = []

        mock_ws_client.users.list.return_value = iter([mock_databricks_user, user2])

        result = manager.get_user_details_by_email("test@example.com", "192.168.1.1")

        # Should use first user
        assert result.user == "Test User"

    def test_get_user_details_by_email_no_workspace_client(self):
        """Test getting user details when workspace client not configured."""
        manager = UsersManager(ws_client=None)

        with pytest.raises(ValueError, match="WorkspaceClient is not configured"):
            manager.get_user_details_by_email("test@example.com", "192.168.1.1")

    def test_get_user_details_by_email_databricks_error(
        self, manager, mock_ws_client
    ):
        """Test handling of Databricks SDK errors."""
        mock_ws_client.users.list.side_effect = DatabricksError("API Error")

        with pytest.raises(RuntimeError, match="Databricks SDK error"):
            manager.get_user_details_by_email("test@example.com", "192.168.1.1")

    def test_get_user_details_by_email_unexpected_error(
        self, manager, mock_ws_client
    ):
        """Test handling of unexpected errors."""
        mock_ws_client.users.list.side_effect = Exception("Unexpected error")

        with pytest.raises(RuntimeError, match="Unexpected error during SDK user lookup"):
            manager.get_user_details_by_email("test@example.com", "192.168.1.1")

    def test_get_user_details_by_email_uses_filter(
        self, manager, mock_ws_client, mock_databricks_user
    ):
        """Test that correct filter is applied when listing users."""
        mock_ws_client.users.list.return_value = iter([mock_databricks_user])

        manager.get_user_details_by_email("test@example.com", "192.168.1.1")

        # Verify filter was used
        mock_ws_client.users.list.assert_called_once_with(
            filter='userName eq "test@example.com"'
        )

    def test_get_user_details_by_email_none_ip(
        self, manager, mock_ws_client, mock_databricks_user
    ):
        """Test getting user details with None IP address."""
        mock_ws_client.users.list.return_value = iter([mock_databricks_user])

        result = manager.get_user_details_by_email("test@example.com", None)

        assert result.ip is None

    def test_get_user_details_by_email_extracts_group_display_names(
        self, manager, mock_ws_client, mock_databricks_user
    ):
        """Test that group display names are correctly extracted."""
        group_with_display = Mock()
        group_with_display.display = "team_alpha"
        
        group_without_display = Mock()
        group_without_display.display = None
        
        mock_databricks_user.groups = [group_with_display, group_without_display]
        mock_ws_client.users.list.return_value = iter([mock_databricks_user])

        result = manager.get_user_details_by_email("test@example.com", "192.168.1.1")

        # Should only include groups with display names
        assert result.groups == ["team_alpha"]

