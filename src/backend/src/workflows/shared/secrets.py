import os
from typing import Tuple


def _parse_secret_ref(secret_ref: str) -> Tuple[str, str]:
    """Parse a secret reference in the form "scope:key" or "scope/key".

    Args:
        secret_ref: The secret reference string.

    Returns:
        A tuple of (scope, key).

    Raises:
        ValueError: If the reference cannot be parsed.
    """
    if ":" in secret_ref:
        scope, key = secret_ref.split(":", 1)
    elif "/" in secret_ref:
        scope, key = secret_ref.split("/", 1)
    else:
        raise ValueError(
            "Secret reference must be in the form 'scope:key' or 'scope/key'"
        )

    scope = scope.strip()
    key = key.strip()
    if not scope or not key:
        raise ValueError("Secret scope and key must be non-empty")
    return scope, key


def get_secret_value(secret_ref: str) -> str:
    """Resolve a Databricks secret value using the Databricks runtime API.

    The secret reference must be provided as "scope:key" or "scope/key".

    Args:
        secret_ref: The Databricks secret reference (scope and key).

    Returns:
        The resolved secret value as a string.

    Raises:
        RuntimeError: If the Databricks runtime is unavailable or the secret cannot be fetched.
    """
    scope, key = _parse_secret_ref(secret_ref)

    # Attempt to use Databricks runtime dbutils (available on clusters/jobs)
    try:
        from databricks.sdk.runtime import dbutils  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "Databricks runtime is not available to resolve secrets."
        ) from e

    try:
        value = dbutils.secrets.get(scope=scope, key=key)
    except Exception as e:
        raise RuntimeError(
            f"Failed to resolve Databricks secret for scope='{scope}' and key='{key}'"
        ) from e

    if value is None:
        raise RuntimeError(
            f"Databricks secret returned no value for scope='{scope}' and key='{key}'"
        )

    return str(value)


