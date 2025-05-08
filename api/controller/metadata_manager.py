import logging
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.catalog import TableInfo, TableType
from pydantic import ValidationError

from api.models.metadata import MetastoreTableInfo
from api.common.workspace_client import CachingWorkspaceClient

from api.common.logging import get_logger

logger = get_logger(__name__)

# Cache for metastore tables to avoid repeated SDK calls within a short period
_metastore_table_cache: Optional[List[MetastoreTableInfo]] = None
_cache_timestamp: Optional[float] = None
CACHE_TTL_SECONDS = 60 # Cache for 1 minute

class MetadataManager:
    def __init__(self, ws_client: CachingWorkspaceClient):
        if ws_client is None:
            raise ValueError("WorkspaceClient cannot be None for MetadataManager")
        self.ws_client = ws_client
        logger.info("MetadataManager initialized.")

    def list_metastore_tables(self, force_refresh: bool = False) -> List[MetastoreTableInfo]:
        """
        Lists accessible tables across all catalogs and schemas in the metastore.
        Leverages the injected DatabricksWorkspaceClient which handles caching.
        """
        global _metastore_table_cache, _cache_timestamp
        # Use client's internal caching logic if force_refresh is not True
        # The manager-level cache might be redundant if client cache works well,
        # but keeping it for now as an example or potential optimization layer.
        
        # Simplified logic: rely primarily on the client's cache mechanism triggered via its methods
        # We just need to iterate correctly.

        all_tables_info: List[MetastoreTableInfo] = []
        try:
            # Use the client's cached catalog list method
            # Correct SDK access pattern: client.catalogs.list()
            catalogs_generator = self.ws_client.catalogs.list()
            # Convert generator to list to get count, assuming catalog list is not huge
            # Alternatively, count while iterating if memory is a concern
            catalogs = list(catalogs_generator) 
            logger.info(f"Found {len(catalogs)} catalogs to scan.")

            for catalog in catalogs:
                catalog_name = catalog.name
                logger.debug(f"Scanning catalog: {catalog_name}")
                try:
                    # Use the client's cached schema list method
                    # Correct SDK access pattern: client.schemas.list(...)
                    # This returns a generator, so we iterate directly
                    schemas_generator = self.ws_client.schemas.list(catalog_name=catalog_name)
                    schema_count = 0
                    for schema in schemas_generator: 
                        schema_count += 1
                        schema_name = schema.name
                        logger.debug(f"Scanning schema: {catalog_name}.{schema_name}")
                        try:
                            # Use the client's cached table list method
                            # Correct SDK access pattern: client.tables.list(...)
                            # This also returns a generator
                            tables_generator = self.ws_client.tables.list(catalog_name=catalog_name, 
                                                                         schema_name=schema_name)
                            table_count_in_schema = 0
                            for table in tables_generator:
                                table_count_in_schema += 1
                                try:
                                    # Basic filtering: Include only MANAGED or EXTERNAL tables
                                    # Could add more filters (e.g., based on owner, tags)
                                    if table.table_type in [TableType.MANAGED, TableType.EXTERNAL]:
                                        table_info = MetastoreTableInfo(
                                            catalog_name=table.catalog_name,
                                            schema_name=table.schema_name,
                                            table_name=table.name,
                                            full_name=table.full_name,
                                            comment=table.comment or "",
                                            owner=table.owner or "Unknown",
                                            table_type=str(table.table_type.value) # Convert Enum to string
                                        )
                                        all_tables_info.append(table_info)
                                except ValidationError as ve:
                                     logger.warning(f"Validation error processing table {table.full_name}: {ve}")
                                except Exception as e_inner:
                                    logger.error(f"Error processing table {catalog_name}.{schema_name}.{table.name}: {e_inner}", exc_info=True)
                            logger.debug(f"Found {table_count_in_schema} tables in schema {catalog_name}.{schema_name}")

                        except Exception as e_mid:
                            # Log error listing tables in a specific schema but continue to next schema
                            logger.error(f"Error listing tables in schema {catalog_name}.{schema_name}: {e_mid}", exc_info=True)
                    logger.info(f"Scanned {schema_count} schemas in catalog {catalog_name}")

                except Exception as e_outer:
                     # Log error listing schemas in a specific catalog but continue to next catalog
                    logger.error(f"Error listing schemas in catalog {catalog_name}: {e_outer}", exc_info=True)

            logger.info(f"Compiled list of {len(all_tables_info)} accessible metastore tables.")
            return all_tables_info

        except Exception as e_top:
            logger.exception(f"Failed to list metastore tables comprehensively: {e_top}")
            return [] # Return empty list on top-level failure

    def search_metastore_tables(self, query: str, limit: int = 50) -> List[MetastoreTableInfo]:
        """Searches the cached metastore tables by full name (case-insensitive)."""
        # Ensure the cache is populated by calling the main list method if needed
        # Note: This assumes list_metastore_tables handles its own caching/refresh logic
        all_tables = self.list_metastore_tables() 
        
        if not query:
            # Return the first N items if query is empty, similar to get_initial
            return all_tables[:limit]

        query_lower = query.lower()
        results = [
            table for table in all_tables 
            if query_lower in table.full_name.lower()
        ]
        logger.info(f"Metastore table search for '{query}' found {len(results)} results (limited to {limit}).")
        return results[:limit] # Apply limit to search results
        
    def get_initial_metastore_tables(self, limit: int = 20) -> List[MetastoreTableInfo]:
        """Returns the first N tables from the cached list."""
        all_tables = self.list_metastore_tables()
        logger.info(f"Returning initial {min(limit, len(all_tables))} metastore tables.")
        return all_tables[:limit]

    def get_schema(self, schema_name: str) -> Dict[str, Any]:
        """Loads and parses a JSON schema file from the schemas directory."""
        try:
            schemas_dir = Path(__file__).parent.parent / 'schemas'
            schema_file = schemas_dir / f"{schema_name}.json"
            
            if not schema_file.exists():
                logger.warning(f"Schema file not found: {schema_file}")
                raise FileNotFoundError(f"Schema '{schema_name}' not found.")

            logger.info(f"Loading schema file: {schema_file}")
            with open(schema_file, 'r') as f:
                schema_data = json.load(f) # Use json.load for direct parsing
            return schema_data
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from schema {schema_name}: {e}")
            raise ValueError(f"Schema '{schema_name}' contains invalid JSON.")
        except Exception as e:
            logger.exception(f"Unexpected error loading schema '{schema_name}': {e}")
            raise

    def clear_cache(self):
        """Clears the metastore table cache."""
        # Note: The current implementation uses the CachingWorkspaceClient's cache primarily.
        # This manager-level cache logic might be less relevant now.
        # Consider removing if CachingWorkspaceClient handles all caching needs.
        logger.info("Clearing manager-level cache (if any). Client cache persists based on its TTL.")
        # Placeholder for potential future manager-level cache clearing:
        # global _metastore_table_cache, _cache_timestamp
        # _metastore_table_cache = None
        # _cache_timestamp = None

