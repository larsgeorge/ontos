"""
ODPS v1.0.0 Data Product Repository

This module implements the repository layer for ODPS v1.0.0 Data Products.
Handles mapping between API models (Pydantic) and DB models (SQLAlchemy).
"""

from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select, distinct
from typing import List, Optional, Any, Dict, Union
import json

from src.common.repository import CRUDBase
from src.models.data_products import (
    DataProduct as DataProductApi,
    DataProductCreate,
    DataProductUpdate,
    Description,
    AuthoritativeDefinition,
    CustomProperty,
    InputPort,
    OutputPort,
    ManagementPort,
    Support,
    Team,
    TeamMember,
    SBOM,
    InputContract
)
from src.db_models.data_products import (
    DataProductDb,
    DescriptionDb,
    AuthoritativeDefinitionDb,
    CustomPropertyDb,
    InputPortDb,
    OutputPortDb,
    ManagementPortDb,
    SupportDb,
    DataProductTeamDb,
    DataProductTeamMemberDb,
    SBOMDb,
    InputContractDb
)
from src.common.logging import get_logger

logger = get_logger(__name__)


class DataProductRepository(CRUDBase[DataProductDb, DataProductCreate, DataProductUpdate]):
    """Repository for ODPS v1.0.0 DataProduct CRUD operations."""

    def create(self, db: Session, *, obj_in: DataProductCreate) -> DataProductDb:
        """Create a new ODPS v1.0.0 Data Product with all relationships."""
        logger.debug(f"Creating ODPS v1.0.0 DataProduct: {obj_in.id}")

        try:
            # 1. Create core DataProduct
            db_obj = self.model(
                id=obj_in.id,
                api_version=obj_in.apiVersion,
                kind=obj_in.kind,
                status=obj_in.status,
                name=obj_in.name,
                version=obj_in.version,
                domain=obj_in.domain,
                tenant=obj_in.tenant,
                owner_team_id=obj_in.owner_team_id,
                project_id=None  # Set via manager if needed
            )

            # 2. Create Structured Description (One-to-One)
            if obj_in.description:
                desc_obj = DescriptionDb(
                    purpose=obj_in.description.purpose,
                    limitations=obj_in.description.limitations,
                    usage=obj_in.description.usage
                )
                db_obj.description = desc_obj

            # 3. Create Authoritative Definitions (One-to-Many)
            if obj_in.authoritativeDefinitions:
                for auth_def in obj_in.authoritativeDefinitions:
                    auth_obj = AuthoritativeDefinitionDb(
                        type=auth_def.type,
                        url=auth_def.url,
                        description=auth_def.description
                    )
                    db_obj.authoritative_definitions.append(auth_obj)

            # 4. Create Custom Properties (One-to-Many)
            if obj_in.customProperties:
                for custom_prop in obj_in.customProperties:
                    # Store value as JSON string to support any type
                    value_str = json.dumps(custom_prop.value) if not isinstance(custom_prop.value, str) else custom_prop.value
                    prop_obj = CustomPropertyDb(
                        property=custom_prop.property,
                        value=value_str,
                        description=custom_prop.description
                    )
                    db_obj.custom_properties.append(prop_obj)

            # 5. Create Input Ports (One-to-Many)
            if obj_in.inputPorts:
                for port in obj_in.inputPorts:
                    port_obj = InputPortDb(
                        name=port.name,
                        version=port.version,
                        contract_id=port.contractId,  # REQUIRED in ODPS!
                        asset_type=port.assetType,
                        asset_identifier=port.assetIdentifier
                    )
                    db_obj.input_ports.append(port_obj)

            # 6. Create Output Ports (One-to-Many) with SBOM and InputContracts
            if obj_in.outputPorts:
                for port in obj_in.outputPorts:
                    # Serialize server as JSON string
                    server_json = None
                    if port.server:
                        server_json = json.dumps(port.server.model_dump(exclude_none=True))

                    port_obj = OutputPortDb(
                        name=port.name,
                        version=port.version,
                        description=port.description,
                        port_type=port.type,
                        contract_id=port.contractId,
                        asset_type=port.assetType,
                        asset_identifier=port.assetIdentifier,
                        status=port.status,
                        server=server_json,
                        contains_pii=port.containsPii,
                        auto_approve=port.autoApprove
                    )

                    # Create SBOM entries for this output port
                    if port.sbom:
                        for sbom in port.sbom:
                            sbom_obj = SBOMDb(
                                type=sbom.type,
                                url=sbom.url
                            )
                            port_obj.sbom.append(sbom_obj)

                    # Create InputContract entries for this output port
                    if port.inputContracts:
                        for input_contract in port.inputContracts:
                            contract_obj = InputContractDb(
                                contract_id=input_contract.id,
                                contract_version=input_contract.version
                            )
                            port_obj.input_contracts.append(contract_obj)

                    db_obj.output_ports.append(port_obj)

            # 7. Create Management Ports (One-to-Many) - NEW in ODPS v1.0.0
            if obj_in.managementPorts:
                for mgmt_port in obj_in.managementPorts:
                    mgmt_obj = ManagementPortDb(
                        name=mgmt_port.name,
                        content=mgmt_port.content,
                        port_type=mgmt_port.type,
                        url=mgmt_port.url,
                        channel=mgmt_port.channel,
                        description=mgmt_port.description
                    )
                    db_obj.management_ports.append(mgmt_obj)

            # 8. Create Support Channels (One-to-Many)
            if obj_in.support:
                for support in obj_in.support:
                    support_obj = SupportDb(
                        channel=support.channel,
                        url=support.url,
                        description=support.description,
                        tool=support.tool,
                        scope=support.scope,
                        invitation_url=support.invitationUrl
                    )
                    db_obj.support_channels.append(support_obj)

            # 9. Create Team (One-to-One) with Members (One-to-Many)
            if obj_in.team:
                team_obj = DataProductTeamDb(
                    name=obj_in.team.name,
                    description=obj_in.team.description
                )

                # Create Team Members
                if obj_in.team.members:
                    for member in obj_in.team.members:
                        member_obj = DataProductTeamMemberDb(
                            username=member.username,
                            name=member.name,
                            description=member.description,
                            role=member.role,
                            date_in=member.dateIn,
                            date_out=member.dateOut,
                            replaced_by_username=member.replacedByUsername
                        )
                        team_obj.members.append(member_obj)

                db_obj.team = team_obj

            # 10. Persist to database
            db.add(db_obj)
            db.flush()
            db.refresh(db_obj)
            logger.info(f"Successfully created ODPS v1.0.0 DataProduct: {db_obj.id}")
            return db_obj

        except Exception as e:
            logger.error(f"Database error creating ODPS DataProduct: {e}", exc_info=True)
            db.rollback()
            raise

    def update(self, db: Session, *, db_obj: DataProductDb, obj_in: Union[DataProductUpdate, Dict[str, Any]]) -> DataProductDb:
        """Update an ODPS v1.0.0 Data Product with all relationships."""
        logger.debug(f"Updating ODPS v1.0.0 DataProduct: {db_obj.id}")

        # Convert Pydantic model to dict if necessary
        if not isinstance(obj_in, dict):
            update_data = obj_in.model_dump(exclude_unset=True, by_alias=True)
        else:
            update_data = obj_in

        try:
            # 1. Update core fields
            if 'apiVersion' in update_data:
                db_obj.api_version = update_data['apiVersion']
            if 'kind' in update_data:
                db_obj.kind = update_data['kind']
            if 'status' in update_data:
                db_obj.status = update_data['status']
            if 'name' in update_data:
                db_obj.name = update_data['name']
            if 'version' in update_data:
                db_obj.version = update_data['version']
            if 'domain' in update_data:
                db_obj.domain = update_data['domain']
            if 'tenant' in update_data:
                db_obj.tenant = update_data['tenant']
            if 'owner_team_id' in update_data:
                db_obj.owner_team_id = update_data['owner_team_id']
            if 'project_id' in update_data:
                db_obj.project_id = update_data['project_id']

            # 2. Update Structured Description
            if 'description' in update_data:
                if db_obj.description:
                    # Update existing
                    desc_data = update_data['description']
                    db_obj.description.purpose = desc_data.get('purpose', db_obj.description.purpose)
                    db_obj.description.limitations = desc_data.get('limitations', db_obj.description.limitations)
                    db_obj.description.usage = desc_data.get('usage', db_obj.description.usage)
                else:
                    # Create new
                    desc_data = update_data['description']
                    desc_obj = DescriptionDb(
                        purpose=desc_data.get('purpose'),
                        limitations=desc_data.get('limitations'),
                        usage=desc_data.get('usage')
                    )
                    db_obj.description = desc_obj

            # 3. Update Authoritative Definitions (replace all)
            if 'authoritativeDefinitions' in update_data:
                db_obj.authoritative_definitions.clear()
                for auth_def_dict in update_data['authoritativeDefinitions'] or []:
                    auth_obj = AuthoritativeDefinitionDb(
                        type=auth_def_dict['type'],
                        url=auth_def_dict['url'],
                        description=auth_def_dict.get('description')
                    )
                    db_obj.authoritative_definitions.append(auth_obj)

            # 4. Update Custom Properties (replace all)
            if 'customProperties' in update_data:
                db_obj.custom_properties.clear()
                for prop_dict in update_data['customProperties'] or []:
                    value_str = json.dumps(prop_dict['value']) if not isinstance(prop_dict['value'], str) else prop_dict['value']
                    prop_obj = CustomPropertyDb(
                        property=prop_dict['property'],
                        value=value_str,
                        description=prop_dict.get('description')
                    )
                    db_obj.custom_properties.append(prop_obj)

            # 5. Update Input Ports (replace all)
            if 'input_ports' in update_data:
                db_obj.input_ports.clear()
                for port_dict in update_data['input_ports'] or []:
                    port_obj = InputPortDb(
                        name=port_dict['name'],
                        version=port_dict['version'],
                        contract_id=port_dict['contract_id'],
                        asset_type=port_dict.get('asset_type'),
                        asset_identifier=port_dict.get('asset_identifier')
                    )
                    db_obj.input_ports.append(port_obj)

            # 6. Update Output Ports (replace all) with SBOM and InputContracts
            if 'output_ports' in update_data:
                db_obj.output_ports.clear()
                for port_dict in update_data['output_ports'] or []:
                    # Serialize server
                    server_json = None
                    if port_dict.get('server'):
                        server_json = json.dumps(port_dict['server']) if isinstance(port_dict['server'], dict) else port_dict['server']

                    port_obj = OutputPortDb(
                        name=port_dict['name'],
                        version=port_dict['version'],
                        description=port_dict.get('description'),
                        port_type=port_dict.get('type'),
                        contract_id=port_dict.get('contract_id'),
                        asset_type=port_dict.get('asset_type'),
                        asset_identifier=port_dict.get('asset_identifier'),
                        status=port_dict.get('status'),
                        server=server_json,
                        contains_pii=port_dict.get('contains_pii', False),
                        auto_approve=port_dict.get('auto_approve', False)
                    )

                    # Add SBOM entries
                    if port_dict.get('sbom'):
                        for sbom_dict in port_dict['sbom']:
                            sbom_obj = SBOMDb(
                                type=sbom_dict.get('type', 'external'),
                                url=sbom_dict['url']
                            )
                            port_obj.sbom.append(sbom_obj)

                    # Add InputContract entries
                    if port_dict.get('input_contracts'):
                        for contract_dict in port_dict['input_contracts']:
                            contract_obj = InputContractDb(
                                contract_id=contract_dict['id'],
                                contract_version=contract_dict['version']
                            )
                            port_obj.input_contracts.append(contract_obj)

                    db_obj.output_ports.append(port_obj)

            # 7. Update Management Ports (replace all)
            if 'management_ports' in update_data:
                db_obj.management_ports.clear()
                for mgmt_dict in update_data['management_ports'] or []:
                    mgmt_obj = ManagementPortDb(
                        name=mgmt_dict['name'],
                        content=mgmt_dict['content'],
                        port_type=mgmt_dict.get('type', 'rest'),
                        url=mgmt_dict.get('url'),
                        channel=mgmt_dict.get('channel'),
                        description=mgmt_dict.get('description')
                    )
                    db_obj.management_ports.append(mgmt_obj)

            # 8. Update Support Channels (replace all)
            if 'support_channels' in update_data:
                db_obj.support_channels.clear()
                for support_dict in update_data['support_channels'] or []:
                    support_obj = SupportDb(
                        channel=support_dict['channel'],
                        url=support_dict['url'],
                        description=support_dict.get('description'),
                        tool=support_dict.get('tool'),
                        scope=support_dict.get('scope'),
                        invitation_url=support_dict.get('invitation_url')
                    )
                    db_obj.support_channels.append(support_obj)

            # 9. Update Team with Members (replace all)
            if 'team' in update_data:
                team_dict = update_data['team']
                # Only process team if team_dict is not None
                if team_dict is not None:
                    if db_obj.team:
                        # Update existing team
                        db_obj.team.name = team_dict.get('name', db_obj.team.name)
                        db_obj.team.description = team_dict.get('description', db_obj.team.description)

                        # Replace members
                        db_obj.team.members.clear()
                        if team_dict.get('members'):
                            for member_dict in team_dict['members']:
                                member_obj = DataProductTeamMemberDb(
                                    username=member_dict['username'],
                                    name=member_dict.get('name'),
                                    description=member_dict.get('description'),
                                    role=member_dict.get('role'),
                                    date_in=member_dict.get('date_in'),
                                    date_out=member_dict.get('date_out'),
                                    replaced_by_username=member_dict.get('replaced_by_username')
                                )
                                db_obj.team.members.append(member_obj)
                    else:
                        # Create new team
                        team_obj = DataProductTeamDb(
                            name=team_dict.get('name'),
                            description=team_dict.get('description')
                        )

                        if team_dict.get('members'):
                            for member_dict in team_dict['members']:
                                member_obj = DataProductTeamMemberDb(
                                    username=member_dict['username'],
                                    name=member_dict.get('name'),
                                    description=member_dict.get('description'),
                                    role=member_dict.get('role'),
                                    date_in=member_dict.get('date_in'),
                                    date_out=member_dict.get('date_out'),
                                    replaced_by_username=member_dict.get('replaced_by_username')
                                )
                                team_obj.members.append(member_obj)

                        db_obj.team = team_obj

            # 10. Persist changes
            db.add(db_obj)
            db.flush()
            db.refresh(db_obj)
            logger.info(f"Successfully updated ODPS v1.0.0 DataProduct: {db_obj.id}")
            return db_obj

        except Exception as e:
            logger.error(f"Database error updating ODPS DataProduct {db_obj.id}: {e}", exc_info=True)
            db.rollback()
            raise

    def get(self, db: Session, id: Any) -> Optional[DataProductDb]:
        """Get a single ODPS v1.0.0 Data Product with all relationships eagerly loaded."""
        logger.debug(f"Fetching ODPS v1.0.0 DataProduct: {id}")
        try:
            return db.query(self.model).options(
                selectinload(self.model.description),
                selectinload(self.model.authoritative_definitions),
                selectinload(self.model.custom_properties),
                selectinload(self.model.input_ports),
                selectinload(self.model.output_ports).selectinload(OutputPortDb.sbom),
                selectinload(self.model.output_ports).selectinload(OutputPortDb.input_contracts),
                selectinload(self.model.management_ports),
                selectinload(self.model.support_channels),
                selectinload(self.model.team).selectinload(DataProductTeamDb.members)
            ).filter(self.model.id == id).first()
        except Exception as e:
            logger.error(f"Database error fetching ODPS DataProduct {id}: {e}", exc_info=True)
            db.rollback()
            raise

    def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        project_id: Optional[str] = None,
        is_admin: bool = False
    ) -> List[DataProductDb]:
        """Get multiple ODPS v1.0.0 Data Products with all relationships eagerly loaded.

        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            project_id: Optional project ID to filter by (ignored if is_admin=True)
            is_admin: If True, return all products regardless of project_id

        Returns:
            List of DataProductDb objects
        """
        logger.debug(f"Fetching multiple ODPS v1.0.0 DataProducts (skip: {skip}, limit: {limit}, project_id: {project_id}, is_admin: {is_admin})")
        try:
            query = db.query(self.model).options(
                selectinload(self.model.description),
                selectinload(self.model.authoritative_definitions),
                selectinload(self.model.custom_properties),
                selectinload(self.model.input_ports),
                selectinload(self.model.output_ports).selectinload(OutputPortDb.sbom),
                selectinload(self.model.output_ports).selectinload(OutputPortDb.input_contracts),
                selectinload(self.model.management_ports),
                selectinload(self.model.support_channels),
                selectinload(self.model.team).selectinload(DataProductTeamDb.members)
            )

            # Apply project filtering only if not admin and project_id is provided
            if not is_admin and project_id:
                logger.debug(f"Filtering products by project_id: {project_id}")
                # Include products with matching project_id OR null project_id (legacy/unassigned)
                query = query.filter(
                    (self.model.project_id == project_id) |
                    (self.model.project_id.is_(None))
                )

            return query.offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"Database error fetching multiple ODPS DataProducts: {e}", exc_info=True)
            db.rollback()
            raise

    # --- ODPS-specific queries ---

    def get_distinct_statuses(self, db: Session) -> List[str]:
        """Get distinct status values from ODPS Data Products."""
        logger.debug("Querying distinct ODPS statuses...")
        try:
            result = db.execute(
                select(distinct(self.model.status)).where(self.model.status.isnot(None))
            ).scalars().all()
            return sorted(list(result))
        except Exception as e:
            logger.error(f"Error querying distinct ODPS statuses: {e}", exc_info=True)
            return []

    def get_distinct_domains(self, db: Session) -> List[str]:
        """Get distinct domain values from ODPS Data Products."""
        logger.debug("Querying distinct ODPS domains...")
        try:
            result = db.execute(
                select(distinct(self.model.domain)).where(self.model.domain.isnot(None))
            ).scalars().all()
            return sorted(list(result))
        except Exception as e:
            logger.error(f"Error querying distinct ODPS domains: {e}", exc_info=True)
            return []

    def get_distinct_tenants(self, db: Session) -> List[str]:
        """Get distinct tenant values from ODPS Data Products."""
        logger.debug("Querying distinct ODPS tenants...")
        try:
            result = db.execute(
                select(distinct(self.model.tenant)).where(self.model.tenant.isnot(None))
            ).scalars().all()
            return sorted(list(result))
        except Exception as e:
            logger.error(f"Error querying distinct ODPS tenants: {e}", exc_info=True)
            return []

    def get_distinct_product_types(self, db: Session) -> List[str]:
        """Get distinct output port type values from ODPS Data Products."""
        from src.db_models.data_products import OutputPortDb
        logger.debug("Querying distinct ODPS product types (output port types)...")
        try:
            result = db.execute(
                select(distinct(OutputPortDb.port_type)).where(OutputPortDb.port_type.isnot(None))
            ).scalars().all()
            return sorted(list(result))
        except Exception as e:
            logger.error(f"Error querying distinct ODPS product types: {e}", exc_info=True)
            return []

    def get_distinct_owners(self, db: Session) -> List[str]:
        """Get distinct owner names from ODPS Data Product teams."""
        from src.db_models.data_products import DataProductTeamMemberDb
        logger.debug("Querying distinct ODPS product owners...")
        try:
            result = db.execute(
                select(distinct(DataProductTeamMemberDb.name))
                .where(DataProductTeamMemberDb.role == 'owner')
                .where(DataProductTeamMemberDb.name.isnot(None))
            ).scalars().all()
            return sorted(list(result))
        except Exception as e:
            logger.error(f"Error querying distinct ODPS product owners: {e}", exc_info=True)
            return []

    def get_by_status(self, db: Session, status: str, skip: int = 0, limit: int = 100) -> List[DataProductDb]:
        """Get ODPS Data Products filtered by status."""
        logger.debug(f"Fetching ODPS DataProducts with status '{status}' (skip: {skip}, limit: {limit})")
        try:
            return db.query(self.model).options(
                selectinload(self.model.description),
                selectinload(self.model.input_ports),
                selectinload(self.model.output_ports),
                selectinload(self.model.team).selectinload(DataProductTeamDb.members)
            ).filter(self.model.status == status).offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"Database error fetching ODPS DataProducts by status: {e}", exc_info=True)
            db.rollback()
            raise

    def get_by_domain(self, db: Session, domain: str, skip: int = 0, limit: int = 100) -> List[DataProductDb]:
        """Get ODPS Data Products filtered by domain."""
        logger.debug(f"Fetching ODPS DataProducts for domain '{domain}' (skip: {skip}, limit: {limit})")
        try:
            return db.query(self.model).options(
                selectinload(self.model.description),
                selectinload(self.model.input_ports),
                selectinload(self.model.output_ports),
                selectinload(self.model.team).selectinload(DataProductTeamDb.members)
            ).filter(self.model.domain == domain).offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"Database error fetching ODPS DataProducts by domain: {e}", exc_info=True)
            db.rollback()
            raise

    # --- Project filtering methods (Databricks extension) ---

    def get_by_project(self, db: Session, project_id: str, skip: int = 0, limit: int = 100) -> List[DataProductDb]:
        """Get ODPS Data Products filtered by project_id (Databricks extension)."""
        logger.debug(f"Fetching ODPS DataProducts for project {project_id} (skip: {skip}, limit: {limit})")
        try:
            return db.query(self.model).options(
                selectinload(self.model.description),
                selectinload(self.model.input_ports),
                selectinload(self.model.output_ports),
                selectinload(self.model.team).selectinload(DataProductTeamDb.members)
            ).filter(self.model.project_id == project_id).offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"Database error fetching ODPS DataProducts by project: {e}", exc_info=True)
            db.rollback()
            raise

    def get_without_project(self, db: Session, skip: int = 0, limit: int = 100) -> List[DataProductDb]:
        """Get ODPS Data Products not assigned to any project."""
        logger.debug(f"Fetching ODPS DataProducts without project (skip: {skip}, limit: {limit})")
        try:
            return db.query(self.model).options(
                selectinload(self.model.description),
                selectinload(self.model.input_ports),
                selectinload(self.model.output_ports),
                selectinload(self.model.team).selectinload(DataProductTeamDb.members)
            ).filter(self.model.project_id.is_(None)).offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"Database error fetching ODPS DataProducts without project: {e}", exc_info=True)
            db.rollback()
            raise

    def count_by_project(self, db: Session, project_id: str) -> int:
        """Count ODPS Data Products for a specific project."""
        logger.debug(f"Counting ODPS DataProducts for project {project_id}")
        try:
            return db.query(self.model).filter(self.model.project_id == project_id).count()
        except Exception as e:
            logger.error(f"Database error counting ODPS DataProducts by project: {e}", exc_info=True)
            db.rollback()
            raise


# Create a single instance of the repository for use
data_product_repo = DataProductRepository(DataProductDb)
