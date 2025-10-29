import os
from pathlib import Path
from typing import List, Dict, Any, Optional

import yaml
from fastapi import APIRouter, HTTPException, UploadFile, File, Body, Depends, Request, BackgroundTasks
from pydantic import ValidationError
import json
import uuid
from sqlalchemy.orm import Session

from src.controller.data_products_manager import DataProductsManager
from src.models.data_products import DataProduct, GenieSpaceRequest, NewVersionRequest
from src.models.users import UserInfo
from databricks.sdk.errors import PermissionDenied

from src.common.authorization import PermissionChecker, ApprovalChecker
from src.common.features import FeatureAccessLevel
from src.common.file_security import sanitize_filename

from src.common.dependencies import (
    CurrentUserDep,
    DBSessionDep,
    AuditManagerDep,
    AuditCurrentUserDep
)
from src.controller.change_log_manager import change_log_manager
from src.models.notifications import NotificationType
from src.common.dependencies import NotificationsManagerDep, CurrentUserDep, DBSessionDep

from src.common.logging import get_logger
logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["data-products"])

DATA_PRODUCTS_FEATURE_ID = "data-products"

def get_data_products_manager(
    request: Request # Inject Request
) -> DataProductsManager:
    manager = getattr(request.app.state, 'data_products_manager', None)
    if manager is None:
         logger.critical("DataProductsManager instance not found in app.state!")
         raise HTTPException(status_code=500, detail="Data Products service is not available.")
    if not isinstance(manager, DataProductsManager):
        logger.critical(f"Object found at app.state.data_products_manager is not a DataProductsManager instance (Type: {type(manager)})!")
        raise HTTPException(status_code=500, detail="Data Products service configuration error.")
    return manager


# --- Lifecycle transitions (minimal) ---

@router.post('/data-products/{product_id}/submit-certification')
async def submit_product_certification(
    product_id: str,
    request: Request,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: AuditCurrentUserDep,
    _: bool = Depends(PermissionChecker(DATA_PRODUCTS_FEATURE_ID, FeatureAccessLevel.READ_WRITE))
):
    try:
        from src.db_models.data_products import DataProductDb
        product = db.query(DataProductDb).filter(DataProductDb.id == product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Data product not found")
        # ODPS v1.0.0: Use status field directly (proposed, draft, active, deprecated, retired)
        cur = (product.status or '').lower()
        if cur != 'draft':
            raise HTTPException(status_code=409, detail=f"Invalid transition from {product.status} to active (certification)")
        product.status = 'active'  # ODPS: certification moves draft to active
        db.add(product)
        db.flush()
        audit_manager.log_action(
            db=db,
            username=current_user.username,
            ip_address=request.client.host if request.client else None,
            feature=DATA_PRODUCTS_FEATURE_ID,
            action='SUBMIT_CERTIFICATION',
            success=True,
            details={ 'product_id': product_id, 'from': cur, 'to': product.status }
        )
        return { 'status': product.status }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Submit product certification failed for product_id=%s", product_id)
        raise HTTPException(status_code=500, detail="Failed to submit product certification")


@router.post('/data-products/{product_id}/certify')
async def certify_product(
    product_id: str,
    request: Request,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: AuditCurrentUserDep,
    _: bool = Depends(ApprovalChecker('PRODUCTS'))
):
    try:
        from src.db_models.data_products import DataProductDb
        product = db.query(DataProductDb).filter(DataProductDb.id == product_id).first()
        if not product or not product.info:
            raise HTTPException(status_code=404, detail="Data product not found")
        cur = (product.info.status or '').upper()
        if cur != 'PENDING_CERTIFICATION':
            raise HTTPException(status_code=409, detail=f"Invalid transition from {product.info.status} to CERTIFIED")
        product.info.status = 'CERTIFIED'
        db.add(product.info)
        db.flush()
        audit_manager.log_action(
            db=db,
            username=current_user.username,
            ip_address=request.client.host if request.client else None,
            feature=DATA_PRODUCTS_FEATURE_ID,
            action='CERTIFY',
            success=True,
            details={ 'product_id': product_id, 'from': cur, 'to': product.info.status }
        )
        return { 'status': product.info.status }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Certify product failed for product_id=%s", product_id)
        raise HTTPException(status_code=500, detail="Failed to certify product")


@router.post('/data-products/{product_id}/reject-certification')
async def reject_product_certification(
    product_id: str,
    request: Request,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: AuditCurrentUserDep,
    _: bool = Depends(ApprovalChecker('PRODUCTS'))
):
    try:
        from src.db_models.data_products import DataProductDb
        product = db.query(DataProductDb).filter(DataProductDb.id == product_id).first()
        if not product or not product.info:
            raise HTTPException(status_code=404, detail="Data product not found")
        cur = (product.info.status or '').upper()
        if cur != 'PENDING_CERTIFICATION':
            raise HTTPException(status_code=409, detail=f"Invalid transition from {product.info.status} to SANDBOX")
        product.info.status = 'SANDBOX'
        db.add(product.info)
        db.flush()
        audit_manager.log_action(
            db=db,
            username=current_user.username,
            ip_address=request.client.host if request.client else None,
            feature=DATA_PRODUCTS_FEATURE_ID,
            action='REJECT_CERTIFICATION',
            success=True,
            details={ 'product_id': product_id, 'from': cur, 'to': product.info.status }
        )
        return { 'status': product.info.status }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Reject product certification failed for product_id=%s", product_id)
        raise HTTPException(status_code=500, detail="Failed to reject product certification")


@router.post('/data-products/{product_id}/publish')
async def publish_product(
    product_id: str,
    request: Request,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: AuditCurrentUserDep,
    _: bool = Depends(PermissionChecker(DATA_PRODUCTS_FEATURE_ID, FeatureAccessLevel.READ_WRITE))
):
    """
    Publish a certified product to make it active and available in the marketplace.

    Validates that all output ports have dataContractId set before allowing publication.
    """
    try:
        from src.db_models.data_products import DataProductDb
        product = db.query(DataProductDb).filter(DataProductDb.id == product_id).first()
        if not product or not product.info:
            raise HTTPException(status_code=404, detail="Data product not found")

        cur = (product.info.status or '').upper()
        if cur != 'CERTIFIED':
            raise HTTPException(
                status_code=409,
                detail=f"Invalid transition from {product.info.status} to ACTIVE. Product must be CERTIFIED first."
            )

        # Validate that all output ports have contracts
        if product.outputPorts:
            ports_without_contracts = [
                port.name for port in product.outputPorts
                if not port.dataContractId
            ]
            if ports_without_contracts:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot publish product: Output ports {', '.join(ports_without_contracts)} must have data contracts assigned"
                )

        product.info.status = 'ACTIVE'
        db.add(product.info)
        db.flush()

        audit_manager.log_action(
            db=db,
            username=current_user.username,
            ip_address=request.client.host if request.client else None,
            feature=DATA_PRODUCTS_FEATURE_ID,
            action='PUBLISH',
            success=True,
            details={'product_id': product_id, 'from': cur, 'to': product.info.status}
        )

        return {'status': product.info.status}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Publish product failed for product_id=%s", product_id)
        raise HTTPException(status_code=500, detail="Failed to publish product")


