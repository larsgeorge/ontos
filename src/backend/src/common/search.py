import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, TypeVar

from .config import get_config_manager
from .logging import get_logger

logger = get_logger(__name__)

T = TypeVar('T')

@dataclass
class SearchIndex:
    """Represents a search index for a dataclass."""
    name: str
    model_class: Type[T]
    search_fields: List[str]
    index_file: Path

class SearchService:
    """Service for indexing and searching dataclasses."""

    def __init__(self) -> None:
        """Initialize the search service."""
        config = get_config_manager()
        self.index_dir = config.data_dir / 'search'
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.indices: Dict[str, SearchIndex] = {}

    def register_index(
        self,
        name: str,
        model_class: Type[T],
        search_fields: List[str]
    ) -> None:
        """Register a new search index.
        
        Args:
            name: Name of the index
            model_class: Dataclass to index
            search_fields: List of fields to include in search
        """
        index_file = self.index_dir / f"{name}.json"
        self.indices[name] = SearchIndex(
            name=name,
            model_class=model_class,
            search_fields=search_fields,
            index_file=index_file
        )
        logger.info(f"Registered search index {name}")

    def index_item(self, name: str, item: Any) -> None:
        """Index a single item.
        
        Args:
            name: Name of the index
            item: Item to index
            
        Raises:
            KeyError: If index not found
        """
        if name not in self.indices:
            raise KeyError(f"Index {name} not found")

        index = self.indices[name]
        items = self._load_index(index)

        # Convert item to dict and extract search fields
        item_dict = {
            k: v for k, v in item.__dict__.items()
            if k in index.search_fields
        }
        item_dict['id'] = getattr(item, 'id', None)
        item_dict['_indexed_at'] = datetime.utcnow().isoformat()

        # Update or append item
        for i, existing in enumerate(items):
            if existing['id'] == item_dict['id']:
                items[i] = item_dict
                break
        else:
            items.append(item_dict)

        self._save_index(index, items)
        logger.debug(f"Indexed item {item_dict['id']} in {name}")

    def search(
        self,
        name: str,
        query: str,
        limit: int = 10,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Search for items in an index.
        
        Args:
            name: Name of the index
            query: Search query
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of matching items
            
        Raises:
            KeyError: If index not found
        """
        if name not in self.indices:
            raise KeyError(f"Index {name} not found")

        index = self.indices[name]
        items = self._load_index(index)

        # Simple prefix search on all search fields
        query = query.lower()
        matches = []

        for item in items:
            for field in index.search_fields:
                if field in item and isinstance(item[field], str):
                    if item[field].lower().startswith(query):
                        matches.append(item)
                        break

        # Sort by most recently indexed
        matches.sort(key=lambda x: x['_indexed_at'], reverse=True)

        return matches[offset:offset + limit]

    def _load_index(self, index: SearchIndex) -> List[Dict[str, Any]]:
        """Load items from an index file.
        
        Args:
            index: Search index
            
        Returns:
            List of indexed items
        """
        if not index.index_file.exists():
            return []

        try:
            with open(index.index_file) as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Error loading index {index.name}: {e!s}")
            return []

    def _save_index(self, index: SearchIndex, items: List[Dict[str, Any]]) -> None:
        """Save items to an index file.
        
        Args:
            index: Search index
            items: List of items to save
        """
        try:
            with open(index.index_file, 'w') as f:
                json.dump(items, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving index {index.name}: {e!s}")
            raise

# Global search service instance
search_service: Optional[SearchService] = None

def init_search_service() -> None:
    """Initialize the global search service instance."""
    global search_service
    search_service = SearchService()

def get_search_service() -> SearchService:
    """Get the global search service instance.
    
    Returns:
        Search service
        
    Raises:
        RuntimeError: If search service is not initialized
    """
    if not search_service:
        raise RuntimeError("Search service not initialized")
    return search_service
