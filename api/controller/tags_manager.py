from typing import List, Optional, Union
from uuid import UUID

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from api.common.logging import get_logger
from api.repositories.tags_repository import (
    tag_namespace_repo, tag_repo, tag_namespace_permission_repo, entity_tag_repo,
    TagNamespaceRepository, TagRepository, TagNamespacePermissionRepository, EntityTagAssociationRepository
)
from api.models.tags import (
    Tag, TagCreate, TagUpdate, TagStatus,
    TagNamespace, TagNamespaceCreate, TagNamespaceUpdate,
    TagNamespacePermission, TagNamespacePermissionCreate, TagNamespacePermissionUpdate, TagAccessLevel,
    AssignedTagCreate, AssignedTag,
    DEFAULT_NAMESPACE_NAME, TAG_NAMESPACE_SEPARATOR
)
from api.db_models.tags import TagDb, TagNamespaceDb # For type hints

from api.common.search_interfaces import SearchableAsset, SearchIndexItem
from api.common.search_registry import searchable_asset

logger = get_logger(__name__)

@searchable_asset
class TagsManager(SearchableAsset):
    def __init__(
        self,
        namespace_repo: TagNamespaceRepository = tag_namespace_repo,
        tag_repository: TagRepository = tag_repo,
        permission_repo: TagNamespacePermissionRepository = tag_namespace_permission_repo,
        entity_assoc_repo: EntityTagAssociationRepository = entity_tag_repo
    ):
        self._namespace_repo = namespace_repo
        self._tag_repo = tag_repository
        self._permission_repo = permission_repo
        self._entity_assoc_repo = entity_assoc_repo

    # --- Namespace Methods ---
    def create_namespace(self, db: Session, *, namespace_in: TagNamespaceCreate, user_email: Optional[str]) -> TagNamespace:
        existing_namespace = self._namespace_repo.get_by_name(db, name=namespace_in.name)
        if existing_namespace:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, 
                                detail=f"Tag namespace '{namespace_in.name}' already exists.")
        db_namespace = self._namespace_repo.create(db, obj_in=namespace_in, user_email=user_email)
        db.commit()
        db.refresh(db_namespace)
        return TagNamespace.from_orm(db_namespace)

    def get_namespace(self, db: Session, *, namespace_id: UUID) -> Optional[TagNamespace]:
        db_namespace = self._namespace_repo.get(db, id=namespace_id)
        return TagNamespace.from_orm(db_namespace) if db_namespace else None

    def get_namespace_by_name(self, db: Session, *, name: str) -> Optional[TagNamespace]:
        db_namespace = self._namespace_repo.get_by_name(db, name=name)
        return TagNamespace.from_orm(db_namespace) if db_namespace else None

    def list_namespaces(self, db: Session, *, skip: int = 0, limit: int = 100) -> List[TagNamespace]:
        db_namespaces = self._namespace_repo.get_multi(db, skip=skip, limit=limit)
        return [TagNamespace.from_orm(ns) for ns in db_namespaces]

    def update_namespace(self, db: Session, *, namespace_id: UUID, namespace_in: TagNamespaceUpdate, user_email: Optional[str]) -> Optional[TagNamespace]:
        db_namespace = self._namespace_repo.get(db, id=namespace_id)
        if not db_namespace:
            return None
        if namespace_in.name:
            existing_namespace_with_name = self._namespace_repo.get_by_name(db, name=namespace_in.name)
            if existing_namespace_with_name and existing_namespace_with_name.id != namespace_id:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, 
                                    detail=f"Tag namespace name '{namespace_in.name}' is already in use.")
        
        updated_db_namespace = self._namespace_repo.update(db, db_obj=db_namespace, obj_in=namespace_in, user_email=user_email)
        db.commit()
        db.refresh(updated_db_namespace)
        return TagNamespace.from_orm(updated_db_namespace)

    def delete_namespace(self, db: Session, *, namespace_id: UUID) -> bool:
        # Ensure it's not the default namespace
        db_namespace = self._namespace_repo.get(db, id=namespace_id)
        if db_namespace and db_namespace.name == DEFAULT_NAMESPACE_NAME:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, 
                                detail=f"Cannot delete the default namespace '{DEFAULT_NAMESPACE_NAME}'.")
        # Add check for existing tags in namespace before deletion if strict policy needed
        # tags_in_namespace = self._tag_repo.get_multi_with_filters(db, namespace_id=namespace_id, limit=1)
        # if tags_in_namespace:
        #     raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Namespace not empty. Delete tags first.")
        
        deleted_count = self._namespace_repo.remove(db, id=namespace_id)
        if deleted_count:
            db.commit()
            return True
        return False

    # --- Entity Tagging Methods (generic across entity types) ---
    def list_assigned_tags(self, db: Session, *, entity_id: str, entity_type: str) -> List[AssignedTag]:
        return self._entity_assoc_repo.get_assigned_tags_for_entity(db, entity_id=entity_id, entity_type=entity_type)

    def set_tags_for_entity(self, db: Session, *, entity_id: str, entity_type: str, tags: List[AssignedTagCreate], user_email: Optional[str]) -> List[AssignedTag]:
        ns_repo = self._namespace_repo
        assigned = self._entity_assoc_repo.set_tags_for_entity(
            db,
            entity_id=entity_id,
            entity_type=entity_type,
            tags_data=tags,
            user_email=user_email,
            tag_repo=self._tag_repo,
            ns_repo=ns_repo,
        )
        db.commit()
        return assigned

    def add_tag_to_entity(self, db: Session, *, entity_id: str, entity_type: str, tag_id: UUID, assigned_value: Optional[str], user_email: Optional[str]) -> AssignedTag:
        assoc = self._entity_assoc_repo.add_tag_to_entity(
            db,
            entity_id=entity_id,
            entity_type=entity_type,
            tag_id=tag_id,
            assigned_value=assigned_value,
            assigned_by=user_email,
        )
        db.commit()
        # Build AssignedTag result
        tag_db = self._tag_repo.get(db, id=tag_id)
        ns = self._namespace_repo.get(db, id=tag_db.namespace_id) if tag_db and tag_db.namespace_id else None
        return AssignedTag(
            tag_id=tag_db.id,
            tag_name=tag_db.name,
            namespace_id=tag_db.namespace_id,
            namespace_name=ns.name if ns else DEFAULT_NAMESPACE_NAME,
            status=TagStatus(tag_db.status),
            fully_qualified_name=f"{(ns.name if ns else DEFAULT_NAMESPACE_NAME)}{TAG_NAMESPACE_SEPARATOR}{tag_db.name}",
            assigned_value=assoc.assigned_value,
            assigned_by=assoc.assigned_by,
            assigned_at=assoc.assigned_at,
        )

    def remove_tag_from_entity(self, db: Session, *, entity_id: str, entity_type: str, tag_id: UUID) -> bool:
        ok = self._entity_assoc_repo.remove_tag_from_entity(db, entity_id=entity_id, entity_type=entity_type, tag_id=tag_id)
        if ok:
            db.commit()
        return ok

    def get_or_create_default_namespace(self, db: Session, *, user_email: Optional[str]) -> TagNamespaceDb:
        """Ensures the default namespace exists, creating it if necessary."""
        # This method returns the DB object, used primarily during startup.
        return self._namespace_repo.get_or_create_default_namespace(db, user_email=user_email)

    # --- Tag Methods ---
    def create_tag(self, db: Session, *, tag_in: TagCreate, user_email: Optional[str]) -> Tag:
        namespace_id_to_use: Optional[UUID] = tag_in.namespace_id
        
        if not namespace_id_to_use:
            ns_name = tag_in.namespace_name or DEFAULT_NAMESPACE_NAME
            namespace_db = self._namespace_repo.get_by_name(db, name=ns_name)
            if not namespace_db:
                if ns_name == DEFAULT_NAMESPACE_NAME:
                    # This should have been created at startup, but as a fallback:
                    namespace_db = self._namespace_repo.get_or_create_default_namespace(db, user_email=user_email)
                else:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Namespace '{ns_name}' not found.")
            namespace_id_to_use = namespace_db.id
        else: # namespace_id was provided
            namespace_db = self._namespace_repo.get(db, id=namespace_id_to_use)
            if not namespace_db:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Namespace with ID '{namespace_id_to_use}' not found.")

        if tag_in.parent_id:
            parent_tag = self._tag_repo.get(db, id=tag_in.parent_id)
            if not parent_tag:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Parent tag with ID '{tag_in.parent_id}' not found.")
            if parent_tag.namespace_id != namespace_id_to_use:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Parent tag must be in the same namespace.")

        # Check for existing tag with the same name in the resolved namespace
        existing_tag = db.query(TagDb).filter(TagDb.namespace_id == namespace_id_to_use, TagDb.name == tag_in.name).first()
        if existing_tag:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, 
                                detail=f"Tag '{tag_in.name}' already exists in namespace '{namespace_db.name if namespace_db else namespace_id_to_use}'.")

        db_tag = self._tag_repo.create_with_namespace(db, obj_in=tag_in, namespace_id=namespace_id_to_use, user_email=user_email)
        db.commit()
        db.refresh(db_tag)
        # Eager load namespace for the response model
        db.refresh(db_tag, attribute_names=['namespace'])
        return Tag.from_orm(db_tag)

    def get_tag(self, db: Session, *, tag_id: UUID) -> Optional[Tag]:
        db_tag = self._tag_repo.get(db, id=tag_id) # get() in repo now eager loads namespace, parent, children
        return Tag.from_orm(db_tag) if db_tag else None

    def get_tag_by_fqn(self, db: Session, *, fqn: str) -> Optional[Tag]:
        db_tag = self._tag_repo.get_by_fully_qualified_name(db, fqn=fqn)
        return Tag.from_orm(db_tag) if db_tag else None

    def list_tags(
        self, db: Session, *, 
        skip: int = 0, limit: int = 100, 
        namespace_id: Optional[UUID] = None,
        namespace_name: Optional[str] = None, 
        name_contains: Optional[str] = None,
        status: Optional[TagStatus] = None,
        parent_id: Optional[UUID] = None,
        is_root: Optional[bool] = None
    ) -> List[Tag]:
        db_tags = self._tag_repo.get_multi_with_filters(
            db, skip=skip, limit=limit, 
            namespace_id=namespace_id, namespace_name=namespace_name,
            name_contains=name_contains, status=status,
            parent_id=parent_id, is_root=is_root
        )
        return [Tag.from_orm(tag) for tag in db_tags]

    def update_tag(self, db: Session, *, tag_id: UUID, tag_in: TagUpdate, user_email: Optional[str]) -> Optional[Tag]:
        db_tag = self._tag_repo.get(db, id=tag_id)
        if not db_tag:
            return None
        
        # If name is being changed, check for conflict within the same namespace
        if tag_in.name and tag_in.name != db_tag.name:
            existing_tag_with_name = db.query(TagDb).filter(TagDb.namespace_id == db_tag.namespace_id, TagDb.name == tag_in.name, TagDb.id != tag_id).first()
            if existing_tag_with_name:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, 
                                    detail=f"Tag name '{tag_in.name}' already exists in this namespace.")

        if tag_in.parent_id and tag_in.parent_id != db_tag.parent_id:
            parent_tag = self._tag_repo.get(db, id=tag_in.parent_id)
            if not parent_tag:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"New parent tag with ID '{tag_in.parent_id}' not found.")
            if parent_tag.namespace_id != db_tag.namespace_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New parent tag must be in the same namespace.")
            # Prevent circular dependencies (simple check: new parent cannot be self or one of its children)
            if tag_in.parent_id == tag_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot set tag as its own parent.")
            # Deeper circular check might be needed if hierarchies are complex

        updated_db_tag = self._tag_repo.update(db, db_obj=db_tag, obj_in=tag_in, user_email=user_email)
        db.commit()
        db.refresh(updated_db_tag)
        db.refresh(updated_db_tag, attribute_names=['namespace']) # Ensure namespace is loaded for FQN
        return Tag.from_orm(updated_db_tag)

    def delete_tag(self, db: Session, *, tag_id: UUID) -> bool:
        # Check if tag is a parent to any other tags
        children_count = db.query(func.count(TagDb.id)).filter(TagDb.parent_id == tag_id).scalar()
        if children_count > 0:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, 
                                detail=f"Tag ID '{tag_id}' is a parent to {children_count} other tag(s). Delete children first or reassign parent.")
        
        # Check if tag is associated with any entities (future enhancement)
        # assoc_count = db.query(func.count(EntityTagAssociationDb.id)).filter(EntityTagAssociationDb.tag_id == tag_id).scalar()
        # if assoc_count > 0:
        #     raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Tag is associated with {assoc_count} entities. Remove associations first.")

        deleted_count = self._tag_repo.remove(db, id=tag_id)
        if deleted_count:
            db.commit()
            return True
        return False

    # --- Namespace Permission Methods ---
    def add_permission_to_namespace(self, db: Session, *, namespace_id: UUID, perm_in: TagNamespacePermissionCreate, user_email: Optional[str]) -> TagNamespacePermission:
        ns = self._namespace_repo.get(db, id=namespace_id)
        if not ns:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Namespace with ID '{namespace_id}' not found.")
        
        existing_perm = self._permission_repo.get_by_namespace_and_group(db, namespace_id=namespace_id, group_id=perm_in.group_id)
        if existing_perm:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, 
                                detail=f"Permission for group '{perm_in.group_id}' on namespace '{namespace_id}' already exists.")
        
        perm_in.namespace_id = namespace_id # Ensure namespace_id is set if not already
        db_perm = self._permission_repo.create(db, obj_in=perm_in, user_email=user_email)
        db.commit()
        db.refresh(db_perm)
        return TagNamespacePermission.from_orm(db_perm)

    def get_namespace_permission(self, db: Session, *, perm_id: UUID) -> Optional[TagNamespacePermission]:
        db_perm = self._permission_repo.get(db, id=perm_id)
        return TagNamespacePermission.from_orm(db_perm) if db_perm else None

    def list_permissions_for_namespace(self, db: Session, *, namespace_id: UUID, skip: int = 0, limit: int = 100) -> List[TagNamespacePermission]:
        # Add skip/limit to repository method if needed, for now fetching all for a namespace.
        db_perms = self._permission_repo.get_permissions_for_namespace(db, namespace_id=namespace_id)
        # Apply skip/limit here if repo doesn't support it directly for this specific query
        return [TagNamespacePermission.from_orm(p) for p in db_perms[skip : skip + limit]]

    def update_namespace_permission(self, db: Session, *, perm_id: UUID, perm_in: TagNamespacePermissionUpdate, user_email: Optional[str]) -> Optional[TagNamespacePermission]:
        db_perm = self._permission_repo.get(db, id=perm_id)
        if not db_perm:
            return None
        
        # If group_id is changing, ensure it doesn't conflict with an existing perm for the new group_id on the same namespace
        if perm_in.group_id and perm_in.group_id != db_perm.group_id:
            existing_perm_for_new_group = self._permission_repo.get_by_namespace_and_group(
                db, namespace_id=db_perm.namespace_id, group_id=perm_in.group_id
            )
            if existing_perm_for_new_group and existing_perm_for_new_group.id != perm_id:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, 
                                    detail=f"A permission for group '{perm_in.group_id}' on this namespace already exists.")

        updated_db_perm = self._permission_repo.update(db, db_obj=db_perm, obj_in=perm_in) # user_email not used in CRUDBase.update
        db.commit()
        db.refresh(updated_db_perm)
        return TagNamespacePermission.from_orm(updated_db_perm)

    def remove_permission_from_namespace(self, db: Session, *, perm_id: UUID) -> bool:
        deleted_count = self._permission_repo.remove(db, id=perm_id)
        if deleted_count:
            db.commit()
            return True
        return False

    # --- SearchableAsset Implementation ---
    def get_search_index_items(self, db: Session) -> List[SearchIndexItem]:
        logger.info("TagsManager: Fetching tags for search indexing...")
        items = []
        try:
            # Fetch all tags with their namespaces for FQN
            db_tags = self._tag_repo.get_multi_with_filters(db, limit=10000) # Adjust limit as needed
            
            for tag_db_obj in db_tags:
                if not tag_db_obj.id or not tag_db_obj.name or not tag_db_obj.namespace:
                     logger.warning(f"Skipping tag for search indexing due to missing id, name, or namespace: {tag_db_obj}")
                     continue
                
                tag_api_model = Tag.from_orm(tag_db_obj) # Use Pydantic model for FQN
                items.append(
                    SearchIndexItem(
                        id=f"tag::{tag_api_model.id}",
                        type="tag",
                        feature_id="tags", # Or "settings.tags" if managed under settings UI
                        title=tag_api_model.fully_qualified_name,
                        description=tag_api_model.description or f"Tag: {tag_api_model.name} in namespace {tag_api_model.namespace_name}",
                        link=f"/settings/tags?tagId={tag_api_model.id}", # Placeholder link, adjust to actual UI path
                        tags=[tag_api_model.name, tag_api_model.namespace_name or DEFAULT_NAMESPACE_NAME, f"status:{tag_api_model.status.value}"]
                    )
                )
            logger.info(f"TagsManager: Prepared {len(items)} tags for search index.")
            return items
        except Exception as e:
            logger.error(f"TagsManager: Error fetching or mapping tags for search: {e}", exc_info=True)
            return [] 