@router.post('/data-products/{product_id}/deprecate')
async def deprecate_product(
    product_id: str,
    request: Request,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: AuditCurrentUserDep,
    _: bool = Depends(PermissionChecker(DATA_PRODUCTS_FEATURE_ID, FeatureAccessLevel.READ_WRITE))
):
    """
    Deprecate an active product to signal it will be retired soon.
    """
    try:
        from src.db_models.data_products import DataProductDb
        product = db.query(DataProductDb).filter(DataProductDb.id == product_id).first()
        if not product or not product.info:
            raise HTTPException(status_code=404, detail="Data product not found")

        cur = (product.info.status or '').upper()
        if cur != 'ACTIVE':
            raise HTTPException(
                status_code=409,
                detail=f"Invalid transition from {product.info.status} to DEPRECATED. Only ACTIVE products can be deprecated."
            )

        product.info.status = 'DEPRECATED'
        db.add(product.info)
        db.flush()

        audit_manager.log_action(
            db=db,
            username=current_user.username,
            ip_address=request.client.host if request.client else None,
            feature=DATA_PRODUCTS_FEATURE_ID,
            action='DEPRECATE',
            success=True,
            details={'product_id': product_id, 'from': cur, 'to': product.info.status}
        )

        return {'status': product.info.status}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Deprecate product failed for product_id=%s", product_id)
        raise HTTPException(status_code=500, detail="Failed to deprecate product")

# --- Contract-Product Integration Endpoints ---

