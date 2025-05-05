from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select, Column, distinct
from typing import List, Optional, Any, Dict, Union
import json # Needed for parsing JSON strings

from api.common.repository import CRUDBase
from api.models.data_products import DataProduct as DataProductApi, Info, InputPort, OutputPort # Pydantic models
# Import all relevant DB models
from api.db_models.data_products import (DataProductDb, InfoDb, InputPortDb, OutputPortDb, Tag)
from api.common.logging import get_logger

logger = get_logger(__name__)

# Define specific Pydantic models for create/update if they differ significantly
# For now, using the main API model for simplicity
DataProductCreate = DataProductApi
DataProductUpdate = DataProductApi 

class DataProductRepository(CRUDBase[DataProductDb, DataProductCreate, DataProductUpdate]):
    """Repository for DataProduct CRUD operations (Normalized Schema)."""

    # We can override methods here if needed, e.g., for complex queries or specific logic.
    # For basic CRUD with JSON fields, the base class might suffice initially.
    # However, let's override create and update to show potential mapping/handling.

    def _get_or_create_tags(self, db: Session, tag_names: List[str]) -> List[Tag]:
        """Finds existing tags or creates new ones."""
        tags = []
        if not tag_names: return tags
        
        existing_tags = db.query(Tag).filter(Tag.name.in_(tag_names)).all()
        existing_names = {t.name for t in existing_tags}
        tags.extend(existing_tags)
        
        new_names = set(tag_names) - existing_names
        for name in new_names:
            new_tag = Tag(name=name)
            tags.append(new_tag)
            db.add(new_tag) # Add new tags to session
            
        # Flush to get IDs if needed immediately, but commit handles it later
        # db.flush()
        return tags

    # Repository create method now expects the validated Pydantic model
    def create(self, db: Session, *, obj_in: DataProductApi) -> DataProductDb:
        logger.debug(f"Creating DataProduct (DB layer - normalized)")
        
        # 1. Prepare core DataProduct data (excluding relationships initially)
        # Directly use attributes from the Pydantic model obj_in
        db_obj = self.model(
            id=obj_in.id,
            dataProductSpecification=obj_in.dataProductSpecification,
            links=json.dumps(obj_in.links) if obj_in.links is not None else '{}',
            custom=json.dumps(obj_in.custom) if obj_in.custom is not None else '{}',
            version=obj_in.version, # Assume validated model has it
            # Handle productType being either enum or string after validation
            product_type=obj_in.productType.value if hasattr(obj_in.productType, 'value') else obj_in.productType
        )

        # 2. Create InfoDb object (Exclude deprecated fields)
        if obj_in.info:
            # Exclude 'maturity' explicitly before passing to InfoDb constructor
            info_data = obj_in.info.model_dump(exclude={'maturity'}) # Use model_dump and exclude
            info_obj = InfoDb(**info_data)
            db_obj.info = info_obj

        # 3. Create InputPortDb objects
        if obj_in.inputPorts: # Check if the list exists
            for port_in in obj_in.inputPorts: # port_in is an InputPort Pydantic model
                # Convert Pydantic model to dict, keep sourceOutputPortId
                port_data = port_in.dict(exclude_none=True) # exclude_none might be useful
                
                # Rename 'type' key if present
                if 'type' in port_data:
                    port_data['port_type'] = port_data.pop('type')
                
                # Map assetType and assetIdentifier
                port_data['asset_type'] = port_in.assetType
                port_data['asset_identifier'] = port_in.assetIdentifier
                
                # Ensure JSON fields are strings
                port_data['links'] = json.dumps(port_data.get('links')) if port_data.get('links') else '{}'
                port_data['custom'] = json.dumps(port_data.get('custom')) if port_data.get('custom') else '{}'
                port_data['tags'] = json.dumps(port_data.get('tags')) if port_data.get('tags') else '[]'

                # sourceOutputPortId is already correctly named from Pydantic model

                port_obj = InputPortDb(**port_data)
                db_obj.inputPorts.append(port_obj)
            
        # 4. Create OutputPortDb objects
        if obj_in.outputPorts: # Check if the list exists
            for port_in in obj_in.outputPorts: # port_in is an OutputPort Pydantic model
                port_data = port_in.dict(exclude_none=True)
                if 'type' in port_data:
                    port_data['port_type'] = port_data.pop('type')
                
                # Map assetType and assetIdentifier
                port_data['asset_type'] = port_in.assetType
                port_data['asset_identifier'] = port_in.assetIdentifier

                port_data['server'] = json.dumps(port_data.get('server')) if port_data.get('server') else '{}'
                port_data['links'] = json.dumps(port_data.get('links')) if port_data.get('links') else '{}'
                port_data['custom'] = json.dumps(port_data.get('custom')) if port_data.get('custom') else '{}'
                port_data['tags'] = json.dumps(port_data.get('tags')) if port_data.get('tags') else '[]'
                port_obj = OutputPortDb(**port_data)
                db_obj.outputPorts.append(port_obj)
            
        # 5. Handle Tags (Many-to-Many)
        if obj_in.tags:
             db_obj.tags = self._get_or_create_tags(db, obj_in.tags)

        try:
            db.add(db_obj) # Adding parent cascades adds related objects
            db.flush() 
            db.refresh(db_obj) # Refresh to get IDs and load relationships if needed
            logger.info(f"Successfully created DataProduct (DB - norm) with id: {db_obj.id}")
            return db_obj
        except Exception as e:
            logger.error(f"Database error creating normalized DataProduct: {e}", exc_info=True)
            db.rollback()
            raise

    def update(self, db: Session, *, db_obj: DataProductDb, obj_in: Union[DataProductUpdate, Dict[str, Any]]) -> DataProductDb:
        logger.debug(f"Updating DataProduct (DB layer - normalized) with id: {db_obj.id}")
        
        # Convert Pydantic model to dict if necessary
        if not isinstance(obj_in, dict):
            update_data = obj_in.dict(exclude_unset=True)
        else:
            update_data = obj_in

        try:
            # Update core DataProduct fields
            db_obj.dataProductSpecification = update_data.get('dataProductSpecification', db_obj.dataProductSpecification)
            if 'links' in update_data: db_obj.links = json.dumps(update_data['links'])
            if 'custom' in update_data: db_obj.custom = json.dumps(update_data['custom'])
            # Update new fields
            db_obj.version = update_data.get('version', db_obj.version)
            if 'productType' in update_data: # Check for Pydantic field name
                 # The value from .dict() or .model_dump() should already be the string value
                 db_obj.product_type = update_data['productType']

            # Update Info (One-to-One)
            if 'info' in update_data and db_obj.info:
                info_update = update_data['info']
                for key, value in info_update.items():
                    # Handle deprecated maturity field if present in input
                    if key == 'maturity' and 'maturity' not in InfoDb.__table__.columns:
                         logger.warning("Ignoring deprecated 'maturity' field during Info update.")
                         continue
                    setattr(db_obj.info, key, value)
            elif 'info' in update_data and not db_obj.info:
                 # Create new Info if it didn't exist
                 info_obj = InfoDb(**update_data['info'])
                 db_obj.info = info_obj

            # Update Ports (One-to-Many) - More complex, needs matching/creation/deletion
            # This is a simplified example - full sync might be needed for robust updates
            # For now, let's just clear and re-add (simpler but less efficient)
            if 'inputPorts' in update_data:
                db_obj.inputPorts.clear() # Clear existing
                for port_in_dict in update_data['inputPorts']:
                     port_data = port_in_dict.copy()
                     # Rename type if present
                     if 'type' in port_data:
                         port_data['port_type'] = port_data.pop('type')
                     
                     # Handle assetType/assetIdentifier from update_data
                     port_data['asset_type'] = port_in_dict.get('assetType') # Use Pydantic name from input dict
                     port_data['asset_identifier'] = port_in_dict.get('assetIdentifier')
                     
                     # Stringify JSON fields
                     port_data['links'] = json.dumps(port_data.get('links')) if port_data.get('links') else '{}'
                     port_data['custom'] = json.dumps(port_data.get('custom')) if port_data.get('custom') else '{}'
                     port_data['tags'] = json.dumps(port_data.get('tags')) if port_data.get('tags') else '[]'
                     # sourceOutputPortId is already correct in port_in_dict
                     port_obj = InputPortDb(**port_data)
                     db_obj.inputPorts.append(port_obj)
                     
            if 'outputPorts' in update_data:
                 db_obj.outputPorts.clear() # Clear existing
                 for port_in_dict in update_data['outputPorts']:
                     port_data = port_in_dict.copy()
                     if 'type' in port_data:
                         port_data['port_type'] = port_data.pop('type')
                     
                     # Handle assetType/assetIdentifier from update_data
                     port_data['asset_type'] = port_in_dict.get('assetType') # Use Pydantic name from input dict
                     port_data['asset_identifier'] = port_in_dict.get('assetIdentifier')
                     
                     port_data['server'] = json.dumps(port_data.get('server')) if port_data.get('server') else '{}'
                     port_data['links'] = json.dumps(port_data.get('links')) if port_data.get('links') else '{}'
                     port_data['custom'] = json.dumps(port_data.get('custom')) if port_data.get('custom') else '{}'
                     port_data['tags'] = json.dumps(port_data.get('tags')) if port_data.get('tags') else '[]'
                     port_obj = OutputPortDb(**port_data)
                     db_obj.outputPorts.append(port_obj)

            # Update Tags (Many-to-Many)
            if 'tags' in update_data:
                db_obj.tags = self._get_or_create_tags(db, update_data['tags'])

            db.add(db_obj)
            db.flush()
            db.refresh(db_obj)
            logger.info(f"Successfully updated DataProduct (DB - norm) with id: {db_obj.id}")
            return db_obj
        except Exception as e:
            logger.error(f"Database error updating normalized DataProduct (id: {db_obj.id}): {e}", exc_info=True)
            db.rollback()
            raise
            
    # --- Overwrite get/get_multi to use relationship loading --- 
    def get(self, db: Session, id: Any) -> Optional[DataProductDb]:
        logger.debug(f"Fetching DataProduct (DB - norm) with id: {id}")
        try:
            # Use options to eagerly load relationships using selectinload (efficient)
            return db.query(self.model).options(
                selectinload(self.model.info),
                selectinload(self.model.inputPorts),
                selectinload(self.model.outputPorts),
                selectinload(self.model.tags)
            ).filter(self.model.id == id).first()
        except Exception as e:
            logger.error(f"Database error fetching normalized DataProduct by id {id}: {e}", exc_info=True)
            db.rollback()
            raise

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> List[DataProductDb]:
        logger.debug(f"Fetching multiple DataProducts (DB - norm) with skip: {skip}, limit: {limit}")
        try:
            return db.query(self.model).options(
                 selectinload(self.model.info),
                 selectinload(self.model.inputPorts),
                 selectinload(self.model.outputPorts),
                 selectinload(self.model.tags)
            ).offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"Database error fetching multiple normalized DataProducts: {e}", exc_info=True)
            db.rollback()
            raise
            
    # --- Distinct Value Queries (Update for Normalized Schema) --- 
    def get_distinct_product_types(self, db: Session) -> List[str]:
        logger.debug("Querying distinct product_types from DB (normalized)...")
        try:
             # Query the DataProductDb table directly for product_type
             result = db.execute(select(distinct(self.model.product_type)).where(self.model.product_type.isnot(None))).scalars().all()
             return sorted(list(result))
        except Exception as e:
             logger.error(f"Error querying distinct product_types (normalized): {e}", exc_info=True)
             return []

    def get_distinct_owners(self, db: Session) -> List[str]:
        logger.debug("Querying distinct owners from DB (normalized)...")
        try:
             result = db.execute(select(distinct(InfoDb.owner)).where(InfoDb.owner.isnot(None))).scalars().all()
             return sorted(list(result))
        except Exception as e:
             logger.error(f"Error querying distinct owners (normalized): {e}", exc_info=True)
             return []
        
    def get_distinct_statuses(self, db: Session) -> List[str]:
        logger.debug("Querying distinct statuses from DB (normalized)...")
        statuses = set()
        try:
            # 1. Get statuses from info.status
            info_statuses = db.execute(select(distinct(InfoDb.status)).where(InfoDb.status.isnot(None))).scalars().all()
            statuses.update(info_statuses)
            
            # 2. Get statuses from outputPorts.status
            port_statuses = db.execute(select(distinct(OutputPortDb.status)).where(OutputPortDb.status.isnot(None))).scalars().all()
            statuses.update(port_statuses)
                     
            return sorted([s for s in statuses if s]) # Filter out None/empty
        except Exception as e:
             logger.error(f"Error querying distinct statuses (normalized): {e}", exc_info=True)
             return []

# Create a single instance of the repository for use
# This could also be instantiated within the manager or injected via FastAPI deps
data_product_repo = DataProductRepository(DataProductDb) 