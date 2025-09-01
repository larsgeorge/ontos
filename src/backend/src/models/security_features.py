from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List

from dateutil import parser


class SecurityFeatureType(str, Enum):
    ROW_FILTERING = "row_filtering"
    COLUMN_MASKING = "column_masking"
    DIFFERENTIAL_PRIVACY = "differential_privacy"
    HOMOMORPHIC_ENCRYPTION = "homomorphic_encryption"
    ENVELOPE_ENCRYPTION = "envelope_encryption"
    TOKENIZATION = "tokenization"

    @classmethod
    def _missing_(cls, value):
        # Handle case-insensitive lookup
        value = str(value).lower()
        for member in cls:
            if member.value == value:
                return member
        return None

@dataclass
class SecurityFeature:
    id: str
    name: str
    description: str
    type: SecurityFeatureType
    status: str = "enabled"
    target: str = ""
    conditions: List[str] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def from_dict(cls, data: dict) -> 'SecurityFeature':
        # Handle datetime string with dateutil.parser
        last_updated = data.get('last_updated')
        if isinstance(last_updated, str):
            try:
                last_updated = parser.parse(last_updated)
            except (ValueError, TypeError):
                last_updated = datetime.utcnow()
        elif not isinstance(last_updated, datetime):
            last_updated = datetime.utcnow()

        # Handle type conversion with case-insensitive lookup
        type_str = data.get('type', 'row_filtering')
        try:
            feature_type = SecurityFeatureType(type_str)
        except ValueError:
            # Try case-insensitive lookup
            feature_type = SecurityFeatureType._missing_(type_str)
            if feature_type is None:
                raise ValueError(f"Invalid security feature type: {type_str}")

        return cls(
            id=data.get('id', ''),
            name=data.get('name', ''),
            description=data.get('description', ''),
            type=feature_type,
            status=data.get('status', 'enabled'),
            target=data.get('target', ''),
            conditions=data.get('conditions', []),
            last_updated=last_updated
        )

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'type': self.type.value,
            'status': self.status,
            'target': self.target,
            'conditions': self.conditions,
            'last_updated': self.last_updated.isoformat()
        }
