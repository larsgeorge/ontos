from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class SearchIndexItem(BaseModel):
    """Standardized structure for items returned by searchable assets."""
    id: str = Field(..., description="Unique identifier for the search item (e.g., 'product::uuid', 'term::uuid')")
    type: str = Field(..., description="Type of the asset (e.g., 'data-product', 'glossary-term', 'data-contract')")
    title: str = Field(..., description="Primary display title for the search result")
    description: Optional[str] = Field(None, description="Short description or snippet for context")
    link: str = Field(..., description="URL path to navigate to the item's details page")
    tags: List[str] = Field(default_factory=list, description="Associated tags for filtering/searching")
    feature_id: str = Field(..., description="Identifier of the feature this item belongs to (e.g., 'data-products', 'glossary')")
    # Add other relevant fields if needed, e.g., owner, status, domain
    # owner: Optional[str] = None
    # status: Optional[str] = None
    # domain: Optional[str] = None

    class Config:
        pass # Removed frozen = True

class SearchableAsset(ABC):
    """Abstract Base Class for managers that provide searchable items."""

    @abstractmethod
    def get_search_index_items(self) -> List[SearchIndexItem]:
        """
        Fetches items from the manager's domain and maps them
        to the standardized SearchIndexItem format.

        Returns:
            List[SearchIndexItem]: A list of items prepared for the global search index.
        """
        pass 