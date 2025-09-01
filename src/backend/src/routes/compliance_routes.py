import logging
import os
from pathlib import Path
from typing import List

from fastapi import APIRouter, FastAPI, HTTPException

from ..controller.compliance_manager import ComplianceManager
from ..models.compliance import CompliancePolicy

router = APIRouter(prefix="/api", tags=["compliance"])
manager = ComplianceManager()

# Check for YAML file in data directory
yaml_path = Path(__file__).parent.parent / 'data' / 'compliance.yaml'
if os.path.exists(yaml_path):
    try:
        # Load data from YAML file
        manager.load_from_yaml(str(yaml_path))
        logging.info(f"Successfully loaded compliance policies from {yaml_path}")
    except Exception as e:
        logging.exception(f"Error loading compliance policies from YAML: {e!s}")

@router.get("/compliance/policies")
async def get_policies():
    """Get all compliance policies and stats"""
    policies = manager.get_policies()
    stats = manager.get_compliance_stats()
    return {
        "policies": policies,
        "stats": stats
    }

@router.get("/compliance/policies/{policy_id}", response_model=CompliancePolicy)
async def get_policy(policy_id: str):
    """Get a specific policy by ID"""
    policy = manager.get_policy(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy

@router.post("/compliance/policies", response_model=CompliancePolicy)
async def create_policy(policy: CompliancePolicy):
    """Create a new compliance policy"""
    return manager.create_policy(policy)

@router.put("/compliance/policies/{policy_id}", response_model=CompliancePolicy)
async def update_policy(policy_id: str, policy: CompliancePolicy):
    """Update an existing policy"""
    updated = manager.update_policy(policy_id, policy)
    if not updated:
        raise HTTPException(status_code=404, detail="Policy not found")
    return updated

@router.delete("/compliance/policies/{policy_id}")
async def delete_policy(policy_id: str):
    """Delete a policy"""
    if not manager.delete_policy(policy_id):
        raise HTTPException(status_code=404, detail="Policy not found")
    return {"status": "success"}

@router.get("/compliance/stats")
async def get_stats():
    """Get compliance statistics"""
    return manager.get_compliance_stats()

@router.get("/compliance/trend")
async def get_compliance_trend():
    """Get compliance trend data for the last 30 days"""
    return manager.get_compliance_trend()

def register_routes(app: FastAPI) -> None:
    """Register all compliance routes with the FastAPI app"""
    app.include_router(router)
