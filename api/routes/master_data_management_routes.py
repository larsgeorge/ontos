import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException

from ..controller.master_data_management_manager import MasterDataManagementManager
from ..models.master_data_management import (
    MasterDataManagementComparisonResult,
    MasterDataManagementDataset,
)

# Configure logging
from api.common.logging import get_logger

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
async def create_dataset(dataset: MasterDataManagementDataset):
    """Create a new dataset"""
    return manager.create_dataset(dataset)

@router.put("/master-data-management/datasets/{dataset_id}", response_model=MasterDataManagementDataset)
async def update_dataset(dataset_id: str, dataset: MasterDataManagementDataset):
    """Update an existing dataset"""
    updated = manager.update_dataset(dataset_id, dataset)
    if not updated:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return updated

@router.delete("/master-data-management/datasets/{dataset_id}")
async def delete_dataset(dataset_id: str):
    """Delete a dataset"""
    if not manager.delete_dataset(dataset_id):
        raise HTTPException(status_code=404, detail="Dataset not found")
    return {"message": "Dataset deleted successfully"}

@router.post("/master-data-management/compare", response_model=List[MasterDataManagementComparisonResult])
async def compare_datasets(dataset_ids: List[str]):
    """Compare selected datasets"""
    if len(dataset_ids) < 2:
        raise HTTPException(status_code=400, detail="At least two datasets must be selected")
    return manager.compare_datasets(dataset_ids)

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
