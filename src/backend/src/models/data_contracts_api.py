from datetime import datetime
from typing import Optional, List, Dict, Any, Union, TYPE_CHECKING

from pydantic import BaseModel, Field

from .tags import AssignedTag, AssignedTagCreate

if TYPE_CHECKING:
    pass  # Used to avoid circular imports if needed


# ODCS-compliant schema models
class ColumnProperty(BaseModel):
    name: str
    logicalType: str = Field(alias='logical_type')
    required: Optional[bool] = False
    unique: Optional[bool] = False
    primaryKey: Optional[bool] = Field(False, alias='primary_key')
    primaryKeyPosition: Optional[int] = Field(-1, alias='primary_key_position')
    partitioned: Optional[bool] = False
    partitionKeyPosition: Optional[int] = Field(-1, alias='partition_key_position')
    description: Optional[str] = None
    physicalType: Optional[str] = Field(None, alias='physical_type')
    classification: Optional[str] = None
    logicalTypeOptions: Optional[Dict[str, Any]] = Field(None, alias='logical_type_options')

    # String constraints
    minLength: Optional[int] = None
    maxLength: Optional[int] = None
    pattern: Optional[str] = None

    # Number/Integer constraints
    minimum: Optional[Union[int, float]] = None
    maximum: Optional[Union[int, float]] = None
    multipleOf: Optional[Union[int, float]] = None
    precision: Optional[int] = None

    # Date constraints
    format: Optional[str] = None
    timezone: Optional[str] = None
    customFormat: Optional[str] = None

    # Array constraints
    itemType: Optional[str] = None
    minItems: Optional[int] = None
    maxItems: Optional[int] = None

    # Semantic concepts for business glossary integration
    semanticConcepts: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    authoritativeDefinitions: Optional[List[Dict[str, Any]]] = Field(default_factory=list)

    # ODCS v3.0.2 additional property fields
    businessName: Optional[str] = None
    encryptedName: Optional[str] = None
    criticalDataElement: Optional[bool] = None
    transformLogic: Optional[str] = None
    transformSourceObjects: Optional[str] = None
    transformDescription: Optional[str] = None

    class Config:
        # Accept both JSON keys: "logicalType" (field name) and "logical_type" (alias)
        populate_by_name = True
        extra = "allow"  # Allow extra fields from wizard that we don't explicitly define


class SchemaObject(BaseModel):
    name: str
    physicalName: Optional[str] = None
    properties: List[ColumnProperty] = Field(default_factory=list)

    # ODCS v3.0.2 additional schema object fields
    businessName: Optional[str] = None
    physicalType: Optional[str] = None  # table, view, etc.
    description: Optional[str] = None
    dataGranularityDescription: Optional[str] = None
    tags: Optional[List[AssignedTagCreate]] = Field(default_factory=list)
    authoritativeDefinitions: Optional[List['AuthoritativeDefinition']] = Field(default_factory=list)
    customProperties: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    quality: Optional[List['QualityRule']] = Field(default_factory=list)  # ODCS quality rules are schema-nested

    class Config:
        populate_by_name = True
        by_alias = False  # Use field names (physicalName) not aliases (physical_name) for serialization
        extra = "allow"  # Allow extra fields from wizard


class ContractDescription(BaseModel):
    usage: Optional[str] = None
    purpose: Optional[str] = None
    limitations: Optional[str] = None


class QualityRule(BaseModel):
    # Core fields
    name: Optional[str] = None
    description: Optional[str] = None
    level: Optional[str] = None  # 'object' or 'property'
    enabled: bool = True

    # ODCS quality framework fields
    dimension: Optional[str] = None  # accuracy, completeness, conformity, consistency, coverage, timeliness, uniqueness
    business_impact: Optional[str] = None  # operational, regulatory
    severity: Optional[str] = None  # info, warning, error

    # Type and engine configuration
    type: str = "library"  # text, library, sql, custom
    method: Optional[str] = None
    schedule: Optional[str] = None
    scheduler: Optional[str] = None
    unit: Optional[str] = None
    tags: Optional[str] = None

    # Type-specific fields
    rule: Optional[str] = None  # for library type
    query: Optional[str] = None  # for sql type
    engine: Optional[str] = None  # for custom type
    implementation: Optional[str] = None  # for custom type (JSON string)

    # Comparators for all types
    must_be: Optional[str] = None
    must_not_be: Optional[str] = None
    must_be_gt: Optional[str] = None
    must_be_ge: Optional[str] = None
    must_be_lt: Optional[str] = None
    must_be_le: Optional[str] = None
    must_be_between_min: Optional[str] = None
    must_be_between_max: Optional[str] = None

    # Legacy support
    threshold: Optional[float] = None


