import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import yaml


class ContractStatus(Enum):
    """ODCS lifecycle status values."""
    DRAFT = "draft"
    PROPOSED = "proposed"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    ACTIVE = "active"
    CERTIFIED = "certified"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


class DataType(Enum):
    STRING = "string"
    INTEGER = "integer"
    LONG = "long"
    FLOAT = "float"
    DOUBLE = "double"
    BOOLEAN = "boolean"
    DATE = "date"
    TIMESTAMP = "timestamp"
    BINARY = "binary"
    ARRAY = "array"
    STRUCT = "struct"
    MAP = "map"


class SecurityClassification(Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    SENSITIVE = "sensitive"


@dataclass
class Metadata:
    domain: str
    owner_team_id: Optional[str] = None  # Team UUID reference
    tags: Dict[str, str] = field(default_factory=dict)
    subdomain: Optional[str] = None
    steward: Optional[str] = None
    business_description: Optional[str] = None
    technical_description: Optional[str] = None


@dataclass
class Quality:
    rules: List[str]
    scores: Dict[str, float]
    metrics: Dict[str, Any]
    last_validated: Optional[datetime] = None


@dataclass
class Security:
    classification: SecurityClassification
    pii_data: bool = False
    compliance_labels: List[str] = field(default_factory=list)
    access_control: Dict[str, List[str]] = field(default_factory=dict)
    encryption_required: bool = False


@dataclass
class ColumnDefinition:
    name: str
    data_type: DataType
    comment: Optional[str] = None
    nullable: bool = True
    default_value: Optional[Any] = None
    precision: Optional[int] = None
    scale: Optional[int] = None
    is_unique: bool = False
    validation_rules: List[str] = field(default_factory=list)
    security: Optional[Security] = None
    business_name: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class DatasetSchema:
    columns: List[ColumnDefinition]
    primary_key: Optional[List[str]] = None
    partition_columns: Optional[List[str]] = None
    clustering_columns: Optional[List[str]] = None
    dependencies: List[str] = field(default_factory=list)
    version: str = "1.0"


@dataclass
class DatasetLifecycle:
    retention_period: Optional[str] = None
    delete_after: Optional[datetime] = None
    archive_after: Optional[datetime] = None
    update_frequency: Optional[str] = None
    last_updated: Optional[datetime] = None
    is_active: bool = True


@dataclass
class Dataset:
    name: str
    type: str  # 'table' or 'view'
    schema: DatasetSchema
    metadata: Metadata
    quality: Quality
    security: Security
    lifecycle: DatasetLifecycle
    description: Optional[str] = None
    location: Optional[str] = None  # for external tables
    view_definition: Optional[str] = None  # for views
    format: Optional[str] = None  # file format for external tables
    constraints: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DataContract:
    id: str
    name: str
    contract_text: str  # Raw contract text (JSON, YAML, etc)
    version: str
    format: str  # Format of the contract (json, yaml, etc)
    owner_team_id: Optional[str] = None  # Team UUID reference
    description: Optional[str] = None
    status: str = "draft"
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self):
        """Convert to dict for API responses"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description or f"Data contract for {self.name}",
            'version': self.version,
            'status': self.status,
            'owner_team_id': self.owner_team_id,
            'format': self.format,
            'created': self.created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            'updated': self.updated_at.strftime("%Y-%m-%dT%H:%M:%SZ")
        }

    def get_contract_data(self) -> dict:
        """Get the contract as a Python dict"""
        if self.format.lower() == 'json':
            return json.loads(self.contract_text)
        elif self.format.lower() in ('yaml', 'yml'):
            return yaml.safe_load(self.contract_text)
        else:
            return {'content': self.contract_text}  # Return raw text for other formats

    @staticmethod
    def validate_contract_text(text: str, format: str) -> bool:
        """Validate if string is valid format"""
        try:
            if format.lower() == 'json':
                json.loads(text)
            elif format.lower() in ('yaml', 'yml'):
                yaml.safe_load(text)
            return True
        except (json.JSONDecodeError, yaml.YAMLError):
            return False
