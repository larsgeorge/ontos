import json
from typing import Any, Dict, Optional, Union, List
from uuid import UUID # Import UUID

from sqlalchemy.orm import Session
from sqlalchemy import func
from uuid import uuid4

from src.common.repository import CRUDBase
from src.db_models.settings import AppRoleDb
from src.models.settings import AppRole as AppRoleApi, AppRoleCreate, AppRoleUpdate
from src.common.logging import get_logger

logger = get_logger(__name__)

# Define Pydantic models for create/update if they differ
AppRoleCreate = AppRoleApi
AppRoleUpdate = AppRoleApi

class AppRoleRepository(CRUDBase[AppRoleDb, AppRoleCreate, AppRoleUpdate]):
    """Repository for AppRole CRUD operations."""

    def create(self, db: Session, *, obj_in: AppRoleCreate) -> AppRoleDb:
        """Creates an AppRole, serializing JSON fields."""
        # Remove exclude_unset=True to ensure all fields are included
        db_obj_data = obj_in.model_dump() 
        # Serialize complex fields
        # Make sure assigned_groups and feature_permissions exist on obj_in
        db_obj_data['assigned_groups'] = json.dumps(getattr(obj_in, 'assigned_groups', []))
        permissions_dict = getattr(obj_in, 'feature_permissions', {})
        db_obj_data['feature_permissions'] = json.dumps(
            {k: v.value for k, v in permissions_dict.items()} # Save enum values
        )
        # Home sections stored as list of strings
        home_sections_list = getattr(obj_in, 'home_sections', [])
        db_obj_data['home_sections'] = json.dumps(home_sections_list)
        db_obj = self.model(**db_obj_data)
        db.add(db_obj)
        db.flush() # Use flush instead of commit within repository method
        db.refresh(db_obj)
        logger.info(f"Created AppRoleDb with id: {db_obj.id}")
        return db_obj

    def update(self, db: Session, *, db_obj: AppRoleDb, obj_in: Union[AppRoleUpdate, Dict[str, Any]]) -> AppRoleDb:
        """Updates an AppRole, serializing JSON fields."""
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        # Serialize complex fields if they are present in the update data
        if 'assigned_groups' in update_data and update_data['assigned_groups'] is not None:
            update_data['assigned_groups'] = json.dumps(update_data['assigned_groups'])
        if 'feature_permissions' in update_data and update_data['feature_permissions'] is not None:
            perm_dict = update_data['feature_permissions']
            update_data['feature_permissions'] = json.dumps(
                 {k: (v.value if hasattr(v, 'value') else v) for k, v in perm_dict.items()}
            )
        if 'home_sections' in update_data and update_data['home_sections'] is not None:
            update_data['home_sections'] = json.dumps(update_data['home_sections'])

        logger.debug(f"Updating AppRoleDb {db_obj.id} with data: {update_data}")
        # Use the base class update method which handles attribute setting
        updated_db_obj = super().update(db, db_obj=db_obj, obj_in=update_data)
        logger.info(f"Updated AppRoleDb with id: {updated_db_obj.id}")
        return updated_db_obj

    def get_by_name(self, db: Session, *, name: str) -> Optional[AppRoleDb]:
        """Retrieves an AppRole by its name."""
        return db.query(self.model).filter(self.model.name == name).first()

    def get_roles_count(self, db: Session) -> int:
        """Returns the total number of AppRole records in the database."""
        count = db.query(func.count(self.model.id)).scalar()
        return count or 0 # Return 0 if count is None

    def get_all_roles(self, db: Session) -> List[AppRoleDb]:
        """Retrieves all AppRole records from the database."""
        logger.debug("Retrieving all roles from the database.")
        return self.get_multi(db=db) # Use the inherited get_multi

    # get and get_multi are inherited from CRUDBase and should work directly


# Create singleton instance of the repository
app_role_repo = AppRoleRepository(AppRoleDb) 