import functools
from typing import Any, Callable, Coroutine, Dict, Optional

from fastapi import Depends, Request, HTTPException, Response, status
from sqlalchemy.orm import Session

# Import Annotated dependency types
from api.common.dependencies import (
    DBSessionDep,
    AuditManagerDep,
    AuditCurrentUserDep,
    get_current_user_details_for_audit # For type hinting _audit_user if needed, or can remove if type is inferred
)
from api.controller.audit_manager import AuditManager # For type hint
from api.models.users import UserInfo # For type hint

# Placeholder for a more sophisticated way to extract details
# This function will need to be context-aware or configurable per route
def _extract_details_default(
    request: Request, 
    response_or_exc: Any, # Can be a Response, HTTPException, or other Exception
    route_args: tuple, 
    route_kwargs: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Default placeholder function to extract details from the request and response/exception.
    This needs careful implementation to avoid logging sensitive data.
    """
    details = {}
    if request.path_params:
        details["path_params"] = dict(request.path_params)
    
    # Try to find Pydantic models in route arguments to log as request_body_preview
    # Search in positional arguments first
    found_body_preview = False
    for arg in route_args:
        if hasattr(arg, "model_dump") and callable(arg.model_dump):
            try:
                # Be very careful about what is dumped. Exclude sensitive fields.
                details["request_body_preview"] = arg.model_dump(mode='json', exclude_none=True, exclude_defaults=True) # or a subset
                found_body_preview = True
                break
            except Exception:
                if "request_body_preview" not in details: # Avoid overwriting if a later one fails
                    details["request_body_preview"] = "Error dumping model from positional args"
        elif isinstance(arg, dict) and not found_body_preview: # Log first dict if no Pydantic model found yet
             details["request_body_preview"] = arg # Or a summary
             # found_body_preview = True # Decide if a dict should stop search for Pydantic in kwargs

    # If not found in positional, check keyword arguments
    if not found_body_preview:
        for kwarg_value in route_kwargs.values():
            if hasattr(kwarg_value, "model_dump") and callable(kwarg_value.model_dump):
                try:
                    details["request_body_preview"] = kwarg_value.model_dump(mode='json', exclude_none=True, exclude_defaults=True)
                    found_body_preview = True
                    break
                except Exception:
                    if "request_body_preview" not in details:
                        details["request_body_preview"] = "Error dumping model from keyword args"
            elif isinstance(kwarg_value, dict) and not found_body_preview:
                 details["request_body_preview"] = kwarg_value # Or a summary
                 # found_body_preview = True # Decide if a dict should stop search

    # If an exception occurred, log its type and detail
    if isinstance(response_or_exc, HTTPException):
        details["exception"] = {"type": "HTTPException", "status_code": response_or_exc.status_code, "detail": response_or_exc.detail}
    elif isinstance(response_or_exc, Exception):
        details["exception"] = {"type": type(response_or_exc).__name__, "message": str(response_or_exc)}
        
    return details

def audit_action(
    feature: str,
    action: Optional[str] = None,
    details_extractor: Callable[ 
        [Request, Any, tuple, Dict[str, Any]], 
        Optional[Dict[str, Any]] 
    ] = _extract_details_default
):
    """
    Decorator to log user actions for a FastAPI route.
    """
    def decorator(func: Callable[..., Coroutine[Any, Any, Any]]):
        @functools.wraps(func)
        async def wrapper(
            *args: Any,
            # Use Annotated types for audit-specific dependencies
            # These are keyword-only arguments due to *args before them.
            _audit_request: Request = Depends(lambda r: r), # Request can stay as direct Depends
            _audit_db_session: DBSessionDep, # Use Annotated type
            _audit_mgr: AuditManagerDep,       # Use Annotated type
            _audit_user: AuditCurrentUserDep,  # Use new Annotated type
            **kwargs: Any
        ):
            username = _audit_user.username if _audit_user else "anonymous"
            ip_address = _audit_request.client.host if _audit_request.client else None
            
            effective_action = action
            if effective_action is None:
                method_to_action = {
                    "POST": "CREATE", "PUT": "UPDATE",
                    "PATCH": "UPDATE", "DELETE": "DELETE",
                }
                effective_action = method_to_action.get(_audit_request.method.upper(), _audit_request.method.upper())

            log_success = False
            response_or_exception_data = None
            try:
                response_or_exception_data = await func(*args, **kwargs)
                log_success = True

                if isinstance(response_or_exception_data, Response): # Includes JSONResponse, HTTPException
                    if not (200 <= response_or_exception_data.status_code < 300):
                        log_success = False
                # If func returns non-Response (e.g. Pydantic model), FastAPI makes it a 200 response by default.

            except HTTPException as http_exc:
                response_or_exception_data = http_exc
                log_success = False # Already set by HTTPException handler
                if 200 <= http_exc.status_code < 300: # Unlikely for an exception, but good to be thorough
                    log_success = True 
                raise
            except Exception as e:
                response_or_exception_data = e
                log_success = False
                raise
            finally:
                extracted_details = None
                if details_extractor:
                    try:
                        extracted_details = details_extractor(_audit_request, response_or_exception_data, args, kwargs)
                    except Exception as e_detail:
                        extracted_details = {"error_extracting_details": str(e_detail)}
                
                await _audit_mgr.log_action(
                    db=_audit_db_session,
                    username=username,
                    ip_address=ip_address,
                    feature=feature,
                    action=effective_action,
                    success=log_success,
                    details=extracted_details,
                )
            return response_or_exception_data
        return wrapper
    return decorator

# get_current_user_details_for_audit function is removed from here, will be moved to dependencies.py 