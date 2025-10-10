"""Compliance Action System.

This module provides an extensible action system for compliance rules.
Actions are executed based on rule evaluation results (ON_PASS, ON_FAIL).

Available Actions:
    - PASS: Mark check as successful (default)
    - FAIL: Mark check as failed with custom message
    - ASSIGN_TAG: Add or update a tag on the entity
    - REMOVE_TAG: Remove a tag from the entity
    - NOTIFY: Trigger notification to recipients
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol
from src.common.logging import get_logger

logger = get_logger(__name__)


class EntityTagManager(Protocol):
    """Protocol for entity tag management."""

    def assign_tag(self, entity_type: str, entity_id: str, key: str, value: str) -> None:
        """Assign a tag to an entity."""
        ...

    def remove_tag(self, entity_type: str, entity_id: str, key: str) -> None:
        """Remove a tag from an entity."""
        ...


class NotificationManager(Protocol):
    """Protocol for notification management."""

    def send_notification(self, recipients: str, message: str, subject: str) -> None:
        """Send a notification to recipients."""
        ...


@dataclass
class ActionContext:
    """Context for action execution."""
    entity: Dict[str, Any]
    entity_type: str
    entity_id: str
    rule_id: str
    rule_name: str
    passed: bool
    message: Optional[str] = None
    tag_manager: Optional[EntityTagManager] = None
    notification_manager: Optional[NotificationManager] = None


@dataclass
class ActionResult:
    """Result of action execution."""
    success: bool
    action_type: str
    message: Optional[str] = None
    error: Optional[str] = None


class Action(ABC):
    """Base class for compliance actions."""

    @abstractmethod
    def execute(self, context: ActionContext) -> ActionResult:
        """Execute the action.

        Args:
            context: Action execution context

        Returns:
            ActionResult with execution status
        """
        pass


class PassAction(Action):
    """Mark check as successful (no-op action)."""

    def execute(self, context: ActionContext) -> ActionResult:
        return ActionResult(
            success=True,
            action_type='PASS',
            message='Check passed'
        )


class FailAction(Action):
    """Mark check as failed with custom message."""

    def __init__(self, message: Optional[str] = None):
        self.custom_message = message

    def execute(self, context: ActionContext) -> ActionResult:
        message = self.custom_message or context.message or 'Check failed'
        return ActionResult(
            success=False,
            action_type='FAIL',
            message=message
        )


class AssignTagAction(Action):
    """Assign a tag to the entity."""

    def __init__(self, key: str, value: str):
        self.key = key
        self.value = value

    def execute(self, context: ActionContext) -> ActionResult:
        if not context.tag_manager:
            return ActionResult(
                success=False,
                action_type='ASSIGN_TAG',
                error='Tag manager not available'
            )

        try:
            context.tag_manager.assign_tag(
                entity_type=context.entity_type,
                entity_id=context.entity_id,
                key=self.key,
                value=self.value
            )
            return ActionResult(
                success=True,
                action_type='ASSIGN_TAG',
                message=f'Assigned tag {self.key}={self.value}'
            )
        except Exception as e:
            logger.exception(f"Failed to assign tag {self.key}={self.value}")
            return ActionResult(
                success=False,
                action_type='ASSIGN_TAG',
                error=str(e)
            )


class RemoveTagAction(Action):
    """Remove a tag from the entity."""

    def __init__(self, key: str):
        self.key = key

    def execute(self, context: ActionContext) -> ActionResult:
        if not context.tag_manager:
            return ActionResult(
                success=False,
                action_type='REMOVE_TAG',
                error='Tag manager not available'
            )

        try:
            context.tag_manager.remove_tag(
                entity_type=context.entity_type,
                entity_id=context.entity_id,
                key=self.key
            )
            return ActionResult(
                success=True,
                action_type='REMOVE_TAG',
                message=f'Removed tag {self.key}'
            )
        except Exception as e:
            logger.exception(f"Failed to remove tag {self.key}")
            return ActionResult(
                success=False,
                action_type='REMOVE_TAG',
                error=str(e)
            )


class NotifyAction(Action):
    """Trigger notification to recipients."""

    def __init__(self, recipients: str):
        self.recipients = recipients

    def execute(self, context: ActionContext) -> ActionResult:
        if not context.notification_manager:
            return ActionResult(
                success=False,
                action_type='NOTIFY',
                error='Notification manager not available'
            )

        try:
            status = 'passed' if context.passed else 'failed'
            message = f"Compliance rule '{context.rule_name}' {status} for {context.entity_type} '{context.entity_id}'"
            if context.message:
                message += f"\n\n{context.message}"

            context.notification_manager.send_notification(
                recipients=self.recipients,
                message=message,
                subject=f"Compliance Alert: {context.rule_name}"
            )
            return ActionResult(
                success=True,
                action_type='NOTIFY',
                message=f'Notified {self.recipients}'
            )
        except Exception as e:
            logger.exception(f"Failed to send notification to {self.recipients}")
            return ActionResult(
                success=False,
                action_type='NOTIFY',
                error=str(e)
            )


class ActionRegistry:
    """Registry for compliance actions."""

    def __init__(self):
        self._actions: Dict[str, type[Action]] = {
            'PASS': PassAction,
            'FAIL': FailAction,
            'ASSIGN_TAG': AssignTagAction,
            'REMOVE_TAG': RemoveTagAction,
            'NOTIFY': NotifyAction,
        }

    def register(self, action_type: str, action_class: type[Action]):
        """Register a new action type.

        Args:
            action_type: Unique identifier for the action
            action_class: Action class to register
        """
        self._actions[action_type] = action_class
        logger.info(f"Registered action type: {action_type}")

    def create_action(self, action_def: Dict[str, Any]) -> Action:
        """Create an action from definition.

        Args:
            action_def: Action definition dict with 'type' and optional parameters

        Returns:
            Instantiated Action object

        Raises:
            ValueError: If action type is unknown
        """
        action_type = action_def.get('type')
        if not action_type or action_type not in self._actions:
            raise ValueError(f"Unknown action type: {action_type}")

        action_class = self._actions[action_type]

        # Build kwargs from action definition
        kwargs = {k: v for k, v in action_def.items() if k != 'type'}

        return action_class(**kwargs)

    def list_actions(self) -> List[str]:
        """List all registered action types."""
        return list(self._actions.keys())


class ActionExecutor:
    """Execute compliance actions."""

    def __init__(self, registry: Optional[ActionRegistry] = None):
        self.registry = registry or ActionRegistry()

    def execute_actions(
        self,
        action_defs: List[Dict[str, Any]],
        context: ActionContext
    ) -> List[ActionResult]:
        """Execute a list of actions.

        Args:
            action_defs: List of action definitions
            context: Execution context

        Returns:
            List of ActionResults
        """
        results = []

        for action_def in action_defs:
            try:
                action = self.registry.create_action(action_def)
                result = action.execute(context)
                results.append(result)

                # Log result
                if result.success:
                    logger.info(
                        f"Action {result.action_type} executed successfully: {result.message}"
                    )
                else:
                    logger.warning(
                        f"Action {result.action_type} failed: {result.error or result.message}"
                    )

            except Exception as e:
                logger.exception(f"Failed to execute action: {action_def}")
                results.append(ActionResult(
                    success=False,
                    action_type=action_def.get('type', 'UNKNOWN'),
                    error=str(e)
                ))

        return results


# Global registry instance
_global_registry = ActionRegistry()


def get_action_registry() -> ActionRegistry:
    """Get the global action registry."""
    return _global_registry


def register_action(action_type: str, action_class: type[Action]):
    """Register a custom action type globally.

    Args:
        action_type: Unique identifier for the action
        action_class: Action class to register

    Example:
        >>> class CustomAction(Action):
        ...     def execute(self, context):
        ...         return ActionResult(success=True, action_type='CUSTOM')
        >>> register_action('CUSTOM', CustomAction)
    """
    _global_registry.register(action_type, action_class)
