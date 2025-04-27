import logging
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

import yaml
from fastapi import APIRouter, HTTPException, UploadFile, File, Body, Depends, Request
from pydantic import ValidationError
import uuid
# Remove Session dependency if get_db is no longer used directly here
# from sqlalchemy.orm import Session

from api.controller.data_products_manager import DataProductsManager
from api.models.data_products import DataProduct, GenieSpaceRequest # Use the updated model
from api.models.users import UserInfo # Needed for user context in auth
# Remove WorkspaceClient dependency if get_workspace_client_dependency is no longer used directly here
# from databricks.sdk import WorkspaceClient 
from databricks.sdk.errors import PermissionDenied # Import specific error

# Remove dependency functions if no longer used directly here
# from api.common.workspace_client import get_workspace_client_dependency
# from api.common.database import get_db

# Import Permission Checker and Levels
from api.common.authorization import PermissionChecker
from api.common.features import FeatureAccessLevel

# Import Annotated dependency types
from api.common.dependencies import CurrentUserDep, DBSessionDep # Add DBSessionDep

# Configure logging
from api.common.logging import setup_logging, get_logger
setup_logging(level=logging.INFO)
logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["data-products"])

# --- Helper to get manager instance with dependencies ---
def get_data_products_manager(
    # Remove old dependencies
    # db: Session = Depends(get_db),
    # ws_client: WorkspaceClient = Depends(get_workspace_client_dependency()) 
    request: Request # Inject Request
) -> DataProductsManager:
    """Retrieves the DataProductsManager singleton from app.state."""
    # Pass both db and ws_client to the manager
    # return DataProductsManager(db=db, ws_client=ws_client) 
    manager = request.app.state.manager_instances.get('data_products')
    if manager is None:
         logger.critical("DataProductsManager instance not found in app.state!")
         raise HTTPException(status_code=500, detail="Data Products service is not available.")
    return manager

# --- ORDERING CRITICAL: Define ALL static paths before ANY dynamic paths --- 

# --- Specific Helper Endpoints (Read-Only Access Needed) --- 

@router.get('/data-products/statuses', response_model=List[str])
async def get_data_product_statuses(
    manager: DataProductsManager = Depends(get_data_products_manager),
    _: bool = Depends(PermissionChecker('data-products', FeatureAccessLevel.READ_ONLY))
):
    """Get all distinct data product statuses from info and output ports."""
    try:
        statuses = manager.get_distinct_statuses()
        logger.info(f"Retrieved {len(statuses)} distinct data product statuses")
        return statuses
    except Exception as e:
        error_msg = f"Error retrieving data product statuses: {e!s}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@router.get('/data-products/archetypes', response_model=List[str])
async def get_data_product_archetypes(
    manager: DataProductsManager = Depends(get_data_products_manager),
    _: bool = Depends(PermissionChecker('data-products', FeatureAccessLevel.READ_ONLY))
):
    """Get all distinct data product archetypes."""
    try:
        archetypes = manager.get_distinct_archetypes()
        logger.info(f"Retrieved {len(archetypes)} distinct data product archetypes")
        return archetypes
    except Exception as e:
        error_msg = f"Error retrieving data product archetypes: {e!s}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@router.get('/data-products/owners', response_model=List[str])
async def get_data_product_owners(
    manager: DataProductsManager = Depends(get_data_products_manager),
    _: bool = Depends(PermissionChecker('data-products', FeatureAccessLevel.READ_ONLY))
):
    """Get all distinct data product owners."""
    try:
        owners = manager.get_distinct_owners()
        logger.info(f"Retrieved {len(owners)} distinct data product owners")
        return owners
    except Exception as e:
        error_msg = f"Error retrieving data product owners: {e!s}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@router.post("/data-products/upload", response_model=List[DataProduct], status_code=201)