@router.post('/data-products/from-contract', response_model=DataProduct, status_code=201)
async def create_product_from_contract(
    contract_id: str = Body(..., embed=True),
    product_name: str = Body(..., embed=True),
    product_type: str = Body(..., embed=True),
    version: str = Body(..., embed=True),
    output_port_name: Optional[str] = Body(None, embed=True),
    request: Request = None,
    db: DBSessionDep = None,
    audit_manager: AuditManagerDep = None,
    current_user: AuditCurrentUserDep = None,
    manager: DataProductsManager = Depends(get_data_products_manager),
    _: bool = Depends(PermissionChecker(DATA_PRODUCTS_FEATURE_ID, FeatureAccessLevel.READ_WRITE))
):
    """
    Create a new Data Product from an existing Data Contract.

    The contract governs one output port of the product. Inherits domain_id,
    owner_team_id, and project_id from the contract.
    """
    try:
        from src.models.data_products import DataProductType

        # Convert product_type string to enum
        try:
            product_type_enum = DataProductType(product_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid product_type: {product_type}. Must be one of: {[t.value for t in DataProductType]}"
            )

        # Create product via manager
        created_product = manager.create_from_contract(
            contract_id=contract_id,
            product_name=product_name,
            product_type=product_type_enum,
            version=version,
            output_port_name=output_port_name
        )

        # Log audit event
        audit_manager.log_action(
            db=db,
            username=current_user.username,
            ip_address=request.client.host if request.client else None,
            feature=DATA_PRODUCTS_FEATURE_ID,
            action='CREATE_FROM_CONTRACT',
            success=True,
            details={
                'product_id': created_product.id,
                'contract_id': contract_id,
                'product_name': product_name,
                'product_type': product_type
            }
        )

        logger.info(f"Created Data Product {created_product.id} from contract {contract_id}")
        return created_product

    except ValueError as e:
        logger.error("Validation error creating product from contract %s: %s", contract_id, e)
        raise HTTPException(status_code=400, detail="Invalid contract data for product creation")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error creating product from contract {contract_id}")
        raise HTTPException(status_code=500, detail=f"Failed to create product from contract: {str(e)}")


@router.get('/data-products/by-contract/{contract_id}', response_model=List[DataProduct])
async def get_products_by_contract(
    contract_id: str,
    manager: DataProductsManager = Depends(get_data_products_manager),
    _: bool = Depends(PermissionChecker(DATA_PRODUCTS_FEATURE_ID, FeatureAccessLevel.READ_ONLY))
):
    """
    Get all Data Products that use a specific Data Contract.

    Returns products that have output ports linked to the specified contract.
    """
    try:
        products = manager.get_products_by_contract(contract_id)
        logger.info(f"Found {len(products)} products for contract {contract_id}")
        return products
    except Exception as e:
        logger.exception(f"Error getting products for contract {contract_id}")
        raise HTTPException(status_code=500, detail=f"Failed to get products for contract: {str(e)}")


@router.get('/data-products/{product_id}/contracts', response_model=List[str])
async def get_contracts_for_product(
    product_id: str,
    manager: DataProductsManager = Depends(get_data_products_manager),
    _: bool = Depends(PermissionChecker(DATA_PRODUCTS_FEATURE_ID, FeatureAccessLevel.READ_ONLY))
):
    """
    Get all Data Contract IDs associated with a Data Product's output ports.

    Returns a list of contract IDs (may be empty if no contracts are linked).
    """
    try:
        contract_ids = manager.get_contracts_for_product(product_id)
        logger.info(f"Found {len(contract_ids)} contracts for product {product_id}")
        return contract_ids
    except ValueError as e:
        logger.error("Product not found %s: %s", product_id, e)
        raise HTTPException(status_code=404, detail="Product not found")
    except Exception as e:
        logger.exception(f"Error getting contracts for product {product_id}")
        raise HTTPException(status_code=500, detail=f"Failed to get contracts for product: {str(e)}")

# --- Utility Endpoints ---

@router.get('/data-products/statuses', response_model=List[str])
async def get_data_product_statuses(
    manager: DataProductsManager = Depends(get_data_products_manager),
    _: bool = Depends(PermissionChecker(DATA_PRODUCTS_FEATURE_ID, FeatureAccessLevel.READ_ONLY))
):
    try:
        statuses = manager.get_distinct_statuses()
        logger.info(f"Retrieved {len(statuses)} distinct data product statuses")
        return statuses
    except Exception as e:
        error_msg = f"Error retrieving data product statuses: {e!s}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@router.get('/data-products/types', response_model=List[str])
async def get_data_product_types(
    manager: DataProductsManager = Depends(get_data_products_manager),
    _: bool = Depends(PermissionChecker(DATA_PRODUCTS_FEATURE_ID, FeatureAccessLevel.READ_ONLY))
):
    try:
        types = manager.get_distinct_product_types()
        logger.info(f"Retrieved {len(types)} distinct data product types")
        return types
    except Exception as e:
        error_msg = f"Error retrieving data product types: {e!s}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@router.get('/data-products/owners', response_model=List[str])
