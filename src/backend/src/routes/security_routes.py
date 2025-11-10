from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.common.logging import get_logger
from src.controller.security_manager import SecurityManager
from src.models.security import SecurityType

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["security"])

# Pydantic models for request/response
class SecurityRuleCreate(BaseModel):
    name: str
    description: str
    type: SecurityType
    target: str = ""
    conditions: List[str] = []

class SecurityRuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    type: Optional[SecurityType] = None
    target: Optional[str] = None
    conditions: Optional[List[str]] = None
    status: Optional[str] = None

class SecurityRuleResponse(BaseModel):
    id: str
    name: str
    description: str
    type: SecurityType
    target: str
    conditions: List[str]
    status: str
    last_updated: str

    class Config:
        from_attributes = True

# Dependency to get security manager
def get_security_manager() -> SecurityManager:
    return SecurityManager()

@router.post("/security/rules", response_model=SecurityRuleResponse)
async def create_rule(
    rule: SecurityRuleCreate,
    manager: SecurityManager = Depends(get_security_manager)
) -> SecurityRuleResponse:
    """Create a new security rule"""
    try:
        new_rule = manager.create_rule(
            name=rule.name,
            description=rule.description,
            type=rule.type,
            target=rule.target,
            conditions=rule.conditions
        )
        return SecurityRuleResponse.from_orm(new_rule)
    except Exception as e:
        logger.error("Failed to create security rule", exc_info=True)
        raise HTTPException(status_code=400, detail="Failed to create security rule")

@router.get("/security/rules", response_model=List[SecurityRuleResponse])
async def list_rules(
    manager: SecurityManager = Depends(get_security_manager)
) -> List[SecurityRuleResponse]:
    """List all security rules"""
    rules = manager.list_rules()
    return [SecurityRuleResponse.from_orm(rule) for rule in rules]

@router.get("/security/rules/{rule_id}", response_model=SecurityRuleResponse)
async def get_rule(
    rule_id: str,
    manager: SecurityManager = Depends(get_security_manager)
) -> SecurityRuleResponse:
    """Get a security rule by ID"""
    rule = manager.get_rule(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return SecurityRuleResponse.from_orm(rule)

@router.put("/security/rules/{rule_id}", response_model=SecurityRuleResponse)
async def update_rule(
    rule_id: str,
    rule_update: SecurityRuleUpdate,
    manager: SecurityManager = Depends(get_security_manager)
) -> SecurityRuleResponse:
    """Update a security rule"""
    updated_rule = manager.update_rule(
        rule_id=rule_id,
        name=rule_update.name,
        description=rule_update.description,
        type=rule_update.type,
        target=rule_update.target,
        conditions=rule_update.conditions,
        status=rule_update.status
    )
    if not updated_rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return SecurityRuleResponse.from_orm(updated_rule)

@router.delete("/security/rules/{rule_id}")
async def delete_rule(
    rule_id: str,
    manager: SecurityManager = Depends(get_security_manager)
) -> dict:
    """Delete a security rule"""
    success = manager.delete_rule(rule_id)
    if not success:
        raise HTTPException(status_code=404, detail="Rule not found")
    return {"message": "Rule deleted successfully"}
