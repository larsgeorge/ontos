import logging
import os
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from api.common.config import Settings
from api.common.logging import get_logger
from api.models.audit_log import AuditLogCreate, AuditLogRead
from api.repositories.audit_log_repository import audit_log_repository
from api.db_models.audit_log import AuditLog # Import the DB model

# Use the main logger configuration but add a specific handler for audit logs
file_audit_logger = logging.getLogger("audit_file")
# Prevent propagation to avoid duplicate logging if root logger has handlers
file_audit_logger.propagate = False 


class AuditManager:
    """Manages logging of user actions to file and database."""

    def __init__(self, settings: Settings, db_session: Session):
        self.settings = settings
        self.db = db_session # Store session for potential direct use if needed, though repo is preferred
        self.repository = audit_log_repository
        self._configure_file_logger()

    def _configure_file_logger(self):
        """Configures the file logger for audit trails."""
        log_dir_path = Path(self.settings.APP_AUDIT_LOG_DIR)
        try:
            log_dir_path.mkdir(parents=True, exist_ok=True)
            log_file = log_dir_path / "audit.log"

            # Use JSON formatter for structured logging
            formatter = logging.Formatter(
                '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}',
                datefmt='%Y-%m-%dT%H:%M:%S%z' # ISO 8601 format
            )
            
            # Rotate logs hourly, keeping 24 * 7 = 168 hours (1 week)
            file_handler = TimedRotatingFileHandler(
                log_file, 
                when="H", 
                interval=1, 
                backupCount=168, # Keep 1 week of hourly logs
                encoding='utf-8'
            )
            file_handler.setFormatter(formatter)

            # Clear existing handlers to avoid duplication if re-initialized
            if file_audit_logger.hasHandlers():
                file_audit_logger.handlers.clear()

            file_audit_logger.addHandler(file_handler)
            file_audit_logger.setLevel(logging.INFO) # Log INFO level and above to file
            file_audit_logger.info(f"Audit file logger configured. Logging to: {log_file}")

        except Exception as e:
            # Fallback to standard logger if file logging fails
            main_logger = get_logger(__name__)
            main_logger.error(f"Failed to configure audit file logger at {log_dir_path}: {e}", exc_info=True)
            # Ensure logger is disabled if setup fails
            file_audit_logger.disabled = True 


    async def log_action(
        self,
        db: Session,
        *,
        username: str,
        ip_address: Optional[str],
        feature: str,
        action: str,
        success: bool,
        details: Optional[Dict[str, Any]] = None
    ):
        """Logs an action to both the audit file and the database."""
        log_entry_data = {
            "username": username,
            "ip_address": ip_address,
            "feature": feature,
            "action": action,
            "success": success,
            "details": details or {},
        }

        # 1. Log to file (structured as JSON string)
        if not file_audit_logger.disabled:
            try:
                # Manually construct the JSON message for the file logger
                file_log_message = {
                    "user": username,
                    "ip": ip_address,
                    "feature": feature,
                    "action": action,
                    "success": success,
                    "details": details or {}
                }
                file_audit_logger.info(str(file_log_message).replace("'", '"')) # Basic JSON-like string
            except Exception as e:
                main_logger = get_logger(__name__)
                main_logger.error(f"Failed to write audit log to file: {e}", exc_info=True)

        # 2. Log to database
        try:
            log_entry = AuditLogCreate(**log_entry_data)
            await self.repository.create(db=db, obj_in=log_entry)
        except Exception as e:
            # Use the main application logger for DB errors
            main_logger = get_logger(__name__)
            main_logger.error(f"Failed to write audit log to database: {e}", exc_info=True)
            # Optionally re-raise or handle differently

    async def get_audit_logs(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        username: Optional[str] = None,
        feature: Optional[str] = None,
        action: Optional[str] = None,
        success: Optional[bool] = None,
    ) -> tuple[int, List[AuditLogRead]]:
        """Retrieves audit logs from the database with filtering and pagination."""
        try:
            total_count = await self.repository.get_multi_count(
                db,
                start_time=start_time,
                end_time=end_time,
                username=username,
                feature=feature,
                action=action,
                success=success,
            )
            db_logs = await self.repository.get_multi(
                db,
                skip=skip,
                limit=limit,
                start_time=start_time,
                end_time=end_time,
                username=username,
                feature=feature,
                action=action,
                success=success,
            )
            # Convert DB models to Pydantic models for response
            return total_count, [AuditLogRead.model_validate(log) for log in db_logs]
        except Exception as e:
            main_logger = get_logger(__name__)
            main_logger.error(f"Failed to retrieve audit logs from database: {e}", exc_info=True)
            # Return empty list or re-raise
            return 0, [] 