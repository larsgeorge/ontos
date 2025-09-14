from datetime import datetime
from typing import Optional, List, Dict, Any, Union

from pydantic import BaseModel, Field


# ODCS-compliant schema models
class ColumnProperty(BaseModel):
    name: str
    logicalType: str = Field(alias='logical_type')
    required: Optional[bool] = False
    unique: Optional[bool] = False
    description: Optional[str] = None


class SchemaObject(BaseModel):
    name: str
    physicalName: Optional[str] = Field(None, alias='physical_name')
    properties: List[ColumnProperty] = Field(default_factory=list)


class ContractDescription(BaseModel):
    usage: Optional[str] = None
    purpose: Optional[str] = None
    limitations: Optional[str] = None


class QualityRule(BaseModel):
    type: str  # 'completeness', 'accuracy', 'consistency', 'custom'
    enabled: bool = True
    threshold: Optional[float] = None
    query: Optional[str] = None


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


class SupportChannels(BaseModel):
    email: Optional[str] = None
    slack: Optional[str] = None
    documentation: Optional[str] = None


class SLARequirements(BaseModel):
    uptime_target: Optional[float] = Field(None, alias='uptimeTarget')  # percentage
    max_downtime_minutes: Optional[int] = Field(None, alias='maxDowntimeMinutes')
    query_response_time_ms: Optional[int] = Field(None, alias='queryResponseTimeMs')
    data_freshness_minutes: Optional[int] = Field(None, alias='dataFreshnessMinutes')


class ServerConfig(BaseModel):
    server_type: Optional[str] = Field(None, alias='serverType')
    connection_string: Optional[str] = Field(None, alias='connectionString')
    environment: Optional[str] = None


# Full ODCS Contract Structure
class ODCSContract(BaseModel):
    """ODCS v3.0.2 compliant contract structure"""
    kind: str = 'DataContract'
    apiVersion: str = Field('v3.0.2', alias='api_version')
    id: Optional[str] = None
    version: str
    status: str
    
    # Metadata section
    name: str
    tenant: Optional[str] = None
    domain: Optional[str] = None
    dataProduct: Optional[str] = Field(None, alias='data_product')
    owner: str
    description: Optional[ContractDescription] = None
    
    # Schema section
    schema: List[SchemaObject] = Field(default_factory=list)
    
    # Data Quality section
    quality_rules: List[QualityRule] = Field(default_factory=list, alias='qualityRules')
    quality_thresholds: Dict[str, float] = Field(default_factory=dict, alias='qualityThresholds')
    
    # Team and Roles section  
    team: List[TeamMember] = Field(default_factory=list)
    access_control: Optional[AccessControl] = Field(None, alias='accessControl')
    support: Optional[SupportChannels] = None
    
    # SLA section
    sla: Optional[SLARequirements] = None
    servers: Optional[ServerConfig] = None
    
    # Custom properties
    custom_properties: Dict[str, Any] = Field(default_factory=dict, alias='customProperties')


class DataContractBase(BaseModel):
    name: str
    version: str = Field('v1.0')
    status: str = Field('draft')
    owner: str
    kind: Optional[str] = Field('DataContract')
    apiVersion: Optional[str] = Field('v3.0.1', alias='api_version')
    domainId: Optional[str] = Field(None, alias='domain_id')
    tenant: Optional[str] = None
    dataProduct: Optional[str] = Field(None, alias='data_product')
    descriptionUsage: Optional[str] = Field(None, alias='description_usage')
    descriptionPurpose: Optional[str] = Field(None, alias='description_purpose')
    descriptionLimitations: Optional[str] = Field(None, alias='description_limitations')


class DataContractCreate(DataContractBase):
    # Additional ODCS fields for wizard
    domain: Optional[str] = None
    tenant: Optional[str] = None
    dataProduct: Optional[str] = Field(None, alias='data_product')
    description: Optional[ContractDescription] = None
    schema: Optional[List[SchemaObject]] = Field(None)
    
    # Full ODCS structure fields
    quality_rules: Optional[List[QualityRule]] = Field(None, alias='qualityRules')
    team: Optional[List[TeamMember]] = Field(None)
    access_control: Optional[AccessControl] = Field(None, alias='accessControl')
    support: Optional[SupportChannels] = None
    sla: Optional[SLARequirements] = None
    servers: Optional[ServerConfig] = None
    custom_properties: Optional[Dict[str, Any]] = Field(None, alias='customProperties')
    
    def to_odcs_contract(self) -> ODCSContract:
        """Convert to full ODCS contract structure"""
        return ODCSContract(
            name=self.name,
            version=self.version,
            status=self.status,
            owner=self.owner,
            domain=self.domain,
            tenant=self.tenant,
            dataProduct=self.dataProduct,
            description=self.description,
            schema=self.schema or [],
        )


class DataContractUpdate(BaseModel):
    name: Optional[str] = None
    version: Optional[str] = None
    status: Optional[str] = None
    owner: Optional[str] = None
    kind: Optional[str] = None
    apiVersion: Optional[str] = Field(None, alias='api_version')
    domainId: Optional[str] = Field(None, alias='domain_id')
    tenant: Optional[str] = None
    dataProduct: Optional[str] = Field(None, alias='data_product')
    descriptionUsage: Optional[str] = Field(None, alias='description_usage')
    descriptionPurpose: Optional[str] = Field(None, alias='description_purpose')
    descriptionLimitations: Optional[str] = Field(None, alias='description_limitations')


class DataContractRead(BaseModel):
    id: str
    name: str
    version: str
    status: str
    owner: str
    kind: Optional[str] = 'DataContract'
    apiVersion: Optional[str] = Field('v3.0.2', alias='api_version')
    tenant: Optional[str] = None
    domain: Optional[str] = None
    domainId: Optional[str] = Field(None, alias='domain_id')
    dataProduct: Optional[str] = Field(None, alias='data_product')
    description: Optional[ContractDescription] = None
    schema: List[SchemaObject] = Field(default_factory=list)
    quality_rules: List[QualityRule] = Field(default_factory=list, alias='qualityRules')
    team: List[TeamMember] = Field(default_factory=list)
    access_control: Optional[AccessControl] = Field(None, alias='accessControl')
    support: Optional[SupportChannels] = None
    sla: Optional[SLARequirements] = None
    servers: Optional[ServerConfig] = None
    custom_properties: Dict[str, Any] = Field(default_factory=dict, alias='customProperties')
    created: Optional[str] = None
    updated: Optional[str] = None


class DataContractCommentCreate(BaseModel):
    message: str


class DataContractCommentRead(BaseModel):
    id: str
    author: str
    message: str
    created_at: Optional[str] = None