class TeamMember(BaseModel):
    role: str  # 'steward', 'consumer', 'expert', 'admin'
    email: str
    name: Optional[str] = None


class AccessControl(BaseModel):
    read_groups: List[str] = Field(default_factory=list, alias='readGroups')
    write_groups: List[str] = Field(default_factory=list, alias='writeGroups') 
    admin_groups: List[str] = Field(default_factory=list, alias='adminGroups')
    classification: Optional[str] = 'internal'
    contains_pii: bool = Field(False, alias='containsPii')
    requires_encryption: bool = Field(False, alias='requiresEncryption')


class SupportChannel(BaseModel):
    """ODCS v3.0.2 Support Channel"""
    channel: str
    url: str
    description: Optional[str] = None
    tool: Optional[str] = None  # slack, email, etc.
    scope: Optional[str] = None
    invitationUrl: Optional[str] = None

    class Config:
        populate_by_name = True


class SupportChannels(BaseModel):
    """Legacy support structure - kept for backward compatibility"""
    email: Optional[str] = None
    slack: Optional[str] = None
    documentation: Optional[str] = None


class PricingInfo(BaseModel):
    """ODCS v3.0.2 Pricing Information"""
    priceAmount: Optional[Union[int, float]] = None
    priceCurrency: Optional[str] = None  # USD, EUR, etc.
    priceUnit: Optional[str] = None  # megabyte, record, etc.

    class Config:
        populate_by_name = True


class ContractRole(BaseModel):
    """ODCS v3.0.2 Role Definition"""
    role: str
    description: Optional[str] = None
    access: Optional[str] = None  # read, write, etc.
    firstLevelApprovers: Optional[str] = None
    secondLevelApprovers: Optional[str] = None
    customProperties: Optional[Dict[str, Any]] = Field(default_factory=dict)

    class Config:
        populate_by_name = True


class AuthoritativeDefinition(BaseModel):
    url: str
    type: str  # businessDefinition, transformationImplementation, videoTutorial, tutorial, implementation


class SLAProperty(BaseModel):
    """ODCS v3.0.2 SLA Property"""
    property: str
    value: Union[str, int, float]
    valueExt: Optional[Union[str, int, float]] = None
    unit: Optional[str] = None
    element: Optional[str] = None
    driver: Optional[str] = None  # regulatory, analytics, operational

    class Config:
        populate_by_name = True


class SLARequirements(BaseModel):
    """Legacy SLA structure - kept for backward compatibility"""
    uptime_target: Optional[float] = Field(None, alias='uptimeTarget')  # percentage
    max_downtime_minutes: Optional[int] = Field(None, alias='maxDowntimeMinutes')
    query_response_time_ms: Optional[int] = Field(None, alias='queryResponseTimeMs')
    data_freshness_minutes: Optional[int] = Field(None, alias='dataFreshnessMinutes')


# ODCS v3.0.2 Server Types
ODCS_SERVER_TYPES = [
    "api", "athena", "azure", "bigquery", "clickhouse", "databricks", "denodo", "dremio",
    "duckdb", "glue", "cloudsql", "db2", "informix", "kafka", "kinesis", "local",
    "mysql", "oracle", "postgresql", "postgres", "presto", "pubsub",
    "redshift", "s3", "sftp", "snowflake", "sqlserver", "synapse", "trino", "vertica", "custom"
]

class ServerConfig(BaseModel):
    server: Optional[str] = None  # identifier
    type: str  # ODCS server type
    description: Optional[str] = None
    environment: Optional[str] = None  # prod, dev, staging, test

    # Common server properties (stored as key-value pairs)
    host: Optional[str] = None
    port: Optional[int] = None
    database: Optional[str] = None
    database_schema: Optional[str] = Field(None, alias="schema")
    catalog: Optional[str] = None
    project: Optional[str] = None
    account: Optional[str] = None
    region: Optional[str] = None
    location: Optional[str] = None

    # Additional properties for specific server types
    properties: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        populate_by_name = True


