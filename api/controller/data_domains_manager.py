import logging
from typing import List, Optional
from uuid import UUID
import json # Import json

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError # Import IntegrityError

from api.repositories.data_domain_repository import DataDomainRepository
from api.models.data_domains import DataDomainCreate, DataDomainUpdate, DataDomainRead
from api.db_models.data_domains import DataDomain
from api.common.logging import get_logger
from api.common.errors import ConflictError, NotFoundError # Import custom errors
# from api.controller.audit_log_manager import AuditLogManager # Placeholder

logger = get_logger(__name__)

class DataDomainManager:
    def __init__(self, repository: DataDomainRepository):
        self.repository = repository
        # self.audit_log_manager = AuditLogManager() # Placeholder: Inject later
        logger.info("DataDomainManager initialized.")

    def create_domain(self, db: Session, domain_in: DataDomainCreate, current_user_id: str) -> DataDomainRead:
        """Creates a new data domain."""
        logger.info(f"Attempting to create data domain: {domain_in.name}")
        # Add created_by user
        # The repository's create method expects the schema, not the raw dict.
        # We need to add created_by to the DB model instance before adding to session.
        
        # Create DB object dictionary without created_by first
        db_obj_data = domain_in.dict()
        db_obj_data['created_by'] = current_user_id

        # Serialize list fields to JSON strings before creating DB model
        if isinstance(db_obj_data.get('owner'), list):
            db_obj_data['owner'] = json.dumps(db_obj_data['owner'])
        if isinstance(db_obj_data.get('tags'), list):
            db_obj_data['tags'] = json.dumps(db_obj_data['tags'])

        db_domain = DataDomain(**db_obj_data)

        try:
            db.add(db_domain)
            db.flush() # Flush to check for constraints like unique name
            db.refresh(db_domain)
            logger.info(f"Successfully created data domain '{db_domain.name}' with id: {db_domain.id}")
            # TODO: Add audit log entry
            # self.audit_log_manager.record_event(db, user=current_user_id, action="create", resource_type="data_domain", resource_id=db_domain.id, details=domain_in.dict())
            return DataDomainRead.from_orm(db_domain)
        except IntegrityError as e:
            db.rollback()
            logger.warning(f"Integrity error creating data domain '{domain_in.name}': {e}")
            # Check if it's a unique constraint violation (specific error code/string might depend on DB)
            if "unique constraint" in str(e).lower() or "duplicate key" in str(e).lower():
                raise ConflictError(f"Data domain with name '{domain_in.name}' already exists.")
            else:
                raise # Re-raise other integrity errors
        except Exception as e:
            db.rollback()
            logger.exception(f"Error creating data domain '{domain_in.name}': {e}")
            raise

    def get_domain_by_id(self, db: Session, domain_id: UUID) -> Optional[DataDomainRead]:
        """Gets a data domain by its ID."""
        logger.debug(f"Fetching data domain with id: {domain_id}")
        db_domain = self.repository.get(db, domain_id)
        if not db_domain:
            logger.warning(f"Data domain with id {domain_id} not found.")
            return None
        return DataDomainRead.from_orm(db_domain)

    def get_all_domains(self, db: Session, skip: int = 0, limit: int = 100) -> List[DataDomainRead]:
        """Gets a list of all data domains."""
        logger.debug(f"Fetching all data domains with skip={skip}, limit={limit}")
        db_domains = self.repository.get_multi(db, skip=skip, limit=limit)
        return [DataDomainRead.from_orm(domain) for domain in db_domains]

    def update_domain(self, db: Session, domain_id: UUID, domain_in: DataDomainUpdate, current_user_id: str) -> Optional[DataDomainRead]:
        """Updates an existing data domain."""
        logger.info(f"Attempting to update data domain with id: {domain_id}")
        db_domain = self.repository.get(db, domain_id)
        if not db_domain:
            logger.warning(f"Data domain with id {domain_id} not found for update.")
            raise NotFoundError(f"Data domain with id '{domain_id}' not found.")
        
        # Use repository's update method
        try:
            updated_db_domain = self.repository.update(db=db, db_obj=db_domain, obj_in=domain_in)
            logger.info(f"Successfully updated data domain '{updated_db_domain.name}' (id: {domain_id})")
            # TODO: Add audit log entry
            # self.audit_log_manager.record_event(db, user=current_user_id, action="update", resource_type="data_domain", resource_id=domain_id, details=domain_in.dict(exclude_unset=True))
            return DataDomainRead.from_orm(updated_db_domain)
        except IntegrityError as e:
             db.rollback()
             logger.warning(f"Integrity error updating data domain {domain_id}: {e}")
             if "unique constraint" in str(e).lower() or "duplicate key" in str(e).lower():
                 raise ConflictError(f"Data domain name '{domain_in.name}' is already in use by another domain.")
             else:
                 raise
        except Exception as e:
            db.rollback()
            logger.exception(f"Error updating data domain {domain_id}: {e}")
            raise

    def delete_domain(self, db: Session, domain_id: UUID, current_user_id: str) -> Optional[DataDomainRead]:
        """Deletes a data domain by its ID."""
        logger.info(f"Attempting to delete data domain with id: {domain_id}")
        
        # Check if domain exists before attempting delete via repository
        db_domain_to_delete = self.repository.get(db, domain_id)
        if not db_domain_to_delete:
             logger.warning(f"Data domain with id {domain_id} not found for deletion.")
             raise NotFoundError(f"Data domain with id '{domain_id}' not found.")

        # TODO: Add check for dependencies before deletion? (e.g., are any data products using this domain?)
        # This might require adding relationships or specific query methods.
        
        try:
            deleted_db_domain = self.repository.remove(db=db, id=domain_id)
            if deleted_db_domain:
                logger.info(f"Successfully deleted data domain '{deleted_db_domain.name}' (id: {domain_id})")
                # TODO: Add audit log entry
                # self.audit_log_manager.record_event(db, user=current_user_id, action="delete", resource_type="data_domain", resource_id=domain_id, details=None)
                return DataDomainRead.from_orm(deleted_db_domain) # Return the deleted object details
            else:
                # Should have been caught by the initial get, but handle defensively
                logger.error(f"Deletion failed for domain {domain_id} even after initial check.")
                raise NotFoundError(f"Data domain with id '{domain_id}' could not be deleted (possibly already gone).")
        except Exception as e:
            db.rollback()
            logger.exception(f"Error deleting data domain {domain_id}: {e}")
            raise

    # --- Demo Data Loading --- #
    def load_initial_data(self, db: Session) -> None:
        """Loads initial data domains from a YAML file if the table is empty."""
        # Add logging before the check
        logger.info("DataDomainManager: Checking if data domains table is empty...")
        try:
            is_empty = self.repository.is_empty(db)
        except Exception as e:
             logger.error(f"DataDomainManager: Error checking if table is empty: {e}", exc_info=True)
             # Depending on requirements, maybe skip loading or re-raise
             return # Skip loading if check fails

        if not is_empty:
            logger.info("Data domains table is not empty. Skipping initial data loading.")
            return

        import yaml
        from pathlib import Path

        data_file = Path(__file__).parent.parent / "data" / "data_domains.yaml"
        if not data_file.exists():
            logger.warning(f"Demo data file not found: {data_file}. Cannot load initial domains.")
            return

        logger.info(f"Loading initial data domains from {data_file}...")
        try:
            with open(data_file, 'r') as f:
                data = yaml.safe_load(f)
            
            if not data or 'domains' not in data or not isinstance(data['domains'], list):
                logger.warning(f"Demo data file {data_file} is empty or has incorrect format.")
                return

            count = 0
            default_creator = "system.init@app.dev" # Or get from config?
            for domain_data in data['domains']:
                try:
                    # Ensure required fields are present
                    if 'name' not in domain_data or 'owner' not in domain_data:
                         logger.warning(f"Skipping domain entry due to missing required fields: {domain_data.get('name', 'N/A')}")
                         continue
                    
                    # Check if domain with this name already exists (shouldn't happen if table is empty, but good practice)
                    # existing = self.repository.get_by_name(db, name=domain_data['name']) # Needs get_by_name method in repo
                    # if existing:
                    #     logger.debug(f"Domain '{domain_data['name']}' already exists. Skipping.")
                    #     continue

                    domain_create = DataDomainCreate(**domain_data)
                    self.create_domain(db=db, domain_in=domain_create, current_user_id=default_creator)
                    count += 1
                except (ValueError, TypeError, ConflictError) as val_err:
                    logger.warning(f"Skipping invalid domain entry '{domain_data.get('name', 'N/A')}' during initial load: {val_err}")
                except Exception as inner_e:
                     logger.error(f"Error loading domain entry '{domain_data.get('name', 'N/A')}': {inner_e}", exc_info=False) # Avoid excessive stack trace for data errors
            
            db.commit() # Commit after loading all demo data for this manager
            logger.info(f"Successfully loaded {count} initial data domains.")

        except yaml.YAMLError as ye:
            logger.error(f"Error parsing YAML file {data_file}: {ye}")
            db.rollback()
        except Exception as e:
            logger.exception(f"Failed to load initial data domains from {data_file}: {e}")
            db.rollback() # Rollback any partial inserts 