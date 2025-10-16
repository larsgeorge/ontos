"""Dependency injection for deployment policy manager."""

from fastapi import Depends
from src.controller.deployment_policy_manager import DeploymentPolicyManager
from src.common.manager_dependencies import get_settings_manager
from src.controller.settings_manager import SettingsManager


def get_deployment_policy_manager(
    settings_manager: SettingsManager = Depends(get_settings_manager)
) -> DeploymentPolicyManager:
    """Dependency to get DeploymentPolicyManager instance."""
    return DeploymentPolicyManager(settings_manager)

