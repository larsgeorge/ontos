"""
ODPS v1.0.0 (Open Data Product Standard) Database Models

This module implements the Bitol ODPS v1.0.0 specification for Data Products.
Schema: https://github.com/bitol-io/open-data-product-standard/blob/main/schema/odps-json-schema-v1.0.0.json

All models follow the ODPS v1.0.0 structure with Databricks-specific extensions where needed.
"""

from sqlalchemy import Column, String, DateTime, Text, Boolean, func, ForeignKey, Date
from sqlalchemy.orm import relationship
from uuid import uuid4

from src.common.database import Base


# ============================================================================
# Main Data Product
# ============================================================================

class DataProductDb(Base):
    """ODPS v1.0.0 Data Product - Main entity"""
    __tablename__ = 'data_products'

    # ==================== ODPS v1.0.0 Required Fields ====================
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    api_version = Column(String, nullable=False, default="v1.0.0")
    kind = Column(String, nullable=False, default="DataProduct")
    status = Column(String, nullable=False, index=True)  # proposed, draft, active, deprecated, retired

    # ==================== ODPS v1.0.0 Optional Fields ====================
    name = Column(String, nullable=True, index=True)
    version = Column(String, nullable=True, index=True)
    domain = Column(String, nullable=True, index=True)
    tenant = Column(String, nullable=True, index=True)
    product_created_ts = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # ==================== Databricks Extensions ====================
    project_id = Column(String, ForeignKey('projects.id'), nullable=True, index=True)
    owner_team_id = Column(String, ForeignKey('teams.id'), nullable=True, index=True)  # Team UUID reference

    # ==================== Audit Fields ====================
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # ==================== ODPS v1.0.0 Relationships ====================
    description = relationship("DescriptionDb", back_populates="product", uselist=False, cascade="all, delete-orphan")
    authoritative_definitions = relationship("AuthoritativeDefinitionDb", back_populates="product", cascade="all, delete-orphan")
    custom_properties = relationship("CustomPropertyDb", back_populates="product", cascade="all, delete-orphan")
    input_ports = relationship("InputPortDb", back_populates="product", cascade="all, delete-orphan", lazy="selectin")
    output_ports = relationship("OutputPortDb", back_populates="product", cascade="all, delete-orphan", lazy="selectin")
    management_ports = relationship("ManagementPortDb", back_populates="product", cascade="all, delete-orphan")
    support_channels = relationship("SupportDb", back_populates="product", cascade="all, delete-orphan")
    team = relationship("DataProductTeamDb", back_populates="product", uselist=False, cascade="all, delete-orphan")
    owner_team = relationship("TeamDb", foreign_keys=[owner_team_id])

    def __repr__(self):
        return f"<DataProductDb(id='{self.id}', name='{self.name}', status='{self.status}')>"


# ============================================================================
# ODPS Description (Structured)
# ============================================================================

class DescriptionDb(Base):
    """ODPS v1.0.0 Structured Description"""
    __tablename__ = 'product_descriptions'

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    product_id = Column(String, ForeignKey('data_products.id'), unique=True, nullable=False)

    purpose = Column(Text, nullable=True)
    limitations = Column(Text, nullable=True)
    usage = Column(Text, nullable=True)

    product = relationship("DataProductDb", back_populates="description")

    def __repr__(self):
        return f"<DescriptionDb(product_id='{self.product_id}')>"


# ============================================================================
# ODPS Authoritative Definitions
# ============================================================================

class AuthoritativeDefinitionDb(Base):
    """ODPS v1.0.0 Authoritative Definition - Links to business definitions, implementations, tutorials"""
    __tablename__ = 'product_authoritative_definitions'

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    product_id = Column(String, ForeignKey('data_products.id'), nullable=False, index=True)

    type = Column(String, nullable=False)  # businessDefinition, transformationImplementation, videoTutorial, tutorial, implementation
    url = Column(String, nullable=False)
    description = Column(Text, nullable=True)

    product = relationship("DataProductDb", back_populates="authoritative_definitions")

    def __repr__(self):
        return f"<AuthoritativeDefinitionDb(type='{self.type}', url='{self.url}')>"


