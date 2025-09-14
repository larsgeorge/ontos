from typing import Any, Dict, List

from databricks.sdk import WorkspaceClient
from urllib.parse import quote

from ..common.logging import get_logger

logger = get_logger(__name__)

class CatalogCommanderManager:
    """Manages catalog operations and queries."""

    def __init__(self, client: WorkspaceClient):
        """Initialize the catalog commander manager.
        
        Args:
            client: Databricks workspace client
        """
        logger.debug("Initializing CatalogCommanderManager...")
        self.client = client
        logger.debug("CatalogCommanderManager initialized successfully")

    def list_catalogs(self) -> List[Dict[str, Any]]:
        """List all catalogs in the Databricks workspace.
        
        Returns:
            List of catalog information dictionaries
        """
        try:
            logger. debug("Fetching all catalogs from Databricks workspace")
            catalogs = list(self.client.catalogs.list())  # Convert generator to list
            logger.debug(f"Retrieved {len(catalogs)} catalogs from Databricks")

            result = [{
                'id': catalog.name,
                'name': catalog.name,
                'type': 'catalog',
                'children': [],  # Empty array means children not fetched yet
                'hasChildren': True  # Catalogs can always have schemas
            } for catalog in catalogs]

            logger.debug(f"Successfully formatted {len(result)} catalogs")
            return result
        except Exception as e:
            logger.error(f"Error in list_catalogs: {e!s}", exc_info=True)
            raise

    def list_schemas(self, catalog_name: str) -> List[Dict[str, Any]]:
        """List all schemas in a catalog.
        
        Args:
            catalog_name: Name of the catalog
            
        Returns:
            List of schema information dictionaries
        """
        logger.debug(f"Fetching schemas for catalog: {catalog_name}")
        schemas = list(self.client.schemas.list(catalog_name=catalog_name))  # Convert generator to list

        result = [{
            'id': f"{catalog_name}.{schema.name}",
            'name': schema.name,
            'type': 'schema',
            'children': [],  # Empty array means children not fetched yet
            'hasChildren': True  # Schemas can always have tables
        } for schema in schemas]

        logger.debug(f"Successfully retrieved {len(result)} schemas for catalog {catalog_name}")
        return result

    def list_tables(self, catalog_name: str, schema_name: str) -> List[Dict[str, Any]]:
        """List all tables and views in a schema.
        
        Args:
            catalog_name: Name of the catalog
            schema_name: Name of the schema
            
        Returns:
            List of table/view information dictionaries
        """
        logger.debug(f"Fetching tables for schema: {catalog_name}.{schema_name}")
        tables = list(self.client.tables.list(catalog_name=catalog_name, schema_name=schema_name))  # Convert generator to list

        result = [{
            'id': f"{catalog_name}.{schema_name}.{table.name}",
            'name': table.name,
            'type': 'view' if hasattr(table, 'table_type') and table.table_type == 'VIEW' else 'table',
            'children': [],  # Empty array for consistency
            'hasChildren': False  # Tables/views are leaf nodes
        } for table in tables]

        logger.debug(f"Successfully retrieved {len(result)} tables for schema {catalog_name}.{schema_name}")
        return result

    def list_views(self, catalog_name: str, schema_name: str) -> List[Dict[str, Any]]:
        """List all views in a schema.

        Args:
            catalog_name: Name of the catalog
            schema_name: Name of the schema

        Returns:
            List of view information dictionaries
        """
        logger.debug(f"Fetching views for schema: {catalog_name}.{schema_name}")
        try:
            # Use tables.list and filter for views
            all_tables = list(self.client.tables.list(catalog_name=catalog_name, schema_name=schema_name))
            views = [tbl for tbl in all_tables if hasattr(tbl, 'table_type') and tbl.table_type == 'VIEW']

            result = [{
                'id': f"{catalog_name}.{schema_name}.{view.name}",
                'name': view.name,
                'type': 'view',
                'children': [],
                'hasChildren': False
            } for view in views]

            logger.debug(f"Successfully retrieved {len(result)} views for schema {catalog_name}.{schema_name}")
            return result
        except Exception as e:
            logger.error(f"Error listing views for {catalog_name}.{schema_name}: {e!s}", exc_info=True)
            raise

    def list_functions(self, catalog_name: str, schema_name: str) -> List[Dict[str, Any]]:
        """List all functions in a schema.

        Args:
            catalog_name: Name of the catalog
            schema_name: Name of the schema

        Returns:
            List of function information dictionaries
        """
        logger.info(f"Fetching functions for schema: {catalog_name}.{schema_name}")
        try:
            functions = list(self.client.functions.list(catalog_name=catalog_name, schema_name=schema_name))

            result = [{
                'id': function.full_name, # Functions usually have full_name
                'name': function.name,
                'type': 'function',
                'children': [],
                'hasChildren': False
            } for function in functions]

            logger.info(f"Successfully retrieved {len(result)} functions for schema {catalog_name}.{schema_name}")
            return result
        except Exception as e:
            logger.error(f"Error listing functions for {catalog_name}.{schema_name}: {e!s}", exc_info=True)
            raise

    def get_dataset(self, dataset_path: str) -> Dict[str, Any]:
        """Get dataset schema and lightweight details using the shared WorkspaceClient.

        This avoids requiring a SQL Warehouse. It returns column metadata only.

        Args:
            dataset_path: Full path to the dataset (catalog.schema.table)

        Returns:
            Dictionary containing at least 'schema': List[{name, type, nullable}]
        """
        logger.info(f"Fetching dataset metadata for: {dataset_path}")
        try:
            parts = dataset_path.split('.')
            if len(parts) != 3:
                raise ValueError("dataset_path must be in the form catalog.schema.table")
            catalog_name, schema_name, table_name = parts

            # Use Unity Catalog Tables API to get table details. Some SDK versions don't expose `.get`.
            tbl = None
            try:
                # Prefer SDK method if available
                get_method = getattr(self.client.tables, 'get', None)
                if callable(get_method):
                    tbl = get_method(catalog_name=catalog_name, schema_name=schema_name, name=table_name)
                else:
                    raise AttributeError('tables.get not available')
            except Exception:
                # Fallback to direct REST call via api_client
                path = f"/api/2.1/unity-catalog/tables/{quote(dataset_path, safe='')}"
                tbl = self.client.api_client.do('GET', path)

            # The SDK returns TableInfo; columns is a list of ColumnInfo-like models
            schema: List[Dict[str, Any]] = []
            columns_iter = None
            if hasattr(tbl, 'columns'):
                columns_iter = tbl.columns
            elif isinstance(tbl, dict) and 'columns' in tbl:
                columns_iter = tbl['columns']

            if columns_iter:
                for col in columns_iter:
                    # ColumnInfo fields vary slightly by SDK version; use getattr with fallbacks
                    if isinstance(col, dict):
                        col_name = col.get('name') or col.get('column_name')
                        col_type = col.get('type_text') or col.get('type_name') or col.get('data_type')
                        nullable = col.get('nullable')
                    else:
                        col_name = getattr(col, 'name', None) or getattr(col, 'column_name', None)
                        col_type = getattr(col, 'type_text', None) or getattr(col, 'type_name', None) or getattr(col, 'data_type', None)
                        nullable = getattr(col, 'nullable', None)
                    schema.append({
                        'name': col_name,
                        'type': col_type,
                        'nullable': nullable,
                    })

            result: Dict[str, Any] = {
                'schema': schema,
                'data': [],
                'total_rows': 0,
            }

            logger.info(f"Successfully retrieved metadata with {len(schema)} columns for {dataset_path}")
            return result
        except Exception as e:
            logger.error(f"Error fetching dataset metadata for {dataset_path}: {e!s}", exc_info=True)
            raise

    def health_check(self) -> Dict[str, str]:
        """Check if the catalog API is healthy.
        
        Returns:
            Dictionary containing health status
        """
        try:
            # Try to list catalogs as a health check
            self.client.catalogs.list()
            logger.info("Health check successful")
            return {"status": "healthy"}
        except Exception as e:
            error_msg = f"Health check failed: {e!s}"
            logger.error(error_msg)
            raise
