from typing import Any, Optional

_managers_registry: dict[str, Any] = {}

def set_app_state_manager(name: str, instance: Any) -> None:
    """Register a globally accessible manager instance by name.

    This is a lightweight fallback for places where request.app.state is not available.
    """
    if not name:
        return
    _managers_registry[name] = instance

def get_app_state_manager(name: str) -> Optional[Any]:
    """Fetch a previously registered manager by name, if any."""
    return _managers_registry.get(name)


