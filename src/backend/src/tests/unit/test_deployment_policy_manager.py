"""
Unit tests for DeploymentPolicyManager
"""
import pytest
from unittest.mock import Mock, MagicMock
from src.controller.deployment_policy_manager import DeploymentPolicyManager
from src.models.settings import DeploymentPolicy, AppRole
from src.models.users import UserInfo


class TestDeploymentPolicyManager:
    """Test suite for DeploymentPolicyManager."""

    @pytest.fixture
    def mock_settings_manager(self):
        """Create mock settings manager."""
        return Mock()

    @pytest.fixture
    def manager(self, mock_settings_manager):
        """Create DeploymentPolicyManager instance for testing."""
        return DeploymentPolicyManager(settings_manager=mock_settings_manager)

    @pytest.fixture
    def sample_user(self):
        """Sample user info."""
        return UserInfo(
            username="testuser",
            email="test@example.com",
            user="testuser",
            ip="127.0.0.1",
            groups=["data_engineers", "team_alpha"],
        )

    @pytest.fixture
    def sample_deployment_policy(self):
        """Sample deployment policy."""
        return DeploymentPolicy(
            allowed_catalogs=["dev_catalog", "test_catalog"],
            allowed_schemas=["schema_*"],
            default_catalog="dev_catalog",
            default_schema="default_schema",
            require_approval=False,
            can_approve_deployments=True,
        )

    # Initialization Tests

    def test_manager_initialization(self, mock_settings_manager):
        """Test manager initializes with settings manager."""
        manager = DeploymentPolicyManager(settings_manager=mock_settings_manager)
        assert manager.settings_manager == mock_settings_manager

    # Get Effective Policy Tests

    def test_get_effective_policy_with_role_override(
        self, manager, mock_settings_manager, sample_user, sample_deployment_policy
    ):
        """Test getting effective policy when user has role override."""
        mock_role = Mock(spec=AppRole)
        mock_role.id = "role-123"
        mock_role.name = "Override Role"
        mock_role.deployment_policy = sample_deployment_policy

        mock_settings_manager.get_applied_role_override_for_user.return_value = "role-123"
        mock_settings_manager.get_app_role.return_value = mock_role

        policy = manager.get_effective_policy(sample_user)

        assert len(policy.allowed_catalogs) == 2
        assert policy.require_approval is False

    def test_get_effective_policy_from_groups(
        self, manager, mock_settings_manager, sample_user, sample_deployment_policy
    ):
        """Test getting effective policy from user's group roles."""
        mock_settings_manager.get_applied_role_override_for_user.return_value = None

        mock_role = Mock(spec=AppRole)
        mock_role.name = "Data Engineer"
        mock_role.assigned_groups = ["data_engineers"]
        mock_role.deployment_policy = sample_deployment_policy

        mock_settings_manager.list_app_roles.return_value = [mock_role]

        policy = manager.get_effective_policy(sample_user)

        assert len(policy.allowed_catalogs) == 2
        assert "dev_catalog" in policy.allowed_catalogs

    def test_get_effective_policy_no_policies_found(
        self, manager, mock_settings_manager, sample_user
    ):
        """Test getting effective policy when no policies are found."""
        mock_settings_manager.get_applied_role_override_for_user.return_value = None
        mock_settings_manager.list_app_roles.return_value = []

        policy = manager.get_effective_policy(sample_user)

        # Should return restrictive default
        assert policy.allowed_catalogs == []
        assert policy.require_approval is True
        assert policy.can_approve_deployments is False

    def test_get_effective_policy_merges_multiple_roles(
        self, manager, mock_settings_manager, sample_user
    ):
        """Test merging policies from multiple roles."""
        mock_settings_manager.get_applied_role_override_for_user.return_value = None

        role1 = Mock(spec=AppRole)
        role1.name = "Role 1"
        role1.assigned_groups = ["data_engineers"]
        role1.deployment_policy = DeploymentPolicy(
            allowed_catalogs=["catalog_a"],
            allowed_schemas=[],
            require_approval=True,
            can_approve_deployments=False,
        )

        role2 = Mock(spec=AppRole)
        role2.name = "Role 2"
        role2.assigned_groups = ["team_alpha"]
        role2.deployment_policy = DeploymentPolicy(
            allowed_catalogs=["catalog_b"],
            allowed_schemas=[],
            require_approval=False,
            can_approve_deployments=True,
        )

        mock_settings_manager.list_app_roles.return_value = [role1, role2]

        policy = manager.get_effective_policy(sample_user)

        # Should merge both catalogs
        assert len(policy.allowed_catalogs) == 2
        assert "catalog_a" in policy.allowed_catalogs
        assert "catalog_b" in policy.allowed_catalogs
        # Most permissive wins
        assert policy.require_approval is False
        assert policy.can_approve_deployments is True

    # Merge Policies Tests

    def test_merge_policies_single_policy(self, manager, sample_deployment_policy):
        """Test merging single policy returns it unchanged."""
        result = manager._merge_policies([sample_deployment_policy])
        assert result == sample_deployment_policy

    def test_merge_policies_union_catalogs(self, manager):
        """Test merging policies creates union of catalogs."""
        policy1 = DeploymentPolicy(
            allowed_catalogs=["cat_a", "cat_b"],
            allowed_schemas=[],
            require_approval=True,
            can_approve_deployments=False,
        )
        policy2 = DeploymentPolicy(
            allowed_catalogs=["cat_b", "cat_c"],
            allowed_schemas=[],
            require_approval=True,
            can_approve_deployments=False,
        )

        merged = manager._merge_policies([policy1, policy2])

        assert len(merged.allowed_catalogs) == 3
        assert "cat_a" in merged.allowed_catalogs
        assert "cat_b" in merged.allowed_catalogs
        assert "cat_c" in merged.allowed_catalogs

    def test_merge_policies_most_permissive_booleans(self, manager):
        """Test merging policies uses most permissive boolean values."""
        policy1 = DeploymentPolicy(
            allowed_catalogs=["cat_a"],
            allowed_schemas=[],
            require_approval=True,
            can_approve_deployments=False,
        )
        policy2 = DeploymentPolicy(
            allowed_catalogs=["cat_b"],
            allowed_schemas=[],
            require_approval=False,
            can_approve_deployments=True,
        )

        merged = manager._merge_policies([policy1, policy2])

        assert merged.require_approval is False
        assert merged.can_approve_deployments is True

    def test_merge_policies_default_values(self, manager):
        """Test merging policies uses first non-None defaults."""
        policy1 = DeploymentPolicy(
            allowed_catalogs=["cat_a"],
            allowed_schemas=[],
            default_catalog="default_cat",
            default_schema="default_schema",
            require_approval=True,
            can_approve_deployments=False,
        )
        policy2 = DeploymentPolicy(
            allowed_catalogs=["cat_b"],
            allowed_schemas=[],
            default_catalog="other_cat",
            default_schema="other_schema",
            require_approval=True,
            can_approve_deployments=False,
        )

        merged = manager._merge_policies([policy1, policy2])

        # First non-None wins
        assert merged.default_catalog == "default_cat"
        assert merged.default_schema == "default_schema"

    # Resolve Policy Templates Tests

    def test_resolve_policy_templates_username(self, manager, sample_user):
        """Test resolving {username} template variable."""
        policy = DeploymentPolicy(
            allowed_catalogs=["user_{username}_catalog"],
            allowed_schemas=[],
            require_approval=True,
            can_approve_deployments=False,
        )

        resolved = manager._resolve_policy_templates(policy, sample_user)

        assert resolved.allowed_catalogs[0] == "user_test_catalog"

    def test_resolve_policy_templates_email(self, manager, sample_user):
        """Test resolving {email} template variable."""
        policy = DeploymentPolicy(
            allowed_catalogs=["{email}_catalog"],
            allowed_schemas=[],
            require_approval=True,
            can_approve_deployments=False,
        )

        resolved = manager._resolve_policy_templates(policy, sample_user)

        assert resolved.allowed_catalogs[0] == "test@example.com_catalog"

    def test_resolve_policy_templates_defaults(self, manager, sample_user):
        """Test resolving templates in default values."""
        policy = DeploymentPolicy(
            allowed_catalogs=["catalog_a"],
            allowed_schemas=[],
            default_catalog="{username}_default",
            default_schema="{username}_schema",
            require_approval=True,
            can_approve_deployments=False,
        )

        resolved = manager._resolve_policy_templates(policy, sample_user)

        assert resolved.default_catalog == "test_default"
        assert resolved.default_schema == "test_schema"

    def test_resolve_policy_templates_none_defaults(self, manager, sample_user):
        """Test resolving templates with None defaults."""
        policy = DeploymentPolicy(
            allowed_catalogs=["catalog_a"],
            allowed_schemas=[],
            default_catalog=None,
            default_schema=None,
            require_approval=True,
            can_approve_deployments=False,
        )

        resolved = manager._resolve_policy_templates(policy, sample_user)

        assert resolved.default_catalog is None
        assert resolved.default_schema is None

    # Apply Replacements Tests

    def test_apply_replacements(self, manager):
        """Test applying template replacements."""
        result = manager._apply_replacements(
            "user_{username}_catalog",
            {"{username}": "jdoe", "{email}": "jdoe@example.com"},
        )
        assert result == "user_jdoe_catalog"

    def test_apply_replacements_multiple(self, manager):
        """Test applying multiple replacements."""
        result = manager._apply_replacements(
            "{username}_{email}_catalog",
            {"{username}": "jdoe", "{email}": "test"},
        )
        assert result == "jdoe_test_catalog"

    # Validate Deployment Target Tests

    def test_validate_deployment_target_empty_policy(self, manager):
        """Test validation with empty policy."""
        policy = DeploymentPolicy(
            allowed_catalogs=[],
            allowed_schemas=[],
            require_approval=True,
            can_approve_deployments=False,
        )

        is_valid, error = manager.validate_deployment_target(policy, "test_catalog")

        assert is_valid is False
        assert "No deployment catalogs allowed" in error

    def test_validate_deployment_target_catalog_allowed(self, manager):
        """Test validation with allowed catalog."""
        policy = DeploymentPolicy(
            allowed_catalogs=["dev_catalog", "test_catalog"],
            allowed_schemas=[],
            require_approval=True,
            can_approve_deployments=False,
        )

        is_valid, error = manager.validate_deployment_target(policy, "dev_catalog")

        assert is_valid is True
        assert error is None

    def test_validate_deployment_target_catalog_not_allowed(self, manager):
        """Test validation with disallowed catalog."""
        policy = DeploymentPolicy(
            allowed_catalogs=["dev_catalog"],
            allowed_schemas=[],
            require_approval=True,
            can_approve_deployments=False,
        )

        is_valid, error = manager.validate_deployment_target(policy, "prod_catalog")

        assert is_valid is False
        assert "not allowed" in error

    def test_validate_deployment_target_schema_allowed(self, manager):
        """Test validation with allowed schema."""
        policy = DeploymentPolicy(
            allowed_catalogs=["dev_catalog"],
            allowed_schemas=["test_schema", "prod_schema"],
            require_approval=True,
            can_approve_deployments=False,
        )

        is_valid, error = manager.validate_deployment_target(
            policy, "dev_catalog", "test_schema"
        )

        assert is_valid is True
        assert error is None

    def test_validate_deployment_target_schema_not_allowed(self, manager):
        """Test validation with disallowed schema."""
        policy = DeploymentPolicy(
            allowed_catalogs=["dev_catalog"],
            allowed_schemas=["allowed_schema"],
            require_approval=True,
            can_approve_deployments=False,
        )

        is_valid, error = manager.validate_deployment_target(
            policy, "dev_catalog", "forbidden_schema"
        )

        assert is_valid is False
        assert "Schema" in error and "not allowed" in error

    def test_validate_deployment_target_no_schema_restrictions(self, manager):
        """Test validation when policy has no schema restrictions."""
        policy = DeploymentPolicy(
            allowed_catalogs=["dev_catalog"],
            allowed_schemas=[],
            require_approval=True,
            can_approve_deployments=False,
        )

        is_valid, error = manager.validate_deployment_target(
            policy, "dev_catalog", "any_schema"
        )

        # Should be valid since no schema restrictions
        assert is_valid is True
        assert error is None

    # Matches Pattern Tests

    def test_matches_pattern_wildcard_all(self, manager):
        """Test wildcard * matches everything."""
        assert manager._matches_pattern("anything", "*") is True
        assert manager._matches_pattern("catalog_123", "*") is True

    def test_matches_pattern_exact_match(self, manager):
        """Test exact pattern matching."""
        assert manager._matches_pattern("test_catalog", "test_catalog") is True
        assert manager._matches_pattern("test_catalog", "other_catalog") is False

    def test_matches_pattern_wildcard_prefix(self, manager):
        """Test wildcard prefix matching."""
        assert manager._matches_pattern("user_jdoe", "user_*") is True
        assert manager._matches_pattern("user_alice", "user_*") is True
        assert manager._matches_pattern("admin_bob", "user_*") is False

    def test_matches_pattern_wildcard_suffix(self, manager):
        """Test wildcard suffix matching."""
        assert manager._matches_pattern("jdoe_catalog", "*_catalog") is True
        assert manager._matches_pattern("alice_catalog", "*_catalog") is True
        assert manager._matches_pattern("schema_test", "*_catalog") is False

    def test_matches_pattern_wildcard_middle(self, manager):
        """Test wildcard in middle of pattern."""
        assert manager._matches_pattern("dev_user_catalog", "dev_*_catalog") is True
        assert manager._matches_pattern("prod_admin_catalog", "dev_*_catalog") is False

    def test_matches_pattern_regex(self, manager):
        """Test regex pattern matching."""
        assert manager._matches_pattern("catalog_123", "^catalog_\\d+$") is True
        assert manager._matches_pattern("catalog_abc", "^catalog_\\d+$") is False

    def test_matches_pattern_invalid_regex(self, manager):
        """Test handling of invalid regex pattern."""
        # Invalid regex should return False and log error
        assert manager._matches_pattern("test", "^(invalid") is False

    def test_matches_pattern_empty_value(self, manager):
        """Test matching with empty value."""
        assert manager._matches_pattern("", "pattern") is False
        assert manager._matches_pattern(None, "pattern") is False

    def test_matches_pattern_empty_pattern(self, manager):
        """Test matching with empty pattern."""
        assert manager._matches_pattern("value", "") is False
        assert manager._matches_pattern("value", None) is False

    # Can Approve Deployment Tests

    def test_can_approve_deployment_without_permission(self, manager):
        """Test approval check when user lacks approval permission."""
        policy = DeploymentPolicy(
            allowed_catalogs=["dev_catalog"],
            allowed_schemas=[],
            require_approval=True,
            can_approve_deployments=False,
        )

        result = manager.can_approve_deployment_to(policy, "dev_catalog")

        assert result is False

    def test_can_approve_deployment_with_permission_and_access(self, manager):
        """Test approval check when user has permission and access."""
        policy = DeploymentPolicy(
            allowed_catalogs=["dev_catalog"],
            allowed_schemas=[],
            require_approval=True,
            can_approve_deployments=True,
        )

        result = manager.can_approve_deployment_to(policy, "dev_catalog")

        assert result is True

    def test_can_approve_deployment_with_permission_without_access(self, manager):
        """Test approval check when user has permission but no access to target."""
        policy = DeploymentPolicy(
            allowed_catalogs=["dev_catalog"],
            allowed_schemas=[],
            require_approval=True,
            can_approve_deployments=True,
        )

        result = manager.can_approve_deployment_to(policy, "prod_catalog")

        assert result is False

    def test_can_approve_deployment_schema_check(self, manager):
        """Test approval check with schema restrictions."""
        policy = DeploymentPolicy(
            allowed_catalogs=["dev_catalog"],
            allowed_schemas=["allowed_schema"],
            require_approval=True,
            can_approve_deployments=True,
        )

        # Can approve to allowed schema
        result1 = manager.can_approve_deployment_to(policy, "dev_catalog", "allowed_schema")
        assert result1 is True

        # Cannot approve to disallowed schema
        result2 = manager.can_approve_deployment_to(policy, "dev_catalog", "forbidden_schema")
        assert result2 is False
