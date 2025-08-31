from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body, Request
from sqlalchemy.orm import Session

from api.common.logging import get_logger
from api.common.dependencies import DBSessionDep, CurrentUserDep, get_tags_manager
from api.controller.tags_manager import TagsManager
from api.models.users import UserInfo # For CurrentUserDep
from api.models.tags import (
    Tag, TagCreate, TagUpdate, TagStatus,
    TagNamespace, TagNamespaceCreate, TagNamespaceUpdate,
    TagNamespacePermission, TagNamespacePermissionCreate, TagNamespacePermissionUpdate,
    AssignedTagCreate, AssignedTag
)

logger = get_logger(__name__)

# Define router with /api prefix, and then /tags group
router = APIRouter(prefix="/api", tags=["Tags"])

# --- Tag Namespace Routes ---
@router.post("/tags/namespaces", response_model=TagNamespace, status_code=status.HTTP_201_CREATED)
async def create_tag_namespace(
    namespace_in: TagNamespaceCreate,
    db: DBSessionDep,
    current_user: CurrentUserDep,
    manager: TagsManager = Depends(get_tags_manager)
):
    logger.info(f"User '{current_user.email}' creating tag namespace: {namespace_in.name}")
    return manager.create_namespace(db, namespace_in=namespace_in, user_email=current_user.email)

@router.get("/tags/namespaces", response_model=List[TagNamespace])
async def list_tag_namespaces(
    db: DBSessionDep,
    manager: TagsManager = Depends(get_tags_manager),
    skip: int = 0,
    limit: int = Query(default=100, le=1000)
):
    return manager.list_namespaces(db, skip=skip, limit=limit)

@router.get("/tags/namespaces/{namespace_id}", response_model=TagNamespace)
async def get_tag_namespace(
    namespace_id: UUID,
    db: DBSessionDep,
    manager: TagsManager = Depends(get_tags_manager)
):
    namespace = manager.get_namespace(db, namespace_id=namespace_id)
    if not namespace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag namespace not found")
    return namespace

@router.put("/tags/namespaces/{namespace_id}", response_model=TagNamespace)
async def update_tag_namespace(
    namespace_id: UUID,
    namespace_in: TagNamespaceUpdate,
    db: DBSessionDep,
    current_user: CurrentUserDep,
    manager: TagsManager = Depends(get_tags_manager)
):
    logger.info(f"User '{current_user.email}' updating tag namespace ID: {namespace_id}")
    updated_namespace = manager.update_namespace(db, namespace_id=namespace_id, namespace_in=namespace_in, user_email=current_user.email)
    if not updated_namespace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag namespace not found")
    return updated_namespace

