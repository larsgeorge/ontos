from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import json
import uuid

from databricks.sdk import WorkspaceClient
from pydantic import ValidationError
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func

from src.common.config import Settings
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.controller.notifications_manager import NotificationsManager
from src.models.notifications import NotificationType, Notification
from src.models.settings import JobCluster, AppRole, AppRoleCreate, AppRoleUpdate, HomeSection
from src.models.workflow_installations import WorkflowInstallation
from src.common.features import get_feature_config, FeatureAccessLevel, get_all_access_levels, APP_FEATURES, ACCESS_LEVEL_ORDER
from src.common.logging import get_logger
from src.repositories.settings_repository import app_role_repo
from src.repositories.workflow_installations_repository import workflow_installation_repo
from src.db_models.settings import AppRoleDb

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
        'teams': FeatureAccessLevel.READ_ONLY,
        'projects': FeatureAccessLevel.READ_ONLY,
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
        'teams': FeatureAccessLevel.READ_ONLY,
        'projects': FeatureAccessLevel.READ_ONLY,
        'business-glossary': FeatureAccessLevel.READ_WRITE,
        'compliance': FeatureAccessLevel.READ_ONLY,
        'data-asset-reviews': FeatureAccessLevel.READ_WRITE,
        'catalog-commander': FeatureAccessLevel.READ_ONLY,
    },
    "Data Consumer": {
        'data-domains': FeatureAccessLevel.READ_ONLY,
        'data-products': FeatureAccessLevel.READ_ONLY,
        'data-contracts': FeatureAccessLevel.READ_ONLY,
        'teams': FeatureAccessLevel.READ_ONLY,
        'projects': FeatureAccessLevel.READ_ONLY,
        'business-glossary': FeatureAccessLevel.READ_ONLY,
        'catalog-commander': FeatureAccessLevel.READ_ONLY,
    },
    "Data Producer": {
        'data-domains': FeatureAccessLevel.READ_ONLY,
        'data-products': FeatureAccessLevel.READ_WRITE,
        'data-contracts': FeatureAccessLevel.READ_WRITE,
        'teams': FeatureAccessLevel.READ_WRITE,
        'projects': FeatureAccessLevel.READ_WRITE,
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
        # Available jobs derive from workflows on disk
        self._available_jobs: List[str] = []
        self._installations: Dict[str, WorkflowInstallation] = {}
        self.app_role_repo = app_role_repo
        self._notifications_manager: Optional['NotificationsManager'] = None
        # In-memory role overrides: user_email -> role_id
        self._applied_role_overrides: Dict[str, str] = {}
        # Initialize available jobs from workflow directory
        try:
            from src.controller.jobs_manager import JobsManager
            self._jobs = JobsManager(db=self._db, ws_client=self._client, notifications_manager=self._notifications_manager, settings=self._settings)
            self._available_jobs = [w["id"] for w in self._jobs.list_available_workflows()]

            # Load installations from database
            self._load_installations_from_db()
        except Exception as e:
            logger.error(f"Error initializing JobsManager: {e}")
            self._jobs = None
            self._available_jobs = []

    # --- Role override helpers (in-memory persistence) ---
    def set_applied_role_override_for_user(self, user_email: Optional[str], role_id: Optional[str]) -> None:
        """Sets or clears the applied role override for a user.

        When role_id is None, the override is cleared and the user's actual group-based
        permissions are used. This stores state in-memory for the backend process lifetime.
        """
        if not user_email:
            raise ValueError("User email is required to set role override")
        if role_id is None:
            self._applied_role_overrides.pop(user_email, None)
            return
        role = self.get_app_role(role_id)
        if not role:
            raise ValueError(f"Role with id '{role_id}' not found")
        self._applied_role_overrides[user_email] = role_id

    def get_applied_role_override_for_user(self, user_email: Optional[str]) -> Optional[str]:
        if not user_email:
            return None
        return self._applied_role_overrides.get(user_email)

    def get_feature_permissions_for_role_id(self, role_id: str) -> Dict[str, FeatureAccessLevel]:
        role = self.get_app_role(role_id)
        if not role:
            raise ValueError(f"Role with id '{role_id}' not found")
        return role.feature_permissions or {}

    def get_canonical_role_for_groups(self, user_groups: Optional[List[str]]) -> Optional[AppRole]:
        """Map a user's groups to the closest configured AppRole.

        Algorithm:
        1) Try direct match via assigned_groups intersection (pick highest-weight role).
        2) If no matches, compute effective permissions from groups and choose the role
           whose permissions are closest (minimum sum of absolute level differences per feature).
        3) Heuristic: if any group contains 'admin' (case-insensitive), prefer Admin role by name.
        """
        if not user_groups:
            return None

        roles = self.list_app_roles()
        user_group_set = set(user_groups)

        # 3) Admin heuristic first for better UX in local dev
        try:
            if any('admin' in g.lower() for g in user_group_set):
                admin = next((r for r in roles if (r.name or '').strip().lower() == 'admin'), None)
                if admin:
                    return admin
        except Exception:
            pass

        # 1) Direct group match
        best_role: Optional[AppRole] = None
        best_weight = -1
        for role in roles:
            try:
                role_groups = set(role.assigned_groups or [])
                if not role_groups.intersection(user_group_set):
                    continue
                weight = sum(ACCESS_LEVEL_ORDER.get(level, 0) for level in (role.feature_permissions or {}).values())
                if weight > best_weight:
                    best_weight = weight
                    best_role = role
            except Exception:
                continue
        if best_role:
            return best_role

        # 2) Distance-based fallback using effective permissions
        try:
            from src.controller.authorization_manager import AuthorizationManager
            auth = AuthorizationManager(self)
            effective = auth.get_user_effective_permissions(list(user_group_set))
            # Normalize feature set
            feature_ids = set(get_feature_config().keys())
            def level_of(perms: Dict[str, FeatureAccessLevel], fid: str) -> int:
                return ACCESS_LEVEL_ORDER.get(perms.get(fid, FeatureAccessLevel.NONE), 0)

            best_role = None
            best_distance = 10**9
            for role in roles:
                role_perms = role.feature_permissions or {}
                # Compute Manhattan distance across features
                distance = 0
                for fid in feature_ids:
                    distance += abs(level_of(role_perms, fid) - level_of(effective, fid))
                if distance < best_distance:
                    best_distance = distance
                    best_role = role
            return best_role
        except Exception:
            return None

    def set_notifications_manager(self, notifications_manager: 'NotificationsManager') -> None:
        self._notifications_manager = notifications_manager

    def _load_installations_from_db(self):
        """Load workflow installations from database into memory."""
        try:
            db_installations = workflow_installation_repo.get_all(self._db)
            for db_inst in db_installations:
                # Deserialize last_job_state from JSON if present
                last_job_state = None
                if db_inst.last_job_state:
                    try:
                        last_job_state = json.loads(db_inst.last_job_state)
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON in last_job_state for workflow {db_inst.workflow_id}")

                installation = WorkflowInstallation(
                    id=db_inst.id,
                    workflow_id=db_inst.workflow_id,
                    name=db_inst.name,
                    job_id=db_inst.job_id,
                    workspace_id=db_inst.workspace_id,
                    status=db_inst.status,
                    installed_at=db_inst.installed_at,
                    updated_at=db_inst.updated_at
                )
                self._installations[db_inst.workflow_id] = installation

            logger.info(f"Loaded {len(self._installations)} workflow installations from database")
        except Exception as e:
            logger.error(f"Error loading installations from database: {e}")

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
                    # Default home sections for Admin
                    role_data["home_sections"] = [
                        HomeSection.REQUIRED_ACTIONS,
                        HomeSection.DATA_CURATION,
                        HomeSection.DISCOVERY,
                    ]
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

                    # Default home sections per role
                    if role_name == "Data Consumer":
                        role_data["home_sections"] = [HomeSection.DISCOVERY]
                    elif role_name == "Data Producer":
                        role_data["home_sections"] = [HomeSection.DATA_CURATION, HomeSection.DISCOVERY]
                    elif role_name in ("Data Steward", "Security Officer", "Data Governance Officer"):
                        role_data["home_sections"] = [HomeSection.REQUIRED_ACTIONS, HomeSection.DISCOVERY]
                    else:
                        role_data["home_sections"] = [HomeSection.DISCOVERY]

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
        """Deprecated: listing clusters is slow; return empty list."""
        return []
        # TODO: This call is too slow and blocks the entire call to get_settings, need to fix this
        # clusters = self._client.clusters.list()
        # return [
        #     JobCluster(
        #         id=cluster.cluster_id,
        #         name=cluster.cluster_name,
        #         node_type_id=cluster.node_type_id,
        #         autoscale=bool(cluster.autoscale),
        #         min_workers=cluster.autoscale.min_workers if cluster.autoscale else cluster.num_workers,
        #         max_workers=cluster.autoscale.max_workers if cluster.autoscale else cluster.num_workers
        #     )
        #     for cluster in clusters
        # ]

    def get_settings(self) -> dict:
        """Get current settings"""
        # Refresh available jobs from filesystem to reflect changes
        available = self._jobs.list_available_workflows() if getattr(self, '_jobs', None) else []
        self._available_jobs = [w["id"] if isinstance(w, dict) else w for w in available]

        # Get enabled jobs from WorkflowInstallationDb (source of truth)
        from src.repositories.workflow_installations_repository import workflow_installation_repo
        enabled_installations = workflow_installation_repo.get_all_installed(self._db)
        enabled_job_ids = [inst.workflow_id for inst in enabled_installations]

        return {
            'job_cluster_id': self._settings.job_cluster_id,
            'enabled_jobs': enabled_job_ids,  # From database, not Settings model
            'available_workflows': available,
            'current_settings': self._settings.to_dict(),
        }

    def update_settings(self, settings: dict) -> Settings:
        """Update settings"""
        # Persist configured cluster ID string; do not scan clusters
        desired_cluster_id: Optional[str] = settings.get('job_cluster_id')
        desired_enabled: List[str] = settings.get('enabled_jobs', []) or []
        
        logger.info(f"SettingsManager.update_settings received cluster_id: {desired_cluster_id}")
        logger.info(f"SettingsManager.update_settings current stored cluster_id: {self._settings.job_cluster_id}")

        # Compute job enable/disable delta against current settings
        current_enabled: List[str] = self._settings.enabled_jobs or []
        self._available_jobs = [w["id"] for w in (self._jobs.list_available_workflows() if self._jobs else [])]

        to_install = sorted(list(set(desired_enabled) - set(current_enabled)))
        to_remove = sorted(list(set(current_enabled) - set(desired_enabled)))

        logger.info(f"Current enabled: {current_enabled}, Desired enabled: {desired_enabled}")
        logger.info(f"To install: {to_install}, To remove: {to_remove}")

        # Apply changes on Databricks and collect errors
        errors = []
        
        for job_id in to_install:
            # Only process jobs that exist in workflows
            if job_id in self._available_jobs:
                try:
                    if self._jobs:
                        # Use the new desired cluster ID value, or fall back to current setting
                        # If None or empty, workflow will use Databricks serverless compute
                        cluster_id_to_use = desired_cluster_id if desired_cluster_id is not None else self._settings.job_cluster_id
                        # Filter out placeholder values that indicate "not set"
                        if cluster_id_to_use in ['cluster-id', '']:
                            cluster_id_to_use = None

                        self._jobs.install_workflow(job_id, job_cluster_id=cluster_id_to_use)
                        logger.info(f"Successfully installed workflow '{job_id}' with cluster_id={cluster_id_to_use or 'serverless'}")
                except Exception as e:
                    error_msg = f"Failed to install workflow '{job_id}': {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
            else:
                error_msg = f"Workflow '{job_id}' not found in available workflows"
                errors.append(error_msg)
                logger.warning(error_msg)

        for job_id in to_remove:
            logger.info(f"Processing removal of workflow '{job_id}'")

            if job_id in self._available_jobs:
                try:
                    if self._jobs:
                        # Look up from database instead of Databricks (much faster)
                        logger.info(f"Looking up installation record for workflow: '{job_id}'")
                        installation = workflow_installation_repo.get_by_workflow_id(self._db, workflow_id=job_id)

                        if installation:
                            logger.info(f"Found installation record, calling remove_workflow with job_id: {installation.job_id}")
                            self._jobs.remove_workflow(installation.job_id)
                            logger.info(f"Successfully removed workflow '{job_id}'")
                        else:
                            logger.warning(f"Installation record for '{job_id}' not found in database, attempting Databricks lookup")
                            # Fallback to Databricks lookup if not in database
                            job = self._jobs.find_job_by_name(job_id)
                            if job:
                                self._jobs.remove_workflow(job.job_id)
                                logger.info(f"Successfully removed workflow '{job_id}' (via Databricks lookup)")
                            else:
                                logger.warning(f"Job '{job_id}' not found in Databricks either, may have been already deleted")
                except Exception as e:
                    error_msg = f"Failed to remove workflow '{job_id}': {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg, exc_info=True)
            else:
                error_msg = f"Workflow '{job_id}' not found in available workflows"
                errors.append(error_msg)
                logger.warning(error_msg)
        
        # If there were errors, raise an exception with all error details
        if errors:
            error_summary = f"Failed to update {len(errors)} workflow(s): " + "; ".join(errors)
            raise RuntimeError(error_summary)

        # Update stored settings after applying infra changes
        self._settings.job_cluster_id = desired_cluster_id
        self._settings.enabled_jobs = sorted(list(set(desired_enabled)))
        self._settings.sync_enabled = settings.get('sync_enabled', False)
        self._settings.sync_repository = settings.get('sync_repository')
        self._settings.updated_at = datetime.utcnow()
        return self._settings

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

    def set_notifications_manager(self, notifications_manager: 'NotificationsManager'):
        """Set the notifications manager and reinitialize jobs manager if needed."""
        self._notifications_manager = notifications_manager
        
        # Reinitialize jobs manager with notifications support
        if self._client:
            try:
                from src.controller.jobs_manager import JobsManager
                self._jobs = JobsManager(
                    db=self._db,
                    ws_client=self._client,
                    notifications_manager=self._notifications_manager,
                    settings=self._settings
                )
                self._available_jobs = [w["id"] for w in self._jobs.list_available_workflows()]
            except Exception as e:
                logger.error(f"Failed to reinitialize jobs manager with notifications: {e}")

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

        try:
            home_sections_raw = json.loads(getattr(role_db, 'home_sections', '[]') or '[]')
            home_sections = [HomeSection(s) for s in home_sections_raw if isinstance(s, str)]
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            logger.warning(f"Could not parse or convert home_sections JSON for role ID {role_db.id}: {getattr(role_db, 'home_sections', None)}. Error: {e}")
            home_sections = []

        return AppRole(
            id=role_db.id, # Keep UUID
            name=role_db.name,
            description=role_db.description,
            assigned_groups=assigned_groups,
            feature_permissions=feature_permissions,
            home_sections=home_sections,
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

            # Backfill default home_sections for roles missing configuration
            updated_any = False
            for role_db in roles_db:
                try:
                    hs_raw = json.loads(getattr(role_db, 'home_sections', '[]') or '[]')
                except Exception:
                    hs_raw = []
                if not hs_raw:
                    default_sections: List[HomeSection]
                    name = (role_db.name or '').strip()
                    if name == 'Admin':
                        default_sections = [HomeSection.REQUIRED_ACTIONS, HomeSection.DATA_CURATION, HomeSection.DISCOVERY]
                    elif name in ('Data Steward', 'Security Officer', 'Data Governance Officer'):
                        default_sections = [HomeSection.REQUIRED_ACTIONS, HomeSection.DISCOVERY]
                    elif name == 'Data Producer':
                        default_sections = [HomeSection.DATA_CURATION, HomeSection.DISCOVERY]
                    else:  # Data Consumer or others
                        default_sections = [HomeSection.DISCOVERY]
                    # Persist backfill
                    self.app_role_repo.update(db=self._db, db_obj=role_db, obj_in={'home_sections': default_sections})
                    updated_any = True

            if updated_any:
                # Flush once after backfill
                try:
                    self._db.flush()
                except Exception:
                    pass

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
