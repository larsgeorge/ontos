import logging
import time
from typing import Awaitable, Callable

from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

from api.common.logging import get_logger

logger = get_logger(__name__)

class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging requests and responses."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        logger.info(f"{request.method} {request.url.path} completed in {process_time:.3f}s")
        return response

class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware for handling errors."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        try:
            return await call_next(request)
        except HTTPException as http_exc: # Handle FastAPI's HTTPExceptions specifically
             logger.warning(f"HTTPException caught by middleware: {http_exc.status_code} {http_exc.detail}")
             # Re-raise HTTPException so FastAPI's default handler can format it
             raise http_exc
        except Exception as e:
            logger.error(f"Unhandled error processing request {request.method} {request.url.path}: {e!s}", exc_info=True)
            # Return a generic 500 response for unhandled exceptions
            return Response(
                content="Internal Server Error",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                media_type="text/plain"
            )
