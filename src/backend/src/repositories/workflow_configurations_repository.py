"""
Repository for workflow configurations.

Provides CRUD operations for workflow configuration storage.
"""

import json
from typing import Any, Dict, Optional, Union, List

from sqlalchemy.orm import Session

from src.common.repository import CRUDBase
from src.db_models.workflow_configurations import WorkflowConfigurationDb
from src.models.workflow_configurations import WorkflowConfiguration, WorkflowConfigurationUpdate
from src.common.logging import get_logger

logger = get_logger(__name__)


class WorkflowConfigurationRepository(CRUDBase[WorkflowConfigurationDb, WorkflowConfiguration, WorkflowConfigurationUpdate]):
    """Repository for WorkflowConfiguration CRUD operations"""

    def create(self, db: Session, *, obj_in: WorkflowConfiguration) -> WorkflowConfigurationDb:
        """Create a WorkflowConfiguration record"""
        db_obj_data = obj_in.model_dump()
        
        # Serialize configuration dict to JSON string
        if 'configuration' in db_obj_data and isinstance(db_obj_data['configuration'], dict):
            db_obj_data['configuration'] = json.dumps(db_obj_data['configuration'])
        
        db_obj = self.model(**db_obj_data)
        db.add(db_obj)
        db.flush()
        db.refresh(db_obj)
        logger.info(f"Created WorkflowConfigurationDb: workflow_id={db_obj.workflow_id}")
        return db_obj

    def update(
        self, 
        db: Session, 
        *, 
        db_obj: WorkflowConfigurationDb, 
        obj_in: Union[WorkflowConfigurationUpdate, Dict[str, Any]]
    ) -> WorkflowConfigurationDb:
        """Update a WorkflowConfiguration record"""
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        # Serialize configuration if present
        if 'configuration' in update_data and isinstance(update_data['configuration'], dict):
            update_data['configuration'] = json.dumps(update_data['configuration'])

        updated_db_obj = super().update(db, db_obj=db_obj, obj_in=update_data)
        logger.info(f"Updated WorkflowConfigurationDb: workflow_id={updated_db_obj.workflow_id}")
        return updated_db_obj

    def get_by_workflow_id(self, db: Session, *, workflow_id: str) -> Optional[WorkflowConfigurationDb]:
        """Retrieve a WorkflowConfiguration by workflow_id"""
        return db.query(self.model).filter(self.model.workflow_id == workflow_id).first()

    def get_configuration_dict(self, db: Session, *, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve configuration as dictionary for a workflow"""
        db_obj = self.get_by_workflow_id(db, workflow_id=workflow_id)
        if not db_obj:
            return None
        
        try:
            return json.loads(db_obj.configuration)
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"Failed to parse configuration for workflow {workflow_id}: {e}")
            return None

    def upsert(
        self, 
        db: Session, 
        *, 
        workflow_id: str, 
        configuration: Dict[str, Any]
    ) -> WorkflowConfigurationDb:
        """Create or update a workflow configuration"""
        db_obj = self.get_by_workflow_id(db, workflow_id=workflow_id)
        
        if db_obj:
            # Update existing
            return self.update(
                db, 
                db_obj=db_obj, 
                obj_in=WorkflowConfigurationUpdate(configuration=configuration)
            )
        else:
            # Create new
            return self.create(
                db,
                obj_in=WorkflowConfiguration(
                    workflow_id=workflow_id,
                    configuration=configuration
                )
            )

    def delete_by_workflow_id(self, db: Session, *, workflow_id: str) -> bool:
        """Delete a workflow configuration by workflow_id"""
        db_obj = self.get_by_workflow_id(db, workflow_id=workflow_id)
        if db_obj:
            db.delete(db_obj)
            db.flush()
            logger.info(f"Deleted WorkflowConfigurationDb: workflow_id={workflow_id}")
            return True
        return False

    def get_all(self, db: Session) -> List[WorkflowConfigurationDb]:
        """Retrieve all workflow configurations"""
        return self.get_multi(db=db)


# Create singleton instance of the repository
workflow_configuration_repo = WorkflowConfigurationRepository(WorkflowConfigurationDb)

