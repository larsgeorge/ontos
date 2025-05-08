from pathlib import Path
from typing import List, Optional
from datetime import datetime
from api.common.workspace_client import WorkspaceClient
from api.common.config import Settings
from api.models.estate import Estate, CloudType, SyncStatus
from api.common.job_runner import JobRunner
import logging
import yaml

# Configure logging
from api.common.logging import get_logger

logger = get_logger(__name__)

class EstateManager:
    def __init__(self, client: WorkspaceClient, settings: Settings):
        self.job_runner = JobRunner(client, settings)
        self.estates: List[Estate] = []

    def load_from_yaml(self, yaml_path: Path) -> None:
        """Load estates from a YAML file"""
        try:
            with open(yaml_path) as f:
                data = yaml.safe_load(f)
                for estate_data in data:
                    estate = Estate(
                        id=estate_data['id'],
                        name=estate_data['name'],
                        description=estate_data['description'],
                        workspace_url=estate_data['workspace_url'],
                        cloud_type=CloudType(estate_data['cloud_type']),
                        metastore_name=estate_data['metastore_name'],
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
        estate.id = str(len(self.estates) + 1)
        self.estates.append(estate)
        return estate

    async def update_estate(self, estate_id: str, estate_update: Estate) -> Optional[Estate]:
        """Update an existing estate"""
        for i, estate in enumerate(self.estates):
            if estate.id == estate_id:
                estate_update.id = estate_id
                estate_update.updated_at = datetime.utcnow()
                self.estates[i] = estate_update
                return estate_update
        return None

    async def delete_estate(self, estate_id: str) -> bool:
        """Delete an estate"""
        for i, estate in enumerate(self.estates):
            if estate.id == estate_id:
                del self.estates[i]
                return True
        return False

    async def sync_estate(self, estate_id: str) -> bool:
        """Trigger a sync for a specific estate"""
        estate = await self.get_estate(estate_id)
        if not estate or not estate.is_enabled:
            return False

        # Update sync status
        estate.last_sync_status = SyncStatus.RUNNING
        estate.updated_at = datetime.utcnow()

        try:
            # TODO: Implement actual sync logic with Databricks API
            # For now, just simulate a successful sync
            estate.last_sync_time = datetime.utcnow()
            estate.last_sync_status = SyncStatus.SUCCESS
            estate.last_sync_error = None
            return True
        except Exception as e:
            estate.last_sync_status = SyncStatus.FAILED
            estate.last_sync_error = str(e)
            return False 