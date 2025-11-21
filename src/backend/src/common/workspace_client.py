import hashlib
import signal
import time
from functools import cached_property, wraps
from typing import Any, Callable, Dict, Optional, final

from databricks import sql
from databricks.sdk import WorkspaceClient
from fastapi import Depends, Header, Request
from typing import Optional as OptionalType

from .config import Settings, get_settings
from src import __version__

# Configure logging
from src.common.logging import get_logger
logger = get_logger(__name__)

# Module-level cache for workspace clients (persists across requests)
# Key: user identifier (email or token hash), Value: (CachingWorkspaceClient, token_hash, last_access_time)
_CLIENT_CACHE: Dict[str, tuple[Any, str, float]] = {}
_CACHE_CLEANUP_INTERVAL = 300  # Clean up every 5 minutes
_CACHE_MAX_AGE = 600  # Keep clients for max 10 minutes of inactivity
_LAST_CLEANUP_TIME = time.time()

def _cleanup_client_cache():
    """Remove stale client instances from cache."""
    global _LAST_CLEANUP_TIME
    current_time = time.time()

    # Only cleanup if interval has passed
    if current_time - _LAST_CLEANUP_TIME < _CACHE_CLEANUP_INTERVAL:
        return

    _LAST_CLEANUP_TIME = current_time
    stale_keys = [
        key for key, (_, _, last_access) in _CLIENT_CACHE.items()
        if current_time - last_access > _CACHE_MAX_AGE
    ]

    for key in stale_keys:
        del _CLIENT_CACHE[key]
        logger.info(f"Cleaned up stale workspace client for user: {key}")

def _get_token_hash(token: str) -> str:
    """Generate a hash of the token for cache comparison."""
    return hashlib.sha256(token.encode()).hexdigest()[:16]

class TimeoutError(Exception):
    """Exception raised when a function times out."""

