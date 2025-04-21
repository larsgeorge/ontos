import json
from typing import Dict, List, Optional
from collections import defaultdict

from api.controller.settings_manager import SettingsManager
from api.models.settings import AppRole
from api.common.features import FeatureAccessLevel, ACCESS_LEVEL_ORDER, get_feature_config
from api.common.logging import get_logger

logger = get_logger(__name__)

class AuthorizationManager:
    def __init__(self, settings_manager: SettingsManager):
        """Requires SettingsManager to access role configurations."""
        self._settings_manager = settings_manager

    def get_user_effective_permissions(self, user_groups: Optional[List[str]]) -> Dict[str, FeatureAccessLevel]:
        """
        Calculates the effective permission level for each feature based on the user's groups.
        Permissions are merged by taking the highest level granted by any matching role.

        Args:
            user_groups: A list of group names the user belongs to.

        Returns:
            A dictionary mapping feature IDs to the highest granted FeatureAccessLevel.
        """
        if not user_groups:
            user_groups = []

        user_group_set = set(user_groups)
        effective_permissions: Dict[str, FeatureAccessLevel] = defaultdict(lambda: FeatureAccessLevel.NONE)
        all_roles = self._settings_manager.list_app_roles() # Fetches roles from DB via SettingsManager
        feature_config = get_feature_config()

        logger.debug(f"Calculating effective permissions for groups: {user_groups}")
        logger.debug(f"Found {len(all_roles)} roles in total.")

        matching_roles = []
        for role in all_roles:
            # Check for intersection between user groups and role's assigned groups
            if user_group_set.intersection(role.assigned_groups):
                matching_roles.append(role)
                logger.debug(f"User groups match role: '{role.name}' (ID: {role.id}) assigned groups: {role.assigned_groups}")

        if not matching_roles:
            logger.debug("No matching roles found for user groups.")
            # Return default NONE permissions for all features if no roles match
            return {feat_id: FeatureAccessLevel.NONE for feat_id in feature_config}

        # Merge permissions from matching roles
        for role in matching_roles:
            for feature_id, assigned_level in role.feature_permissions.items():
                if feature_id not in feature_config:
                    logger.warning(f"Role '{role.name}' contains permission for unknown feature ID '{feature_id}'. Skipping.")
                    continue

                current_effective_level = effective_permissions[feature_id]
                # Compare levels using the defined order
                if ACCESS_LEVEL_ORDER[assigned_level] > ACCESS_LEVEL_ORDER[current_effective_level]:
                    effective_permissions[feature_id] = assigned_level
                    logger.debug(f"Updated effective permission for '{feature_id}' to '{assigned_level.value}' from role '{role.name}'")

        # Ensure all features have at least NONE permission defined
        for feature_id in feature_config:
            if feature_id not in effective_permissions:
                effective_permissions[feature_id] = FeatureAccessLevel.NONE

        logger.info(f"Calculated effective permissions for groups {user_groups}: { {k: v.value for k,v in effective_permissions.items()} }")
        return dict(effective_permissions)

    def has_permission(self, effective_permissions: Dict[str, FeatureAccessLevel], feature_id: str, required_level: FeatureAccessLevel) -> bool:
        """
        Checks if the user's effective permissions meet the required level for a specific feature.

        Args:
            effective_permissions: The user's calculated effective permissions.
            feature_id: The ID of the feature to check.
            required_level: The minimum FeatureAccessLevel required.

        Returns:
            True if the user has sufficient permission, False otherwise.
        """
        user_level = effective_permissions.get(feature_id, FeatureAccessLevel.NONE)
        has_perm = ACCESS_LEVEL_ORDER[user_level] >= ACCESS_LEVEL_ORDER[required_level]
        logger.debug(f"Permission check for feature '{feature_id}': Required='{required_level.value}', User has='{user_level.value}'. Granted: {has_perm}")
        return has_perm 