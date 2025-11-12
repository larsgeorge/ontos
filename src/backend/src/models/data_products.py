"""
ODPS v1.0.0 (Open Data Product Standard) API Models

This module implements Pydantic models for the Bitol ODPS v1.0.0 specification.
Schema: https://github.com/bitol-io/open-data-product-standard/blob/main/schema/odps-json-schema-v1.0.0.json

These models are used for API request/response validation and serialization.
"""

from datetime import datetime, date
from enum import Enum
from typing import List, Optional, Dict, Any, Union
import json

from pydantic import BaseModel, Field, field_validator

from .tags import AssignedTag, AssignedTagCreate

from src.common.logging import get_logger
logger = get_logger(__name__)


# ============================================================================
# ODPS v1.0.0 Enums
# ============================================================================

class DataProductStatus(str, Enum):
    """ODPS v1.0.0 Status values"""
    PROPOSED = "proposed"
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


# ============================================================================
# Shared Validators
# ============================================================================

def parse_json_if_string(v: Any) -> Any:
    """Parses input if it's a string, returns original otherwise."""
    if isinstance(v, str):
        try:
            return json.loads(v)
        except json.JSONDecodeError:
            pass
    return v


# ============================================================================
# ODPS v1.0.0 Core Models
# ============================================================================

class AuthoritativeDefinition(BaseModel):
    """ODPS v1.0.0 Authoritative Definition"""
    type: str = Field(..., description="Type of definition (businessDefinition, transformationImplementation, etc.)")
    url: str = Field(..., description="URL to the authoritative source")
    description: Optional[str] = Field(None, description="Optional description")

    model_config = {"from_attributes": True}


class CustomProperty(BaseModel):
    """ODPS v1.0.0 Custom Property"""
    property: str = Field(..., description="Property name in camelCase")
    value: Any = Field(..., description="Property value (can be any type)")
    description: Optional[str] = Field(None, description="Optional description")

    model_config = {"from_attributes": True}


class Description(BaseModel):
    """ODPS v1.0.0 Structured Description"""
    purpose: Optional[str] = Field(None, description="Intended purpose for the provided data")
    limitations: Optional[str] = Field(None, description="Technical, compliance, and legal limitations for data use")
    usage: Optional[str] = Field(None, description="Recommended usage of the data")
    authoritativeDefinitions: Optional[List[AuthoritativeDefinition]] = Field(None, description="Links to authoritative sources")
    customProperties: Optional[List[CustomProperty]] = Field(None, description="Custom properties for description")

    model_config = {"from_attributes": True}


# ============================================================================
# ODPS v1.0.0 Port Models
# ============================================================================

class InputPort(BaseModel):
    """ODPS v1.0.0 Input Port"""
    # ODPS required fields
    name: str = Field(..., description="Name of the input port")
    version: str = Field(..., description="Version of the input port")
    contractId: str = Field(..., alias="contract_id", description="Contract ID for the input port (REQUIRED in ODPS)")

    # ODPS optional fields
    tags: Optional[List[str]] = Field(None, description="Tags for categorization")
    customProperties: Optional[List[CustomProperty]] = Field(None, description="Custom properties")
    authoritativeDefinitions: Optional[List[AuthoritativeDefinition]] = Field(None, description="Authoritative definitions")

    # Databricks extensions
    assetType: Optional[str] = Field(None, alias="asset_type", description="Type of Databricks asset (table, notebook, job)")
    assetIdentifier: Optional[str] = Field(None, alias="asset_identifier", description="Unique identifier for the asset")

    model_config = {
        "from_attributes": True,
        "populate_by_name": True
    }


class SBOM(BaseModel):
    """ODPS v1.0.0 Software Bill of Materials"""
    type: str = Field("external", description="Type of SBOM")
    url: str = Field(..., description="URL to the SBOM")

    model_config = {"from_attributes": True}


class InputContract(BaseModel):
    """ODPS v1.0.0 Input Contract (Dependency)"""
    id: str = Field(..., alias="contract_id", description="Contract ID or contractId")
    version: str = Field(..., alias="contract_version", description="Version of the input contract")

    model_config = {
        "from_attributes": True,
        "populate_by_name": True
    }


