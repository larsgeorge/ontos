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

from api.common.config import Settings
from api.models.settings import JobCluster, WorkflowInstallation, AppRole, AppRoleCreate
from api.common.features import get_feature_config, FeatureAccessLevel, get_all_access_levels
from api.common.logging import get_logger
from api.repositories.settings_repository import app_role_repo, AppRoleRepository
from api.db_models.settings import AppRoleDb

logger = get_logger(__name__)

# Define the path for storing roles configuration
# ROLES_YAML_PATH = Path("api/data/app_roles.yaml")


class SettingsManager:
    def __init__(self, db: Session, workspace_client: Optional[WorkspaceClient] = None):
        """Inject database session."""
        self._db = db
        self._client = workspace_client # Renamed from _workspace_client for consistency
        self._settings = Settings()
        self._available_jobs = [
            'data_contracts',
            'business_glossaries',
            'entitlements',
            'mdm_jobs',
            'catalog_commander_jobs'
        ]
        self._installations: Dict[str, WorkflowInstallation] = {}
        # self._app_roles: Dict[str, AppRole] = {}  # REMOVED In-memory storage
        self._ensure_default_roles_exist() # Check/create default roles in DB on init

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

    def _ensure_default_roles_exist(self):
        """Ensures the default Admin role exists if the roles table is empty."""
        try:
            # Check if any roles exist
            existing_roles = app_role_repo.get_multi(self._db, limit=1)
            if existing_roles:
                logger.info("Roles table is not empty. Skipping default Admin role creation.")
                return

            logger.info("Roles table is empty. Creating default Admin role...")

            # Get admin groups from settings
            try:
                # Use the initialized self._settings object
                admin_groups_str = self._settings.app_admin_default_groups or '[]'
                admin_groups = json.loads(admin_groups_str)
                if not isinstance(admin_groups, list):
                    logger.warning(f"APP_ADMIN_DEFAULT_GROUPS ({admin_groups_str}) is not a valid JSON list. Using default ['admins'].")
                    admin_groups = ["admins"]
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f"Could not parse APP_ADMIN_DEFAULT_GROUPS. Using default ['admins']. Error: {e}")
                admin_groups = ["admins"]
            
            # Create only the Admin role with a generated UUID
            admin_role_api = AppRoleCreate(
                id=str(uuid.uuid4()), # Generate UUID for the ID
                name="Admin",
                description="Full access to all application features.",
                assigned_groups=admin_groups, 
                feature_permissions={feat_id: FeatureAccessLevel.ADMIN for feat_id in get_feature_config() if feat_id != 'about'}
            )
            app_role_repo.create(self._db, obj_in=admin_role_api)
            logger.info("Default Admin role created successfully.")
            # Commit is handled by the context manager managing self._db

        except SQLAlchemyError as e:
            logger.error(f"Database error ensuring default Admin role: {e}", exc_info=True)
            # Allow application to continue, but log the error
        except Exception as e:
            logger.error(f"Unexpected error ensuring default Admin role: {e}", exc_info=True)

    def _map_db_to_api(self, role_db: AppRoleDb) -> AppRole:
        """Maps the DB model to the API Pydantic model, handling JSON parsing."""
        try:
            assigned_groups = json.loads(role_db.assigned_groups or '[]')
            feature_perms_dict = json.loads(role_db.feature_permissions or '{}')
            # Convert permission strings back to enums
            feature_permissions = {
                k: FeatureAccessLevel(v) for k, v in feature_perms_dict.items()
                if v in FeatureAccessLevel.__members__.values() # Check if value is valid enum member
            }

            return AppRole(
                id=role_db.id,
                name=role_db.name,
                description=role_db.description,
                assigned_groups=assigned_groups,
                feature_permissions=feature_permissions
            )
        except (json.JSONDecodeError, ValueError, ValidationError) as e:
            logger.error(f"Error mapping AppRoleDb (ID: {role_db.id}) to API model: {e}")
            # Raise a specific error or return a default/empty model?
            # Raising makes the issue apparent upstream.
            raise ValueError(f"Internal data mapping error for role ID {role_db.id}") from e

    def get_features_with_access_levels(self) -> Dict[str, Dict[str, str | List[str]]]:
        """Get the application feature configuration with allowed access levels."""
        features = get_feature_config()
        # Convert Enum members to string values for API response
        result = {}
        for feature_id, config in features.items():
            result[feature_id] = {
                'name': config['name'],
                'allowed_levels': [level.value for level in config.get('allowed_levels', [])]
            }
        return result

    def list_app_roles(self) -> List[AppRole]:
        """List all configured application roles from the database."""
        try:
            roles_db = app_role_repo.get_multi(self._db, limit=1000) # Get all roles
            return [self._map_db_to_api(role_db) for role_db in roles_db]
        except SQLAlchemyError as e:
            logger.error(f"Database error listing roles: {e}")
            raise
        except ValueError as e: # Catch mapping errors
            logger.error(f"Error mapping roles during list: {e}")
            raise RuntimeError(f"Internal data error listing roles: {e}")
        except Exception as e:
            logger.error(f"Unexpected error listing roles: {e}")
            raise

    def get_app_role(self, role_id: str) -> Optional[AppRole]:
        """Get a specific application role by its ID from the database."""
        try:
            role_db = app_role_repo.get(self._db, id=role_id)
            if role_db:
                return self._map_db_to_api(role_db)
            return None
        except SQLAlchemyError as e:
            logger.error(f"Database error getting role {role_id}: {e}")
            raise
        except ValueError as e: # Catch mapping errors
             logger.error(f"Error mapping role {role_id}: {e}")
             raise RuntimeError(f"Internal data error getting role {role_id}: {e}")
        except Exception as e:
             logger.error(f"Unexpected error getting role {role_id}: {e}")
             raise

    def create_app_role(self, role_data: AppRoleCreate) -> AppRole:
        """Create a new application role in the database."""
        # Ensure ID is generated if not provided, using UUID.
        if not role_data.id:
            role_data.id = str(uuid.uuid4())
        # No lowercase needed for UUIDs

        # Check if the provided ID (if any) or generated ID already exists
        existing_by_id = app_role_repo.get(self._db, id=role_data.id)
        if existing_by_id:
            # If an ID was provided and it conflicts, raise error
            # If ID was generated, this check prevents extremely rare UUID collisions
            raise ValueError(f"Role with ID '{role_data.id}' already exists.")

        # Check for existing role by name before creation
        existing_by_name = app_role_repo.get_by_name(self._db, name=role_data.name)
        if existing_by_name:
             raise ValueError(f"Role with Name '{role_data.name}' already exists.")

        # Validate permissions against feature config
        self._validate_permissions(role_data.feature_permissions)

        try:
            # Pass the AppRoleCreate object (with ID now set) to the repository
            created_db_obj = app_role_repo.create(self._db, obj_in=role_data)
            # No commit here, handled by get_db context manager
            # Map the DB object back to the full AppRole model for the response
            return self._map_db_to_api(created_db_obj)
        except SQLAlchemyError as e:
            logger.error(f"Database error creating role '{role_data.name}': {e}")
            # Rollback is handled by get_db context manager
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating role '{role_data.name}': {e}")
            raise

    def _validate_permissions(self, permissions: Dict[str, FeatureAccessLevel]):
        """Validates the provided feature permissions against the config."""
        feature_config = get_feature_config()
        for feature_id, assigned_level in permissions.items():
            if feature_id not in feature_config:
                raise ValueError(f"Invalid feature ID '{feature_id}' in permissions.")
            allowed = feature_config[feature_id].get('allowed_levels', [])
            if assigned_level not in allowed:
                # Ensure comparison works if assigned_level is str vs enum
                assigned_value = assigned_level.value if isinstance(assigned_level, Enum) else assigned_level
                allowed_values = [l.value for l in allowed]
                if assigned_value not in allowed_values:
                    raise ValueError(f"Access level '{assigned_value}' is not allowed for feature '{feature_id}'. Allowed: {allowed_values}")

    def update_app_role(self, role_id: str, role_data: AppRole) -> Optional[AppRole]:
        """Update an existing application role in the database."""
        # Validate permissions first
        self._validate_permissions(role_data.feature_permissions)

        try:
            db_obj = app_role_repo.get(self._db, id=role_id)
            if not db_obj:
                return None
            
            # Prevent renaming the default Admin role?
            if db_obj.name == "Admin" and role_data.name != "Admin":
                 raise ValueError("Cannot rename the default Admin role.")

            # Check if name is being changed and if the new name already exists
            if role_data.name != db_obj.name:
                 existing_by_name = app_role_repo.get_by_name(self._db, name=role_data.name)
                 if existing_by_name and existing_by_name.id != role_id:
                      raise ValueError(f"Another role with the name '{role_data.name}' already exists.")

            updated_db_obj = app_role_repo.update(self._db, db_obj=db_obj, obj_in=role_data)
            # No commit here, handled by get_db context manager
            return self._map_db_to_api(updated_db_obj)
        except SQLAlchemyError as e:
            logger.error(f"Database error updating role '{role_id}': {e}")
            # Rollback handled by get_db context manager
            raise
        except ValueError as e: # Catch validation or mapping errors
            logger.warning(f"Validation/Mapping error updating role '{role_id}': {e!s}")
            raise
        except Exception as e:
             logger.error(f"Unexpected error updating role '{role_id}': {e}")
             raise

    def delete_app_role(self, role_id: str) -> bool:
        """Delete an application role from the database."""
        try:
            # Fetch the role first to check its name
            db_obj = app_role_repo.get(self._db, id=role_id)
            if not db_obj:
                 return False # Already deleted or never existed

            # Prevent deleting the default Admin role by checking its name
            if db_obj.name == 'Admin':
                 raise ValueError("Cannot delete the default Admin role.")

            # Proceed with deletion
            deleted_obj = app_role_repo.remove(self._db, id=role_id)
            # No commit here, handled by get_db context manager
            return deleted_obj is not None
        except SQLAlchemyError as e:
            logger.error(f"Database error deleting role '{role_id}': {e}")
            # Rollback handled by get_db context manager
            raise
        except ValueError as e: # Catch the ValueError from the Admin check
             logger.warning(f"Prevented deletion of role '{role_id}': {e!s}")
             raise # Re-raise to return 400 Bad Request
        except Exception as e:
            logger.error(f"Unexpected error deleting role '{role_id}': {e}")
            raise

    # --- Workflow/Job Methods (Existing) ---

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