async def get_data_product_owners(
    manager: DataProductsManager = Depends(get_data_products_manager),
    _: bool = Depends(PermissionChecker(DATA_PRODUCTS_FEATURE_ID, FeatureAccessLevel.READ_ONLY))
):
    try:
        owners = manager.get_distinct_owners()
        logger.info(f"Retrieved {len(owners)} distinct data product owners")
        return owners
    except Exception as e:
        error_msg = f"Error retrieving data product owners: {e!s}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@router.get('/data-products/published', response_model=List[DataProduct])
async def get_published_products(
    manager: DataProductsManager = Depends(get_data_products_manager),
    _: bool = Depends(PermissionChecker(DATA_PRODUCTS_FEATURE_ID, FeatureAccessLevel.READ_ONLY))
):
    """
    Get all published (ACTIVE status) data products for marketplace/discovery.

    Returns only products that are in ACTIVE status, meaning they have been:
    - Certified
    - Published (all output ports have contracts)
    - Made available for consumption
    """
    try:
        # Get all products
        all_products = manager.list_products(limit=10000)

        # Filter to only ACTIVE products
        published_products = [
            product for product in all_products
            if product.info and product.info.status and product.info.status.upper() == 'ACTIVE'
        ]

        logger.info(f"Retrieved {len(published_products)} published data products (ACTIVE status)")
        return published_products
    except Exception as e:
        error_msg = f"Error retrieving published data products: {e!s}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@router.post("/data-products/upload", response_model=List[DataProduct], status_code=201)
async def upload_data_products(
    request: Request, 
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: AuditCurrentUserDep,
    file: UploadFile = File(...),
    manager: DataProductsManager = Depends(get_data_products_manager),
    _: bool = Depends(PermissionChecker(DATA_PRODUCTS_FEATURE_ID, FeatureAccessLevel.READ_WRITE))
):
    # SECURITY: Sanitize filename for safe logging and validation
    raw_filename = file.filename or "upload.bin"
    safe_filename = sanitize_filename(raw_filename, default="upload.bin")
    
    # Validate file extension using sanitized filename
    if not (safe_filename.lower().endswith('.yaml') or safe_filename.lower().endswith('.json')):
        audit_manager.log_action(
            db=db,
            username=current_user.username,
            ip_address=request.client.host if request.client else None,
            feature=DATA_PRODUCTS_FEATURE_ID,
            action="UPLOAD",
            success=False,
            details={
                "filename": safe_filename,
                "error": "Invalid file type",
                "params": { "filename_in_request": safe_filename },
                "response_status_code": 400
            }
        )
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a YAML or JSON file.")

    success = False
    response_status_code = 500
    created_products_for_response: List[DataProduct] = []
    processing_errors_for_audit: List[Dict[str, Any]] = []
    created_ids_for_audit: List[str] = []

    details_for_audit = {
        "filename": safe_filename,
        "params": { "filename_in_request": safe_filename },
    }

    try:
        content = await file.read()
        if safe_filename.lower().endswith('.yaml'):
            data = yaml.safe_load(content)
        else:
            import json
            data = json.loads(content)
            
        data_list: List[Dict[str, Any]]
        if isinstance(data, dict):
            data_list = [data]
        elif isinstance(data, list):
            data_list = data
        else:
            response_status_code = 400
            exc = HTTPException(status_code=response_status_code, detail="File must contain a JSON object/array or a YAML mapping/list of data product objects.")
            details_for_audit["exception"] = {"type": "HTTPException", "status_code": exc.status_code, "detail": exc.detail}
            raise exc

        errors_for_response_detail = [] 
        for product_data in data_list:
             if not isinstance(product_data, dict):
                 err_detail = {"error": "Skipping non-dictionary item within list/array.", "item_preview": str(product_data)[:100]}
                 errors_for_response_detail.append(err_detail)
                 processing_errors_for_audit.append(err_detail)
                 continue
             
             product_id_in_data = product_data.get('id')
             
             try:
                 if not product_id_in_data:
                     generated_id = str(uuid.uuid4())
                     product_data['id'] = generated_id
                     logger.info(f"Generated ID {generated_id} for uploaded product lacking one.")
                     product_id_in_data = generated_id 
                 
                 if product_id_in_data and manager.get_product(product_id_in_data):
                     err_detail = {"id": product_id_in_data, "error": "Product with this ID already exists. Skipping."}
                     errors_for_response_detail.append(err_detail)
                     processing_errors_for_audit.append(err_detail)
                     continue
                 
                 try:
                    _ = DataProduct(**product_data)
                 except ValidationError as e_val:
                     logger.error(f"Validation failed for uploaded product (ID: {product_id_in_data}): {e_val}")
                     err_detail = {"id": product_id_in_data, "error": f"Validation failed: {e_val.errors() if hasattr(e_val, 'errors') else str(e_val)}"}
                     errors_for_response_detail.append(err_detail)
                     processing_errors_for_audit.append(err_detail)
                     continue 

                 created_product = manager.create_product(product_data)
                 created_products_for_response.append(created_product)
                 if created_product and hasattr(created_product, 'id'):
                    created_ids_for_audit.append(str(created_product.id))
                 
             except Exception as e_item:
                 error_id_for_log = product_id_in_data if product_id_in_data else 'N/A_CreationFailure'
                 err_detail = {"id": error_id_for_log, "error": f"Creation failed: {e_item!s}"}
                 errors_for_response_detail.append(err_detail)
                 processing_errors_for_audit.append(err_detail)

        if errors_for_response_detail:
            success = False
            response_status_code = 422 
            logger.warning(f"Encountered {len(errors_for_response_detail)} errors during file upload processing.")
            raise HTTPException(
                status_code=response_status_code, 
                detail={"message": "Validation or creation errors occurred during upload.", "errors": errors_for_response_detail}
            )
        
        success = True
        response_status_code = 201
        logger.info(f"Successfully created {len(created_products_for_response)} data products from uploaded file {safe_filename}")
        return created_products_for_response

    except yaml.YAMLError as e_yaml:
        success = False
        response_status_code = 400
        details_for_audit["exception"] = {"type": "YAMLError", "message": str(e_yaml)}
        raise HTTPException(status_code=response_status_code, detail=f"Invalid YAML format: {e_yaml}")
    except json.JSONDecodeError as e_json:
        success = False
        response_status_code = 400
        details_for_audit["exception"] = {"type": "JSONDecodeError", "message": str(e_json)}
        raise HTTPException(status_code=response_status_code, detail=f"Invalid JSON format: {e_json}")
    except HTTPException as http_exc:
        if response_status_code != 422 and response_status_code != 400 :
            success = False
        response_status_code = http_exc.status_code
        if "exception" not in details_for_audit:
            details_for_audit["exception"] = {"type": "HTTPException", "status_code": http_exc.status_code, "detail": http_exc.detail}
        raise
    except Exception as e_general:
        success = False
        response_status_code = 500 
        error_msg = f"Unexpected error processing uploaded file: {e_general!s}"
        details_for_audit["exception"] = {"type": type(e_general).__name__, "message": str(e_general)}
        logger.exception(error_msg)
        raise HTTPException(status_code=response_status_code, detail=error_msg)
    finally:
        if "exception" not in details_for_audit and not success:
             details_for_audit["processing_summary"] = "One or more items failed processing but no overarching exception was raised."
        elif "exception" not in details_for_audit and success:
             details_for_audit["response_status_code"] = response_status_code

        if created_ids_for_audit:
            details_for_audit["created_resource_ids"] = created_ids_for_audit
        if processing_errors_for_audit:
            details_for_audit["item_processing_errors"] = processing_errors_for_audit
        
        audit_manager.log_action(
            db=db,
            username=current_user.username,
            ip_address=request.client.host if request.client else None,
            feature=DATA_PRODUCTS_FEATURE_ID,
            action="UPLOAD_BATCH",
            success=success,
            details=details_for_audit,
        )

