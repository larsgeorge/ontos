from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
import json
import logging # Import logging

from pydantic import BaseModel, Field, HttpUrl, field_validator, computed_field

# Get a logger instance for this module
logger = logging.getLogger(__name__)

class DataProductType(str, Enum):
    SOURCE_ALIGNED = "source-aligned"
    AGGREGATE = "aggregate"
    CONSUMER_ALIGNED = "consumer-aligned"
    TABLE = "table"
    VIEW = "view"
    STREAMING_TABLE = "streaming_table"
    MATERIALIZED_VIEW = "materialized_view"
    EXTERNAL_TABLE = "external_table"
    FUNCTION = "function"
    MODEL = "model"
    DASHBOARD = "dashboard"
    JOB = "job"
    NOTEBOOK = "notebook"

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
    schema: List[SchemaField]

class Info(BaseModel):
    title: str = Field(..., description="The display name of this data product", example="Search Queries all")
    owner: str = Field(..., description="The technical id of the team that owns the data product", example="search-team")
    domain: Optional[str] = Field(None, description="The technical id of the domain", example="ecommerce")
    description: Optional[str] = Field(None, example="All search queries with user interactions")
    status: Optional[str] = Field(None, description="Status like 'proposed', 'in development', 'active', 'retired'", example="active")
    archetype: Optional[str] = Field(None, description="The domain data archetype, e.g., 'consumer-aligned', 'aggregate', 'source-aligned'", example="consumer-aligned")
    maturity: Optional[str] = Field(None, description="Deprecated maturity level", example="managed", deprecated=True)

    class Config:
        orm_mode = True
        from_attributes=True # Pydantic v2 alias for orm_mode

class Link(BaseModel):
    href: HttpUrl
    rel: Optional[str] = None
    type: Optional[str] = None

    class Config:
        orm_mode = True
        from_attributes=True

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
    location: Optional[str] = Field(None, description="Location details (e.g., topic name, table name)")
    links: Optional[Dict[str, str]] = Field(default_factory=dict, description="Links to external resources like schemas or catalogs")
    custom: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Custom fields")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")

    # Validator for fields stored as JSON string in DB Port models
    _parse_port_json_fields = field_validator('links', 'custom', 'tags', mode='before')(parse_json_if_string)

    class Config:
        orm_mode = True
        from_attributes=True

class InputPort(Port):
    sourceSystemId: str = Field(..., description="Technical identifier for the source system", example="search-service")

    class Config:
        orm_mode = True
        from_attributes=True

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

    class Config:
        from_attributes = True
        orm_mode = True # Add ORM mode

class OutputPort(Port):
    status: Optional[str] = Field(None, description="Status of the output port implementation", example="active")
    server: Optional[Server] = Field(None, description="Connection details for the actual data")
    containsPii: bool = Field(False, description="Flag if this output port contains PII")
    autoApprove: bool = Field(False, description="Automatically approve requested data usage agreements")
    dataContractId: Optional[str] = Field(None, description="Technical identifier of the data contract", example="search-queries-all")

    # Validator for the 'server' field stored as JSON string in OutputPortDb
    _parse_server_json = field_validator('server', mode='before')(parse_json_if_string)

    class Config:
        orm_mode = True
        from_attributes=True

class DataProduct(BaseModel):
    dataProductSpecification: str = Field("0.0.1", description="Version of the Data Product Specification")
    id: str = Field(..., description="Organizational unique technical identifier", example="search-queries-all")
    info: Info = Field(..., description="Information about the data product")
    inputPorts: List[InputPort] = Field(default_factory=list, description="List of input ports")
    outputPorts: List[OutputPort] = Field(default_factory=list, description="List of output ports")
    links: Optional[Dict[str, str]] = Field(default_factory=dict)
    custom: Optional[Dict[str, Any]] = Field(default_factory=dict)
    # Add tags as a regular field
    tags: List[str] = Field(default_factory=list, description="Tags associated with the data product")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Validator for fields stored as JSON string in DataProductDb
    _parse_root_json_fields = field_validator('links', 'custom', mode='before')(parse_json_if_string)

    # Add a validator to convert ORM Tag objects to strings
    @field_validator('tags', mode='before')
    def convert_tags_from_orm(cls, v: Any) -> List[str]:
        # Check if the input looks like a list of ORM Tag objects
        if isinstance(v, list) and v and hasattr(v[0], 'name'):
            tag_names = [tag.name for tag in v if hasattr(tag, 'name')]
            return tag_names
        # If it's already a list of strings (e.g., from direct dict), pass through
        if isinstance(v, list) and all(isinstance(item, str) for item in v):
             return v
        # Handle other cases or potential errors
        logger.warning(f"Unexpected type for tags validation: {type(v)}. Value: {v}. Returning empty list.")
        return [] # Default to empty list if conversion fails

    class Config:
        use_enum_values = True
        orm_mode = True
        from_attributes = True


# --- Request Models ---

class GenieSpaceRequest(BaseModel):
    """Request model for initiating Genie Space creation."""
    product_ids: List[str] = Field(..., description="List of Data Product IDs to include in the Genie Space.")
