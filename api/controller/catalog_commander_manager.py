from typing import Any, Dict, List

from databricks import sql
from databricks.sdk import WorkspaceClient

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
        """Get dataset content and schema from a specific path.
        
        Args:
            dataset_path: Full path to the dataset (catalog.schema.table)
            
        Returns:
            Dictionary containing schema and data information
        """
        connection = None
        try:
            logger.info(f"Fetching dataset content for: {dataset_path}")
            connection = sql.connect(
                server_hostname=self.client.config.host,
                http_path=f"/sql/1.0/warehouses/{self.client.config.warehouse_id}",
                access_token=self.client.config.token
            )
            cursor = connection.cursor()

            # Format the dataset path properly for SQL
            path_parts = dataset_path.split('.')
            quoted_path = '.'.join(f'`{part}`' for part in path_parts)

            # Get data with Arrow for better performance
            logger.info(f"Executing SQL query: SELECT * FROM {quoted_path} LIMIT 1000")
            cursor.execute(f"SELECT * FROM {quoted_path} LIMIT 1000")
            arrow_table = cursor.fetchall_arrow()

            # Convert Arrow table to pandas DataFrame
            import pandas as pd
            df = arrow_table.to_pandas()

            # Get schema from DataFrame
            schema = [
                {
                    'name': col_name,
                    'type': str(df[col_name].dtype),
                    'nullable': df[col_name].hasnans
                }
                for col_name in df.columns
            ]

            # Convert DataFrame to records
            rows = df.replace({pd.NA: None}).to_dict('records')

            # Convert any non-string values to strings for JSON serialization
            for row in rows:
                for key, value in row.items():
                    if value is not None:
                        row[key] = str(value)

            result = {
                'schema': schema,
                'data': rows,
                'total_rows': len(rows)
            }

            logger.info(f"Successfully retrieved dataset with {len(rows)} rows and {len(schema)} columns")
            return result

        finally:
            if connection:
                try:
                    connection.close()
                    logger.info("Database connection closed")
                except Exception as e:
                    logger.warning(f"Error closing database connection: {e!s}")

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