@router.get('/data-products', response_model=Any)
async def get_data_products(
    manager: DataProductsManager = Depends(get_data_products_manager),
    _: bool = Depends(PermissionChecker(DATA_PRODUCTS_FEATURE_ID, FeatureAccessLevel.READ_ONLY))
):
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
    request: Request,
    background_tasks: BackgroundTasks,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: AuditCurrentUserDep,
    payload: Dict[str, Any] = Body(...),
    manager: DataProductsManager = Depends(get_data_products_manager),
    _: bool = Depends(PermissionChecker(DATA_PRODUCTS_FEATURE_ID, FeatureAccessLevel.READ_WRITE))
):
    success = False
    details_for_audit = {
        "params": {"product_id_in_payload": payload.get('id', 'N/A_PreCreate')},
    }
    created_product_response = None

    try:
        logger.info(f"Received raw payload for creation: {payload}")
        product_id = payload.get('id')

        if product_id and manager.get_product(product_id):
            raise HTTPException(status_code=409, detail=f"Data product with ID {product_id} already exists.")

        if not product_id:
            generated_id = str(uuid.uuid4())
            payload['id'] = generated_id
            details_for_audit["params"]["generated_product_id"] = generated_id
            logger.info(f"Generated ID for new product: {payload['id']}")

        try:
            validated_model = DataProduct(**payload)
        except ValidationError as e:
            logger.error(f"Validation failed for payload (ID: {payload.get('id', 'N/A_Validation')}): {e}")
            error_details = e.errors() if hasattr(e, 'errors') else str(e)
            details_for_audit["validation_error"] = error_details
            raise HTTPException(status_code=422, detail=error_details)

        created_product_response = manager.create_product(payload)
        success = True

        if created_product_response and hasattr(created_product_response, 'id'):
            details_for_audit["created_resource_id"] = str(created_product_response.id)

        logger.info(f"Successfully created data product with ID: {created_product_response.id if created_product_response else payload.get('id')}")
        return created_product_response

    except HTTPException as http_exc:
        details_for_audit["exception"] = {"type": "HTTPException", "status_code": http_exc.status_code, "detail": http_exc.detail}
        raise
    except Exception as e:
        error_msg = f"Unexpected error creating data product (ID: {payload.get('id', 'N/A_Exception')}): {e!s}"
        logger.exception(error_msg)
        details_for_audit["exception"] = {"type": type(e).__name__, "message": str(e)}
        raise HTTPException(status_code=500, detail=error_msg)
    finally:
        background_tasks.add_task(
            audit_manager.log_action_background,
            username=current_user.username,
            ip_address=request.client.host if request.client else None,
            feature=DATA_PRODUCTS_FEATURE_ID,
            action="CREATE",
            success=success,
            details=details_for_audit.copy()
        )

