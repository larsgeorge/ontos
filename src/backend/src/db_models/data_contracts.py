from uuid import uuid4
from sqlalchemy import (
    Column,
    String,
    DateTime,
    Text,
    Boolean,
    Integer,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from src.common.database import Base


class DataContractDb(Base):
    __tablename__ = "data_contracts"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    name = Column(String, nullable=False, index=True)  # Required for app usability
    kind = Column(String, nullable=False, default="DataContract")
    api_version = Column(String, nullable=False, default="v3.0.2")
    version = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, default="draft", index=True)
    owner_team_id = Column(String, ForeignKey('teams.id'), nullable=True, index=True)  # Team UUID reference
    tenant = Column(String, nullable=True)
    data_product = Column(String, nullable=True)
    domain_id = Column(String, ForeignKey("data_domains.id"), nullable=True, index=True)

    # Project relationship (nullable for backward compatibility)
    project_id = Column(String, ForeignKey('projects.id'), nullable=True, index=True)

    # Top-level description fields
    description_usage = Column(Text, nullable=True)
    description_purpose = Column(Text, nullable=True)
    description_limitations = Column(Text, nullable=True)

    # ODCS v3.0.2 additional top-level fields
    sla_default_element = Column(String, nullable=True)  # ODCS slaDefaultElement field
    contract_created_ts = Column(DateTime(timezone=True), nullable=True)  # ODCS contractCreatedTs field

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by = Column(String, nullable=True)
    updated_by = Column(String, nullable=True)

    # Relationships
    owner_team = relationship("TeamDb", foreign_keys=[owner_team_id])
    tags = relationship("DataContractTagDb", back_populates="contract", cascade="all, delete-orphan")
    servers = relationship("DataContractServerDb", back_populates="contract", cascade="all, delete-orphan")
    roles = relationship("DataContractRoleDb", back_populates="contract", cascade="all, delete-orphan")
    team = relationship("DataContractTeamDb", back_populates="contract", cascade="all, delete-orphan")
    support = relationship("DataContractSupportDb", back_populates="contract", cascade="all, delete-orphan")
    pricing = relationship("DataContractPricingDb", back_populates="contract", uselist=False, cascade="all, delete-orphan")
    authoritative_defs = relationship("DataContractAuthorityDb", back_populates="contract", cascade="all, delete-orphan")
    custom_properties = relationship("DataContractCustomPropertyDb", back_populates="contract", cascade="all, delete-orphan")
    sla_properties = relationship("DataContractSlaPropertyDb", back_populates="contract", cascade="all, delete-orphan")
    schema_objects = relationship("SchemaObjectDb", back_populates="contract", cascade="all, delete-orphan")
    comments = relationship("DataContractCommentDb", back_populates="contract", cascade="all, delete-orphan")


