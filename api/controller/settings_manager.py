from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import json
import uuid

import yaml
from databricks.sdk import WorkspaceClient
from databricks.sdk.service import jobs
from pydantic import ValidationError
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func

from api.common.config import Settings
from api.models.settings import JobCluster, WorkflowInstallation, AppRole, AppRoleCreate, AppRoleUpdate
from api.common.features import get_feature_config, FeatureAccessLevel, get_all_access_levels, APP_FEATURES
from api.common.logging import get_logger
from api.repositories.settings_repository import app_role_repo, AppRoleRepository
from api.db_models.settings import AppRoleDb

logger = get_logger(__name__)

# Define the path for storing roles configuration
# ROLES_YAML_PATH = Path("api/data/app_roles.yaml")

# --- Default Role Definitions --- 

# Define default roles structure
DEFAULT_ROLES = [
    {"name": "Admin", "description": "Default role: Admin"},
    {"name": "Data Governance Officer", "description": "Default role: Data Governance Officer"},
    {"name": "Data Steward", "description": "Default role: Data Steward"},
    {"name": "Data Consumer", "description": "Default role: Data Consumer"},
    {"name": "Data Producer", "description": "Default role: Data Producer"},
    {"name": "Security Officer", "description": "Default role: Security Officer"},
]

# Define desired default permissions for non-Admin roles
# These should be validated against allowed_levels in ensure_default_roles_exist
DEFAULT_ROLE_PERMISSIONS = {
    "Data Governance Officer": {
        'data-domains': FeatureAccessLevel.ADMIN,
        'data-products': FeatureAccessLevel.ADMIN,
        'data-contracts': FeatureAccessLevel.ADMIN,
        'business-glossary': FeatureAccessLevel.ADMIN,
        'compliance': FeatureAccessLevel.ADMIN,
        'estate-manager': FeatureAccessLevel.ADMIN,
        'master-data': FeatureAccessLevel.ADMIN,
        'security': FeatureAccessLevel.ADMIN,
        'entitlements': FeatureAccessLevel.ADMIN,
        'entitlements-sync': FeatureAccessLevel.ADMIN,
        'data-asset-reviews': FeatureAccessLevel.ADMIN,
        'catalog-commander': FeatureAccessLevel.FULL,
        'settings': FeatureAccessLevel.READ_ONLY, # DGO can view settings?
    },
    "Data Steward": {
        'data-domains': FeatureAccessLevel.READ_WRITE,
        'data-products': FeatureAccessLevel.READ_WRITE,
        'data-contracts': FeatureAccessLevel.READ_WRITE,
        'business-glossary': FeatureAccessLevel.READ_WRITE,
        'compliance': FeatureAccessLevel.READ_ONLY,
        'data-asset-reviews': FeatureAccessLevel.READ_WRITE,
        'catalog-commander': FeatureAccessLevel.READ_ONLY,
    },
    "Data Consumer": {
        'data-domains': FeatureAccessLevel.READ_ONLY,
        'data-products': FeatureAccessLevel.READ_ONLY,
        'data-contracts': FeatureAccessLevel.READ_ONLY,
        'business-glossary': FeatureAccessLevel.READ_ONLY,
        'catalog-commander': FeatureAccessLevel.READ_ONLY,
    },
    "Data Producer": {
        'data-domains': FeatureAccessLevel.READ_ONLY,
        'data-products': FeatureAccessLevel.READ_WRITE,
        'data-contracts': FeatureAccessLevel.READ_WRITE,
        'business-glossary': FeatureAccessLevel.READ_ONLY,
        'catalog-commander': FeatureAccessLevel.READ_ONLY,
    },
    "Security Officer": {
        'security': FeatureAccessLevel.ADMIN,
        'entitlements': FeatureAccessLevel.ADMIN,
        'entitlements-sync': FeatureAccessLevel.ADMIN,
        'compliance': FeatureAccessLevel.READ_WRITE,
        'data-asset-reviews': FeatureAccessLevel.READ_ONLY,
    },
}