@router.post("/data-products/{product_id}/versions", response_model=DataProduct, status_code=201)
async def create_data_product_version(
    product_id: str, # This is the original product ID
    request: Request, 
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: AuditCurrentUserDep,
    version_request: NewVersionRequest = Body(...), # Ensure Body is used if it was intended
    manager: DataProductsManager = Depends(get_data_products_manager),
    _: bool = Depends(PermissionChecker(DATA_PRODUCTS_FEATURE_ID, FeatureAccessLevel.READ_WRITE))
):
    success = False
    response_status_code = 500
    details_for_audit = {
        "params": {"original_product_id": product_id, "requested_new_version": version_request.new_version},
    }
    new_product_response = None

    try:
        logger.info(f"Received request to create version '{version_request.new_version}' from product ID: {product_id}")
        # The manager method handles its own DB interactions
        new_product_response = manager.create_new_version(product_id, version_request.new_version)
        
        # request.state.audit_created_resource_id is no longer needed here as we capture it below
        
        success = True
        response_status_code = 201
        logger.info(f"Successfully created new version ID: {new_product_response.id} from original product ID: {product_id}")
        return new_product_response

    except ValueError as ve:
        success = False
        # Determine status code based on error message content, or default to 400/404
        response_status_code = 404 if "not found" in str(ve).lower() else 400
        details_for_audit["exception"] = {"type": "ValueError", "status_code": response_status_code, "message": str(ve)}
        logger.error(f"Value error creating version for {product_id}: {ve!s}")
        raise HTTPException(status_code=response_status_code, detail=str(ve))
    except HTTPException as http_exc: # Should come after more specific exceptions if they might raise HTTPExceptions
        success = False
        response_status_code = http_exc.status_code
        details_for_audit["exception"] = {"type": "HTTPException", "status_code": http_exc.status_code, "detail": http_exc.detail}
        raise
    except Exception as e:
        success = False
        response_status_code = 500
        error_msg = f"Unexpected error creating version for data product {product_id}: {e!s}"
        details_for_audit["exception"] = {"type": type(e).__name__, "message": str(e)}
        logger.exception(error_msg)
        raise HTTPException(status_code=response_status_code, detail=error_msg)
    finally:
        if "exception" not in details_for_audit:
             details_for_audit["response_status_code"] = response_status_code
        
        if success and new_product_response and hasattr(new_product_response, 'id'):
            details_for_audit["created_version_id"] = str(new_product_response.id)
        
        audit_manager.log_action(
            db=db,
            username=current_user.username,
            ip_address=request.client.host if request.client else None,
            feature=DATA_PRODUCTS_FEATURE_ID,
            action="CREATE_VERSION", # Specific action type
            success=success,
            details=details_for_audit,
        )

