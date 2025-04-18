import logging
from typing import Any, Dict, List, Optional, Iterable

# Import Search Interfaces
from api.common.search_interfaces import SearchableAsset, SearchIndexItem

from api.common.logging import setup_logging, get_logger
setup_logging(level=logging.INFO)
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
                items = manager.get_search_index_items()
                new_index.extend(items)
            except Exception as e:
                logger.error(f"Failed to get search items from {manager_name}: {e}", exc_info=True)
        
        # Atomically replace the index
        self.index = new_index
        logger.info(f"Search index build complete. Total items: {len(self.index)}")

    def search(self, query: str) -> List[SearchIndexItem]: # Return type is now List[SearchIndexItem]
        """Performs a case-insensitive prefix search on title, description, tags."""
        if not query:
            return []

        query_lower = query.lower()
        results = []
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
                # Return the SearchIndexItem directly
                results.append(item)

        logger.info(f"Prefix search for '{query}' returned {len(results)} results.")
        # Ensure the return type matches the route's expectation (List[Dict] vs List[SearchIndexItem])
        # If the route expects List[Dict], convert items: [r.model_dump() for r in results]
        # For now, assume route can handle List[SearchIndexItem] or will be updated
        return results 
