from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any, Union
import json
import logging # Import logging

from pydantic import BaseModel, Field, HttpUrl, field_validator, computed_field

from .tags import AssignedTag, AssignedTagCreate

# Get a logger instance for this module
logger = logging.getLogger(__name__)

class DataProductType(str, Enum):
    SOURCE = "source"
    SOURCE_ALIGNED = "source-aligned"
    AGGREGATE = "aggregate"
    CONSUMER_ALIGNED = "consumer-aligned"
    SINK = "sink"

class DataProductStatus(str, Enum):
    DRAFT = "draft"
    CANDIDATE = "candidate"
    IN_DEVELOPMENT = "in-development"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"
    RETIRED = "retired"
    DELETED = "deleted"

class SchemaField(BaseModel):
    name: str
    type: str
    description: Optional[str] = None

class DataSource(BaseModel):
    name: str
    type: str
    connection: str

class DataOutput(BaseModel):
    name: str
    type: str
    location: str
    data_fields: List[SchemaField] = Field(..., alias="schema")

class Info(BaseModel):
    title: str = Field(..., description="The display name of this data product", example="Search Queries all")
    owner_team_id: Optional[str] = Field(None, description="The UUID of the team that owns the data product")
    domain: Optional[str] = Field(None, description="The technical id of the domain", example="ecommerce")
    description: Optional[str] = Field(None, example="All search queries with user interactions")
    status: Optional[str] = Field(None, description="Status like 'proposed', 'in development', 'active', 'retired'", example="active")
    archetype: Optional[str] = Field(None, description="The domain data archetype, e.g., 'consumer-aligned', 'aggregate', 'source-aligned'", example="consumer-aligned")
    maturity: Optional[str] = Field(None, description="Deprecated maturity level", example="managed", deprecated=True)

    model_config = {
        "from_attributes": True # Pydantic v2 alias for orm_mode
    }

class Link(BaseModel):
    href: HttpUrl
    rel: Optional[str] = None
    type: Optional[str] = None

    model_config = {
        "from_attributes": True
    }

# --- Shared Validator --- 
def parse_json_if_string(v: Any) -> Any:
    """Parses input if it's a string, returns original otherwise."""
    if isinstance(v, str):
        try:
            return json.loads(v)
        except json.JSONDecodeError:
            # Let standard validation handle errors for invalid JSON
            pass 
    return v

class Port(BaseModel):
    id: str = Field(..., description="A technical identifier for this port", example="kafka_search_topic")
    name: str = Field(..., description="The display name for this port", example="kafka_search_topic")
    description: Optional[str] = Field(None, description="The description for this port")
    type: Optional[str] = Field(None, description="The technical type of the port (e.g., 'Kafka', 'snowflake')")
    assetType: Optional[str] = Field(None, alias="asset_type", description="Type of linked Databricks asset (e.g., 'table', 'notebook', 'job')", example="table")
    assetIdentifier: Optional[str] = Field(None, alias="asset_identifier", description="Unique identifier for the linked asset (e.g., catalog.schema.table, /path/to/notebook, job_id)", example="main.data.raw_sales")
    location: Optional[str] = Field(None, description="Location details (e.g., topic name, table name)")
    links: Optional[Dict[str, str]] = Field(default_factory=dict, description="Links to external resources like schemas or catalogs")
    custom: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Custom fields")
    tags: Optional[List[AssignedTagCreate]] = Field(default_factory=list, description="Rich tags with metadata")

    # Validator for fields stored as JSON string in DB Port models
    _parse_port_json_fields = field_validator('links', 'custom', 'tags', mode='before')(parse_json_if_string)

    model_config = {
        "from_attributes": True,
        "populate_by_name": True # Allow using DB column names
    }

class InputPort(Port):
    sourceSystemId: str = Field(..., description="Technical identifier for the source system", example="search-service")
    sourceOutputPortId: Optional[str] = Field(None, description="The specific output port ID on the source system this input connects to")

    model_config = {
        "from_attributes": True,
        "populate_by_name": True
    }