@router.put('/data-products/{product_id}', response_model=DataProduct)
async def update_data_product(
    product_id: str,
    request: Request,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: AuditCurrentUserDep,
    background_tasks: BackgroundTasks,
    manager: DataProductsManager = Depends(get_data_products_manager),
    _: bool = Depends(PermissionChecker(DATA_PRODUCTS_FEATURE_ID, FeatureAccessLevel.READ_WRITE))
):
    # --- Manually read and validate body ---
    try:
        body_dict = await request.json()
        product_update = DataProduct(**body_dict)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON body.")
    except ValidationError as e:
        logger.error(f"Validation failed for PUT request body (ID: {product_id}): {e}")
        raise HTTPException(status_code=422, detail=e.errors())
    # --------------------------------------

    if product_id != product_update.id:
        exc = HTTPException(status_code=400, detail="Product ID in path does not match ID in request body.")
        audit_manager.log_action(
            db=db,
            username=current_user.username,
            ip_address=request.client.host if request.client else None,
            feature=DATA_PRODUCTS_FEATURE_ID,
            action="UPDATE",
            success=False, 
            details={"error": "mismatch id"}
        )
        raise exc

    success = False
    response_status_code = 500 
    details_for_audit = {
        "params": {"product_id": product_id},
    }
    updated_product_response = None
    exception_details = None

    try:
        logger.info(f"Received request to update data product ID: {product_id}")
        
        # Get existing product to check project membership
        from src.repositories.data_products_repository import data_product_repo
        existing_product = data_product_repo.get(db, id=product_id)
        if not existing_product:
            response_status_code = 404
            exc = HTTPException(status_code=response_status_code, detail="Data product not found")
            details_for_audit["exception"] = {"type": "HTTPException", "status_code": exc.status_code, "detail": exc.detail}
            logger.warning(f"Update failed: Data product not found with ID: {product_id}")
            raise exc
        
        # Check project membership if product belongs to a project
        if existing_product.project_id:
            from src.controller.projects_manager import projects_manager
            from src.common.config import get_settings
            user_groups = current_user.groups or []
            settings = get_settings()
            is_member = projects_manager.is_user_project_member(
                db=db,
                user_identifier=current_user.email,
                user_groups=user_groups,
                project_id=existing_product.project_id,
                settings=settings
            )
            if not is_member:
                response_status_code = 403
                exc = HTTPException(
                    status_code=response_status_code,
                    detail="You must be a member of the project to edit this data product"
                )
                details_for_audit["exception"] = {"type": "HTTPException", "status_code": exc.status_code, "detail": exc.detail}
                raise exc
        
        # Use the manually validated model 
        product_dict = product_update.model_dump(by_alias=True)
        
        updated_product_response = manager.update_product(product_id, product_dict)

        if not updated_product_response:
            response_status_code = 404
            exc = HTTPException(status_code=response_status_code, detail="Data product not found")
            details_for_audit["exception"] = {"type": "HTTPException", "status_code": exc.status_code, "detail": exc.detail}
            logger.warning(f"Update failed: Data product not found with ID: {product_id}")
            raise exc

        success = True
        response_status_code = 200 
        logger.info(f"Successfully updated data product with ID: {product_id}")
        return updated_product_response

    except HTTPException as http_exc:
        success = False
        response_status_code = http_exc.status_code
        exception_details = {"type": "HTTPException", "status_code": http_exc.status_code, "detail": http_exc.detail}
        raise
    except ValueError as ve:
        success = False
        response_status_code = 400
        exception_details = {"type": "ValueError", "message": str(ve)}
        raise HTTPException(status_code=response_status_code, detail=str(ve))
    except Exception as e:
        success = False
        response_status_code = 500
        error_msg = f"Unexpected error updating data product {product_id}: {e!s}"
        exception_details = {"type": type(e).__name__, "message": str(e)}
        logger.exception(error_msg)
        raise HTTPException(status_code=response_status_code, detail=error_msg)
    finally:
        if exception_details:
            details_for_audit["exception"] = exception_details
        else:
             details_for_audit["response_status_code"] = response_status_code
        
        if success and updated_product_response and hasattr(updated_product_response, 'id'):
            details_for_audit["updated_resource_id"] = str(updated_product_response.id)

        background_tasks.add_task(
            audit_manager.log_action_background,
            username=current_user.username,
            ip_address=request.client.host if request.client else None,
            feature=DATA_PRODUCTS_FEATURE_ID,
            action="UPDATE",
            success=success,
            details=details_for_audit.copy()
        )