# Example usage (for testing or direct invocation if needed)
if __name__ == '__main__':
    # This requires DATABRICKS_HOST and DATABRICKS_TOKEN to be set in environment
    # or other SDK authentication methods.
    logging.basicConfig(level=logging.INFO)
    try:
        # Ensure SDK client is initialized correctly for testing
        # Note: Requires appropriate environment variables or config
        ws_sdk_client = WorkspaceClient() 
        cached_client = CachingWorkspaceClient(ws_sdk_client) # Wrap it
        manager = MetadataManager(cached_client)
        
        print("Listing tables (first time)...")
        tables = manager.list_metastore_tables()
        print(f"Found {len(tables)} tables.")
        # Example: Print details of the first few tables found
        # for table in tables[:10]: 
        #     print(f"- {table.full_name} (Type: {table.table_type}, Owner: {table.owner})")

        # Example of using cache (commented out by default)
        # print("\nListing tables (cached)...")
        # tables_cached = manager.list_metastore_tables()
        # print(f"Found {len(tables_cached)} tables from cache.")

        # Example of forcing refresh (commented out by default)
        # print("\nListing tables (forced refresh)...")
        # tables_refreshed = manager.list_metastore_tables(force_refresh=True)
        # print(f"Found {len(tables_refreshed)} tables after refresh.")

    except Exception as main_e:
        print(f"An error occurred during standalone test: {main_e}")
        # Optionally log the exception traceback for more details
        # logger.exception("Error during standalone test run") 