class Server(BaseModel):
    project: Optional[str] = Field(None, description="The project name (bigquery)", example="dp-search")
    dataset: Optional[str] = Field(None, description="The dataset name (bigquery)", example="search-queries")
    account: Optional[str] = Field(None, description="The account name (snowflake)", example="https://acme-test_aws_us_east_2.snowflakecomputing.com")
    database: Optional[str] = Field(None, description="The database name (snowflake,postgres)", example="SEARCH_DB")
    schema_name: Optional[str] = Field(None, alias="schema", description="The schema name (snowflake,postgres)", example="SEARCH_QUERIES_ALL_NPII_V1")
    host: Optional[str] = Field(None, description="The host name (kafka)", example="kafka.acme.com")
    topic: Optional[str] = Field(None, description="The topic name (kafka)", example="search-queries")
    location: Optional[str] = Field(None, description="The location url (s3)", example="s3://acme-search-queries")
    delimiter: Optional[str] = Field(None, description="The delimiter (s3)", example="'newline'")
    format: Optional[str] = Field(None, description="The format of the data (s3)", example="'json'")
    table: Optional[str] = Field(None, description="The table name (postgres)", example="search_queries")
    view: Optional[str] = Field(None, description="The view name (postgres)", example="search_queries")
    share: Optional[str] = Field(None, description="The share name (databricks)")
    additionalProperties: Optional[str] = Field(None, description="Field for additional server properties, expected as a single string by the schema.")

    model_config = {
        "from_attributes": True,
        "populate_by_name": True
    }

class OutputPort(Port):
    status: Optional[str] = Field(None, description="Status of the output port implementation", example="active")
    server: Optional[Server] = Field(None, description="Connection details for the actual data")
    containsPii: bool = Field(False, description="Flag if this output port contains PII")
    autoApprove: bool = Field(False, description="Automatically approve requested data usage agreements")
    dataContractId: Optional[str] = Field(None, description="Technical identifier of the data contract", example="search-queries-all")

    # Validator for the 'server' field stored as JSON string in OutputPortDb
    _parse_server_json = field_validator('server', mode='before')(parse_json_if_string)

    model_config = {
        "from_attributes": True,
        "populate_by_name": True
    }