class Server(BaseModel):
    """Databricks extension - Connection details for output ports"""
    project: Optional[str] = Field(None, description="Project name (BigQuery)")
    dataset: Optional[str] = Field(None, description="Dataset name (BigQuery)")
    account: Optional[str] = Field(None, description="Account name (Snowflake)")
    database: Optional[str] = Field(None, description="Database name (Snowflake, Postgres)")
    schema_name: Optional[str] = Field(None, alias="schema", description="Schema name (Snowflake, Postgres)")
    host: Optional[str] = Field(None, description="Host name (Kafka)")
    topic: Optional[str] = Field(None, description="Topic name (Kafka)")
    location: Optional[str] = Field(None, description="Location URL (S3)")
    delimiter: Optional[str] = Field(None, description="Delimiter (S3)")
    format: Optional[str] = Field(None, description="Format of the data (S3)")
    table: Optional[str] = Field(None, description="Table name (Postgres)")
    view: Optional[str] = Field(None, description="View name (Postgres)")
    share: Optional[str] = Field(None, description="Share name (Databricks)")
    additionalProperties: Optional[str] = Field(None, description="Additional server properties")

    _parse_server_json = field_validator('*', mode='before')(parse_json_if_string)

    model_config = {
        "from_attributes": True,
        "populate_by_name": True
    }


class OutputPort(BaseModel):
    """ODPS v1.0.0 Output Port"""
    # ODPS required fields
    name: str = Field(..., description="Name of the output port")
    version: str = Field(..., description="Version of the output port")

    # ODPS optional fields
    description: Optional[str] = Field(None, description="Description of the output port")
    type: Optional[str] = Field(None, alias="port_type", description="Type of output port")
    contractId: Optional[str] = Field(None, alias="contract_id", description="Contract ID for the output port")
    sbom: Optional[List[SBOM]] = Field(None, description="Software Bill of Materials")
    inputContracts: Optional[List[InputContract]] = Field(None, alias="input_contracts", description="Input contract dependencies")
    tags: Optional[List[str]] = Field(None, description="Tags for categorization")
    customProperties: Optional[List[CustomProperty]] = Field(None, description="Custom properties")
    authoritativeDefinitions: Optional[List[AuthoritativeDefinition]] = Field(None, description="Authoritative definitions")

    # Databricks extensions
    assetType: Optional[str] = Field(None, alias="asset_type", description="Type of Databricks asset")
    assetIdentifier: Optional[str] = Field(None, alias="asset_identifier", description="Unique identifier for the asset")
    status: Optional[str] = Field(None, description="Status of the output port")
    server: Optional[Server] = Field(None, description="Connection details")
    containsPii: bool = Field(False, alias="contains_pii", description="Contains PII flag")
    autoApprove: bool = Field(False, alias="auto_approve", description="Auto-approve flag")

    _parse_server_json = field_validator('server', mode='before')(parse_json_if_string)

    model_config = {
        "from_attributes": True,
        "populate_by_name": True
    }


# ============================================================================
# ODPS v1.0.0 Management Port (NEW)
# ============================================================================

class ManagementPort(BaseModel):
    """ODPS v1.0.0 Management Port - For observability, control, etc."""
    # ODPS required fields
    name: str = Field(..., description="Endpoint identifier or unique name")
    content: str = Field(..., description="Content type (discoverability, observability, control, dictionary)")

    # ODPS optional fields
    type: str = Field("rest", alias="port_type", description="Type (rest or topic)")
    url: Optional[str] = Field(None, description="URL to access the endpoint")
    channel: Optional[str] = Field(None, description="Channel to communicate with the data product")
    description: Optional[str] = Field(None, description="Purpose and usage")
    tags: Optional[List[str]] = Field(None, description="Tags")
    customProperties: Optional[List[CustomProperty]] = Field(None, description="Custom properties")
    authoritativeDefinitions: Optional[List[AuthoritativeDefinition]] = Field(None, description="Authoritative definitions")

    model_config = {
        "from_attributes": True,
        "populate_by_name": True
    }


# ============================================================================
# ODPS v1.0.0 Support Channel
# ============================================================================

class Support(BaseModel):
    """ODPS v1.0.0 Support Channel"""
    # ODPS required fields
    channel: str = Field(..., description="Channel name or identifier")
    url: str = Field(..., description="Access URL")

    # ODPS optional fields
    description: Optional[str] = Field(None, description="Description of the channel")
    tool: Optional[str] = Field(None, description="Tool name (email, slack, teams, discord, ticket, other)")
    scope: Optional[str] = Field(None, description="Scope (interactive, announcements, issues)")
    invitationUrl: Optional[str] = Field(None, alias="invitation_url", description="Invitation URL")
    tags: Optional[List[str]] = Field(None, description="Tags")
    customProperties: Optional[List[CustomProperty]] = Field(None, description="Custom properties")
    authoritativeDefinitions: Optional[List[AuthoritativeDefinition]] = Field(None, description="Authoritative definitions")

    model_config = {
        "from_attributes": True,
        "populate_by_name": True
    }


