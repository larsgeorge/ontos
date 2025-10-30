import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import yaml

from src.models.entitlements import AccessPrivilege, Persona

from src.common.logging import get_logger
logger = get_logger(__name__)

class EntitlementsManager:
    def __init__(self, yaml_path: Optional[str] = None):
        """Initialize the entitlements manager.

        Args:
            yaml_path: Optional path to YAML file to load. If None, attempts to load
                      from default location (src/backend/src/data/entitlements.yaml)
        """
        self._personas: Dict[str, Persona] = {}
        self._yaml_path: Optional[str] = None

        # Auto-load from YAML if path provided or default exists
        if yaml_path:
            self._yaml_path = yaml_path
            self._load_yaml_file(yaml_path)
        else:
            # Try default location
            from pathlib import Path
            import os
            default_path = Path(__file__).parent.parent / 'data' / 'entitlements.yaml'
            if os.path.exists(default_path):
                self._yaml_path = str(default_path)
                self._load_yaml_file(str(default_path))

    def _load_yaml_file(self, yaml_path: str):
        """Internal helper to load YAML file during initialization."""
        try:
            success = self.load_from_yaml(yaml_path)
            if success:
                logger.info(f"Successfully loaded entitlements data from {yaml_path}")
            else:
                logger.warning(f"Failed to load entitlements data from {yaml_path}")
        except Exception as e:
            logger.error(f"Error loading entitlements data from {yaml_path}: {e}")

    def _persist(self):
        """Auto-persist to YAML if path is configured."""
        if self._yaml_path:
            try:
                self.save_to_yaml(self._yaml_path)
                logger.info(f"Saved updated entitlements data to {self._yaml_path}")
            except Exception as e:
                logger.warning(f"Could not save updated data to YAML: {e}")

    def _format_persona(self, persona: Persona) -> Dict[str, Any]:
        """Format a Persona object as an API-ready dict.

        Args:
            persona: Persona object to format

        Returns:
            Dict with formatted timestamps and serialized privileges
        """
        return {
            'id': persona.id,
            'name': persona.name,
            'description': persona.description,
            'groups': persona.groups,
            'created_at': persona.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            'updated_at': persona.updated_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            'privileges': [
                {
                    'securable_id': priv.securable_id,
                    'securable_type': priv.securable_type,
                    'permission': priv.permission
                } for priv in persona.privileges
            ]
        }

    def get_personas_formatted(self) -> List[Dict[str, Any]]:
        """Get all personas formatted for API response.

        Returns:
            List of formatted persona dicts
        """
        personas = self.list_personas()
        return [self._format_persona(p) for p in personas]

    def get_persona_formatted(self, persona_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific persona formatted for API response.

        Args:
            persona_id: Persona ID to retrieve

        Returns:
            Formatted persona dict or None if not found
        """
        persona = self.get_persona(persona_id)
        return self._format_persona(persona) if persona else None

    def create_persona(self,
                      name: str,
                      description: str = None,
                      privileges: List[Dict[str, Any]] = None,
                      groups: List[str] = None) -> Persona:
        """Create a new persona"""
        persona_id = str(uuid.uuid4())
        now = datetime.utcnow()

        # Convert privileges dict to AccessPrivilege objects
        access_privileges = []
        if privileges:
            for priv in privileges:
                access_privileges.append(AccessPrivilege(
                    securable_id=priv.get('securable_id', ''),
                    securable_type=priv.get('securable_type', ''),
                    permission=priv.get('permission', 'READ')
                ))

        persona = Persona(
            id=persona_id,
            name=name,
            description=description,
            created_at=now,
            updated_at=now,
            privileges=access_privileges,
            groups=groups or []
        )

        self._personas[persona_id] = persona
        self._persist()  # Auto-save to YAML
        return persona

    def get_persona(self, persona_id: str) -> Optional[Persona]:
        """Get a persona by ID"""
        return self._personas.get(persona_id)

    def list_personas(self) -> List[Persona]:
        """List all personas"""
        return list(self._personas.values())

    def update_persona(self, persona_id: str, name: str = None, description: str = None,
                      privileges: List[Dict] = None, groups: List[str] = None) -> Optional[Persona]:
        """Update a persona's details"""
        persona = self._personas.get(persona_id)
        if not persona:
            return None

        if name is not None:
            persona.name = name
        if description is not None:
            persona.description = description
        if privileges is not None:
            persona.privileges = [AccessPrivilege.from_dict(p) for p in privileges]
        if groups is not None:
            persona.groups = groups

        persona.updated_at = datetime.utcnow()
        self._persist()  # Auto-save to YAML
        return persona

    def delete_persona(self, persona_id: str) -> bool:
        """Delete a persona"""
        if persona_id in self._personas:
            del self._personas[persona_id]
            self._persist()  # Auto-save to YAML
            return True
        return False

    def add_privilege(self, persona_id: str, securable_id: str, securable_type: str, permission: str) -> Optional[Persona]:
        """Add a privilege to a persona"""
        persona = self._personas.get(persona_id)
        if not persona:
            return None

        # Check if privilege already exists
        for priv in persona.privileges:
            if priv.securable_id == securable_id:
                priv.permission = permission
                persona.updated_at = datetime.utcnow()
                self._persist()  # Auto-save to YAML
                return persona

        # Add new privilege
        persona.privileges.append(AccessPrivilege(
            securable_id=securable_id,
            securable_type=securable_type,
            permission=permission
        ))

        persona.updated_at = datetime.utcnow()
        self._persist()  # Auto-save to YAML
        return persona

    def remove_privilege(self, persona_id: str, securable_id: str) -> Optional[Persona]:
        """Remove a privilege from a persona"""
        persona = self._personas.get(persona_id)
        if not persona:
            return None

        # Filter out the privilege to remove
        persona.privileges = [p for p in persona.privileges if p.securable_id != securable_id]
        persona.updated_at = datetime.utcnow()
        self._persist()  # Auto-save to YAML
        return persona

    def update_persona_groups(self, persona_id: str, groups: List[str]) -> Persona:
        """Update the groups assigned to a persona"""
        if persona_id not in self._personas:
            raise ValueError(f"Persona not found with ID: {persona_id}")

        persona = self._personas[persona_id]
        persona.groups = groups
        persona.updated_at = datetime.now()
        self._persist()  # Auto-save to YAML
        return persona

    def load_from_yaml(self, file_path: str) -> bool:
        """Load personas from YAML file"""
        try:
            with open(file_path) as f:
                data = yaml.safe_load(f)

            if not data or 'personas' not in data:
                return False

            self._personas.clear()
            for p_data in data['personas']:
                persona = Persona.from_dict(p_data)
                self._personas[persona.id] = persona

            return True
        except Exception as e:
            logger.error(f"Error loading from YAML: {e!s}")
            return False

    def save_to_yaml(self, file_path: str) -> bool:
        """Save personas to YAML file"""
        try:
            data = {
                'personas': [p.to_dict() for p in self._personas.values()]
            }

            with open(file_path, 'w') as f:
                yaml.dump(data, f, sort_keys=False)

            return True
        except Exception as e:
            logger.error(f"Error saving to YAML: {e!s}")
            return False
