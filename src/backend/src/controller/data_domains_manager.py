import logging
from typing import List, Optional
from uuid import UUID
import json # Import json

from sqlalchemy.orm import Session, joinedload, selectinload # Added joinedload, selectinload
from sqlalchemy.exc import IntegrityError # Import IntegrityError

from src.repositories.data_domain_repository import DataDomainRepository
from src.models.data_domains import DataDomainCreate, DataDomainUpdate, DataDomainRead, DataDomainBasicInfo # Added DataDomainBasicInfo
from src.db_models.data_domains import DataDomain
from src.common.logging import get_logger
from src.common.errors import ConflictError, NotFoundError, AppError # Import custom errors, AppError for validation
# from src.controller.audit_log_manager import AuditLogManager # Placeholder

logger = get_logger(__name__)

class DataDomainManager:
    def __init__(self, repository: DataDomainRepository):
        self.repository = repository
        # self.audit_log_manager = AuditLogManager() # Placeholder: Inject later
        logger.debug("DataDomainManager initialized.")

    def _convert_db_to_read_model(self, db_domain: DataDomain) -> DataDomainRead:
        """Helper to convert DB model to Read model, populating parent_name and children_count."""
        parent_name = None
        parent_info_data: Optional[DataDomainBasicInfo] = None
        if db_domain.parent: # Assuming parent is loaded
            parent_name = db_domain.parent.name
            parent_info_data = DataDomainBasicInfo.model_validate(db_domain.parent) # Use model_validate for Pydantic v2
        
        children_count = len(db_domain.children) # Assuming children are loaded or counted
        children_info_data: List[DataDomainBasicInfo] = []
        if db_domain.children:
            for child_db_obj in db_domain.children:
                children_info_data.append(DataDomainBasicInfo.model_validate(child_db_obj))

        # Ensure tags and owner are lists when converting from JSON string
        # The DataDomainRead model's validator will handle JSON string parsing if it gets a string.
        # If already parsed by repository or earlier, it should be a list.
        # For safety, let's ensure it. This might be redundant if DataDomainRead validator is robust.
        owner_list = db_domain.owner
        if isinstance(db_domain.owner, str):
            try:
                owner_list = json.loads(db_domain.owner.replace("'", '"'))
            except json.JSONDecodeError:
                logger.warning(f"Could not parse owner field for domain {db_domain.id}: {db_domain.owner}")
                owner_list = [] # Default to empty list on parsing error

        tags_list = db_domain.tags
        if db_domain.tags and isinstance(db_domain.tags, str):
            try:
                tags_list = json.loads(db_domain.tags.replace("'", '"'))
            except json.JSONDecodeError:
                logger.warning(f"Could not parse tags field for domain {db_domain.id}: {db_domain.tags}")
                tags_list = [] # Default to empty list on parsing error
        elif not db_domain.tags:
            tags_list = None # Keep it None if it's None

        return DataDomainRead(
            id=db_domain.id,
            name=db_domain.name,
            description=db_domain.description,
            owner=owner_list,
            tags=tags_list,
            parent_id=db_domain.parent_id,
            created_at=db_domain.created_at,
            updated_at=db_domain.updated_at,
            created_by=db_domain.created_by,
            parent_name=parent_name,
            children_count=children_count,
            parent_info=parent_info_data,
            children_info=children_info_data
        )

    def create_domain(self, db: Session, domain_in: DataDomainCreate, current_user_id: str) -> DataDomainRead:
        """Creates a new data domain."""
        logger.debug(f"Attempting to create data domain: {domain_in.name}")
        
        if domain_in.parent_id:
            parent_domain = self.repository.get(db, domain_in.parent_id)
            if not parent_domain:
                raise NotFoundError(f"Parent domain with id '{domain_in.parent_id}' not found.")

        db_obj_data = domain_in.model_dump(exclude_unset=True) # Use model_dump for Pydantic v2
        db_obj_data['created_by'] = current_user_id

        if isinstance(db_obj_data.get('owner'), list):
            db_obj_data['owner'] = json.dumps(db_obj_data['owner'])
        if isinstance(db_obj_data.get('tags'), list):
            db_obj_data['tags'] = json.dumps(db_obj_data['tags'])

        db_domain = DataDomain(**db_obj_data)

        try:
            db.add(db_domain)
            db.flush() 
            db.refresh(db_domain, attribute_names=['id', 'parent']) # Refresh to get ID and potentially loaded parent
            # Eagerly load children for count, or rely on lazy load if simple len() is fine.
            # For now, let's assume session context handles children for len()
            # If specific loading is needed: db.refresh(db_domain, attribute_names=['children'])
            # but this loads all children objects, which might be heavy.
            # A subquery for count in repository.get might be better for children_count.
            # For now, using len(db_domain.children) implicitly assumes they are accessible.

            logger.debug(f"Successfully created data domain '{db_domain.name}' with id: {db_domain.id}")
            # Load parent again to ensure its name is available for the read model conversion
            # This is needed if the initial refresh didn't fully populate it or if not using joinedload in repo.
            if db_domain.parent_id and not db_domain.parent:
                 # This might be redundant if db.refresh already handled it or if repo.get loads parent.
                 # This specific refresh for parent might not be needed if the relationship is configured correctly (e.g. lazy='joined')
                 # or if the repo method that fetches it does a joinedload.
                 # For now, let's explicitly fetch the parent if parent_id exists but parent object is not loaded.
                 # This explicit query ensures parent.name is available for _convert_db_to_read_model.
                 parent_obj = db.query(DataDomain).filter(DataDomain.id == db_domain.parent_id).one_or_none()
                 db_domain.parent = parent_obj # Assign it to the instance

            # Explicitly load children to count them. This can be inefficient.
            # A better approach would be a COUNT subquery in the repository layer.
            # For simplicity here, assume children relationship can be counted via len().
            # db.refresh(db_domain, with_for_update=None, attribute_names=['children']) # This reloads ALL children objects.

            return self._convert_db_to_read_model(db_domain)
        except IntegrityError as e:
            db.rollback()
            logger.warning(f"Integrity error creating data domain '{domain_in.name}': {e}")
            if "unique constraint" in str(e).lower() or "duplicate key" in str(e).lower():
                raise ConflictError(f"Data domain with name '{domain_in.name}' already exists.")
            else:
                raise 
        except Exception as e:
            db.rollback()
            logger.exception(f"Error creating data domain '{domain_in.name}': {e}")
            raise

    def get_domain_by_id(self, db: Session, domain_id: UUID) -> Optional[DataDomainRead]:
        """Gets a data domain by its ID, including parent name and children count."""
        logger.debug(f"Fetching data domain with id: {domain_id}")
        # Modify repository call or logic here to ensure parent and children (for count) are loaded
        # Using options for joinedload for parent and potentially a subquery for children count in repo is best.
        # For now, we rely on lazy loading and direct access, which might cause N+1 queries if not careful.
        db_domain = self.repository.get_with_details(db, domain_id) # Assume repo method loads parent and children for count
        
        if not db_domain:
            logger.warning(f"Data domain with id {domain_id} not found.")
            return None
        return self._convert_db_to_read_model(db_domain)

    def get_all_domains(self, db: Session, skip: int = 0, limit: int = 100) -> List[DataDomainRead]:
        """Gets a list of all data domains, including parent name and children count."""
        logger.debug(f"Fetching all data domains with skip={skip}, limit={limit}")
        # Same as get_domain_by_id, ensure repository loads necessary data efficiently.
        db_domains = self.repository.get_multi_with_details(db, skip=skip, limit=limit) # Assume repo method loads details
        return [self._convert_db_to_read_model(domain) for domain in db_domains]

    def update_domain(self, db: Session, domain_id: UUID, domain_in: DataDomainUpdate, current_user_id: str) -> Optional[DataDomainRead]:
        """Updates an existing data domain."""
        logger.debug(f"Attempting to update data domain with id: {domain_id}")
        db_domain = self.repository.get(db, domain_id) # Get the raw domain first
        if not db_domain:
            logger.warning(f"Data domain with id {domain_id} not found for update.")
            raise NotFoundError(f"Data domain with id '{domain_id}' not found.")

        if domain_in.parent_id:
            if domain_in.parent_id == domain_id:
                 raise AppError(f"Cannot set a domain as its own parent.") # Use a more specific error like ValidationError or BadRequest
            parent_domain = self.repository.get(db, domain_in.parent_id)
            if not parent_domain:
                raise NotFoundError(f"Parent domain with id '{domain_in.parent_id}' not found.")
        
        # obj_in here is Pydantic model, repository.update expects a dict or Pydantic model
        update_data = domain_in.model_dump(exclude_unset=True)

        # Serialize lists to JSON strings if they are provided in the update
        if 'owner' in update_data and isinstance(update_data['owner'], list):
            update_data['owner'] = json.dumps(update_data['owner'])
        if 'tags' in update_data and isinstance(update_data['tags'], list):
            update_data['tags'] = json.dumps(update_data['tags'])

        try:
            # The CRUDBase update method takes obj_in which can be a dict or Pydantic model.
            # It iterates fields and sets them on db_obj.
            updated_db_domain = self.repository.update(db=db, db_obj=db_domain, obj_in=update_data)
            # After update, refresh to get potentially updated relationships or counts
            db.flush()
            db.refresh(updated_db_domain, attribute_names=['parent']) # Ensure parent is loaded if parent_id changed
            # db.refresh(updated_db_domain, attribute_names=['children']) # if children count could change indirectly

            logger.debug(f"Successfully updated data domain '{updated_db_domain.name}' (id: {domain_id})")
            return self._convert_db_to_read_model(updated_db_domain)
        except IntegrityError as e:
             db.rollback()
             logger.warning(f"Integrity error updating data domain {domain_id}: {e}")
             if "unique constraint" in str(e).lower() or "duplicate key" in str(e).lower():
                 raise ConflictError(f"Data domain name '{domain_in.name}' is already in use by another domain.")
             else:
                 raise
        except AppError as e: # Catch our custom validation error
            db.rollback()
            raise # Re-raise it to be caught by FastAPI error handling (e.g., return 400)
        except Exception as e:
            db.rollback()
            logger.exception(f"Error updating data domain {domain_id}: {e}")
            raise

    def delete_domain(self, db: Session, domain_id: UUID, current_user_id: str) -> Optional[DataDomainRead]:
        """Deletes a data domain by its ID."""
        logger.debug(f"Attempting to delete data domain with id: {domain_id}")
        
        db_domain_to_delete = self.repository.get_with_details(db, domain_id) # Load details for return
        if not db_domain_to_delete:
             logger.warning(f"Data domain with id {domain_id} not found for deletion.")
             raise NotFoundError(f"Data domain with id '{domain_id}' not found.")

        # Check for children - prevent deletion if domain has children, or handle cascading based on policy
        # The cascade="all, delete-orphan" on DB model will delete children.
        # If we want to prevent deletion of parents with children, we add a check here.
        if db_domain_to_delete.children:
            # Current cascade rule will delete children. If this is not desired, raise error.
            # logger.warning(f"Attempt to delete domain {domain_id} which has {len(db_domain_to_delete.children)} children. Deletion allowed due to cascade rule.")
            # To prevent deletion: 
            # raise ConflictError(f"Cannot delete domain '{db_domain_to_delete.name}' because it has child domains. Please delete or re-parent children first.")
            pass # Current setup allows cascade delete.

        read_model_of_deleted = self._convert_db_to_read_model(db_domain_to_delete)
        
        try:
            # The repository.remove(db, id) should work.
            # The actual object `db_domain_to_delete` will become stale after deletion from session.
            self.repository.remove(db=db, id=domain_id)
            # db.commit() is handled by the route typically
            logger.debug(f"Successfully marked data domain '{read_model_of_deleted.name}' (id: {domain_id}) for deletion.")
            return read_model_of_deleted 
        except Exception as e:
            db.rollback()
            logger.exception(f"Error deleting data domain {domain_id}: {e}")
            raise

    # --- Demo Data Loading --- #
    def load_initial_data(self, db: Session) -> None:
        """Loads initial data domains from a YAML file if the table is empty."""
        logger.debug("DataDomainManager: Checking if data domains table is empty...")
        try:
            is_empty = self.repository.is_empty(db)
        except Exception as e:
             logger.error(f"DataDomainManager: Error checking if table is empty: {e}", exc_info=True)
             return 

        if not is_empty:
            logger.debug("Data domains table is not empty. Skipping initial data loading.")
            return

        import yaml
        from pathlib import Path

        data_file = Path(__file__).parent.parent / "data" / "data_domains.yaml"
        if not data_file.exists():
            logger.warning(f"Demo data file not found: {data_file}. Cannot load initial domains.")
            return

        logger.debug(f"Loading initial data domains from {data_file}...")
        try:
            with open(data_file, 'r') as f:
                data = yaml.safe_load(f)
            
            if not data or 'domains' not in data or not isinstance(data['domains'], list):
                logger.warning(f"Demo data file {data_file} is empty or has incorrect format.")
                return

            count = 0
            default_creator = "system.init@app.dev"
            
            # First pass: create all domains without parent_id (if parent_name is used)
            # Or, if parent_id is directly in YAML, this isn't strictly needed but good for name resolution
            domains_created_map = {} # To map name to ID for parent resolution

            for domain_data in data['domains']:
                try:
                    if 'name' not in domain_data or 'owner' not in domain_data:
                         logger.warning(f"Skipping domain entry due to missing required fields: {domain_data.get('name', 'N/A')}")
                         continue
                    
                    # Create a copy for mutation, remove parent_name if it exists
                    create_data = domain_data.copy()
                    parent_name_to_resolve = create_data.pop('parent_name', None)
                    create_data.pop('id', None) # remove id if present, we generate it

                    # If parent_id is directly provided and valid UUID, use it.
                    # If parent_name is provided, we will resolve it later.
                    if 'parent_id' in create_data and create_data['parent_id'] is None:
                        del create_data['parent_id'] # Pydantic expects UUID or None, not string 'null' from yaml if not set

                    domain_create_schema = DataDomainCreate(**create_data)
                    # Temporarily skip parent_id assignment if resolving by name later
                    if parent_name_to_resolve:
                        domain_create_schema.parent_id = None 
                        
                    created_domain_obj = self.create_domain_internal(db=db, domain_in=domain_create_schema, current_user_id=default_creator, perform_commit=False)
                    domains_created_map[created_domain_obj.name] = created_domain_obj.id
                    count += 1
                except (ValueError, TypeError, ConflictError, NotFoundError, AppError) as val_err:
                    logger.warning(f"Skipping invalid domain entry '{domain_data.get('name', 'N/A')}' during initial load pass 1: {val_err}")
                except Exception as inner_e:
                     logger.error(f"Error loading domain entry '{domain_data.get('name', 'N/A')}' (pass 1): {inner_e}", exc_info=False)
            
            db.flush() # Flush all first-pass creations

            # Second pass: update parent_id if parent_name was used
            if any('parent_name' in d for d in data['domains']):
                logger.debug("Starting second pass to link parent domains by name...")
                for domain_data in data['domains']:
                    parent_name_to_resolve = domain_data.get('parent_name')
                    current_domain_name = domain_data.get('name')
                    if parent_name_to_resolve and current_domain_name in domains_created_map:
                        parent_id_resolved = domains_created_map.get(parent_name_to_resolve)
                        current_domain_id = domains_created_map[current_domain_name]
                        if parent_id_resolved:
                            logger.debug(f"Linking '{current_domain_name}' to parent '{parent_name_to_resolve}' (ID: {parent_id_resolved})")
                            db_domain_to_update = self.repository.get(db, current_domain_id)
                            if db_domain_to_update:
                                db_domain_to_update.parent_id = parent_id_resolved
                                db.add(db_domain_to_update) # Add to session for update
                            else:
                                logger.warning(f"Could not find domain '{current_domain_name}' for parent update.")
                        else:
                            logger.warning(f"Could not resolve parent_name '{parent_name_to_resolve}' for domain '{current_domain_name}'. Skipping parent link.")
            
            db.commit() 
            logger.debug(f"Successfully processed {count} initial data domains over two passes.")

        except yaml.YAMLError as ye:
            logger.error(f"Error parsing YAML file {data_file}: {ye}")
            db.rollback()
        except Exception as e:
            logger.exception(f"Failed to load initial data domains from {data_file}: {e}")
            db.rollback() 

    def create_domain_internal(self, db: Session, domain_in: DataDomainCreate, current_user_id: str, perform_commit: bool = True) -> DataDomain:
        """Internal method to create domain, returns DB object, used by load_initial_data."""
        if domain_in.parent_id:
            parent_domain = self.repository.get(db, domain_in.parent_id)
            if not parent_domain:
                raise NotFoundError(f"Parent domain with id '{domain_in.parent_id}' not found.")

        db_obj_data = domain_in.model_dump(exclude_unset=True)
        db_obj_data['created_by'] = current_user_id
        if isinstance(db_obj_data.get('owner'), list):
            db_obj_data['owner'] = json.dumps(db_obj_data['owner'])
        if isinstance(db_obj_data.get('tags'), list):
            db_obj_data['tags'] = json.dumps(db_obj_data['tags'])
        
        db_domain = DataDomain(**db_obj_data)
        try:
            db.add(db_domain)
            if perform_commit:
                db.commit()
                db.refresh(db_domain)
            else:
                db.flush() # Flush to get ID if not committing
                db.refresh(db_domain, attribute_names=['id'])
            return db_domain
        except IntegrityError as e:
            db.rollback()
            if "unique constraint" in str(e).lower() or "duplicate key" in str(e).lower():
                raise ConflictError(f"Data domain with name '{domain_in.name}' already exists.")
            raise
        except Exception as e:
            db.rollback()
            raise 