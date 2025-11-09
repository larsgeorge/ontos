"""
Unit tests for search_registry module

Tests search registry functionality including:
- Decorator registration
- Registry management
- Type validation
"""
import pytest
from typing import List

from src.common.search_registry import searchable_asset, SEARCHABLE_ASSET_MANAGERS
from src.common.search_interfaces import SearchableAsset


class TestSearchRegistry:
    """Test suite for search registry"""

    def setup_method(self):
        """Clear registry before each test."""
        SEARCHABLE_ASSET_MANAGERS.clear()

    def test_searchable_asset_decorator_registers_class(self):
        """Test that decorator registers class."""
        # Arrange
        class TestManager(SearchableAsset):
            def get_searchable_items(self, db, **kwargs) -> List[dict]:
                return []

        # Act
        searchable_asset(TestManager)

        # Assert
        assert TestManager in SEARCHABLE_ASSET_MANAGERS

    def test_searchable_asset_decorator_returns_class(self):
        """Test that decorator returns the class unchanged."""
        # Arrange
        class TestManager(SearchableAsset):
            def get_searchable_items(self, db, **kwargs) -> List[dict]:
                return []

        # Act
        result = searchable_asset(TestManager)

        # Assert
        assert result is TestManager

    def test_searchable_asset_decorator_as_decorator(self):
        """Test decorator used with @ syntax."""
        # Arrange & Act
        @searchable_asset
        class TestManager(SearchableAsset):
            def get_searchable_items(self, db, **kwargs) -> List[dict]:
                return []

        # Assert
        assert TestManager in SEARCHABLE_ASSET_MANAGERS

    def test_searchable_asset_rejects_non_searchable_class(self):
        """Test decorator rejects class not inheriting from SearchableAsset."""
        # Arrange
        class InvalidManager:
            pass

        # Act & Assert
        with pytest.raises(TypeError, match="must inherit from SearchableAsset"):
            searchable_asset(InvalidManager)

    def test_searchable_asset_prevents_duplicate_registration(self):
        """Test decorator doesn't register same class twice."""
        # Arrange
        class TestManager(SearchableAsset):
            def get_searchable_items(self, db, **kwargs) -> List[dict]:
                return []

        # Act
        searchable_asset(TestManager)
        initial_count = len(SEARCHABLE_ASSET_MANAGERS)
        searchable_asset(TestManager)  # Register again
        final_count = len(SEARCHABLE_ASSET_MANAGERS)

        # Assert
        assert initial_count == final_count
        assert SEARCHABLE_ASSET_MANAGERS.count(TestManager) == 1

    def test_searchable_asset_registers_multiple_classes(self):
        """Test registering multiple different classes."""
        # Arrange
        class Manager1(SearchableAsset):
            def get_searchable_items(self, db, **kwargs) -> List[dict]:
                return []

        class Manager2(SearchableAsset):
            def get_searchable_items(self, db, **kwargs) -> List[dict]:
                return []

        # Act
        searchable_asset(Manager1)
        searchable_asset(Manager2)

        # Assert
        assert Manager1 in SEARCHABLE_ASSET_MANAGERS
        assert Manager2 in SEARCHABLE_ASSET_MANAGERS
        assert len(SEARCHABLE_ASSET_MANAGERS) >= 2

    def test_registry_is_list(self):
        """Test SEARCHABLE_ASSET_MANAGERS is a list."""
        assert isinstance(SEARCHABLE_ASSET_MANAGERS, list)

    def test_registry_initially_cleared(self):
        """Test registry is cleared at test start."""
        # Due to setup_method, registry should be empty
        assert len(SEARCHABLE_ASSET_MANAGERS) == 0