# Full ODCS Contract Structure
class ODCSContract(BaseModel):
    """ODCS v3.0.2 compliant contract structure"""
    kind: str = 'DataContract'  # Required by ODCS
    apiVersion: str = Field('v3.0.2', alias='api_version')  # Required by ODCS
    id: str  # Required by ODCS
    version: str  # Required by ODCS
    status: str  # Required by ODCS

    # Metadata section
    name: str  # Required for app usability
    tenant: Optional[str] = None
    domain: Optional[str] = None
    dataProduct: Optional[str] = Field(None, alias='data_product')
    owner_team_id: Optional[str] = Field(None, alias='ownerTeamId')
    description: Optional[ContractDescription] = None

    # ODCS v3.0.2 top-level fields
    tags: Optional[List[AssignedTag]] = Field(default_factory=list)
    contractCreatedTs: Optional[str] = None  # ISO datetime string

    # Schema section
    contract_schema: List[SchemaObject] = Field(default_factory=list, alias="schema")

    # SLA section (ODCS v3.0.2 structure)
    slaDefaultElement: Optional[str] = None
    slaProperties: Optional[List[SLAProperty]] = Field(default_factory=list)
    sla: Optional[SLARequirements] = None  # Legacy structure

    # Pricing section
    price: Optional[PricingInfo] = None

    # Team and Roles section
    team: List[TeamMember] = Field(default_factory=list)
    roles: Optional[List[ContractRole]] = Field(default_factory=list)  # ODCS roles
    access_control: Optional[AccessControl] = Field(None, alias='accessControl')  # Legacy

    # Support section (ODCS v3.0.2 structure)
    support: Union[List[SupportChannel], SupportChannels, None] = None

    # Infrastructure section
    servers: List[ServerConfig] = Field(default_factory=list)

    # Authoritative definitions
    authoritativeDefinitions: Optional[List[AuthoritativeDefinition]] = Field(default_factory=list)

    # Custom properties
    customProperties: Optional[Dict[str, Any]] = Field(default_factory=dict)

    class Config:
        populate_by_name = True


class DataContractBase(BaseModel):
    name: str  # Required for app usability
    version: str = Field('1.0.0')
    status: str = Field('draft')
    owner_team_id: Optional[str] = Field(None, alias='ownerTeamId')
    kind: str = Field('DataContract')  # Required by ODCS
    apiVersion: str = Field('v3.0.2', alias='api_version')  # Required by ODCS
    domainId: Optional[str] = Field(None, alias='domain_id')
    tenant: Optional[str] = None
    dataProduct: Optional[str] = Field(None, alias='data_product')
    descriptionUsage: Optional[str] = Field(None, alias='description_usage')
    descriptionPurpose: Optional[str] = Field(None, alias='description_purpose')
    descriptionLimitations: Optional[str] = Field(None, alias='description_limitations')


class DataContractCreate(DataContractBase):
    # Additional ODCS fields for wizard
    domain: Optional[str] = None
    domainId: Optional[str] = None  # Domain ID for direct domain assignment
    tenant: Optional[str] = None
    dataProduct: Optional[str] = Field(None, alias='data_product')
    description: Optional[ContractDescription] = None
    contract_schema: Optional[List[SchemaObject]] = Field(None, alias="schema")

    # ODCS v3.0.2 top-level fields
    tags: Optional[List[AssignedTagCreate]] = Field(default_factory=list)
    contractCreatedTs: Optional[str] = None

    # SLA section (ODCS v3.0.2 structure)
    slaDefaultElement: Optional[str] = None
    slaProperties: Optional[List[SLAProperty]] = Field(default_factory=list)
    sla: Optional[SLARequirements] = None  # Legacy structure

    # Pricing section
    price: Optional[PricingInfo] = None

    # Team and Roles section
    team: Optional[List[TeamMember]] = Field(None)
    roles: Optional[List[ContractRole]] = Field(default_factory=list)
    access_control: Optional[AccessControl] = Field(None, alias='accessControl')  # Legacy

    # Support section (ODCS v3.0.2 structure)
    support: Union[List[SupportChannel], SupportChannels, None] = None

    # Infrastructure section
    servers: List[ServerConfig] = Field(default_factory=list)

    # Authoritative definitions
    authoritativeDefinitions: Optional[List[AuthoritativeDefinition]] = Field(default_factory=list)

    # Custom properties
    customProperties: Optional[Dict[str, Any]] = Field(default_factory=dict)

    # Legacy fields (kept for backward compatibility)
    quality_rules: Optional[List[QualityRule]] = Field(None, alias='qualityRules')
    
    def to_odcs_contract(self) -> ODCSContract:
        """Convert to full ODCS contract structure"""
        return ODCSContract(
            name=self.name,
            version=self.version,
            status=self.status,
            owner_team_id=self.owner_team_id,
            domain=self.domain,
            tenant=self.tenant,
            dataProduct=self.dataProduct,
            description=self.description,
            contract_schema=self.contract_schema or [],
        )