# ============================================================================
# ODPS v1.0.0 Team
# ============================================================================

class TeamMember(BaseModel):
    """ODPS v1.0.0 Team Member"""
    # ODPS required fields
    username: str = Field(..., description="User's username or email")

    # ODPS optional fields
    name: Optional[str] = Field(None, description="User's name")
    description: Optional[str] = Field(None, description="User's description")
    role: Optional[str] = Field(None, description="User's role (owner, data steward, etc.)")
    dateIn: Optional[date] = Field(None, alias="date_in", description="Date when user joined")
    dateOut: Optional[date] = Field(None, alias="date_out", description="Date when user left")
    replacedByUsername: Optional[str] = Field(None, alias="replaced_by_username", description="Replacement username")
    tags: Optional[List[str]] = Field(None, description="Tags")
    customProperties: Optional[List[CustomProperty]] = Field(None, description="Custom properties")
    authoritativeDefinitions: Optional[List[AuthoritativeDefinition]] = Field(None, description="Authoritative definitions")

    model_config = {
        "from_attributes": True,
        "populate_by_name": True
    }


class Team(BaseModel):
    """ODPS v1.0.0 Team"""
    name: Optional[str] = Field(None, description="Team name")
    description: Optional[str] = Field(None, description="Team description")
    members: Optional[List[TeamMember]] = Field(None, description="List of team members")
    tags: Optional[List[str]] = Field(None, description="Tags")
    customProperties: Optional[List[CustomProperty]] = Field(None, description="Custom properties")
    authoritativeDefinitions: Optional[List[AuthoritativeDefinition]] = Field(None, description="Authoritative definitions")

    model_config = {"from_attributes": True}


# ============================================================================
# ODPS v1.0.0 Data Product (Main Model)
# ============================================================================

class DataProduct(BaseModel):
    """ODPS v1.0.0 Data Product"""
    # ODPS v1.0.0 required fields
    apiVersion: str = Field("v1.0.0", description="Version of the ODPS standard")
    kind: str = Field("DataProduct", description="Resource type")
    id: str = Field(..., description="Unique identifier")
    status: str = Field(..., description="Status (proposed, draft, active, deprecated, retired)")

    # ODPS v1.0.0 optional fields
    name: Optional[str] = Field(None, description="Name of the data product")
    version: Optional[str] = Field(None, description="Version of the data product")
    domain: Optional[str] = Field(None, description="Business domain")
    tenant: Optional[str] = Field(None, description="Organization identifier")
    owner_team_id: Optional[str] = Field(None, description="Owner team UUID")
    project_id: Optional[str] = Field(None, description="Project association")
    authoritativeDefinitions: Optional[List[AuthoritativeDefinition]] = Field(None, description="Authoritative definitions")
    description: Optional[Description] = Field(None, description="Structured description")
    customProperties: Optional[List[CustomProperty]] = Field(None, description="Custom properties")
    tags: Optional[List[Union[AssignedTag, AssignedTagCreate]]] = Field(default_factory=list, description="List of assigned tags (full metadata or IDs for creation)")
    inputPorts: Optional[List[InputPort]] = Field(None, alias="input_ports", description="Input ports")
    outputPorts: Optional[List[OutputPort]] = Field(None, alias="output_ports", description="Output ports")
    managementPorts: Optional[List[ManagementPort]] = Field(None, alias="management_ports", description="Management ports")
    support: Optional[List[Support]] = Field(None, alias="support_channels", description="Support channels")
    team: Optional[Team] = Field(None, description="Team information")
    productCreatedTs: Optional[datetime] = Field(None, alias="product_created_ts", description="Product creation timestamp")

    # Audit fields (not in ODPS, but useful)
    created_at: Optional[datetime] = Field(None, description="Record creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Record update timestamp")

    # Field validators to parse JSON strings from database
    @field_validator('tags', mode='before')
    def parse_tags(cls, value):
        if value is None:
            return []
        # If it's already a list of AssignedTag objects, return as-is
        if isinstance(value, list) and value and hasattr(value[0], 'tag_id'):
            return value
        # Handle list of string IDs from frontend (convert to dicts for AssignedTagCreate)
        if isinstance(value, list) and value and isinstance(value[0], str):
            return [{'tag_id': tag_id} for tag_id in value]
        # Legacy support for JSON strings (should not be used anymore)
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    # Handle if parsed is a list of strings
                    if parsed and isinstance(parsed[0], str):
                        return [{'tag_id': tag_id} for tag_id in parsed]
                    return parsed
            except (json.JSONDecodeError, ValueError):
                pass
            return []
        return value or []

    model_config = {
        "from_attributes": True,
        "populate_by_name": True
    }


