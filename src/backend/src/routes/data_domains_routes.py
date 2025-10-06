from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from src.models.data_domains import DataDomainCreate, DataDomainUpdate, DataDomainRead
from src.controller.data_domains_manager import DataDomainManager
from src.common.database import get_db
from sqlalchemy.orm import Session
from src.common.authorization import PermissionChecker # Import PermissionChecker
from src.common.features import FeatureAccessLevel
from src.common.dependencies import (
    DBSessionDep, 
    CurrentUserDep, # Provides UserInfo
    get_data_domain_manager # Import the dependency getter
) 
from src.models.users import UserInfo # To type hint current_user
from src.common.errors import NotFoundError, ConflictError

from src.common.logging import get_logger
logger = get_logger(__name__)

# Define router
# Using kebab-case for endpoint path as per convention
router = APIRouter(prefix="/api", tags=["Data Domains"])

# --- Feature ID Constant --- #
DATA_DOMAINS_FEATURE_ID = "data-domains" # Use a consistent ID

# --- Route Definitions --- #

@router.post(
    "/data-domains", 
    response_model=DataDomainRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(PermissionChecker(DATA_DOMAINS_FEATURE_ID, FeatureAccessLevel.READ_WRITE))]
)
def create_data_domain(
    domain_in: DataDomainCreate,
    db: DBSessionDep,
    current_user: CurrentUserDep, # Moved before manager
    manager: DataDomainManager = Depends(get_data_domain_manager) # Default arg last
):
    """Creates a new data domain."""
    logger.info(f"User '{current_user.email}' attempting to create data domain: {domain_in.name}")
    try:
        # Pass current_user.email or another suitable identifier as creator
        created_domain = manager.create_domain(db=db, domain_in=domain_in, current_user_id=current_user.email)
        db.commit() # Commit the transaction after successful creation
        return created_domain
    except ConflictError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        db.rollback()
        logger.exception(f"Failed to create data domain '{domain_in.name}': {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create data domain: {e!s}")

@router.get(
    "/data-domains", 
    response_model=List[DataDomainRead],
    dependencies=[Depends(PermissionChecker(DATA_DOMAINS_FEATURE_ID, FeatureAccessLevel.READ_ONLY))]
)
def get_all_data_domains(
    # Dependencies first
    db: DBSessionDep,
    manager: DataDomainManager = Depends(get_data_domain_manager),
    # Then query parameters
    skip: int = 0,
    limit: int = 100,
):
    """Lists all data domains."""
    logger.debug(f"Fetching all data domains (skip={skip}, limit={limit})")
    try:
        return manager.get_all_domains(db=db, skip=skip, limit=limit)
    except Exception as e:
        logger.exception(f"Failed to fetch data domains: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch data domains")

@router.get(
    "/data-domains/{domain_id}", 
    response_model=DataDomainRead,
    dependencies=[Depends(PermissionChecker(DATA_DOMAINS_FEATURE_ID, FeatureAccessLevel.READ_ONLY))]
)
def get_data_domain(
    domain_id: UUID,
    db: DBSessionDep,
    manager: DataDomainManager = Depends(get_data_domain_manager)
):
    """Gets a specific data domain by its ID."""
    logger.debug(f"Fetching data domain with id: {domain_id}")
    domain = manager.get_domain_by_id(db=db, domain_id=domain_id)
    if not domain:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Data domain with id '{domain_id}' not found")
    return domain

@router.put(
    "/data-domains/{domain_id}", 
    response_model=DataDomainRead,
    dependencies=[Depends(PermissionChecker(DATA_DOMAINS_FEATURE_ID, FeatureAccessLevel.READ_WRITE))]
)
def update_data_domain(
    domain_id: UUID,
    domain_in: DataDomainUpdate,
    db: DBSessionDep,
    current_user: CurrentUserDep, # Moved before manager
    manager: DataDomainManager = Depends(get_data_domain_manager) # Default arg last
):
    """Updates an existing data domain."""
    logger.info(f"User '{current_user.email}' attempting to update data domain: {domain_id}")
    try:
        updated_domain = manager.update_domain(
            db=db, 
            domain_id=domain_id, 
            domain_in=domain_in, 
            current_user_id=current_user.email
        )
        db.commit()
        return updated_domain
    except NotFoundError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ConflictError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        db.rollback()
        logger.exception(f"Failed to update data domain {domain_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to update data domain: {e!s}")

@router.delete(
    "/data-domains/{domain_id}", 
    response_model=DataDomainRead, # Return the deleted domain
    status_code=status.HTTP_200_OK, 
    dependencies=[Depends(PermissionChecker(DATA_DOMAINS_FEATURE_ID, FeatureAccessLevel.ADMIN))] # Require Admin to delete
)
def delete_data_domain(
    domain_id: UUID,
    db: DBSessionDep,
    current_user: CurrentUserDep, # Moved before manager
    manager: DataDomainManager = Depends(get_data_domain_manager) # Default arg last
):
    """Deletes a data domain. Requires Admin privileges."""
    logger.info(f"User '{current_user.email}' attempting to delete data domain: {domain_id}")
    try:
        deleted_domain = manager.delete_domain(db=db, domain_id=domain_id, current_user_id=current_user.email)
        db.commit()
        return deleted_domain
    except NotFoundError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        db.rollback()
        logger.exception(f"Failed to delete data domain {domain_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete data domain: {e!s}")

def register_routes(app):
    app.include_router(router)
    logger.info("Data Domain routes registered with prefix /api/data-domains") 