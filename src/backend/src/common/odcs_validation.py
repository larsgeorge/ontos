"""
ODCS JSON Schema Validation

This module provides validation utilities for Open Data Contract Standard (ODCS) v3.0.2
compliance using the official JSON schema.
"""
import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional

import jsonschema
from jsonschema import ValidationError, Draft7Validator
from src.common.logging import get_logger

logger = get_logger(__name__)

# Path to the ODCS JSON schema file
ODCS_SCHEMA_PATH = Path(__file__).parent.parent / "schemas" / "odcs-json-schema-v3.0.2-strict.json"


class ODCSValidationError(Exception):
    """Custom exception for ODCS validation errors"""
    def __init__(self, message: str, validation_errors: Optional[List[str]] = None):
        self.message = message
        self.validation_errors = validation_errors or []
        super().__init__(self.message)


class ODCSValidator:
    """ODCS JSON Schema Validator"""

    def __init__(self):
        self._schema = None
        self._validator = None
        self._load_schema()

    def _load_schema(self):
        """Load the ODCS JSON schema"""
        try:
            if not ODCS_SCHEMA_PATH.exists():
                raise FileNotFoundError(f"ODCS schema file not found at {ODCS_SCHEMA_PATH}")

            with open(ODCS_SCHEMA_PATH, 'r', encoding='utf-8') as f:
                self._schema = json.load(f)

            # Create validator with Draft7 (as specified in the schema)
            self._validator = Draft7Validator(self._schema)

            logger.info(f"Successfully loaded ODCS schema from {ODCS_SCHEMA_PATH}")
        except Exception as e:
            logger.error(f"Failed to load ODCS schema: {e}")
            raise ODCSValidationError(f"Failed to load ODCS schema: {e}")

    def validate(self, contract_data: Dict[str, Any], strict: bool = True) -> bool:
        """
        Validate a data contract against the ODCS v3.0.2 schema

        Args:
            contract_data: The contract data to validate
            strict: If True, raises exception on validation errors. If False, returns boolean.

        Returns:
            bool: True if valid, False if invalid (when strict=False)

        Raises:
            ODCSValidationError: If validation fails and strict=True
        """
        if not self._validator:
            raise ODCSValidationError("ODCS validator not initialized")

        try:
            # Validate against schema
            self._validator.validate(contract_data)
            logger.debug("Contract data passed ODCS validation")
            return True

        except ValidationError as e:
            errors = list(self._validator.iter_errors(contract_data))
            error_messages = []

            for error in errors:
                # Build a user-friendly error message
                path = " → ".join(str(p) for p in error.absolute_path) if error.absolute_path else "root"
                message = f"At '{path}': {error.message}"
                error_messages.append(message)

            logger.warning(f"Contract data failed ODCS validation: {len(error_messages)} errors found")

            if strict:
                raise ODCSValidationError(
                    f"Contract does not comply with ODCS v3.0.2 specification. Found {len(error_messages)} validation errors.",
                    validation_errors=error_messages
                )
            else:
                return False

        except Exception as e:
            logger.error(f"Unexpected error during ODCS validation: {e}")
            if strict:
                raise ODCSValidationError(f"Validation error: {e}")
            else:
                return False

    def get_validation_errors(self, contract_data: Dict[str, Any]) -> List[str]:
        """
        Get detailed validation errors for a contract without raising exceptions

        Args:
            contract_data: The contract data to validate

        Returns:
            List[str]: List of validation error messages
        """
        if not self._validator:
            return ["ODCS validator not initialized"]

        try:
            self._validator.validate(contract_data)
            return []
        except ValidationError:
            errors = list(self._validator.iter_errors(contract_data))
            error_messages = []

            for error in errors:
                path = " → ".join(str(p) for p in error.absolute_path) if error.absolute_path else "root"
                message = f"At '{path}': {error.message}"
                error_messages.append(message)

            return error_messages
        except Exception as e:
            return [f"Validation error: {e}"]


# Global validator instance
_odcs_validator = None


def get_odcs_validator() -> ODCSValidator:
    """Get the global ODCS validator instance"""
    global _odcs_validator
    if _odcs_validator is None:
        _odcs_validator = ODCSValidator()
    return _odcs_validator


def validate_odcs_contract(contract_data: Dict[str, Any], strict: bool = True) -> bool:
    """
    Convenience function to validate a contract against ODCS v3.0.2

    Args:
        contract_data: The contract data to validate
        strict: If True, raises exception on validation errors

    Returns:
        bool: True if valid, False if invalid (when strict=False)
    """
    validator = get_odcs_validator()
    return validator.validate(contract_data, strict=strict)


def get_odcs_validation_errors(contract_data: Dict[str, Any]) -> List[str]:
    """
    Get validation errors for a contract without raising exceptions

    Args:
        contract_data: The contract data to validate

    Returns:
        List[str]: List of validation error messages
    """
    validator = get_odcs_validator()
    return validator.get_validation_errors(contract_data)