class DataContractTagDb(Base):
    __tablename__ = "data_contract_tags"
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    contract_id = Column(String, ForeignKey("data_contracts.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    contract = relationship("DataContractDb", back_populates="tags")
    __table_args__ = (UniqueConstraint("contract_id", "name", name="uq_contract_tag"),)


class DataContractServerDb(Base):
    __tablename__ = "data_contract_servers"
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    contract_id = Column(String, ForeignKey("data_contracts.id", ondelete="CASCADE"), nullable=False, index=True)
    server = Column(String, nullable=True)  # identifier
    type = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    environment = Column(String, nullable=True)
    contract = relationship("DataContractDb", back_populates="servers")
    properties = relationship("DataContractServerPropertyDb", back_populates="server_row", cascade="all, delete-orphan")


class DataContractServerPropertyDb(Base):
    __tablename__ = "data_contract_server_properties"
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    server_id = Column(String, ForeignKey("data_contract_servers.id", ondelete="CASCADE"), nullable=False, index=True)
    key = Column(String, nullable=False)
    value = Column(String, nullable=True)
    server_row = relationship("DataContractServerDb", back_populates="properties")


class DataContractRoleDb(Base):
    __tablename__ = "data_contract_roles"
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    contract_id = Column(String, ForeignKey("data_contracts.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    access = Column(String, nullable=True)
    first_level_approvers = Column(String, nullable=True)
    second_level_approvers = Column(String, nullable=True)
    contract = relationship("DataContractDb", back_populates="roles")
    custom_properties = relationship("DataContractRolePropertyDb", back_populates="role_row", cascade="all, delete-orphan")


class DataContractRolePropertyDb(Base):
    __tablename__ = "data_contract_role_properties"
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    role_id = Column(String, ForeignKey("data_contract_roles.id", ondelete="CASCADE"), nullable=False, index=True)
    property = Column(String, nullable=False)
    value = Column(Text, nullable=True)
    role_row = relationship("DataContractRoleDb", back_populates="custom_properties")


class DataContractTeamDb(Base):
    __tablename__ = "data_contract_team"
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    contract_id = Column(String, ForeignKey("data_contracts.id", ondelete="CASCADE"), nullable=False, index=True)
    username = Column(String, nullable=False)
    role = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    date_in = Column(String, nullable=True)  # ISO date string
    date_out = Column(String, nullable=True)
    replaced_by_username = Column(String, nullable=True)
    contract = relationship("DataContractDb", back_populates="team")


class DataContractSupportDb(Base):
    __tablename__ = "data_contract_support"
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    contract_id = Column(String, ForeignKey("data_contracts.id", ondelete="CASCADE"), nullable=False, index=True)
    channel = Column(String, nullable=False)
    url = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    tool = Column(String, nullable=True)
    scope = Column(String, nullable=True)
    invitation_url = Column(String, nullable=True)
    contract = relationship("DataContractDb", back_populates="support")


class DataContractPricingDb(Base):
    __tablename__ = "data_contract_pricing"
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    contract_id = Column(String, ForeignKey("data_contracts.id", ondelete="CASCADE"), nullable=False, index=True)
    price_amount = Column(String, nullable=True)
    price_currency = Column(String, nullable=True)
    price_unit = Column(String, nullable=True)
    contract = relationship("DataContractDb", back_populates="pricing")


class DataContractAuthorityDb(Base):
    __tablename__ = "data_contract_authorities"
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    contract_id = Column(String, ForeignKey("data_contracts.id", ondelete="CASCADE"), nullable=False, index=True)
    url = Column(String, nullable=False)
    type = Column(String, nullable=False)
    contract = relationship("DataContractDb", back_populates="authoritative_defs")


class DataContractCustomPropertyDb(Base):
    __tablename__ = "data_contract_custom_properties"
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    contract_id = Column(String, ForeignKey("data_contracts.id", ondelete="CASCADE"), nullable=False, index=True)
    property = Column(String, nullable=False)
    value = Column(Text, nullable=True)
    contract = relationship("DataContractDb", back_populates="custom_properties")


class DataContractSlaPropertyDb(Base):
    __tablename__ = "data_contract_sla_properties"
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    contract_id = Column(String, ForeignKey("data_contracts.id", ondelete="CASCADE"), nullable=False, index=True)
    property = Column(String, nullable=False)
    value = Column(String, nullable=True)
    value_ext = Column(String, nullable=True)
    unit = Column(String, nullable=True)
    element = Column(String, nullable=True)
    driver = Column(String, nullable=True)
    contract = relationship("DataContractDb", back_populates="sla_properties")


class SchemaObjectDb(Base):
    __tablename__ = "data_contract_schema_objects"
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    contract_id = Column(String, ForeignKey("data_contracts.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    logical_type = Column(String, nullable=False, default="object")
    physical_name = Column(String, nullable=True)
    data_granularity_description = Column(Text, nullable=True)

    # ODCS v3.0.2 additional schema object fields
    business_name = Column(String, nullable=True)  # ODCS businessName field
    physical_type = Column(String, nullable=True)  # ODCS physicalType field (table, view, etc.)
    tags = Column(Text, nullable=True)  # ODCS schema-level tags (JSON array stored as text)
    description = Column(Text, nullable=True)  # ODCS description field

    contract = relationship("DataContractDb", back_populates="schema_objects")
    properties = relationship("SchemaPropertyDb", back_populates="schema_object", cascade="all, delete-orphan")
    quality_checks = relationship("DataQualityCheckDb", back_populates="schema_object", cascade="all, delete-orphan")
    authoritative_definitions = relationship("SchemaObjectAuthorityDb", back_populates="schema_object", cascade="all, delete-orphan")
    custom_properties = relationship("SchemaObjectCustomPropertyDb", back_populates="schema_object", cascade="all, delete-orphan")


class SchemaPropertyDb(Base):
    __tablename__ = "data_contract_schema_properties"
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    object_id = Column(String, ForeignKey("data_contract_schema_objects.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_property_id = Column(String, ForeignKey("data_contract_schema_properties.id", ondelete="CASCADE"), nullable=True, index=True)
    name = Column(String, nullable=False)
    logical_type = Column(String, nullable=True)
    physical_type = Column(String, nullable=True)
    required = Column(Boolean, nullable=False, default=False)
    unique = Column(Boolean, nullable=False, default=False)
    primary_key = Column(Boolean, nullable=False, default=False)
    partitioned = Column(Boolean, nullable=False, default=False)
    primary_key_position = Column(Integer, nullable=False, default=-1)
    partition_key_position = Column(Integer, nullable=False, default=-1)
    classification = Column(String, nullable=True)
    encrypted_name = Column(String, nullable=True)
    transform_source_objects = Column(Text, nullable=True)  # comma-separated
    transform_logic = Column(Text, nullable=True)
    transform_description = Column(Text, nullable=True)
    examples = Column(Text, nullable=True)  # comma-separated or JSON-like string
    critical_data_element = Column(Boolean, nullable=False, default=False)
    logical_type_options_json = Column(Text, nullable=True)  # JSON string of ODCS type-specific options
    items_logical_type = Column(String, nullable=True)  # for arrays
    business_name = Column(String, nullable=True)  # ODCS businessName field at property level
    schema_object = relationship("SchemaObjectDb", back_populates="properties")
    parent_property = relationship("SchemaPropertyDb", remote_side=[id])
    authoritative_definitions = relationship("SchemaPropertyAuthorityDb", back_populates="property", cascade="all, delete-orphan")


class DataQualityCheckDb(Base):
    __tablename__ = "data_contract_quality_checks"
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    object_id = Column(String, ForeignKey("data_contract_schema_objects.id", ondelete="CASCADE"), nullable=False, index=True)
    level = Column(String, nullable=True)  # optional, e.g., object/property
    name = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    dimension = Column(String, nullable=True)  # ODCS quality dimensions: accuracy, completeness, conformity, consistency, coverage, timeliness, uniqueness
    business_impact = Column(String, nullable=True)  # ODCS business impact: operational, regulatory
    method = Column(String, nullable=True)
    schedule = Column(String, nullable=True)
    scheduler = Column(String, nullable=True)
    severity = Column(String, nullable=True)  # ODCS severity: info, warning, error
    type = Column(String, nullable=False, default="library")  # text|library|sql|custom
    unit = Column(String, nullable=True)
    tags = Column(Text, nullable=True)

    # Type-specific fields
    rule = Column(String, nullable=True)  # library
    query = Column(Text, nullable=True)   # sql
    engine = Column(String, nullable=True)  # custom
    implementation = Column(Text, nullable=True)  # custom impl string/json

    # Comparators
    must_be = Column(String, nullable=True)
    must_not_be = Column(String, nullable=True)
    must_be_gt = Column(String, nullable=True)
    must_be_ge = Column(String, nullable=True)
    must_be_lt = Column(String, nullable=True)
    must_be_le = Column(String, nullable=True)
    must_be_between_min = Column(String, nullable=True)
    must_be_between_max = Column(String, nullable=True)
    must_not_between_min = Column(String, nullable=True)
    must_not_between_max = Column(String, nullable=True)

    schema_object = relationship("SchemaObjectDb", back_populates="quality_checks")


class DataContractCommentDb(Base):
    __tablename__ = "data_contract_comments"
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    contract_id = Column(String, ForeignKey("data_contracts.id", ondelete="CASCADE"), nullable=False, index=True)
    author = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    contract = relationship("DataContractDb", back_populates="comments")


class SchemaObjectAuthorityDb(Base):
    """ODCS v3.0.2 schema-level authoritative definitions"""
    __tablename__ = "data_contract_schema_object_authorities"
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    schema_object_id = Column(String, ForeignKey("data_contract_schema_objects.id", ondelete="CASCADE"), nullable=False, index=True)
    url = Column(String, nullable=False)
    type = Column(String, nullable=False)
    schema_object = relationship("SchemaObjectDb", back_populates="authoritative_definitions")


class SchemaObjectCustomPropertyDb(Base):
    """ODCS v3.0.2 schema-level custom properties"""
    __tablename__ = "data_contract_schema_object_custom_properties"
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    schema_object_id = Column(String, ForeignKey("data_contract_schema_objects.id", ondelete="CASCADE"), nullable=False, index=True)
    property = Column(String, nullable=False)
    value = Column(Text, nullable=True)
    schema_object = relationship("SchemaObjectDb", back_populates="custom_properties")


class SchemaPropertyAuthorityDb(Base):
    """ODCS v3.0.2 property-level authoritative definitions"""
    __tablename__ = "data_contract_schema_property_authorities"
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    property_id = Column(String, ForeignKey("data_contract_schema_properties.id", ondelete="CASCADE"), nullable=False, index=True)
    url = Column(String, nullable=False)
    type = Column(String, nullable=False)
    property = relationship("SchemaPropertyDb", back_populates="authoritative_definitions")


