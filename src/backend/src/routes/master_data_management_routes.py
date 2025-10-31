
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request

from src.common.dependencies import DBSessionDep, AuditManagerDep, AuditCurrentUserDep
from ..controller.master_data_management_manager import MasterDataManagementManager
from ..models.master_data_management import (
    MasterDataManagementComparisonResult,
    MasterDataManagementDataset,
)

# Configure logging
from src.common.logging import get_logger
logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["master-data-management"])
manager = MasterDataManagementManager()

@router.get("/master-data-management/datasets", response_model=List[MasterDataManagementDataset])
async def get_datasets(entity_type: Optional[str] = None):
    """Get all datasets, optionally filtered by entity type"""
    return manager.get_datasets(entity_type)

@router.get("/master-data-management/datasets/{dataset_id}", response_model=MasterDataManagementDataset)
async def get_dataset(dataset_id: str):
    """Get a specific dataset by ID"""
    dataset = manager.get_dataset_by_id(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset

@router.post("/master-data-management/datasets", response_model=MasterDataManagementDataset)
async def create_dataset(
    dataset: MasterDataManagementDataset,
    request: Request,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    audit_user: AuditCurrentUserDep
):
    """Create a new dataset"""
    success = False
    details = {
        "params": {
            "dataset_id": dataset.id,
            "entity_type": dataset.entity_type,
            "name": dataset.name,
            "source_tables_count": len(dataset.source_tables) if dataset.source_tables else 0
        }
    }

    try:
        result = manager.create_dataset(dataset)
        success = True
        return result
    except HTTPException as e:
        details["exception"] = {"type": "HTTPException", "status_code": e.status_code, "detail": e.detail}
        raise
    except Exception as e:
        logger.exception("Failed creating MDM dataset %s", dataset.id)
        details["exception"] = {"type": type(e).__name__, "message": str(e)}
        raise HTTPException(status_code=500, detail="Failed to create dataset")
    finally:
        audit_manager.log_action(
            db=db,
            username=audit_user.username,
            ip_address=request.client.host if request.client else None,
            feature="master-data-management",
            action="CREATE",
            success=success,
            details=details
        )

@router.put("/master-data-management/datasets/{dataset_id}", response_model=MasterDataManagementDataset)
async def update_dataset(
    dataset_id: str,
    dataset: MasterDataManagementDataset,
    request: Request,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    audit_user: AuditCurrentUserDep
):
    """Update an existing dataset"""
    success = False
    details = {
        "params": {
            "dataset_id": dataset_id,
            "name": dataset.name,
            "entity_type": dataset.entity_type
        }
    }

    try:
        updated = manager.update_dataset(dataset_id, dataset)
        if not updated:
            raise HTTPException(status_code=404, detail="Dataset not found")
        success = True
        return updated
    except HTTPException as e:
        details["exception"] = {"type": "HTTPException", "status_code": e.status_code, "detail": e.detail}
        raise
    except Exception as e:
        logger.exception("Failed updating MDM dataset %s", dataset_id)
        details["exception"] = {"type": type(e).__name__, "message": str(e)}
        raise HTTPException(status_code=500, detail="Failed to update dataset")
    finally:
        audit_manager.log_action(
            db=db,
            username=audit_user.username,
            ip_address=request.client.host if request.client else None,
            feature="master-data-management",
            action="UPDATE",
            success=success,
            details=details
        )

@router.delete("/master-data-management/datasets/{dataset_id}")
async def delete_dataset(
    dataset_id: str,
    request: Request,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    audit_user: AuditCurrentUserDep
):
    """Delete a dataset"""
    success = False
    details = {"params": {"dataset_id": dataset_id}}

    try:
        if not manager.delete_dataset(dataset_id):
            raise HTTPException(status_code=404, detail="Dataset not found")
        success = True
        return {"message": "Dataset deleted successfully"}
    except HTTPException as e:
        details["exception"] = {"type": "HTTPException", "status_code": e.status_code, "detail": e.detail}
        raise
    except Exception as e:
        logger.exception("Failed deleting MDM dataset %s", dataset_id)
        details["exception"] = {"type": type(e).__name__, "message": str(e)}
        raise HTTPException(status_code=500, detail="Failed to delete dataset")
    finally:
        audit_manager.log_action(
            db=db,
            username=audit_user.username,
            ip_address=request.client.host if request.client else None,
            feature="master-data-management",
            action="DELETE",
            success=success,
            details=details
        )

@router.post("/master-data-management/compare", response_model=List[MasterDataManagementComparisonResult])
async def compare_datasets(
    dataset_ids: List[str],
    request: Request,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    audit_user: AuditCurrentUserDep
):
    """Compare selected datasets"""
    success = False
    details = {
        "params": {
            "dataset_ids": dataset_ids,
            "dataset_count": len(dataset_ids)
        }
    }

    try:
        if len(dataset_ids) < 2:
            raise HTTPException(status_code=400, detail="At least two datasets must be selected")
        result = manager.compare_datasets(dataset_ids)
        success = True
        details["comparison_count"] = len(result)
        return result
    except HTTPException as e:
        details["exception"] = {"type": "HTTPException", "status_code": e.status_code, "detail": e.detail}
        raise
    except Exception as e:
        logger.exception("Failed comparing MDM datasets")
        details["exception"] = {"type": type(e).__name__, "message": str(e)}
        raise HTTPException(status_code=500, detail="Failed to compare datasets")
    finally:
        audit_manager.log_action(
            db=db,
            username=audit_user.username,
            ip_address=request.client.host if request.client else None,
            feature="master-data-management",
            action="COMPARE",
            success=success,
            details=details
        )

@router.get("/master-data-management/comparisons", response_model=List[MasterDataManagementComparisonResult])
async def get_comparisons():
    """Get all comparison results"""
    return manager.get_comparison_results()

@router.get("/master-data-management/comparisons/{dataset_a}/{dataset_b}", response_model=MasterDataManagementComparisonResult)
async def get_comparison(dataset_a: str, dataset_b: str):
    """Get comparison result for specific datasets"""
    comparison = manager.get_comparison_by_datasets(dataset_a, dataset_b)
    if not comparison:
        raise HTTPException(status_code=404, detail="Comparison not found")
    return comparison

def register_routes(app):
    """Register master data management routes with the app"""
    app.include_router(router)
    logger.info("Master data management routes registered")
