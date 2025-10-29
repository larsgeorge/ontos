import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.controller.security_features_manager import SecurityFeaturesManager
from src.models.security_features import SecurityFeature, SecurityFeatureType

# Configure logging
from src.common.logging import get_logger
logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["security-features"])

# Create a single instance of the manager
manager = SecurityFeaturesManager()

# Check for YAML file in data directory
yaml_path = Path(__file__).parent.parent / 'data' / 'security_features.yaml'
if os.path.exists(yaml_path):
    try:
        # Load data from YAML file
        success = manager.load_from_yaml(yaml_path)
        if success:
            logger.info(f"Successfully loaded security features from {yaml_path}")
        else:
            logger.warning(f"Failed to load security features from {yaml_path}")
    except Exception as e:
        logger.error(f"Error loading security features: {e!s}")

# Pydantic models for request/response
class SecurityFeatureCreate(BaseModel):
    name: str
    description: str
    type: SecurityFeatureType
    target: str
    conditions: List[str] = []
    status: str = "active"

class SecurityFeatureUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    type: Optional[SecurityFeatureType] = None
    target: Optional[str] = None
    conditions: Optional[List[str]] = None
    status: Optional[str] = None

class SecurityFeatureResponse(BaseModel):
    id: str
    name: str
    description: str
    type: SecurityFeatureType
    status: str
    target: str
    conditions: List[str]
    last_updated: datetime

    class Config:
        from_attributes = True

@router.post("/security-features", response_model=SecurityFeatureResponse)
async def create_security_feature(feature: SecurityFeatureCreate) -> SecurityFeatureResponse:
    """Create a new security feature"""
    try:
        logging.info(f"Creating security feature: {feature}")
        new_feature = SecurityFeature(
            id=str(len(manager.features) + 1),
            name=feature.name,
            description=feature.description,
            type=feature.type,
            status=feature.status,
            target=feature.target,
            conditions=feature.conditions
        )
        created_feature = manager.create_feature(new_feature)
        return SecurityFeatureResponse.from_orm(created_feature)
    except Exception as e:
        logging.exception("Error creating security feature")
        raise HTTPException(status_code=500, detail="Failed to create security feature")

@router.get("/security-features", response_model=List[SecurityFeatureResponse])
async def list_security_features():
    try:
        features = manager.list_features()
        logger.debug(f"Found {len(features)} security features")
        logger.debug(f"Features: {features}")
        # Add detailed logging for each feature
        for feature in features:
            try:
                logger.debug(f"Feature details: {feature.to_dict()}")
                # Try to convert to response model
                response = SecurityFeatureResponse.from_orm(feature)
                logger.debug(f"Response model: {response.dict()}")
            except Exception as e:
                logger.error(f"Error processing feature {feature.id}: {e!s}")
                logger.error(f"Feature data: {feature.to_dict()}")
                raise
        return [SecurityFeatureResponse.from_orm(feature) for feature in features]
    except Exception as e:
        logger.error("Error listing security features", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list security features")

@router.get("/security-features/{feature_id}", response_model=SecurityFeatureResponse)
async def get_security_feature(feature_id: str) -> SecurityFeatureResponse:
    """Get a security feature by ID"""
    try:
        logging.debug(f"Getting security feature: {feature_id}")
        feature = manager.get_feature(feature_id)
        if not feature:
            raise HTTPException(status_code=404, detail="Security feature not found")
        return SecurityFeatureResponse.from_orm(feature)
    except HTTPException:
        raise
    except Exception as e:
        logging.exception("Error getting security feature %s", feature_id)
        raise HTTPException(status_code=500, detail="Failed to get security feature")

@router.put("/security-features/{feature_id}", response_model=SecurityFeatureResponse)
async def update_security_feature(feature_id: str, feature_update: SecurityFeatureUpdate) -> SecurityFeatureResponse:
    """Update a security feature"""
    try:
        logging.debug(f"Updating security feature: {feature_id}")
        existing_feature = manager.get_feature(feature_id)
        if not existing_feature:
            raise HTTPException(status_code=404, detail="Security feature not found")

        update_data = feature_update.dict(exclude_unset=True)
        updated_feature = SecurityFeature(
            id=existing_feature.id,
            name=update_data.get('name', existing_feature.name),
            description=update_data.get('description', existing_feature.description),
            type=update_data.get('type', existing_feature.type),
            status=update_data.get('status', existing_feature.status),
            target=update_data.get('target', existing_feature.target),
            conditions=update_data.get('conditions', existing_feature.conditions),
            last_updated=datetime.utcnow()
        )

        result = manager.update_feature(feature_id, updated_feature)
        if not result:
            raise HTTPException(status_code=500, detail="Failed to update security feature")
        return SecurityFeatureResponse.from_orm(result)
    except HTTPException:
        raise
    except Exception as e:
        logging.exception("Error updating security feature %s", feature_id)
        raise HTTPException(status_code=500, detail="Failed to update security feature")

@router.delete("/security-features/{feature_id}")
async def delete_security_feature(feature_id: str):
    """Delete a security feature"""
    try:
        logging.debug(f"Deleting security feature: {feature_id}")
        if not manager.delete_feature(feature_id):
            raise HTTPException(status_code=404, detail="Security feature not found")
        return {"message": "Security feature deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logging.exception("Error deleting security feature %s", feature_id)
        raise HTTPException(status_code=500, detail="Failed to delete security feature")

def register_routes(app):
    """Register security features routes with the app"""
    app.include_router(router)
    logger.info("Security features routes registered")