# ============================================================================
# ODPS Custom Properties
# ============================================================================

class CustomPropertyDb(Base):
    """ODPS v1.0.0 Custom Property - Key/value pairs for extensibility"""
    __tablename__ = 'product_custom_properties'

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    product_id = Column(String, ForeignKey('data_products.id'), nullable=False, index=True)

    property = Column(String, nullable=False)  # camelCase name
    value = Column(Text, nullable=True)  # Stored as JSON string for complex values
    description = Column(Text, nullable=True)

    product = relationship("DataProductDb", back_populates="custom_properties")

    def __repr__(self):
        return f"<CustomPropertyDb(property='{self.property}')>"


# ============================================================================
# ODPS Input Ports
# ============================================================================

class InputPortDb(Base):
    """ODPS v1.0.0 Input Port - Describes data product inputs"""
    __tablename__ = 'input_ports'

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    product_id = Column(String, ForeignKey('data_products.id'), nullable=False, index=True)

    # ==================== ODPS v1.0.0 Required Fields ====================
    name = Column(String, nullable=False)
    version = Column(String, nullable=False)
    contract_id = Column(String, nullable=False, index=True)  # REQUIRED in ODPS!

    # ==================== Databricks Extensions ====================
    asset_type = Column(String, nullable=True, index=True)  # table, notebook, job, etc.
    asset_identifier = Column(String, nullable=True, index=True)  # catalog.schema.table, /path/to/notebook, job_id

    product = relationship("DataProductDb", back_populates="input_ports")

    def __repr__(self):
        return f"<InputPortDb(name='{self.name}', version='{self.version}', contract_id='{self.contract_id}')>"


# ============================================================================
# ODPS Output Ports
# ============================================================================