@router.delete('/data-products/{product_id}', status_code=204) 
async def delete_data_product(
    product_id: str,
    request: Request, 
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: AuditCurrentUserDep,
    manager: DataProductsManager = Depends(get_data_products_manager),
    _: bool = Depends(PermissionChecker(DATA_PRODUCTS_FEATURE_ID, FeatureAccessLevel.ADMIN))
):
    success = False
    response_status_code = 500 # Default for audit in case of unexpected server error
    details_for_audit = {
        "params": {"product_id": product_id},
        # For delete, body_preview is not applicable from route args
    }

    try:
        logger.info(f"Received request to delete data product ID: {product_id}")
        deleted = manager.delete_product(product_id)
        if not deleted:
            response_status_code = 404
            exc = HTTPException(status_code=response_status_code, detail="Data product not found")
            details_for_audit["exception"] = {"type": "HTTPException", "status_code": exc.status_code, "detail": exc.detail}
            logger.warning(f"Deletion failed: Data product not found with ID: {product_id}")
            raise exc

        success = True
        response_status_code = 204 # Standard for successful DELETE
        logger.info(f"Successfully deleted data product with ID: {product_id}")
        # No response body for 204, so no updated_product_response or response_preview
        return None 

    except HTTPException as http_exc:
        success = False
        response_status_code = http_exc.status_code
        details_for_audit["exception"] = {"type": "HTTPException", "status_code": http_exc.status_code, "detail": http_exc.detail}
        raise
    except Exception as e:
        success = False
        response_status_code = 500 
        error_msg = f"Unexpected error deleting data product {product_id}: {e!s}"
        details_for_audit["exception"] = {"type": type(e).__name__, "message": str(e)}
        logger.exception(error_msg)
        raise HTTPException(status_code=response_status_code, detail=error_msg)
    finally:
        if "exception" not in details_for_audit:
             details_for_audit["response_status_code"] = response_status_code
        
        # For delete, we can confirm the ID of the resource that was targeted for deletion.
        details_for_audit["deleted_resource_id_attempted"] = product_id

        audit_manager.log_action(
            db=db,
            username=current_user.username,
            ip_address=request.client.host if request.client else None,
            feature=DATA_PRODUCTS_FEATURE_ID,
            action="DELETE",
            success=success,
            details=details_for_audit,
        )

@router.get('/data-products/{product_id}', response_model=Any)
async def get_data_product(
    product_id: str,
    manager: DataProductsManager = Depends(get_data_products_manager),
    _: bool = Depends(PermissionChecker(DATA_PRODUCTS_FEATURE_ID, FeatureAccessLevel.READ_ONLY))
) -> Any: # Return Any to allow returning a dict
    try:
        product = manager.get_product(product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Data product not found")
        return product.model_dump(by_alias=False, exclude={'created_at', 'updated_at'}, exclude_none=True, exclude_unset=True)
    except ValueError as e:
        logger.error("Validation error fetching product %s: %s", product_id, e)
        raise HTTPException(status_code=404, detail="Data product not found")
    except Exception as e:
        logger.exception(f"Unexpected error fetching product {product_id}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/data-products/genie-space", status_code=202)
async def create_genie_space_from_products(
    request_body: GenieSpaceRequest,
    current_user: CurrentUserDep, # Moved up, no default value
    db: DBSessionDep, # Inject the database session
    manager: DataProductsManager = Depends(get_data_products_manager), # Has default
    _: bool = Depends(PermissionChecker(DATA_PRODUCTS_FEATURE_ID, FeatureAccessLevel.READ_WRITE)) # Has default
):
    if not request_body.product_ids:
        raise HTTPException(status_code=400, detail="No product IDs provided.")

    try:
        await manager.initiate_genie_space_creation(request_body, current_user, db=db)
        return {"message": "Genie Space creation process initiated. You will be notified upon completion."}
    except RuntimeError as e:
        logger.error("Runtime error initiating Genie Space creation", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to initiate Genie Space creation")
    except Exception as e:
        logger.error(f"Unexpected error initiating Genie Space creation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to initiate Genie Space creation.")

@router.get('/data-products/{product_id}/import-team-members', response_model=list)
async def get_team_members_for_import(
    product_id: str,
    team_id: str,
    request: Request,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: AuditCurrentUserDep,
    manager: DataProductsManager = Depends(get_data_products_manager),
    _: bool = Depends(PermissionChecker(DATA_PRODUCTS_FEATURE_ID, FeatureAccessLevel.READ_WRITE))
):
    """Get team members formatted for import into product ODPS team array.
    
    Route handler: parses parameters, audits request, delegates to manager, returns response.
    All business logic is in the manager.
    """
    success = False
    members = []
    try:
        # Delegate business logic to manager
        members = manager.get_team_members_for_import(
            product_id=product_id,
            team_id=team_id,
            current_user=current_user.username if current_user else None
        )
        
        success = True
        return members
        
    except ValueError as e:
        logger.error("Validation error fetching team members for product %s: %s", product_id, e)
        raise HTTPException(status_code=404, detail="Product or team not found")
    except Exception as e:
        logger.error("Error fetching team members for import for product %s", product_id, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch team members for import")
    finally:
        # Audit the action
        audit_manager.log_action(
            db=db,
            username=current_user.username if current_user else 'anonymous',
            ip_address=request.client.host if request.client else None,
            feature=DATA_PRODUCTS_FEATURE_ID,
            action='GET_TEAM_MEMBERS_FOR_IMPORT',
            success=success,
            details={"product_id": product_id, "team_id": team_id, "member_count": len(members)}
        )

def register_routes(app):
    app.include_router(router)
    logger.info("Data product routes registered")