async def upload_data_products(
    file: UploadFile = File(...),
    manager: DataProductsManager = Depends(get_data_products_manager),
    _: bool = Depends(PermissionChecker('data-products', FeatureAccessLevel.READ_WRITE))
):
    """Upload a YAML or JSON file containing a list of data products."""
    if not (file.filename.endswith('.yaml') or file.filename.endswith('.json')):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a YAML or JSON file.")

    try:
        content = await file.read()
        if file.filename.endswith('.yaml'):
            data = yaml.safe_load(content)
        else: # .json
            import json
            data = json.loads(content)
            
        # Allow either a single object or a list
        data_list: List[Dict[str, Any]]
        if isinstance(data, dict): 
            data_list = [data] # Wrap single object in a list
        elif isinstance(data, list):
            data_list = data # Use the list directly
        else:
            # Raise error if it's neither a dict nor a list
            raise HTTPException(status_code=400, detail="File must contain a JSON object/array or a YAML mapping/list of data product objects.")

        created_products = []
        errors = []
        # Process the unified data_list
        for product_data in data_list:
             if not isinstance(product_data, dict):
                 errors.append({"error": "Skipping non-dictionary item within list/array.", "item": product_data})
                 continue
             
             product_id_in_data = product_data.get('id')
             
             try:
                 # --- Generate ID if missing BEFORE validation --- 
                 if not product_id_in_data:
                     generated_id = str(uuid.uuid4())
                     product_data['id'] = generated_id
                     logger.info(f"Generated ID {generated_id} for uploaded product lacking one.")
                     # Update product_id_in_data for the duplicate check below
                     product_id_in_data = generated_id 
                 
                 # --- Duplicate Check (using potentially generated ID) --- 
                 if product_id_in_data and manager.get_product(product_id_in_data):
                     errors.append({"id": product_id_in_data, "error": "Product with this ID already exists. Skipping."})
                     continue
                 
                 # --- Pydantic Validation --- 
                 # Now validate with the ID definitely present
                 product_model = DataProduct(**product_data)
                 product_dict = product_model.model_dump(by_alias=True)
                 
                 # --- Creation --- 
                 # The ID is already in product_dict from model_dump
                 created_product = manager.create_product(product_dict)
                 created_products.append(created_product)
                 
             except ValidationError as e:
                 # Use the ID we determined (original or generated) for the error message
                 error_id = product_id_in_data if product_id_in_data else 'N/A_ValidationFailure'
                 errors.append({"id": error_id, "error": f"Validation failed: {e}"})
             except Exception as e:
                 error_id = product_id_in_data if product_id_in_data else 'N/A_CreationFailure'
                 errors.append({"id": error_id, "error": f"Creation failed: {e!s}"})

        # After processing all items, check if any errors occurred
        if errors:
            logger.warning(f"Encountered {len(errors)} errors during file upload processing.")
            # Return a 422 error if any product failed validation or processing
            raise HTTPException(
                status_code=422, 
                detail={"message": "Validation errors occurred during upload.", "errors": errors}
            )

        # If no errors, proceed with success logging and return
        logger.info(f"Successfully created {len(created_products)} data products from uploaded file {file.filename}")
        return created_products # Return list of successfully created products

    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"Invalid YAML format: {e}")
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON format: {e}")
    except HTTPException as e:
        # Re-raise specific HTTPExceptions (like 400 for non-list input)
        raise e
    except Exception as e:
        error_msg = f"Error processing uploaded file: {e!s}"
        logger.exception(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

# --- Generic List/Create Endpoints --- 

@router.get('/data-products', response_model=Any)
async def get_data_products(
    manager: DataProductsManager = Depends(get_data_products_manager),
    _: bool = Depends(PermissionChecker('data-products', FeatureAccessLevel.READ_ONLY))
):
    """Get all data products."""
    try:
        logger.info("Retrieving all data products via get_data_products route...")
        products = manager.list_products()
        logger.info(f"Retrieved {len(products)} data products")
        return [p.model_dump() for p in products]
    except Exception as e:
        error_msg = f"Error retrieving data products: {e!s}"
        logger.exception(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@router.post('/data-products', response_model=DataProduct, status_code=201)
async def create_data_product(
    payload: Dict[str, Any] = Body(...),
    manager: DataProductsManager = Depends(get_data_products_manager),
    _: bool = Depends(PermissionChecker('data-products', FeatureAccessLevel.READ_WRITE))
):
    """Create a new data product from a JSON payload dictionary."""
    try:
        logger.info(f"Received raw payload for creation: {payload}")
        product_id = payload.get('id')

        # Existence check
        if product_id and manager.get_product(product_id):
             raise HTTPException(status_code=409, detail=f"Data product with ID {product_id} already exists.")
        # ID generation if missing (fallback, frontend should provide it)
        if not product_id:
             payload['id'] = str(uuid.uuid4())
             logger.info(f"Generated ID for new product: {payload['id']}")

        # --- Explicit Validation (Optional but recommended for 422 errors) ---
        # Although the manager validates internally, doing it here allows returning detailed 422 errors.
        try:
            _ = DataProduct(**payload) # Attempt validation
        except ValidationError as e:
             logger.error(f"Validation failed for payload: {e}")
             raise HTTPException(status_code=422, detail=e.errors()) # Return Pydantic validation errors

        created_product = manager.create_product(payload)
        
        logger.info(f"Successfully created data product with ID: {created_product.id}")
        return created_product
    
    except HTTPException: # Re-raise specific HTTP exceptions (like 409, 422)
        raise
    # Note: ValueError from manager.create_product (if internal validation fails) 
    # might be caught here if explicit validation above is skipped or passes unexpectedly.
    # It would result in a 500 error unless specifically caught.
    except Exception as e:
        error_msg = f"Unexpected error creating data product: {e!s}"
        logger.exception(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

# --- Dynamic ID Endpoints (MUST BE LAST) --- 

@router.get('/data-products/{product_id}', response_model=Any)
async def get_data_product(
    product_id: str,
    manager: DataProductsManager = Depends(get_data_products_manager),
    _: bool = Depends(PermissionChecker('data-products', FeatureAccessLevel.READ_ONLY))
) -> Any: # Return Any to allow returning a dict
    """Gets a single data product by its ID."""
    try:
        product = manager.get_product(product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Data product not found")
        return product.model_dump(exclude={'created_at', 'updated_at'}, exclude_none=True, exclude_unset=True)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception(f"Unexpected error fetching product {product_id}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put('/data-products/{product_id}', response_model=DataProduct)
async def update_data_product(
    product_id: str,
    product_data: DataProduct = Body(...),
    manager: DataProductsManager = Depends(get_data_products_manager),
    _: bool = Depends(PermissionChecker('data-products', FeatureAccessLevel.READ_WRITE))
):
    """Update an existing data product using a JSON payload conforming to the schema."""
    if product_id != product_data.id:
         raise HTTPException(status_code=400, detail="Product ID in path does not match ID in request body.")

    try:
        logger.info(f"Received request to update data product ID: {product_id}")
        
        product_dict = product_data.model_dump(by_alias=True)
        
        updated_product = manager.update_product(product_id, product_dict)
        if not updated_product:
            logger.warning(f"Update failed: Data product not found with ID: {product_id}")
            raise HTTPException(status_code=404, detail="Data product not found")

        logger.info(f"Successfully updated data product with ID: {product_id}")
        return updated_product
    except ValueError as e: # Catch validation errors from manager
        logger.error(f"Validation error during product update for ID {product_id}: {e!s}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException: # Re-raise specific HTTP exceptions
        raise
    except Exception as e:
        error_msg = f"Unexpected error updating data product {product_id}: {e!s}"
        logger.exception(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@router.delete('/data-products/{product_id}', status_code=204) # No content response
async def delete_data_product(
    product_id: str,
    manager: DataProductsManager = Depends(get_data_products_manager),
    _: bool = Depends(PermissionChecker('data-products', FeatureAccessLevel.ADMIN)) # Require ADMIN to delete
):
    """Delete a data product by ID."""
    try:
        logger.info(f"Received request to delete data product ID: {product_id}")
        deleted = manager.delete_product(product_id)
        if not deleted:
            logger.warning(f"Deletion failed: Data product not found with ID: {product_id}")
            raise HTTPException(status_code=404, detail="Data product not found")

        logger.info(f"Successfully deleted data product with ID: {product_id}")
        return None 
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Unexpected error deleting data product {product_id}: {e!s}"
        logger.exception(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

# --- Genie Space Endpoint --- 
@router.post("/data-products/genie-space", status_code=202)
async def create_genie_space_from_products(
    request_body: GenieSpaceRequest,
    current_user: CurrentUserDep, # Moved up, no default value
    db: DBSessionDep, # Inject the database session
    manager: DataProductsManager = Depends(get_data_products_manager), # Has default
    _: bool = Depends(PermissionChecker('data-products', FeatureAccessLevel.READ_WRITE)) # Has default
):
    """
    Initiates the (simulated) creation of a Databricks Genie Space 
    based on selected Data Products.
    """
    if not request_body.product_ids:
        raise HTTPException(status_code=400, detail="No product IDs provided.")

    try:
        # Call the manager method to start the process, passing the db session and user info
        await manager.initiate_genie_space_creation(request_body, current_user, db=db) # Pass full current_user object
        return {"message": "Genie Space creation process initiated. You will be notified upon completion."}
    except RuntimeError as e:
        logger.error(f"Runtime error initiating Genie Space creation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error initiating Genie Space creation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to initiate Genie Space creation.")

# Function to register routes (if used elsewhere)
def register_routes(app):
    """Register routes with the FastAPI app."""
    app.include_router(router)
    logger.info("Data product routes registered")
