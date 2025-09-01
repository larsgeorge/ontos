from __future__ import annotations # Ensure forward references work
import logging
from typing import Any, Dict, List, Optional, Iterable, TYPE_CHECKING

# Import Search Interfaces
from src.common.search_interfaces import SearchableAsset, SearchIndexItem
# Import Permission Checker and Feature Access Level
if TYPE_CHECKING:
    from src.common.authorization import PermissionChecker
# Import AuthorizationManager and UserInfo
from src.controller.authorization_manager import AuthorizationManager
from src.models.users import UserInfo
from src.common.features import FeatureAccessLevel

from src.common.logging import get_logger

logger = get_logger(__name__)

class SearchManager:
    def __init__(
        self,
        searchable_managers: Iterable[SearchableAsset]
    ):
        """Initialize search manager with a collection of pre-instantiated searchable asset managers."""
        self.searchable_managers = list(searchable_managers)
        self.index: List[SearchIndexItem] = []
        
        logger.info(f"SearchManager initialized with {len(self.searchable_managers)} managers.")
        
        self.build_index() # Build index after receiving managers

    def build_index(self):
        """Builds or rebuilds the search index by querying searchable managers."""
        logger.info(f"Building search index from {len(self.searchable_managers)} managers...")
        new_index: List[SearchIndexItem] = [] # Build into a new list

        for manager in self.searchable_managers:
            manager_name = manager.__class__.__name__
            try:
                # Ensure managers populate the new feature_id field
                items = manager.get_search_index_items()
                for item in items:
                    if not hasattr(item, 'feature_id') or not item.feature_id:
                         logger.warning(f"Search item {item.id} from {manager_name} is missing feature_id. Skipping.")
                         continue
                    new_index.append(item)
            except Exception as e:
                logger.error(f"Failed to get search items from {manager_name}: {e}", exc_info=True)
        
        # Atomically replace the index
        self.index = new_index
        logger.info(f"Search index build complete. Total items: {len(self.index)}")

    def search(self, query: str, auth_manager: AuthorizationManager, user: UserInfo) -> List[SearchIndexItem]:
        """
        Performs a case-insensitive prefix search on title, description, tags,
        filtered by user permissions for the associated feature using AuthorizationManager.
        """
        if not query:
            return []

        query_lower = query.lower()
        potential_results = []
        for item in self.index:
            match = False
            # Check title
            if item.title and item.title.lower().startswith(query_lower):
                 match = True
            # Check description (if not already matched)
            elif item.description and item.description.lower().startswith(query_lower):
                 match = True
            # Check tags (if not already matched)
            elif item.tags:
                for tag in item.tags:
                     if str(tag).lower().startswith(query_lower):
                         match = True
                         break # Found a matching tag
            
            if match:
                potential_results.append(item)

        # Filter based on permissions using AuthorizationManager
        if not user.groups:
             logger.warning(f"User {user.username} has no groups, returning empty search results.")
             return []
             
        filtered_results = []
        try:
             effective_permissions = auth_manager.get_user_effective_permissions(user.groups)
             for item in potential_results:
                 if auth_manager.has_permission(effective_permissions, item.feature_id, FeatureAccessLevel.READ_ONLY):
                     filtered_results.append(item)
        except Exception as e:
            logger.error(f"Error checking permissions during search for user {user.username}: {e}", exc_info=True)
            # Return empty list or raise? Returning empty for now.
            return []

        logger.info(f"Prefix search for '{query}' returned {len(filtered_results)} results after permission filtering for user {user.username}.")
        return filtered_results 
