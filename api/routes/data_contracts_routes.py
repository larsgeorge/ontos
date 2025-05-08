import json
import logging
import os
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, Depends, Request
from fastapi.responses import JSONResponse

from api.controller.data_contracts_manager import DataContractsManager

# Configure logging
from api.common.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["data-contracts"])

def get_data_contracts_manager(request: Request) -> DataContractsManager:
    """Retrieves the DataContractsManager singleton from app.state."""
    manager = getattr(request.app.state, 'data_contracts_manager', None)
    if manager is None:
        logger.critical("DataContractsManager instance not found in app.state!")
        raise HTTPException(status_code=500, detail="Data Contracts service is not available.")
    if not isinstance(manager, DataContractsManager):
        logger.critical(f"Object found at app.state.data_contracts_manager is not a DataContractsManager instance (Type: {type(manager)})!")
        raise HTTPException(status_code=500, detail="Data Contracts service configuration error.")
    return manager

@router.get('/data-contracts')
async def get_contracts(manager: DataContractsManager = Depends(get_data_contracts_manager)):
    """Get all data contracts"""
    try:
        contracts = manager.list_contracts()

        # Format the response to match what the frontend expects
        formatted_contracts = []
        for c in contracts:
            # Use the contract's to_dict() method which now includes all needed fields
            formatted_contracts.append(c.to_dict())

        logger.info(f"Retrieved {len(formatted_contracts)} data contracts")
        return formatted_contracts
    except Exception as e:
        error_msg = f"Error retrieving data contracts: {e!s}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@router.get('/data-contracts/{contract_id}')
async def get_contract(contract_id: str, manager: DataContractsManager = Depends(get_data_contracts_manager)):
    """Get a specific data contract"""
    try:
        contract = manager.get_contract(contract_id)
        if not contract:
            raise HTTPException(status_code=404, detail="Contract not found")

        # Return full contract including contract_text
        response = contract.to_dict()
        response['contract_text'] = contract.contract_text
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post('/data-contracts')
async def create_contract(contract_data: dict, manager: DataContractsManager = Depends(get_data_contracts_manager)):
    """Create a new data contract"""
    try:
        contract = manager.create_contract(
            name=contract_data['name'],
            contract_text=contract_data['contract_text'],
            format=contract_data.get('format', 'json'),  # Default to JSON if not specified
            version=contract_data['version'],
            owner=contract_data['owner'],
            description=contract_data.get('description')
        )

        return contract.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put('/data-contracts/{contract_id}')
async def update_contract(contract_id: str, contract_data: dict, manager: DataContractsManager = Depends(get_data_contracts_manager)):
    """Update a data contract"""
    try:
        contract = manager.get_contract(contract_id)
        if not contract:
            logger.warning(f"Data contract not found for update with ID: {contract_id}")
            raise HTTPException(status_code=404, detail="Contract not found")

        logger.info(f"Updating data contract with ID: {contract_id}")

        # Update contract
        updated_contract = manager.update_contract(
            contract_id=contract_id,
            name=contract_data.get('name'),
            contract_text=contract_data.get('contract_text'),
            format=contract_data.get('format'),
            version=contract_data.get('version'),
            owner=contract_data.get('owner'),
            description=contract_data.get('description'),
            status=contract_data.get('status')
        )

        return updated_contract.to_dict()
    except Exception as e:
        error_msg = f"Error updating data contract {contract_id}: {e!s}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@router.delete('/data-contracts/{contract_id}')
async def delete_contract(contract_id: str, manager: DataContractsManager = Depends(get_data_contracts_manager)):
    """Delete a data contract"""
    try:
        if not manager.get_contract(contract_id):
            logger.warning(f"Data contract not found for deletion with ID: {contract_id}")
            raise HTTPException(status_code=404, detail="Contract not found")

        logger.info(f"Deleting data contract with ID: {contract_id}")
        manager.delete_contract(contract_id)
        logger.info(f"Successfully deleted data contract with ID: {contract_id}")
        return None
    except Exception as e:
        error_msg = f"Error deleting data contract {contract_id}: {e!s}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@router.post('/data-contracts/upload')
async def upload_contract(file: UploadFile = File(...), manager: DataContractsManager = Depends(get_data_contracts_manager)):
    """Upload a contract file"""
    try:
        content_type = file.content_type
        filename = file.filename or ''

        # Determine format from content type or extension
        format = 'json'  # default
        if content_type == 'application/x-yaml' or filename.endswith(('.yaml', '.yml')):
            format = 'yaml'
        elif content_type.startswith('text/'):
            format = 'text'

        # Read file content
        contract_text = (await file.read()).decode('utf-8')

        # Create contract
        contract = manager.create_contract(
            name=filename,
            contract_text=contract_text,
            format=format,
            version='1.0',
            owner='Unknown',
            description=f"Uploaded {format.upper()} contract"
        )

        return contract.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get('/data-contracts/{contract_id}/export')
async def export_contract(contract_id: str, manager: DataContractsManager = Depends(get_data_contracts_manager)):
    """Export a contract as JSON"""
    try:
        contract = manager.get_contract(contract_id)
        if not contract:
            raise HTTPException(status_code=404, detail="Contract not found")

        return JSONResponse(
            content=json.loads(contract.contract_json),
            media_type='application/json',
            headers={
                'Content-Disposition': f'attachment; filename="{contract.name.lower().replace(" ", "_")}.json"'
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def register_routes(app):
    """Register routes with the app"""
    app.include_router(router)
    logger.info("Data contract routes registered")