@router.delete("/tags/namespaces/{namespace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tag_namespace(
    namespace_id: UUID,
    db: DBSessionDep,
    current_user: CurrentUserDep, # For logging/audit
    manager: TagsManager = Depends(get_tags_manager)
):
    logger.info(f"User '{current_user.email}' deleting tag namespace ID: {namespace_id}")
    if not manager.delete_namespace(db, namespace_id=namespace_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag namespace not found or could not be deleted")
    return

# --- Tag Routes ---
@router.post("/tags", response_model=Tag, status_code=status.HTTP_201_CREATED)
async def create_tag(
    tag_in: TagCreate,
    db: DBSessionDep,
    current_user: CurrentUserDep,
    manager: TagsManager = Depends(get_tags_manager)
):
    logger.info(f"User '{current_user.email}' creating tag: {tag_in.name} in namespace {tag_in.namespace_name or tag_in.namespace_id or 'default'}")
    return manager.create_tag(db, tag_in=tag_in, user_email=current_user.email)

@router.get("/tags", response_model=List[Tag])
async def list_tags(
    db: DBSessionDep,
    manager: TagsManager = Depends(get_tags_manager),
    skip: int = 0,
    limit: int = Query(default=100, le=1000),
    namespace_id: Optional[UUID] = Query(None, description="Filter by namespace ID"),
    namespace_name: Optional[str] = Query(None, description="Filter by namespace name"),
    name_contains: Optional[str] = Query(None, description="Filter by tag name containing string (case-insensitive)"),
    status: Optional[TagStatus] = Query(None, description="Filter by tag status"),
    parent_id: Optional[UUID] = Query(None, description="Filter by parent tag ID"),
    is_root: Optional[bool] = Query(None, description="Filter for root tags (parent_id is null) or non-root tags")
):
    return manager.list_tags(db, skip=skip, limit=limit, namespace_id=namespace_id, namespace_name=namespace_name,
                             name_contains=name_contains, status=status, parent_id=parent_id, is_root=is_root)

@router.get("/tags/{tag_id}", response_model=Tag)
async def get_tag(
    tag_id: UUID,
    db: DBSessionDep,
    manager: TagsManager = Depends(get_tags_manager)
):
    tag = manager.get_tag(db, tag_id=tag_id)
    if not tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")
    return tag

@router.get("/tags/fqn/{fully_qualified_name:path}", response_model=Tag, name="get_tag_by_fqn")
async def get_tag_by_fully_qualified_name_route(
    fully_qualified_name: str,
    db: DBSessionDep,
    manager: TagsManager = Depends(get_tags_manager)
):
    # Example: /api/tags/fqn/default/my-tag or /api/tags/fqn/custom_ns/another-tag
    tag = manager.get_tag_by_fqn(db, fqn=fully_qualified_name)
    if not tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Tag with FQN '{fully_qualified_name}' not found")
    return tag

@router.put("/tags/{tag_id}", response_model=Tag)
async def update_tag(
    tag_id: UUID,
    tag_in: TagUpdate,
    db: DBSessionDep,
    current_user: CurrentUserDep,
    manager: TagsManager = Depends(get_tags_manager)
):
    logger.info(f"User '{current_user.email}' updating tag ID: {tag_id}")
    updated_tag = manager.update_tag(db, tag_id=tag_id, tag_in=tag_in, user_email=current_user.email)
    if not updated_tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")
    return updated_tag

@router.delete("/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tag(
    tag_id: UUID,
    db: DBSessionDep,
    current_user: CurrentUserDep, # For logging/audit
    manager: TagsManager = Depends(get_tags_manager)
):
    logger.info(f"User '{current_user.email}' deleting tag ID: {tag_id}")
    if not manager.delete_tag(db, tag_id=tag_id):
        # Manager raises HTTPException for specific cases like not found or conflicts
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found or could not be deleted") # Fallback
    return

# --- Tag Namespace Permission Routes ---
@router.post("/tags/namespaces/{namespace_id}/permissions", response_model=TagNamespacePermission, status_code=status.HTTP_201_CREATED)
async def add_namespace_permission(
    namespace_id: UUID,
    permission_in: TagNamespacePermissionCreate,
    db: DBSessionDep,
    current_user: CurrentUserDep,
    manager: TagsManager = Depends(get_tags_manager)
):
    logger.info(f"User '{current_user.email}' adding permission to namespace {namespace_id} for group {permission_in.group_id}")
    return manager.add_permission_to_namespace(db, namespace_id=namespace_id, perm_in=permission_in, user_email=current_user.email)

@router.get("/tags/namespaces/{namespace_id}/permissions", response_model=List[TagNamespacePermission])
async def list_namespace_permissions(
    namespace_id: UUID,
    db: DBSessionDep,
    manager: TagsManager = Depends(get_tags_manager),
    skip: int = 0,
    limit: int = Query(default=100, le=1000)
):
    # Check if namespace exists first (optional, manager method might do it)
    ns = manager.get_namespace(db, namespace_id=namespace_id)
    if not ns:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag namespace not found")
    return manager.list_permissions_for_namespace(db, namespace_id=namespace_id, skip=skip, limit=limit)

@router.get("/tags/namespaces/{namespace_id}/permissions/{permission_id}", response_model=TagNamespacePermission)
async def get_namespace_permission_detail(
    namespace_id: UUID, # Keep for path consistency, though perm_id is unique
    permission_id: UUID,
    db: DBSessionDep,
    manager: TagsManager = Depends(get_tags_manager)
):
    permission = manager.get_namespace_permission(db, perm_id=permission_id)
    if not permission or permission.namespace_id != namespace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found for this namespace")
    return permission

@router.put("/tags/namespaces/{namespace_id}/permissions/{permission_id}", response_model=TagNamespacePermission)
async def update_namespace_permission(
    namespace_id: UUID,
    permission_id: UUID,
    permission_in: TagNamespacePermissionUpdate,
    db: DBSessionDep,
    current_user: CurrentUserDep,
    manager: TagsManager = Depends(get_tags_manager)
):
    logger.info(f"User '{current_user.email}' updating permission ID {permission_id} for namespace {namespace_id}")
    # First, check if the permission belongs to the given namespace_id to ensure path integrity
    existing_perm_check = manager.get_namespace_permission(db, perm_id=permission_id)
    if not existing_perm_check or existing_perm_check.namespace_id != namespace_id:
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found or does not belong to the specified namespace.")

    updated_permission = manager.update_namespace_permission(db, perm_id=permission_id, perm_in=permission_in, user_email=current_user.email)
    if not updated_permission:
        # This specific check might be redundant if the above check passes and manager.update handles not found for perm_id itself.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found for update")
    return updated_permission

@router.delete("/tags/namespaces/{namespace_id}/permissions/{permission_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_namespace_permission(
    namespace_id: UUID,
    permission_id: UUID,
    db: DBSessionDep,
    current_user: CurrentUserDep, # For logging/audit
    manager: TagsManager = Depends(get_tags_manager)
):
    logger.info(f"User '{current_user.email}' deleting permission ID {permission_id} from namespace {namespace_id}")
    # Optional: Check if permission belongs to namespace before deleting
    perm_to_delete = manager.get_namespace_permission(db, perm_id=permission_id)
    if not perm_to_delete or perm_to_delete.namespace_id != namespace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found or does not belong to specified namespace.")

    if not manager.remove_permission_from_namespace(db, perm_id=permission_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found or could not be deleted") # Fallback
    return

# --- Generic Entity Tagging Routes ---
@router.get("/entities/{entity_type}/{entity_id}/tags", response_model=List[AssignedTag])
async def list_entity_tags(
    entity_type: str,
    entity_id: str,
    db: DBSessionDep,
    manager: TagsManager = Depends(get_tags_manager)
):
    return manager.list_assigned_tags(db, entity_id=entity_id, entity_type=entity_type)

@router.post("/entities/{entity_type}/{entity_id}/tags:set", response_model=List[AssignedTag])
async def set_entity_tags(
    entity_type: str,
    entity_id: str,
    tags: List[AssignedTagCreate],
    db: DBSessionDep,
    current_user: CurrentUserDep,
    manager: TagsManager = Depends(get_tags_manager)
):
    return manager.set_tags_for_entity(db, entity_id=entity_id, entity_type=entity_type, tags=tags, user_email=current_user.email)

@router.post("/entities/{entity_type}/{entity_id}/tags:add", response_model=AssignedTag)
async def add_tag_to_entity_route(
    entity_type: str,
    entity_id: str,
    tag_id: UUID,
    db: DBSessionDep,
    current_user: CurrentUserDep,
    assigned_value: Optional[str] = None,
    manager: TagsManager = Depends(get_tags_manager)
):
    return manager.add_tag_to_entity(db, entity_id=entity_id, entity_type=entity_type, tag_id=tag_id, assigned_value=assigned_value, user_email=current_user.email)

@router.delete("/entities/{entity_type}/{entity_id}/tags:remove", status_code=status.HTTP_204_NO_CONTENT)
async def remove_tag_from_entity_route(
    entity_type: str,
    entity_id: str,
    tag_id: UUID,
    db: DBSessionDep,
    manager: TagsManager = Depends(get_tags_manager)
):
    ok = manager.remove_tag_from_entity(db, entity_id=entity_id, entity_type=entity_type, tag_id=tag_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag association not found")
    return


def register_routes(app):
    app.include_router(router)
    logger.info("Tag routes registered with prefix /api/tags") 