class DataProduct(BaseModel):
    dataProductSpecification: str = Field("0.0.1", description="Version of the Data Product Specification")
    id: str = Field(..., description="Organizational unique technical identifier", example="search-queries-all")
    info: Info = Field(..., description="Information about the data product")
    version: str = Field("v1.0", description="Version identifier for the data product", example="v1.0")
    productType: DataProductType = Field(..., alias='product_type', description="Type indicating the stage in the data flow", example=DataProductType.CONSUMER_ALIGNED)
    inputPorts: Optional[List[InputPort]] = Field(default_factory=list, description="List of input ports")
    outputPorts: Optional[List[OutputPort]] = Field(default_factory=list, description="List of output ports")
    links: Optional[Dict[str, str]] = Field(default_factory=dict)
    custom: Optional[Dict[str, Any]] = Field(default_factory=dict)
    # Rich tags with metadata
    tags: Optional[List[AssignedTagCreate]] = Field(default_factory=list, description="Rich tags with metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Validator for fields stored as JSON string in DataProductDb
    _parse_root_json_fields = field_validator('links', 'custom', mode='before')(parse_json_if_string)

    # Rich tags are now handled through AssignedTag objects

    model_config = {
        "use_enum_values": True,
        "populate_by_name": True,
        "from_attributes": True
    }


# --- Request Models ---

class GenieSpaceRequest(BaseModel):
    """Request model for initiating Genie Space creation."""
    product_ids: List[str] = Field(..., description="List of Data Product IDs to include in the Genie Space.")

class NewVersionRequest(BaseModel):
    """Request model for creating a new version of a Data Product."""
    new_version: str = Field(..., description="The new version string (e.g., v1.1, v2.0)", example="v1.1")
    # Optional fields could be added later, e.g.:
    # copy_tags: bool = Field(True, description="Copy tags from the original version.")
    # reset_status_to_draft: bool = Field(True, description="Reset the status of the new version to 'draft'.")

# --- Create Models for Input (Accept both simple strings and rich tags) ---

class PortCreate(BaseModel):
    """Create model for ports that accepts both string and rich tags"""
    id: str = Field(..., description="A technical identifier for this port")
    name: str = Field(..., description="The display name for this port")
    description: Optional[str] = Field(None, description="The description for this port")
    type: Optional[str] = Field(None, description="The technical type of the port")
    assetType: Optional[str] = Field(None, alias="asset_type", description="Type of linked Databricks asset")
    assetIdentifier: Optional[str] = Field(None, alias="asset_identifier", description="Unique identifier for the linked asset")
    location: Optional[str] = Field(None, description="Location details")
    links: Optional[Dict[str, str]] = Field(default_factory=dict, description="Links to external resources")
    custom: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Custom fields")
    tags: Optional[List[AssignedTagCreate]] = Field(default_factory=list, description="Rich tags with metadata")

    model_config = {
        "from_attributes": True,
        "populate_by_name": True
    }

class InputPortCreate(PortCreate):
    """Create model for input ports"""
    sourceSystemId: str = Field(..., description="Technical identifier for the source system")
    sourceOutputPortId: Optional[str] = Field(None, description="The specific output port ID on the source system")

class OutputPortCreate(PortCreate):
    """Create model for output ports"""
    status: Optional[str] = Field(None, description="Status of the output port implementation")
    server: Optional[Server] = Field(None, description="Connection details for the actual data")
    containsPii: bool = Field(False, description="Flag if this output port contains PII")
    autoApprove: bool = Field(False, description="Automatically approve requested data usage agreements")
    dataContractId: Optional[str] = Field(None, description="Technical identifier of the data contract")

class DataProductCreate(BaseModel):
    """Create model for data products that accepts both string and rich tags"""
    dataProductSpecification: str = Field("0.0.1", description="Version of the Data Product Specification")
    id: str = Field(..., description="Organizational unique technical identifier")
    info: Info = Field(..., description="Information about the data product")
    version: str = Field("v1.0", description="Version identifier for the data product")
    productType: DataProductType = Field(..., alias='product_type', description="Type indicating the stage in the data flow")
    inputPorts: Optional[List[InputPortCreate]] = Field(default_factory=list, description="List of input ports")
    outputPorts: Optional[List[OutputPortCreate]] = Field(default_factory=list, description="List of output ports")
    links: Optional[Dict[str, str]] = Field(default_factory=dict)
    custom: Optional[Dict[str, Any]] = Field(default_factory=dict)
    tags: Optional[List[AssignedTagCreate]] = Field(default_factory=list, description="Rich tags with metadata")

    model_config = {
        "use_enum_values": True,
        "populate_by_name": True,
        "from_attributes": True
    }

class DataProductUpdate(BaseModel):
    """Update model for data products"""
    info: Optional[Info] = Field(None, description="Information about the data product")
    version: Optional[str] = Field(None, description="Version identifier for the data product")
    productType: Optional[DataProductType] = Field(None, alias='product_type', description="Type indicating the stage in the data flow")
    inputPorts: Optional[List[InputPortCreate]] = Field(None, description="List of input ports")
    outputPorts: Optional[List[OutputPortCreate]] = Field(None, description="List of output ports")
    links: Optional[Dict[str, str]] = Field(None)
    custom: Optional[Dict[str, Any]] = Field(None)
    tags: Optional[List[AssignedTagCreate]] = Field(None, description="Rich tags with metadata")

    model_config = {
        "use_enum_values": True,
        "populate_by_name": True,
        "from_attributes": True
    }