# ============================================================================
# Request/Response Models
# ============================================================================

class GenieSpaceRequest(BaseModel):
    """Request model for initiating Genie Space creation."""
    product_ids: List[str] = Field(..., description="List of Data Product IDs to include in the Genie Space")


class NewVersionRequest(BaseModel):
    """Request model for creating a new version of a Data Product."""
    new_version: str = Field(..., description="The new version string (e.g., 1.1.0, 2.0.0)")


# ============================================================================
# Create/Update Models
# ============================================================================

class DataProductCreate(BaseModel):
    """Create model for Data Products"""
    # ODPS v1.0.0 required
    apiVersion: str = Field("v1.0.0", description="ODPS version")
    kind: str = Field("DataProduct", description="Resource type")
    id: str = Field(..., description="Unique identifier")
    status: str = Field("draft", description="Initial status")

    # ODPS optional
    name: Optional[str] = Field(None, description="Product name")
    version: Optional[str] = Field(None, description="Product version")
    domain: Optional[str] = Field(None, description="Domain")
    tenant: Optional[str] = Field(None, description="Tenant")
    owner_team_id: Optional[str] = Field(None, description="Owner team UUID")
    project_id: Optional[str] = Field(None, description="Project association")
    description: Optional[Description] = Field(None, description="Description")
    authoritativeDefinitions: Optional[List[AuthoritativeDefinition]] = Field(None, description="Authoritative definitions")
    customProperties: Optional[List[CustomProperty]] = Field(None, description="Custom properties")
    tags: Optional[List[Union[AssignedTag, AssignedTagCreate]]] = Field(None, description="Tags (IDs or full objects)")
    inputPorts: Optional[List[InputPort]] = Field(None, alias="input_ports", description="Input ports")
    outputPorts: Optional[List[OutputPort]] = Field(None, alias="output_ports", description="Output ports")
    managementPorts: Optional[List[ManagementPort]] = Field(None, alias="management_ports", description="Management ports")
    support: Optional[List[Support]] = Field(None, alias="support_channels", description="Support channels")
    team: Optional[Team] = Field(None, description="Team")

    # Field validator to handle string IDs from frontend
    @field_validator('tags', mode='before')
    def parse_tags(cls, value):
        if value is None:
            return None
        # If it's already a list of tag objects, return as-is
        if isinstance(value, list) and value and (hasattr(value[0], 'tag_id') or isinstance(value[0], dict)):
            return value
        # Handle list of string IDs from frontend (convert to dicts for AssignedTagCreate)
        if isinstance(value, list) and value and isinstance(value[0], str):
            return [{'tag_id': tag_id} for tag_id in value]
        return value

    model_config = {
        "from_attributes": True,
        "populate_by_name": True
    }


class DataProductUpdate(BaseModel):
    """Update model for Data Products"""
    name: Optional[str] = None
    version: Optional[str] = None
    status: Optional[str] = None
    domain: Optional[str] = None
    tenant: Optional[str] = None
    owner_team_id: Optional[str] = None
    project_id: Optional[str] = None
    description: Optional[Description] = None
    authoritativeDefinitions: Optional[List[AuthoritativeDefinition]] = None
    customProperties: Optional[List[CustomProperty]] = None
    tags: Optional[List[Union[AssignedTag, AssignedTagCreate]]] = None
    inputPorts: Optional[List[InputPort]] = Field(None, alias="input_ports")
    outputPorts: Optional[List[OutputPort]] = Field(None, alias="output_ports")
    managementPorts: Optional[List[ManagementPort]] = Field(None, alias="management_ports")
    support: Optional[List[Support]] = Field(None, alias="support_channels")
    team: Optional[Team] = None

    # Field validator to handle string IDs from frontend
    @field_validator('tags', mode='before')
    def parse_tags(cls, value):
        if value is None:
            return None
        # If it's already a list of tag objects, return as-is
        if isinstance(value, list) and value and (hasattr(value[0], 'tag_id') or isinstance(value[0], dict)):
            return value
        # Handle list of string IDs from frontend (convert to dicts for AssignedTagCreate)
        if isinstance(value, list) and value and isinstance(value[0], str):
            return [{'tag_id': tag_id} for tag_id in value]
        return value

    model_config = {
        "from_attributes": True,
        "populate_by_name": True
    }
