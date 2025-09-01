from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List


@dataclass
class AccessPrivilege:
    securable_id: str  # Unity Catalog securable ID (e.g., catalog.schema.table)
    securable_type: str  # 'catalog', 'schema', 'table', 'view'
    permission: str  # 'READ', 'WRITE', 'MANAGE', etc.

    def to_dict(self) -> Dict[str, Any]:
        return {
            'securable_id': self.securable_id,
            'securable_type': self.securable_type,
            'permission': self.permission
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'AccessPrivilege':
        return AccessPrivilege(
            securable_id=data['securable_id'],
            securable_type=data['securable_type'],
            permission=data['permission']
        )

class Persona:
    def __init__(self,
                 id: str,
                 name: str,
                 description: str,
                 privileges: List[AccessPrivilege] = None,
                 groups: List[str] = None,
                 created_at: datetime = None,
                 updated_at: datetime = None):
        self.id = id
        self.name = name
        self.description = description
        self.privileges = privileges or []
        self.groups = groups or []
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'groups': self.groups,
            'created_at': self.created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            'updated_at': self.updated_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            'privileges': [p.to_dict() for p in self.privileges]
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Persona':
        privileges = [AccessPrivilege.from_dict(p) for p in data.get('privileges', [])]

        def parse_datetime(dt_str: str) -> datetime:
            formats = [
                "%Y-%m-%dT%H:%M:%S.%fZ",
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%dT%H:%M:%S"
            ]

            for fmt in formats:
                try:
                    return datetime.strptime(dt_str, fmt)
                except ValueError:
                    continue
            raise ValueError(f"time data '{dt_str}' does not match any expected format")

        created_at = parse_datetime(data['created_at']) if 'created_at' in data else None
        updated_at = parse_datetime(data['updated_at']) if 'updated_at' in data else None

        return Persona(
            id=data['id'],
            name=data['name'],
            description=data['description'],
            privileges=privileges,
            groups=data.get('groups', []),
            created_at=created_at,
            updated_at=updated_at
        )
