"""
Workspace Manager

Handles Databricks workspace asset search and discovery operations.
Provides unified interface for searching tables, notebooks, jobs, and other workspace objects.
"""

from typing import List, Optional
from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import NotFound, PermissionDenied, DatabricksError
from databricks.sdk.service.workspace import ObjectType

from src.models.workspace import WorkspaceAsset
from src.common.logging import get_logger

logger = get_logger(__name__)


class WorkspaceManager:
    """Manager for Databricks workspace asset operations."""
    
    def __init__(self, ws_client: Optional[WorkspaceClient] = None):
        """
        Initialize the WorkspaceManager.
        
        Args:
            ws_client: Optional Databricks WorkspaceClient for SDK operations
        """
        self._ws_client = ws_client
        
        if not self._ws_client:
            logger.warning("WorkspaceClient not provided to WorkspaceManager. SDK operations will fail.")
    
    def search_workspace_assets(
        self,
        asset_type: str,
        search_term: Optional[str] = None,
        limit: int = 25
    ) -> List[WorkspaceAsset]:
        """
        Search for Databricks workspace assets by type and optional search term.
        
        Args:
            asset_type: Type of asset to search ('table', 'notebook', 'job', 'view', 'function', 'model')
            search_term: Optional search term to filter results by name/identifier
            limit: Maximum number of results to return (1-100)
            
        Returns:
            List of WorkspaceAsset objects matching the search criteria
            
        Raises:
            ValueError: If workspace client is not configured or asset_type is invalid
            PermissionDenied: If user lacks permissions to access requested resources
            DatabricksError: For other SDK-related errors
        """
        if not self._ws_client:
            raise ValueError("Workspace client not configured")
        
        # Validate limit
        limit = max(1, min(limit, 100))
        
        asset_type_lower = asset_type.lower()
        logger.info(f"Searching workspace assets: type={asset_type_lower}, term={search_term}, limit={limit}")
        
        try:
            if asset_type_lower == 'table':
                return self._search_tables(search_term, limit)
            elif asset_type_lower == 'notebook':
                return self._search_notebooks(search_term, limit)
            elif asset_type_lower == 'job':
                return self._search_jobs(search_term, limit)
            elif asset_type_lower in ('view', 'function', 'model', 'dashboard'):
                # Placeholder for future implementation
                logger.warning(f"Asset type '{asset_type}' search not yet implemented")
                return []
            else:
                raise ValueError(f"Unsupported asset type: {asset_type}")
                
        except PermissionDenied as e:
            logger.error(f"Permission denied searching {asset_type}: {e}")
            raise
        except ValueError:
            raise
        except DatabricksError as e:
            logger.error(f"Databricks error searching {asset_type}: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error searching {asset_type}: {e}", exc_info=True)
            raise
    
    def _search_tables(self, search_term: Optional[str], limit: int) -> List[WorkspaceAsset]:
        """
        Search for Unity Catalog tables.
        
        Note: This implementation searches across available catalogs and schemas.
        For large workspaces, this may be slow. Consider implementing catalog/schema
        filters or caching strategies for production use.
        """
        results: List[WorkspaceAsset] = []
        
        try:
            # Get available catalogs
            catalogs = list(self._ws_client.catalogs.list())
            
            for catalog in catalogs:
                if len(results) >= limit:
                    break
                
                try:
                    # Get schemas in this catalog
                    schemas = list(self._ws_client.schemas.list(catalog_name=catalog.name))
                    
                    for schema in schemas:
                        if len(results) >= limit:
                            break
                        
                        try:
                            # List tables in this schema
                            tables = self._ws_client.tables.list(
                                catalog_name=catalog.name,
                                schema_name=schema.name
                            )
                            
                            for table in tables:
                                if len(results) >= limit:
                                    break
                                
                                # Apply search filter if provided
                                if search_term:
                                    table_name = table.name or ""
                                    full_name = table.full_name or ""
                                    if search_term.lower() not in table_name.lower() and \
                                       search_term.lower() not in full_name.lower():
                                        continue
                                
                                results.append(WorkspaceAsset(
                                    type='table',
                                    identifier=table.full_name or f"{catalog.name}.{schema.name}.{table.name}",
                                    name=table.name or "unknown",
                                    path=f"/{catalog.name}/{schema.name}/{table.name}",
                                    url=None  # Could construct Databricks URL if needed
                                ))
                                
                        except (NotFound, PermissionDenied) as e:
                            # Skip schemas we can't access
                            logger.debug(f"Cannot access tables in {catalog.name}.{schema.name}: {e}")
                            continue
                            
                except (NotFound, PermissionDenied) as e:
                    # Skip catalogs we can't access
                    logger.debug(f"Cannot access schemas in catalog {catalog.name}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error searching tables: {e}", exc_info=True)
            # Return partial results rather than failing completely
            
        logger.info(f"Found {len(results)} tables matching search criteria")
        return results
    
    def _search_notebooks(self, search_term: Optional[str], limit: int) -> List[WorkspaceAsset]:
        """
        Search for notebooks in the workspace.
        
        Note: This searches common paths like /Users, /Repos, and /Shared.
        For large workspaces, consider implementing path-based filtering.
        """
        results: List[WorkspaceAsset] = []
        search_paths = ['/Users', '/Repos', '/Shared']
        
        for base_path in search_paths:
            if len(results) >= limit:
                break
            
            try:
                # Recursively list workspace objects
                self._search_notebooks_recursive(
                    path=base_path,
                    search_term=search_term,
                    results=results,
                    limit=limit,
                    max_depth=5,
                    current_depth=0
                )
            except (NotFound, PermissionDenied) as e:
                # Skip paths we can't access
                logger.debug(f"Cannot access path {base_path}: {e}")
                continue
            except Exception as e:
                logger.warning(f"Error searching notebooks in {base_path}: {e}")
                continue
        
        logger.info(f"Found {len(results)} notebooks matching search criteria")
        return results
    
    def _search_notebooks_recursive(
        self,
        path: str,
        search_term: Optional[str],
        results: List[WorkspaceAsset],
        limit: int,
        max_depth: int,
        current_depth: int
    ):
        """Recursively search for notebooks in workspace paths."""
        if len(results) >= limit or current_depth >= max_depth:
            return
        
        try:
            objects = self._ws_client.workspace.list(path=path)
            
            for obj in objects:
                if len(results) >= limit:
                    break
                
                # If it's a notebook, add to results if matches search term
                if obj.object_type == ObjectType.NOTEBOOK:
                    if search_term:
                        obj_path = obj.path or ""
                        if search_term.lower() not in obj_path.lower():
                            continue
                    
                    # Extract name from path
                    name = obj.path.split('/')[-1] if obj.path else "unknown"
                    
                    results.append(WorkspaceAsset(
                        type='notebook',
                        identifier=obj.path or "unknown",
                        name=name,
                        path=obj.path,
                        url=None
                    ))
                
                # If it's a directory, recurse into it
                elif obj.object_type == ObjectType.DIRECTORY:
                    self._search_notebooks_recursive(
                        path=obj.path,
                        search_term=search_term,
                        results=results,
                        limit=limit,
                        max_depth=max_depth,
                        current_depth=current_depth + 1
                    )
                    
        except (NotFound, PermissionDenied):
            # Skip directories we can't access
            pass
        except Exception as e:
            logger.debug(f"Error listing workspace path {path}: {e}")
    
    def _search_jobs(self, search_term: Optional[str], limit: int) -> List[WorkspaceAsset]:
        """Search for Databricks jobs."""
        results: List[WorkspaceAsset] = []
        
        try:
            # Use SDK's built-in filtering if search term provided
            jobs_list = self._ws_client.jobs.list(
                name=search_term if search_term else None,
                limit=limit
            )
            
            for job in jobs_list:
                if len(results) >= limit:
                    break
                
                job_name = job.settings.name if job.settings else f"Job {job.job_id}"
                
                results.append(WorkspaceAsset(
                    type='job',
                    identifier=str(job.job_id),
                    name=job_name,
                    path=None,
                    url=None  # Could construct Databricks job URL if needed
                ))
                
        except Exception as e:
            logger.error(f"Error searching jobs: {e}", exc_info=True)
        
        logger.info(f"Found {len(results)} jobs matching search criteria")
        return results