class OutputPortDb(Base):
    """ODPS v1.0.0 Output Port - Describes data product outputs"""
    __tablename__ = 'output_ports'

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    product_id = Column(String, ForeignKey('data_products.id'), nullable=False, index=True)

    # ==================== ODPS v1.0.0 Required Fields ====================
    name = Column(String, nullable=False)
    version = Column(String, nullable=False)

    # ==================== ODPS v1.0.0 Optional Fields ====================
    description = Column(Text, nullable=True)
    port_type = Column(String, nullable=True)  # Type of output port
    contract_id = Column(String, nullable=True, index=True)  # Optional link to contract

    # ==================== Databricks Extensions ====================
    asset_type = Column(String, nullable=True, index=True)  # table, view, etc.
    asset_identifier = Column(String, nullable=True, index=True)  # catalog.schema.table
    status = Column(String, nullable=True, index=True)  # active, deprecated, etc.
    server = Column(Text, nullable=True)  # JSON string with connection details
    contains_pii = Column(Boolean, default=False)
    auto_approve = Column(Boolean, default=False)

    product = relationship("DataProductDb", back_populates="output_ports")
    sbom = relationship("SBOMDb", back_populates="output_port", cascade="all, delete-orphan")
    input_contracts = relationship("InputContractDb", back_populates="output_port", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<OutputPortDb(name='{self.name}', version='{self.version}')>"


# ============================================================================
# ODPS SBOM (Software Bill of Materials)
# ============================================================================

class SBOMDb(Base):
    """ODPS v1.0.0 SBOM - Software Bill of Materials for output ports"""
    __tablename__ = 'output_port_sbom'

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    output_port_id = Column(String, ForeignKey('output_ports.id'), nullable=False, index=True)

    type = Column(String, default="external")
    url = Column(String, nullable=False)

    output_port = relationship("OutputPortDb", back_populates="sbom")

    def __repr__(self):
        return f"<SBOMDb(type='{self.type}', url='{self.url}')>"


# ============================================================================
# ODPS Input Contracts (Dependencies)
# ============================================================================

class InputContractDb(Base):
    """ODPS v1.0.0 Input Contract - Dependencies for output ports"""
    __tablename__ = 'output_port_input_contracts'

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    output_port_id = Column(String, ForeignKey('output_ports.id'), nullable=False, index=True)

    contract_id = Column(String, nullable=False, index=True)
    contract_version = Column(String, nullable=False)

    output_port = relationship("OutputPortDb", back_populates="input_contracts")

    def __repr__(self):
        return f"<InputContractDb(contract_id='{self.contract_id}', version='{self.contract_version}')>"


# ============================================================================
# ODPS Management Ports (NEW CONCEPT)
# ============================================================================

class ManagementPortDb(Base):
    """ODPS v1.0.0 Management Port - Endpoints for managing the data product"""
    __tablename__ = 'management_ports'

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    product_id = Column(String, ForeignKey('data_products.id'), nullable=False, index=True)

    # ==================== ODPS v1.0.0 Required Fields ====================
    name = Column(String, nullable=False)  # Endpoint identifier
    content = Column(String, nullable=False)  # discoverability, observability, control, dictionary

    # ==================== ODPS v1.0.0 Optional Fields ====================
    port_type = Column(String, default="rest")  # rest or topic
    url = Column(String, nullable=True)
    channel = Column(String, nullable=True)
    description = Column(Text, nullable=True)

    product = relationship("DataProductDb", back_populates="management_ports")

    def __repr__(self):
        return f"<ManagementPortDb(name='{self.name}', content='{self.content}')>"


# ============================================================================
# ODPS Support Channels
# ============================================================================

class SupportDb(Base):
    """ODPS v1.0.0 Support Channel - Communication channels for support"""
    __tablename__ = 'product_support_channels'

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    product_id = Column(String, ForeignKey('data_products.id'), nullable=False, index=True)

    # ==================== ODPS v1.0.0 Required Fields ====================
    channel = Column(String, nullable=False)
    url = Column(String, nullable=False)

    # ==================== ODPS v1.0.0 Optional Fields ====================
    description = Column(Text, nullable=True)
    tool = Column(String, nullable=True)  # email, slack, teams, discord, ticket, other
    scope = Column(String, nullable=True)  # interactive, announcements, issues
    invitation_url = Column(String, nullable=True)

    product = relationship("DataProductDb", back_populates="support_channels")

    def __repr__(self):
        return f"<SupportDb(channel='{self.channel}', tool='{self.tool}')>"


# ============================================================================
# ODPS Team
# ============================================================================

class DataProductTeamDb(Base):
    """ODPS v1.0.0 Team - Team information for the data product"""
    __tablename__ = 'product_teams'

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    product_id = Column(String, ForeignKey('data_products.id'), unique=True, nullable=False)

    name = Column(String, nullable=True)
    description = Column(Text, nullable=True)

    product = relationship("DataProductDb", back_populates="team")
    members = relationship("DataProductTeamMemberDb", back_populates="team", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<DataProductTeamDb(name='{self.name}')>"


# ============================================================================
# ODPS Team Members
# ============================================================================

class DataProductTeamMemberDb(Base):
    """ODPS v1.0.0 Team Member - Individual team member information"""
    __tablename__ = 'product_team_members'

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    team_id = Column(String, ForeignKey('product_teams.id'), nullable=False, index=True)

    # ==================== ODPS v1.0.0 Required Fields ====================
    username = Column(String, nullable=False)  # Email or username

    # ==================== ODPS v1.0.0 Optional Fields ====================
    name = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    role = Column(String, nullable=True)  # owner, data steward, contributor, etc.
    date_in = Column(Date, nullable=True)
    date_out = Column(Date, nullable=True)
    replaced_by_username = Column(String, nullable=True)

    team = relationship("DataProductTeamDb", back_populates="members")

    def __repr__(self):
        return f"<DataProductTeamMemberDb(username='{self.username}', role='{self.role}')>"
