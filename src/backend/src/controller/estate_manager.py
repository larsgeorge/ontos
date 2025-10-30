from pathlib import Path
from typing import List, Optional
from datetime import datetime
import uuid # Import uuid for generating policy IDs
from src.common.workspace_client import WorkspaceClient
from src.common.config import Settings
from src.models.estate import Estate, CloudType, SyncStatus, ConnectionType, SharingPolicy, SharingRule, SharingResourceType, SharingRuleOperator # Import new models
import yaml

# Configure logging
from src.common.logging import get_logger
logger = get_logger(__name__)

class EstateManager:
    def __init__(self, client: WorkspaceClient, settings: Settings, yaml_path: Optional[Path] = None):
        """Initialize EstateManager.
        
        Args:
            client: WorkspaceClient for SDK operations
            settings: Application settings
            yaml_path: Optional path to YAML file to load estates from.
                      If not provided, attempts to load from default location
                      (data/estates.yaml relative to controller directory).
        """
        self.estates: List[Estate] = []
        
        # Auto-load from YAML if path provided or default exists
        if yaml_path is None:
            # Try default location
            default_path = Path(__file__).parent.parent / 'data' / 'estates.yaml'
            if default_path.exists():
                yaml_path = default_path
        
        if yaml_path and yaml_path.exists():
            try:
                self.load_from_yaml(yaml_path)
                logger.info(f"Successfully loaded estates from {yaml_path}")
            except Exception as e:
                logger.exception(f"Error loading estates from YAML: {e!s}")

    def _parse_sharing_policies(self, policies_data: Optional[List[dict]]) -> List[SharingPolicy]:
        if not policies_data:
            return []
        parsed_policies = []
        for policy_data in policies_data:
            rules_data = policy_data.get('rules', [])
            parsed_rules = [
                SharingRule(
                    filter_type=rule_data['filter_type'],
                    operator=SharingRuleOperator(rule_data['operator']),
                    filter_value=rule_data['filter_value']
                ) for rule_data in rules_data
            ]
            parsed_policies.append(
                SharingPolicy(
                    id=policy_data.get('id', str(uuid.uuid4())), # Generate ID if not present
                    name=policy_data['name'],
                    description=policy_data.get('description'),
                    resource_type=SharingResourceType(policy_data['resource_type']),
                    rules=parsed_rules,
                    is_enabled=policy_data.get('is_enabled', True),
                    created_at=datetime.fromisoformat(policy_data['created_at'].replace('Z', '+00:00')) if policy_data.get('created_at') else datetime.utcnow(),
                    updated_at=datetime.fromisoformat(policy_data['updated_at'].replace('Z', '+00:00')) if policy_data.get('updated_at') else datetime.utcnow()
                )
            )
        return parsed_policies

    def load_from_yaml(self, yaml_path: Path) -> None:
        """Load estates from a YAML file"""
        try:
            with open(yaml_path) as f:
                data = yaml.safe_load(f)
                for estate_data in data:
                    sharing_policies = self._parse_sharing_policies(estate_data.get('sharing_policies'))
                    estate = Estate(
                        id=estate_data['id'],
                        name=estate_data['name'],
                        description=estate_data['description'],
                        workspace_url=estate_data['workspace_url'],
                        cloud_type=CloudType(estate_data['cloud_type']),
                        metastore_name=estate_data['metastore_name'],
                        connection_type=ConnectionType(estate_data.get('connection_type', ConnectionType.DELTA_SHARE.value)), # Default to delta_share if not present
                        sharing_policies=sharing_policies,
                        is_enabled=estate_data['is_enabled'],
                        sync_schedule=estate_data['sync_schedule'],
                        last_sync_time=datetime.fromisoformat(estate_data['last_sync_time'].replace('Z', '+00:00')) if estate_data.get('last_sync_time') else None,
                        last_sync_status=SyncStatus(estate_data['last_sync_status']) if estate_data.get('last_sync_status') else None,
                        last_sync_error=estate_data.get('last_sync_error'),
                        created_at=datetime.fromisoformat(estate_data['created_at'].replace('Z', '+00:00')) if estate_data.get('created_at') else datetime.utcnow(),
                        updated_at=datetime.fromisoformat(estate_data['updated_at'].replace('Z', '+00:00')) if estate_data.get('updated_at') else datetime.utcnow()
                    )
                    self.estates.append(estate)
            logger.info(f"Loaded {len(self.estates)} estates from {yaml_path}")
        except Exception as e:
            logger.exception(f"Error loading estates from {yaml_path}: {e}")
            self.estates = []

    async def list_estates(self) -> List[Estate]:
        """List all configured estates"""
        logger.info(f"Returning {len(self.estates)} estates.")
        return self.estates

    async def get_estate(self, estate_id: str) -> Optional[Estate]:
        """Get a specific estate by ID"""
        return next((estate for estate in self.estates if estate.id == estate_id), None)

    async def create_estate(self, estate: Estate) -> Estate:
        """Create a new estate"""
        # Ensure new policies get IDs if they don't have them
        for policy in estate.sharing_policies:
            if not policy.id:
                policy.id = str(uuid.uuid4())
            policy.created_at = datetime.utcnow()
            policy.updated_at = datetime.utcnow()

        estate.id = str(uuid.uuid4()) # Ensure estate ID is unique
        estate.created_at = datetime.utcnow()
        estate.updated_at = datetime.utcnow()
        self.estates.append(estate)
        # TODO: Persist to YAML if git sync is enabled
        return estate

    async def update_estate(self, estate_id: str, estate_update: Estate) -> Optional[Estate]:
        """Update an existing estate"""
        for i, estate in enumerate(self.estates):
            if estate.id == estate_id:
                # Update sharing policies: assign IDs to new policies, update timestamps
                for policy_update in estate_update.sharing_policies:
                    if not policy_update.id:
                        policy_update.id = str(uuid.uuid4())
                        policy_update.created_at = datetime.utcnow()
                    policy_update.updated_at = datetime.utcnow()
                
                estate_update.id = estate_id # Preserve original ID
                estate_update.created_at = estate.created_at # Preserve original creation time
                estate_update.updated_at = datetime.utcnow()
                self.estates[i] = estate_update
                # TODO: Persist to YAML if git sync is enabled
                return estate_update
        return None

    async def delete_estate(self, estate_id: str) -> bool:
        """Delete an estate"""
        for i, estate in enumerate(self.estates):
            if estate.id == estate_id:
                del self.estates[i]
                # TODO: Persist to YAML if git sync is enabled
                return True
        return False

    async def sync_estate(self, estate_id: str) -> bool:
        """Trigger a sync for a specific estate"""
        estate = await self.get_estate(estate_id)
        if not estate or not estate.is_enabled:
            logger.warning(f"Sync attempt for disabled or non-existent estate: {estate_id}")
            return False

        # Update sync status
        estate.last_sync_status = SyncStatus.RUNNING
        estate.last_sync_error = None # Clear previous error
        estate.updated_at = datetime.utcnow()

        logger.info(f"Attempting to sync estate: {estate.name} ({estate_id}) with connection type {estate.connection_type.value}")

        try:
            # TODO: Implement actual sync logic with Databricks API / Delta Sharing
            # This will involve:
            # 1. Identifying data to share based on estate.sharing_policies.
            # 2. For DELTA_SHARE connection_type:
            #    - Preparing local Delta tables.
            #    - Managing Delta Shares (creating/updating shares, recipients).
            #    - For incoming shares: Reading shared tables and making data available.
            # 3. For DATABASE connection_type (future):
            #    - Connecting to the remote database and exchanging data.
            # 4. This entire process should likely be a Databricks job triggered by self.job_runner
            
            logger.info(f"Simulating sync for estate: {estate.name}")
            # For now, just simulate a successful sync after a brief delay
            # import asyncio
            # await asyncio.sleep(2) # Simulate work

            estate.last_sync_time = datetime.utcnow()
            estate.last_sync_status = SyncStatus.SUCCESS
            logger.info(f"Successfully synced estate: {estate.name}")
            return True
        except Exception as e:
            logger.exception(f"Error during sync for estate {estate.name}: {e}")
            estate.last_sync_status = SyncStatus.FAILED
            estate.last_sync_error = str(e)
            return False 