class DataContractUpdate(BaseModel):
    name: Optional[str] = None
    version: Optional[str] = None
    status: Optional[str] = None
    published: Optional[bool] = None  # Marketplace publication status
    owner_team_id: Optional[str] = Field(None, alias='ownerTeamId')
    kind: Optional[str] = None
    apiVersion: Optional[str] = Field(None, alias='api_version')
    domainId: Optional[str] = Field(None, alias='domain_id')
    tenant: Optional[str] = None
    dataProduct: Optional[str] = Field(None, alias='data_product')
    descriptionUsage: Optional[str] = Field(None, alias='description_usage')
    descriptionPurpose: Optional[str] = Field(None, alias='description_purpose')
    descriptionLimitations: Optional[str] = Field(None, alias='description_limitations')
    # Add schema and semantic links support for updates from wizard
    contract_schema: Optional[List[SchemaObject]] = Field(None, alias="schema")
    authoritativeDefinitions: Optional[List[AuthoritativeDefinition]] = Field(None)
    qualityRules: Optional[List[QualityRule]] = Field(None)
    serverConfigs: Optional[List[ServerConfig]] = Field(None)
    sla: Optional[SLARequirements] = None


class DataContractRead(BaseModel):
    id: str  # Required by ODCS
    name: str  # Required for app usability
    version: str  # Required by ODCS
    status: str  # Required by ODCS
    published: bool = False  # Marketplace publication status
    owner_team_id: Optional[str] = Field(None, alias='ownerTeamId')
    kind: str = Field('DataContract')  # Required by ODCS
    # Ensure JSON uses camelCase key 'apiVersion' so frontend reads it
    apiVersion: str = Field('v3.0.2', alias='apiVersion')  # Required by ODCS
    tenant: Optional[str] = None
    domain: Optional[str] = None
    domainId: Optional[str] = Field(None, alias='domain_id')
    dataProduct: Optional[str] = Field(None, alias='data_product')
    description: Optional[ContractDescription] = None

    # ODCS v3.0.2 top-level fields
    tags: Optional[List[AssignedTagCreate]] = Field(default_factory=list)
    contractCreatedTs: Optional[str] = None

    # Schema section
    contract_schema: List[SchemaObject] = Field(default_factory=list, alias="schema")

    # SLA section (ODCS v3.0.2 structure)
    slaDefaultElement: Optional[str] = None
    slaProperties: Optional[List[SLAProperty]] = Field(default_factory=list)
    sla: Optional[SLARequirements] = None  # Legacy structure

    # Pricing section
    price: Optional[PricingInfo] = None

    # Team and Roles section
    team: List[TeamMember] = Field(default_factory=list)
    roles: Optional[List[ContractRole]] = Field(default_factory=list)
    access_control: Optional[AccessControl] = Field(None, alias='accessControl')  # Legacy

    # Support section (ODCS v3.0.2 structure)
    support: Union[List[SupportChannel], SupportChannels, None] = None

    # Infrastructure section
    servers: List[ServerConfig] = Field(default_factory=list)

    # Authoritative definitions
    authoritativeDefinitions: Optional[List[AuthoritativeDefinition]] = Field(default_factory=list)

    # Custom properties
    customProperties: Optional[Dict[str, Any]] = Field(default_factory=dict)

    # Legacy fields (kept for backward compatibility)
    quality_rules: List[QualityRule] = Field(default_factory=list, alias='qualityRules')

    # Timestamps
    created: Optional[str] = None
    updated: Optional[str] = None

    class Config:
        populate_by_name = True


class DataContractCommentCreate(BaseModel):
    message: str


class DataContractCommentRead(BaseModel):
    id: str
    author: str
    message: str
    created_at: Optional[str] = None


# ===== Data Contract Tag Models (ODCS Top-Level Tags) =====
class ContractTagCreate(BaseModel):
    """Create a simple tag for a data contract (ODCS top-level tags)"""
    name: str = Field(..., min_length=1, max_length=255, description="Tag name")


class ContractTagUpdate(BaseModel):
    """Update a contract tag"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="New tag name")


class ContractTagRead(BaseModel):
    """Response model for contract tag"""
    id: str
    contract_id: str
    name: str

    class Config:
        from_attributes = True


# Rebuild models to resolve forward references
SchemaObject.model_rebuild()
ODCSContract.model_rebuild()
DataContractCreate.model_rebuild()
DataContractRead.model_rebuild()