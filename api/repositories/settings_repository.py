import json
from typing import Any, Dict, Optional, Union, List

from sqlalchemy.orm import Session

from api.common.repository import CRUDBase
from api.db_models.settings import AppRoleDb
from api.models.settings import AppRole as AppRoleApi # API model
from api.common.logging import get_logger

logger = get_logger(__name__)

# Define Pydantic models for create/update if they differ
AppRoleCreate = AppRoleApi
AppRoleUpdate = AppRoleApi

class AppRoleRepository(CRUDBase[AppRoleDb, AppRoleCreate, AppRoleUpdate]):
    """Repository for AppRole CRUD operations."""

    def create(self, db: Session, *, obj_in: AppRoleCreate) -> AppRoleDb:
        """Creates an AppRole, serializing JSON fields."""
        db_obj_data = obj_in.model_dump(exclude_unset=True)
        # Serialize complex fields
        db_obj_data['assigned_groups'] = json.dumps(obj_in.assigned_groups)
        db_obj_data['feature_permissions'] = json.dumps(
            {k: v.value for k, v in obj_in.feature_permissions.items()} # Save enum values
        )
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
        if 'assigned_groups' in update_data:
            update_data['assigned_groups'] = json.dumps(update_data['assigned_groups'])
        if 'feature_permissions' in update_data:
            # Ensure we are saving enum string values
            perm_dict = update_data['feature_permissions']
            update_data['feature_permissions'] = json.dumps(
                 {k: (v.value if hasattr(v, 'value') else v) for k, v in perm_dict.items()}
            )

        logger.debug(f"Updating AppRoleDb {db_obj.id} with data: {update_data}")
        # Use the base class update method which handles attribute setting
        updated_db_obj = super().update(db, db_obj=db_obj, obj_in=update_data)
        logger.info(f"Updated AppRoleDb with id: {updated_db_obj.id}")
        return updated_db_obj

    def get_by_name(self, db: Session, *, name: str) -> Optional[AppRoleDb]:
        """Retrieves an AppRole by its name."""
        return db.query(self.model).filter(self.model.name == name).first()

    # get and get_multi are inherited from CRUDBase and should work directly

# Create a singleton instance of the repository
app_role_repo = AppRoleRepository(AppRoleDb) 