class CachingWorkspaceClient(WorkspaceClient):
    def __init__(self, client: WorkspaceClient, timeout: int = 30):
        self._client = client
        self._cache: Dict[str, Any] = {}
        self._cache_times: Dict[str, float] = {}
        self._cache_duration = 60  # 1 minute in seconds
        self._timeout = timeout

    def __call__(self, timeout: int = 30):
        return CachingWorkspaceClient(self._client, timeout=timeout)

    def clear_cache(self, key: Optional[str] = None):
        """Clear the cache. If key is provided, clear only that key."""
        if key:
            self._cache.pop(key, None)
            self._cache_times.pop(key, None)
            logger.info(f"Cleared cache for {key}")
        else:
            self._cache.clear()
            self._cache_times.clear()
            logger.info("Cleared all cache")

    def _make_api_call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute a function with a timeout.
        
        Args:
            func: The function to execute
            *args: Positional arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            The result of the function call
            
        Raises:
            TimeoutError: If the function call times out
        """
        try:
            # Directly call the function without signal-based timeout
            # Rely on underlying SDK/HTTP client timeouts configured elsewhere
            # or add asyncio timeout if func is async and called in event loop
            result = func(*args, **kwargs)
            return result
        except Exception as e:
             # Log the original exception if needed
             logger.error(f"Error during API call in _make_api_call: {e}")
             raise # Re-raise the original exception

    def _cache_result(self, key: str) -> Callable:
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                current_time = time.time()
                # Check if we have a cached result that's still valid
                if (
                    key in self._cache
                    and key in self._cache_times
                    and current_time - self._cache_times[key] < self._cache_duration
                ):
                    logger.info(f"Cache hit for {key} (age: {current_time - self._cache_times[key]:.1f}s)")
                    return self._cache[key]

                # Call the actual function and cache the result
                logger.info(f"Cache miss for {key}, calling Databricks workspace")
                try:
                    result = self._make_api_call(func, *args, **kwargs)
                    self._cache[key] = result
                    self._cache_times[key] = current_time
                    return result
                except TimeoutError as e:
                    logger.error(f"Timeout while fetching {key}: {e}")
                    # Return cached data if available, even if expired
                    if key in self._cache:
                        logger.warning(f"Returning stale cached data for {key}")
                        return self._cache[key]
                    raise
                except Exception as e:
                    logger.error(f"Error fetching {key}: {e}")
                    # Return cached data if available, even if expired
                    if key in self._cache:
                        logger.warning(f"Returning stale cached data for {key}")
                        return self._cache[key]
                    raise
            return wrapper
        return decorator

    @property
    def clusters(self):
        class CachedClusters:
            def __init__(self, parent):
                self._parent = parent

            def list(self):
                return self._parent._cache_result('clusters.list')(
                    lambda: list(self._parent._client.clusters.list())
                )()

        return CachedClusters(self)

    @property
    def connections(self):
        class CachedConnections:
            def __init__(self, parent):
                self._parent = parent

            def list(self):
                return self._parent._cache_result('connections.list')(
                    lambda: list(self._parent._client.connections.list())
                )()

        return CachedConnections(self)

    @property
    def catalogs(self):
        class CachedCatalogs:
            def __init__(self, parent):
                self._parent = parent

            def list(self):
                return self._parent._cache_result('catalogs.list')(
                    lambda: list(self._parent._client.catalogs.list())
                )()

        return CachedCatalogs(self)

    @property
    def schemas(self):
        class CachedSchemas:
            def __init__(self, parent):
                self._parent = parent

            # Schemas are listed per catalog
            def list(self, catalog_name: str):
                cache_key = f'schemas.list::{catalog_name}' 
                return self._parent._cache_result(cache_key)(
                    # Convert generator to list for caching
                    lambda: list(self._parent._client.schemas.list(catalog_name=catalog_name))
                )()

        return CachedSchemas(self)

    @property
    def tables(self):
        class CachedTables:
            def __init__(self, parent):
                self._parent = parent

            # Tables are listed per catalog and schema
            def list(self, catalog_name: str, schema_name: str):
                cache_key = f'tables.list::{catalog_name}::{schema_name}'
                return self._parent._cache_result(cache_key)(
                    # Convert generator to list for caching
                    lambda: list(self._parent._client.tables.list(catalog_name=catalog_name, schema_name=schema_name))
                )()

        return CachedTables(self)

    # Delegate all other attributes to the original client
    def __getattr__(self, name):
        # Ensure we don't accidentally delegate properties we've explicitly handled
        if name in ['clusters', 'connections', 'catalogs', 'schemas', 'tables']:
            # This case shouldn't typically be hit due to @property lookups,
            # but added as a safeguard.
             raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}' - use the property")
        return getattr(self._client, name)

@staticmethod
@final
def _verify_workspace_client(ws: WorkspaceClient) -> WorkspaceClient:
    """
    Verify the Databricks WorkspaceClient configuration and connectivity.
    Sets product info for telemetry tracking.
    """
    # Using reflection to set right value for _product_info as ontos for telemetry
    product_info = getattr(ws.config, '_product_info')
    if product_info[0] != "ontos":
        setattr(ws.config, '_product_info', ('ontos', __version__))
        logger.info(f"Set workspace client product info to: ontos {__version__}")

    # make sure Databricks workspace is accessible
    # use api that works on all workspaces and clusters including group assigned clusters
    try:
        ws.clusters.select_spark_version()
        logger.info("Workspace connectivity verified successfully")
    except Exception as e:
        logger.error(f"Failed to verify workspace connectivity: {e}")
        raise

    return ws

def get_workspace_client(settings: Optional[Settings] = None, timeout: int = 30) -> WorkspaceClient:
    """Get a configured Databricks workspace client with caching.

    Supports both explicit token authentication (for local development) and implicit
    authentication (for Databricks Apps where credentials are provided by the platform).

    Args:
        settings: Application settings (optional, will be fetched if not provided)
        timeout: Timeout in seconds for API calls

    Returns:
        Cached workspace client instance with verified connectivity and telemetry
    """
    if settings is None:
        settings = get_settings()

    # Cleanup stale clients periodically
    _cleanup_client_cache()

    # Determine authentication mode and cache key
    token = settings.DATABRICKS_TOKEN
    
    if token:
        # Explicit token authentication (e.g., local development)
        token_hash = _get_token_hash(token)
        cache_key = f"sp_{token_hash}"  # sp = service principal
        
        # Check if we have a cached client with matching token
        if cache_key in _CLIENT_CACHE:
            cached_client, cached_token_hash, _ = _CLIENT_CACHE[cache_key]
            if cached_token_hash == token_hash:
                # Update last access time
                _CLIENT_CACHE[cache_key] = (cached_client, token_hash, time.time())
                logger.info(f"Reusing cached service principal workspace client")
                return cached_client
        
        # Log environment values with obfuscated token
        masked_token = f"{token[:4]}...{token[-4:]}"
        logger.info(f"Initializing NEW service principal workspace client with host: {settings.DATABRICKS_HOST}, token: {masked_token}, timeout: {timeout}s")
        
        # Create client with explicit token
        # Explicitly set auth_type to 'pat' to prevent SDK from using OAuth env vars
        client = WorkspaceClient(
            host=settings.DATABRICKS_HOST,
            token=token,
            auth_type="pat"  # Force PAT authentication, ignore OAuth env vars
        )
        
        cache_identifier = token_hash
    else:
        # Implicit authentication (e.g., Databricks Apps)
        cache_key = "implicit_auth"
        
        # Check if we have a cached implicit auth client
        if cache_key in _CLIENT_CACHE:
            cached_client, cached_identifier, _ = _CLIENT_CACHE[cache_key]
            # Update last access time
            _CLIENT_CACHE[cache_key] = (cached_client, cached_identifier, time.time())
            logger.info(f"Reusing cached implicit auth workspace client")
            return cached_client
        
        logger.info(f"Initializing NEW implicit auth workspace client with host: {settings.DATABRICKS_HOST}, timeout: {timeout}s")
        
        # Create client with implicit authentication (no token parameter)
        client = WorkspaceClient(host=settings.DATABRICKS_HOST)
        
        cache_identifier = "implicit"

    # Verify connectivity and set telemetry headers
    verified_client = _verify_workspace_client(client)

    caching_client = CachingWorkspaceClient(verified_client, timeout=timeout)

    # Store in cache
    _CLIENT_CACHE[cache_key] = (caching_client, cache_identifier, time.time())

    return caching_client

def get_workspace_client_dependency(timeout: int = 30):
    """Returns the actual dependency function for FastAPI."""

    def _get_ws_client() -> Optional[WorkspaceClient]:
        """The actual FastAPI dependency function that gets the client."""
        client = get_workspace_client(timeout=timeout)
        return client

    return _get_ws_client

def get_obo_workspace_client(
    request: Request,
    settings: Optional[Settings] = None,
    timeout: int = 30
) -> WorkspaceClient:
    """Get a workspace client using the OBO (On-Behalf-Of) token from headers.

    This creates a workspace client using the user's access token from the
    x-forwarded-access-token header, allowing the app to perform operations
    on behalf of the user with their permissions.

    Uses user email as cache key to handle token refresh efficiently - when a user's
    token is refreshed, the old cached client is automatically replaced.

    Args:
        request: FastAPI request object containing headers
        settings: Application settings (optional, will be fetched if not provided)
        timeout: Timeout in seconds for API calls

    Returns:
        Workspace client instance configured with the user's token

    Raises:
        HTTPException: If the OBO token is not present in headers
    """
    from fastapi import HTTPException

    if settings is None:
        settings = get_settings()

    # Cleanup stale clients periodically
    _cleanup_client_cache()

    # Extract OBO token from header
    obo_token = request.headers.get('x-forwarded-access-token')

    if not obo_token:
        logger.warning("OBO token not found in request headers, falling back to service principal")
        # Fall back to service principal client
        return get_workspace_client(settings, timeout)

    # Extract user email for stable cache key
    user_email = request.headers.get('X-Forwarded-Email') or request.headers.get('X-Forwarded-User')

    if not user_email:
        logger.warning("User email not found in headers, using token hash as cache key")
        # Fallback to token-based caching if no email available
        cache_key = f"obo_{_get_token_hash(obo_token)}"
    else:
        # Use email as cache key (stable across token refreshes)
        cache_key = f"user_{user_email}"

    token_hash = _get_token_hash(obo_token)

    # Check if we have a cached client for this user
    if cache_key in _CLIENT_CACHE:
        cached_client, cached_token_hash, _ = _CLIENT_CACHE[cache_key]

        # Check if token has changed (e.g., after refresh)
        if cached_token_hash == token_hash:
            # Same token, reuse client
            _CLIENT_CACHE[cache_key] = (cached_client, token_hash, time.time())
            logger.info(f"Reusing cached OBO workspace client for user: {user_email or 'unknown'}")
            return cached_client
        else:
            # Token changed, need to create new client
            logger.info(f"Token changed for user {user_email or 'unknown'}, creating new workspace client")

    # Log with obfuscated token
    masked_token = f"{obo_token[:4]}...{obo_token[-4:]}"
    logger.info(f"Initializing NEW OBO workspace client for user: {user_email or 'unknown'}, host: {settings.DATABRICKS_HOST}, token: {masked_token}, timeout: {timeout}s")

    # Create client with user's token
    # Explicitly set auth_type to 'pat' to prevent SDK from using OAuth env vars
    client = WorkspaceClient(
        host=settings.DATABRICKS_HOST,
        token=obo_token,
        auth_type="pat"  # Force PAT authentication, ignore OAuth env vars
    )

    # Verify connectivity and set telemetry headers
    verified_client = _verify_workspace_client(client)

    caching_client = CachingWorkspaceClient(verified_client, timeout=timeout)

    # Store in cache with token hash for token change detection
    _CLIENT_CACHE[cache_key] = (caching_client, token_hash, time.time())

    return caching_client