class SettingsManager:
    def __init__(self, db: Session, settings: Settings, workspace_client: Optional[WorkspaceClient] = None):
        """Inject database session, settings, and optional workspace client."""
        self._db = db
        self._settings = settings # Store settings
        self._client = workspace_client
        self._available_jobs = [
            'data_contracts',
            'business_glossaries',
            'entitlements',
            'mdm_jobs',
            'catalog_commander_jobs'
        ]
        self._installations: Dict[str, WorkflowInstallation] = {}
        self.app_role_repo = app_role_repo

    def ensure_default_roles_exist(self):
        """Checks if default roles exist and creates them if necessary."""
        try:
            existing_roles_count = self.get_app_roles_count()
            if existing_roles_count > 0:
                logger.info(f"Found {existing_roles_count} existing roles. Skipping default role creation.")
                return

            logger.info("No existing roles found. Creating default roles...")
            
            # Parse Admin Groups
            admin_groups = []
            try:
                groups_json = self._settings.APP_ADMIN_DEFAULT_GROUPS # Use self._settings
                if groups_json:
                    admin_groups = json.loads(groups_json)
                    if not isinstance(admin_groups, list):
                        logger.warning(f"APP_ADMIN_DEFAULT_GROUPS ({groups_json}) is not a valid JSON list. Defaulting Admin role to no groups.")
                        admin_groups = []
                else:
                    logger.info("APP_ADMIN_DEFAULT_GROUPS is not set. Defaulting Admin role to no groups.")
            except json.JSONDecodeError:
                logger.warning(f"Could not parse APP_ADMIN_DEFAULT_GROUPS JSON: '{self._settings.APP_ADMIN_DEFAULT_GROUPS}'. Defaulting Admin role to no groups.")
                admin_groups = []
            
            logger.info(f"Using default admin groups for 'Admin' role: {admin_groups}")
            all_features_config = get_feature_config() # Get the full config
            logger.info(f"Found features: {list(all_features_config.keys())}")

            for role_def in DEFAULT_ROLES:
                role_data = role_def.copy()
                role_name = role_data["name"]
                
                if role_name == "Admin":
                    role_data["assigned_groups"] = admin_groups
                    role_data["feature_permissions"] = {
                        feat_id: FeatureAccessLevel.ADMIN
                        for feat_id in all_features_config
                    }
                    logger.info(f"Assigning default ADMIN permissions to Admin role for features: {list(all_features_config.keys())}")
                else:
                    role_data["assigned_groups"] = []
                    desired_permissions = DEFAULT_ROLE_PERMISSIONS.get(role_name, {})
                    final_permissions = {}
                    for feat_id, feature_config in all_features_config.items():
                        desired_level = desired_permissions.get(feat_id, FeatureAccessLevel.NONE)
                        allowed_levels = feature_config.get('allowed_levels', [])
                        
                        if desired_level in allowed_levels:
                            final_permissions[feat_id] = desired_level
                        else:
                            final_permissions[feat_id] = FeatureAccessLevel.NONE
                            if desired_level != FeatureAccessLevel.NONE:
                                allowed_str = [lvl.value for lvl in allowed_levels]
                                logger.warning(
                                    f"Desired default permission '{desired_level.value}' for role '{role_name}' "
                                    f"on feature '{feat_id}' is not allowed (Allowed: {allowed_str}). Setting to NONE."
                                )
                                
                    role_data["feature_permissions"] = final_permissions
                    logger.info(f"Assigning default permissions for role '{role_name}': { {k: v.value for k,v in final_permissions.items()} }")

                logger.debug(f"Final permissions data for role '{role_name}': {role_data['feature_permissions']}")

                try:
                    role_create_model = AppRoleCreate(**role_data)
                    self.create_app_role(role=role_create_model) # Use self.create_app_role
                    logger.info(f"Successfully created default role: {role_name}")
                except Exception as e:
                    # Log the specific role data that failed validation/creation
                    logger.error(f"Failed to create default role {role_name} with data {role_data}: {e}", exc_info=True)
                    # Should we raise here to prevent startup? Probably yes.
                    raise RuntimeError(f"Failed to create default role {role_name}. Halting startup.") from e
            
            # Commit once after all roles are potentially created within the calling transaction context
            # No, the commit should happen in the startup task after all managers are init
            # logger.info("Default role creation process finished.")

        except SQLAlchemyError as e:
            logger.error(f"Database error during default role check/creation: {e}", exc_info=True)
            self._db.rollback() # Rollback on DB error
            raise RuntimeError("Failed during default role creation due to database error.")
        except Exception as e:
            logger.error(f"Unexpected error during default role check/creation: {e}", exc_info=True)
            raise # Re-raise other unexpected errors

    def get_job_clusters(self) -> List[JobCluster]:
        """Get available job clusters"""
        clusters = self._client.clusters.list()
        return [
            JobCluster(
                id=cluster.cluster_id,
                name=cluster.cluster_name,
                node_type_id=cluster.node_type_id,
                autoscale=bool(cluster.autoscale),
                min_workers=cluster.autoscale.min_workers if cluster.autoscale else cluster.num_workers,
                max_workers=cluster.autoscale.max_workers if cluster.autoscale else cluster.num_workers
            )
            for cluster in clusters
        ]

    def get_settings(self) -> dict:
        """Get current settings"""
        return {
            'job_clusters': self.get_job_clusters(),
            'current_settings': self._settings.to_dict(),
            'available_jobs': self._available_jobs
        }

    def update_settings(self, settings: dict) -> Settings:
        """Update settings"""
        self._settings.job_cluster_id = settings.get('job_cluster_id')
        self._settings.sync_enabled = settings.get('sync_enabled', False)
        self._settings.sync_repository = settings.get('sync_repository')
        self._settings.enabled_jobs = settings.get('enabled_jobs', [])
        self._settings.updated_at = datetime.utcnow()
        return self._settings

    def list_available_workflows(self) -> List[str]:
        """List all available workflow definitions from YAML files."""
        workflow_path = Path("workflows")
        if not workflow_path.exists():
            return []

        return [f.stem for f in workflow_path.glob("*.yaml")]

    def list_installed_workflows(self) -> List[WorkflowInstallation]:
        """List all workflows installed in the Databricks workspace."""
        return list(self._installations.values())

    def install_workflow(self, workflow_name: str) -> WorkflowInstallation:
        """Install a workflow from YAML definition into Databricks workspace."""
        # Load workflow definition
        yaml_path = Path("workflows") / f"{workflow_name}.yaml"
        if not yaml_path.exists():
            raise ValueError(f"Workflow definition not found: {workflow_name}")

        with open(yaml_path) as f:
            workflow_def = yaml.safe_load(f)

        # Create job in Databricks
        try:
            job_settings = jobs.JobSettings.from_dict(workflow_def)
            response = self._client.jobs.create(
                name=workflow_def.get('name', workflow_name),
                settings=job_settings
            )

            # Record installation
            installation = WorkflowInstallation(
                id=str(response.job_id),
                name=workflow_name,
                installed_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                status="active",
                workspace_id=self._client.config.host
            )
            self._installations[workflow_name] = installation
            return installation

        except Exception as e:
            raise RuntimeError(f"Failed to install workflow: {e!s}")

    def update_workflow(self, workflow_name: str) -> WorkflowInstallation:
        """Update an existing workflow in the Databricks workspace."""
        if workflow_name not in self._installations:
            raise ValueError(f"Workflow not installed: {workflow_name}")

        # Load updated workflow definition
        yaml_path = Path("workflows") / f"{workflow_name}.yaml"
        if not yaml_path.exists():
            raise ValueError(f"Workflow definition not found: {workflow_name}")

        with open(yaml_path) as f:
            workflow_def = yaml.safe_load(f)

        # Update job in Databricks
        try:
            job_id = int(self._installations[workflow_name].id)
            job_settings = jobs.JobSettings.from_dict(workflow_def)
            self._client.jobs.update(
                job_id=job_id,
                new_settings=job_settings
            )

            # Update installation record
            self._installations[workflow_name].updated_at = datetime.utcnow()
            return self._installations[workflow_name]

        except Exception as e:
            raise RuntimeError(f"Failed to update workflow: {e!s}")

    def remove_workflow(self, workflow_name: str) -> bool:
        """Remove a workflow from the Databricks workspace."""
        if workflow_name not in self._installations:
            return False

        try:
            job_id = int(self._installations[workflow_name].id)
            self._client.jobs.delete(job_id=job_id)
            del self._installations[workflow_name]
            return True

        except Exception as e:
            raise RuntimeError(f"Failed to remove workflow: {e!s}")

    def install_job(self, job_id: str) -> dict:
        """Install and enable a background job"""
        if job_id not in self._available_jobs:
            raise ValueError(f"Job {job_id} not found")

        try:
            # Update settings to enable the job
            if not self._settings.enabled_jobs:
                self._settings.enabled_jobs = []
            self._settings.enabled_jobs.append(job_id)
            self._settings.updated_at = datetime.utcnow()

            # Install the job in Databricks
            workflow_def = self._get_workflow_definition(job_id)
            job_settings = jobs.JobSettings.from_dict(workflow_def)
            response = self._client.jobs.create(
                name=workflow_def.get('name', job_id),
                settings=job_settings
            )

            return {
                'id': str(response.job_id),
                'name': job_id,
                'installed_at': self._settings.updated_at.isoformat(),
                'status': 'active',
                'workspace_id': self._client.config.host
            }
        except Exception as e:
            # Remove from enabled jobs if installation fails
            if job_id in self._settings.enabled_jobs:
                self._settings.enabled_jobs.remove(job_id)
            raise RuntimeError(f"Failed to install job: {e!s}")

    def update_job(self, job_id: str, enabled: bool) -> dict:
        """Enable or disable a background job"""
        if job_id not in self._available_jobs:
            raise ValueError(f"Job {job_id} not found")

        try:
            if enabled and job_id not in (self._settings.enabled_jobs or []):
                return self.install_job(job_id)
            elif not enabled and job_id in (self._settings.enabled_jobs or []):
                return self.remove_job(job_id)

            return {
                'name': job_id,
                'status': 'active' if enabled else 'disabled',
                'updated_at': datetime.utcnow().isoformat()
            }
        except Exception as e:
            raise RuntimeError(f"Failed to update job: {e!s}")

    def remove_job(self, job_id: str) -> bool:
        """Remove and disable a background job"""
        if job_id not in self._available_jobs:
            raise ValueError(f"Job {job_id} not found")

        try:
            # Remove from enabled jobs
            if job_id in (self._settings.enabled_jobs or []):
                self._settings.enabled_jobs.remove(job_id)
                self._settings.updated_at = datetime.utcnow()

            # Remove job from Databricks
            job = self._find_job_by_name(job_id)
            if job:
                self._client.jobs.delete(job_id=job.job_id)
            return True
        except Exception as e:
            raise RuntimeError(f"Failed to remove job: {e!s}")

    def _get_workflow_definition(self, job_id: str) -> dict:
        """Get the workflow definition for a job"""
        # Implementation depends on how you store job definitions
        # Could be from YAML files, database, etc.

    def _find_job_by_name(self, job_name: str) -> Optional[jobs.Job]:
        """Find a job in Databricks by name"""
        all_jobs = self._client.jobs.list()
        return next((job for job in all_jobs if job.settings.name == job_name), None)

    # --- RBAC Methods --- 

    def get_app_roles_count(self) -> int:
        """Returns the total number of application roles."""
        try:
            count = self.app_role_repo.get_roles_count(db=self._db)
            logger.debug(f"Found {count} application roles in the database.")
            return count
        except SQLAlchemyError as e:
            logger.error(f"Database error while counting roles: {e}", exc_info=True)
            self._db.rollback()
            raise RuntimeError("Failed to count application roles due to database error.")

    def _map_db_to_api(self, role_db: AppRoleDb) -> AppRole:
        """Converts an AppRoleDb model to an AppRole API model."""
        # Deserialize JSON fields safely
        try:
            assigned_groups = json.loads(role_db.assigned_groups or '[]') # Handle None
        except (json.JSONDecodeError, TypeError):
            logger.warning(f"Could not parse assigned_groups JSON for role ID {role_db.id}: {role_db.assigned_groups}")
            assigned_groups = []

        try:
            feature_permissions_raw = json.loads(role_db.feature_permissions or '{}') # Handle None
            feature_permissions = {
                k: FeatureAccessLevel(v) 
                for k, v in feature_permissions_raw.items() 
                if isinstance(v, str) # Ensure value is string before enum conversion
            }
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            logger.warning(f"Could not parse or convert feature_permissions JSON for role ID {role_db.id}: {role_db.feature_permissions}. Error: {e}")
            feature_permissions = {}

        return AppRole(
            id=role_db.id, # Keep UUID
            name=role_db.name,
            description=role_db.description,
            assigned_groups=assigned_groups,
            feature_permissions=feature_permissions,
            # created_at=role_db.created_at, # Uncomment if needed
            # updated_at=role_db.updated_at  # Uncomment if needed
        )

    def get_features_with_access_levels(self) -> Dict[str, Dict[str, str | List[str]]]:
        """Returns a dictionary of features and their allowed access levels."""
        features_config = get_feature_config()
        all_levels = get_all_access_levels()
        # Convert enum members to their string values for API response
        return {
            feature_id: {
                'name': config['name'],
                'allowed_levels': [level.value for level in config['allowed_levels']]
            }
            for feature_id, config in features_config.items()
        }

    def list_app_roles(self) -> List[AppRole]:
        """Lists all configured application roles from the database."""
        try:
            roles_db = self.app_role_repo.get_all_roles(db=self._db)
            return [self._map_db_to_api(role_db) for role_db in roles_db]
        except SQLAlchemyError as e:
            logger.error(f"Database error listing roles: {e}", exc_info=True)
            self._db.rollback()
            return [] # Return empty list on error

    def get_app_role(self, role_id: str) -> Optional[AppRole]:
        """Retrieves a specific application role by ID."""
        try:
            role_db = self.app_role_repo.get(db=self._db, id=role_id)
            if role_db:
                return self._map_db_to_api(role_db)
            return None
        except SQLAlchemyError as e:
            logger.error(f"Database error getting role {role_id}: {e}", exc_info=True)
            self._db.rollback()
            return None

    def get_app_role_by_name(self, role_name: str) -> Optional[AppRole]:
        """Retrieves a specific application role by name."""
        try:
            role_db = self.app_role_repo.get_by_name(db=self._db, name=role_name)
            if role_db:
                return self._map_db_to_api(role_db)
            return None
        except SQLAlchemyError as e:
            logger.error(f"Database error getting role by name '{role_name}': {e}", exc_info=True)
            self._db.rollback()
            return None

    def create_app_role(self, role: AppRoleCreate) -> AppRole:
        """Creates a new application role."""
        # Validate name uniqueness
        existing_role = self.get_app_role_by_name(role_name=role.name)
        if existing_role:
            logger.warning(f"Attempted to create role with duplicate name: {role.name}")
            raise ValueError(f"Role with name '{role.name}' already exists.")

        # Validate permissions against allowed levels
        self._validate_permissions(role.feature_permissions)

        try:
            # Pass the Pydantic model directly to the repository
            role_db = self.app_role_repo.create(db=self._db, obj_in=role)
            # Commit is handled by the request lifecycle or calling function
            # self._db.commit() # Remove commit from manager method
            # self._db.refresh(role_db) # Refresh is handled in repo
            logger.info(f"Successfully created role '{role.name}' with ID {role_db.id}")
            return self._map_db_to_api(role_db)
        except SQLAlchemyError as e:
            logger.error(f"Database error creating role '{role.name}': {e}", exc_info=True)
            self._db.rollback()
            raise RuntimeError("Failed to create application role due to database error.")
        except Exception as e:
            logger.error(f"Unexpected error creating role '{role.name}': {e}", exc_info=True)
            self._db.rollback()
            raise

    def _validate_permissions(self, permissions: Dict[str, FeatureAccessLevel]):
        """Validates that assigned permission levels are allowed for each feature."""
        feature_config = get_feature_config()
        for feature_id, level in permissions.items():
            if feature_id not in feature_config:
                raise ValueError(f"Invalid feature ID provided in permissions: '{feature_id}'")
            allowed_levels = feature_config[feature_id].get('allowed_levels', [])
            if level not in allowed_levels:
                allowed_str = [lvl.value for lvl in allowed_levels]
                raise ValueError(
                    f"Invalid access level '{level.value}' for feature '{feature_id}'. "
                    f"Allowed levels are: {allowed_str}"
                )

    def update_app_role(self, role_id: str, role_update: AppRoleUpdate) -> Optional[AppRole]:
        """Updates an existing application role."""
        try:
            role_db = self.app_role_repo.get(db=self._db, id=role_id)
            if not role_db:
                return None

            # Validate name uniqueness if name is being changed
            if role_update.name is not None and role_update.name != role_db.name:
                existing_role = self.get_app_role_by_name(role_name=role_update.name)
                if existing_role and str(existing_role.id) != role_id:
                    logger.warning(f"Attempted to update role {role_id} with duplicate name: {role_update.name}")
                    raise ValueError(f"Role with name '{role_update.name}' already exists.")

            # Validate permissions if provided
            if role_update.feature_permissions is not None:
                self._validate_permissions(role_update.feature_permissions)

            # Pass the Pydantic model (AppRoleUpdate) directly to the repository update method
            updated_role_db = self.app_role_repo.update(db=self._db, db_obj=role_db, obj_in=role_update)
            # Commit handled by request lifecycle
            logger.info(f"Successfully updated role (ID: {role_id})")
            return self._map_db_to_api(updated_role_db)
        except SQLAlchemyError as e:
            logger.error(f"Database error updating role {role_id}: {e}", exc_info=True)
            self._db.rollback()
            raise RuntimeError(f"Failed to update role {role_id} due to database error.")
        except ValueError as e: # Catch validation errors
             logger.warning(f"Validation error updating role {role_id}: {e}")
             self._db.rollback()
             raise # Re-raise validation errors
        except Exception as e:
            logger.error(f"Unexpected error updating role {role_id}: {e}", exc_info=True)
            self._db.rollback()
            raise

    def delete_app_role(self, role_id: str) -> bool:
        """Deletes an application role by ID."""
        try:
            role_db = self.app_role_repo.get(db=self._db, id=role_id)
            if not role_db:
                logger.warning(f"Attempted to delete non-existent role with ID: {role_id}")
                return False
            
            # Prevent deletion of the default Admin role? (Consider adding logic if needed)
            # if role_db.name == "Admin":
            #    logger.warning("Attempted to delete the default Admin role.")
            #    raise ValueError("Cannot delete the default Admin role.")

            self.app_role_repo.remove(db=self._db, id=role_id)
            # Commit handled by request lifecycle
            # self._db.commit()
            logger.info(f"Successfully deleted role with ID: {role_id}")
            return True
        except SQLAlchemyError as e:
            logger.error(f"Database error deleting role {role_id}: {e}", exc_info=True)
            self._db.rollback()
            raise RuntimeError(f"Failed to delete role {role_id} due to database error.")
        except Exception as e:
            logger.error(f"Unexpected error deleting role {role_id}: {e}", exc_info=True)
            self._db.rollback()
            raise

    # --- Methods related to workflows and jobs remain unchanged --- 
    # list_installed_workflows, install_workflow, update_workflow, remove_workflow
    # install_job, update_job, remove_job
    # _get_workflow_definition, _find_job_by_name
