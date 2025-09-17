import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile, Depends, Request, Body
from fastapi.responses import JSONResponse

from src.controller.data_contracts_manager import DataContractsManager
from src.common.dependencies import (
    DBSessionDep,
    AuditManagerDep,
    CurrentUserDep,
    AuditCurrentUserDep,
)
from src.common.audit_logging import _extract_details_default
from src.repositories.data_contracts_repository import data_contract_repo
from src.db_models.data_contracts import (
    DataContractDb,
    DataContractCommentDb,
    DataContractTagDb,
    DataContractRoleDb,
    SchemaObjectDb,
    SchemaPropertyDb,
    DataContractTeamDb,
    DataContractSupportDb,
    DataContractCustomPropertyDb,
    DataContractSlaPropertyDb,
    DataQualityCheckDb,
    DataContractServerDb,
    DataContractServerPropertyDb,
    DataContractAuthorityDb,
    SchemaObjectAuthorityDb,
    SchemaObjectCustomPropertyDb,
    DataContractPricingDb,
    DataContractRolePropertyDb
)
from src.models.data_contracts_api import (
    DataContractCreate,
    DataContractUpdate,
    DataContractRead,
    DataContractCommentCreate,
    DataContractCommentRead,
)
from src.common.odcs_validation import validate_odcs_contract, ODCSValidationError
from src.common.authorization import PermissionChecker
from src.common.features import FeatureAccessLevel
import yaml

# Configure logging
from src.common.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["data-contracts"])

def get_data_contracts_manager(request: Request) -> DataContractsManager:
    """Retrieves the DataContractsManager singleton from app.state."""
    manager = getattr(request.app.state, 'data_contracts_manager', None)
    if manager is None:
        logger.critical("DataContractsManager instance not found in app.state!")
        raise HTTPException(status_code=500, detail="Data Contracts service is not available.")
    if not isinstance(manager, DataContractsManager):
        logger.critical(f"Object found at app.state.data_contracts_manager is not a DataContractsManager instance (Type: {type(manager)})!")
        raise HTTPException(status_code=500, detail="Data Contracts service configuration error.")
    return manager

 

@router.get('/data-contracts', response_model=list[DataContractRead])
async def get_contracts(
    db: DBSessionDep,
    domain_id: Optional[str] = None,
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_ONLY))
):
    """Get all data contracts with basic ODCS structure"""
    try:
        if domain_id:
            # Filter by domain ID
            contracts = db.query(DataContractDb).filter(DataContractDb.domain_id == domain_id).all()
        else:
            # Get all contracts
            contracts = data_contract_repo.get_multi(db)

        return [
            DataContractRead(
                id=c.id,
                name=c.name,
                version=c.version,
                status=c.status,
                owner=c.owner,
                kind=c.kind,
                apiVersion=c.api_version,
                tenant=c.tenant,
                domainId=c.domain_id,  # Include domainId for frontend resolution
                dataProduct=c.data_product,
                created=c.created_at.isoformat() if c.created_at else None,
                updated=c.updated_at.isoformat() if c.updated_at else None,
            )
            for c in contracts
        ]
    except Exception as e:
        error_msg = f"Error retrieving data contracts: {e!s}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@router.get('/data-contracts/{contract_id}', response_model=DataContractRead)
async def get_contract(contract_id: str, db: DBSessionDep, _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_ONLY))):
    """Get a specific data contract with full ODCS structure"""
    try:
        contract = data_contract_repo.get_with_all(db, id=contract_id)
        if not contract:
            raise HTTPException(status_code=404, detail="Contract not found")

        return _build_contract_read_from_db(db, contract)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def _build_contract_read_from_db(db, db_contract) -> DataContractRead:
    """Build DataContractRead from normalized database models"""
    from src.models.data_contracts_api import ContractDescription, SchemaObject, ColumnProperty

    # Resolve domain name from domain_id if available
    domain_name = None
    if db_contract.domain_id:
        try:
            from src.repositories.data_domain_repository import data_domain_repo
            domain = data_domain_repo.get(db, id=db_contract.domain_id)
            if domain:
                domain_name = domain.name
        except Exception as e:
            logger.warning(f"Failed to resolve domain name for domain_id {db_contract.domain_id}: {e}")

    # Build description
    description = None
    if db_contract.description_usage or db_contract.description_purpose or db_contract.description_limitations:
        description = ContractDescription(
            usage=db_contract.description_usage,
            purpose=db_contract.description_purpose,
            limitations=db_contract.description_limitations
        )
    
    # Build schema objects
    schema_objects = []
    for schema_obj in db_contract.schema_objects:
        properties = []
        for prop in schema_obj.properties:
            # Parse logical type options if available
            options = {}
            if prop.logical_type_options_json:
                try:
                    options = json.loads(prop.logical_type_options_json)
                except:
                    pass

            prop_dict = {
                'name': prop.name,
                'logicalType': prop.logical_type or 'string',
                'required': prop.required,
                'unique': prop.unique,
                'description': prop.transform_description,
                'primaryKeyPosition': prop.primary_key_position,
                'partitionKeyPosition': prop.partition_key_position,
            }

            # Add logical type options to property
            prop_dict.update(options)

            properties.append(ColumnProperty(**prop_dict))

        schema_objects.append(SchemaObject(
            name=schema_obj.name,
            physicalName=schema_obj.physical_name,
            properties=properties
        ))

    # Build team (legacy minimal)
    team = []
    if getattr(db_contract, 'team', None):
        for member in db_contract.team:
            team.append({
                'role': member.role or 'member',
                'email': member.username,
                'name': None,
            })

    # Build support channels (legacy minimal)
    support = None
    if getattr(db_contract, 'support', None):
        support = {}
        for ch in db_contract.support:
            if ch.channel and ch.url:
                support[ch.channel] = ch.url

    # Custom properties
    custom_properties = {}
    if getattr(db_contract, 'custom_properties', None):
        for cp in db_contract.custom_properties:
            custom_properties[cp.property] = cp.value

    # SLA properties (flatten basic key/value)
    sla = None
    if getattr(db_contract, 'sla_properties', None):
        sla = {}
        for sp in db_contract.sla_properties:
            if sp.property and sp.value is not None:
                sla[sp.property] = sp.value

    # Servers (full ODCS mapping)
    servers = []
    if getattr(db_contract, 'servers', None):
        from src.models.data_contracts_api import ServerConfig
        for s in db_contract.servers:
            # Build properties dict from server properties
            properties = {}
            if getattr(s, 'properties', None):
                for prop in s.properties:
                    properties[prop.key] = prop.value

            # Create ServerConfig object
            server_config = ServerConfig(
                server=s.server,
                type=s.type,
                description=s.description,
                environment=s.environment,
                host=properties.get('host'),
                port=int(properties.get('port')) if properties.get('port') else None,
                database=properties.get('database'),
                schema=properties.get('schema'),
                catalog=properties.get('catalog'),
                project=properties.get('project'),
                account=properties.get('account'),
                region=properties.get('region'),
                location=properties.get('location'),
                properties={k: v for k, v in properties.items() if k not in ['host', 'port', 'database', 'schema', 'catalog', 'project', 'account', 'region', 'location']}
            )
            servers.append(server_config)

    # Authoritative definitions
    authoritative_definitions = []
    if getattr(db_contract, 'authoritative_defs', None):
        from src.models.data_contracts_api import AuthoritativeDefinition
        for auth_def in db_contract.authoritative_defs:
            authoritative_definitions.append(AuthoritativeDefinition(
                url=auth_def.url,
                type=auth_def.type
            ))

    # Quality rules
    quality_rules = []
    if hasattr(db_contract, 'schema_objects') and db_contract.schema_objects:
        from src.models.data_contracts_api import QualityRule
        for schema_obj in db_contract.schema_objects:
            if hasattr(schema_obj, 'quality_checks') and schema_obj.quality_checks:
                for check in schema_obj.quality_checks:
                    quality_rules.append(QualityRule(
                        name=check.name,
                        description=check.description,
                        level=check.level,
                        dimension=check.dimension,
                        business_impact=check.business_impact,
                        severity=check.severity,
                        type=check.type,
                        method=check.method,
                        schedule=check.schedule,
                        scheduler=check.scheduler,
                        unit=check.unit,
                        tags=check.tags,
                        rule=check.rule,
                        query=check.query,
                        engine=check.engine,
                        implementation=check.implementation,
                        must_be=check.must_be,
                        must_not_be=check.must_not_be,
                        must_be_gt=check.must_be_gt,
                        must_be_ge=check.must_be_ge,
                        must_be_lt=check.must_be_lt,
                        must_be_le=check.must_be_le,
                        must_be_between_min=check.must_be_between_min,
                        must_be_between_max=check.must_be_between_max
                    ))

    return DataContractRead(
        id=db_contract.id,
        name=db_contract.name,
        version=db_contract.version,
        status=db_contract.status,
        owner=db_contract.owner,
        kind=db_contract.kind,
        apiVersion=db_contract.api_version,
        tenant=db_contract.tenant,
        domain=domain_name,  # Resolved domain name
        domainId=db_contract.domain_id,  # Provide domain ID for frontend resolution
        dataProduct=db_contract.data_product,
        description=description,
        schema=schema_objects,
        team=team,
        support=support,
        customProperties=custom_properties,
        sla=sla,
        servers=servers,
        authoritativeDefinitions=authoritative_definitions,
        qualityRules=quality_rules,
        created=db_contract.created_at.isoformat() if db_contract.created_at else None,
        updated=db_contract.updated_at.isoformat() if db_contract.updated_at else None,
    )


@router.post('/data-contracts', response_model=DataContractRead)
async def create_contract(
    db: DBSessionDep,
    current_user: CurrentUserDep,
    contract_data: DataContractCreate = Body(...),
    manager: DataContractsManager = Depends(get_data_contracts_manager),
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_WRITE)),
):
    """Create a new data contract with normalized ODCS structure"""
    try:
        # Validate required fields for app usability
        if not contract_data.name or not contract_data.name.strip():
            raise HTTPException(status_code=400, detail="Contract name is required")

        # Resolve domain_id from provided domainId (UUID) or domain (name)
        resolved_domain_id: str | None = None
        try:
            domain_id = getattr(contract_data, 'domainId', None)
            if domain_id and domain_id.strip():  # Only if not empty
                # Validate that the domain exists
                from src.repositories.data_domain_repository import data_domain_repo
                domain_obj = data_domain_repo.get(db, id=domain_id)
                if not domain_obj:
                    raise HTTPException(status_code=400, detail=f"Domain with ID {domain_id} not found")
                resolved_domain_id = domain_id
            elif getattr(contract_data, 'domain', None):
                from src.repositories.data_domain_repository import data_domain_repo
                domain_obj = data_domain_repo.get_by_name(db, name=contract_data.domain)
                if domain_obj:
                    resolved_domain_id = domain_obj.id
        except HTTPException:
            raise  # Re-raise HTTPException for validation errors
        except Exception as e:
            logger.warning(f"Domain resolution failed during create_contract: {e}")

        # Create main contract record
        db_obj = DataContractDb(
            name=contract_data.name,
            version=contract_data.version or 'v1.0',
            status=contract_data.status or 'draft',
            owner=contract_data.owner or (current_user.username if current_user else 'unknown'),
            kind=contract_data.kind or 'DataContract',
            api_version=contract_data.apiVersion or 'v3.0.2',
            tenant=contract_data.tenant,
            data_product=contract_data.dataProduct,
            domain_id=resolved_domain_id,
            description_usage=contract_data.description.usage if contract_data.description else None,
            description_purpose=contract_data.description.purpose if contract_data.description else None,
            description_limitations=contract_data.description.limitations if contract_data.description else None,
            created_by=current_user.username if current_user else None,
            updated_by=current_user.username if current_user else None,
        )
        created = data_contract_repo.create(db=db, obj_in=db_obj)
        
        # Create schema objects and properties if provided
        if contract_data.schema:
            # SchemaObjectDb and SchemaPropertyDb already imported at top level
            for schema_obj_data in contract_data.schema:
                schema_obj = SchemaObjectDb(
                    contract_id=created.id,
                    name=schema_obj_data.name,
                    physical_name=schema_obj_data.physicalName,
                    logical_type='object'
                )
                db.add(schema_obj)
                db.flush()  # Get ID for properties
                
                # Add properties
                for prop_data in schema_obj_data.properties:
                    # Build logical type options JSON from type-specific constraints
                    logical_type_options = {}

                    # String constraints
                    if hasattr(prop_data, 'minLength') and prop_data.minLength is not None:
                        logical_type_options['minLength'] = prop_data.minLength
                    if hasattr(prop_data, 'maxLength') and prop_data.maxLength is not None:
                        logical_type_options['maxLength'] = prop_data.maxLength
                    if hasattr(prop_data, 'pattern') and prop_data.pattern:
                        logical_type_options['pattern'] = prop_data.pattern

                    # Number/Integer constraints
                    if hasattr(prop_data, 'minimum') and prop_data.minimum is not None:
                        logical_type_options['minimum'] = prop_data.minimum
                    if hasattr(prop_data, 'maximum') and prop_data.maximum is not None:
                        logical_type_options['maximum'] = prop_data.maximum
                    if hasattr(prop_data, 'multipleOf') and prop_data.multipleOf is not None:
                        logical_type_options['multipleOf'] = prop_data.multipleOf
                    if hasattr(prop_data, 'precision') and prop_data.precision is not None:
                        logical_type_options['precision'] = prop_data.precision

                    # Date constraints
                    if hasattr(prop_data, 'format') and prop_data.format:
                        logical_type_options['format'] = prop_data.format
                    if hasattr(prop_data, 'timezone') and prop_data.timezone:
                        logical_type_options['timezone'] = prop_data.timezone
                    if hasattr(prop_data, 'customFormat') and prop_data.customFormat:
                        logical_type_options['customFormat'] = prop_data.customFormat

                    # Array constraints
                    if hasattr(prop_data, 'itemType') and prop_data.itemType:
                        logical_type_options['itemType'] = prop_data.itemType
                    if hasattr(prop_data, 'minItems') and prop_data.minItems is not None:
                        logical_type_options['minItems'] = prop_data.minItems
                    if hasattr(prop_data, 'maxItems') and prop_data.maxItems is not None:
                        logical_type_options['maxItems'] = prop_data.maxItems

                    prop = SchemaPropertyDb(
                        object_id=schema_obj.id,
                        name=prop_data.name,
                        logical_type=prop_data.logicalType,
                        required=prop_data.required or False,
                        unique=prop_data.unique or False,
                        primary_key_position=getattr(prop_data, 'primaryKeyPosition', None),
                        partition_key_position=getattr(prop_data, 'partitionKeyPosition', None),
                        logical_type_options_json=json.dumps(logical_type_options) if logical_type_options else None,
                        classification=getattr(prop_data, 'classification', None),
                        examples=str(getattr(prop_data, 'examples', None)) if getattr(prop_data, 'examples', None) is not None else None,
                        transform_description=prop_data.description
                    )
                    db.add(prop)

        # Create quality checks if provided
        if hasattr(contract_data, 'qualityRules') and contract_data.qualityRules:
            from src.db_models.data_contracts import DataQualityCheckDb
            # Get the first schema object to attach quality checks to
            schema_obj = db.query(SchemaObjectDb).filter(SchemaObjectDb.contract_id == created.id).first()
            if schema_obj:
                for rule_data in contract_data.qualityRules:
                    quality_check = DataQualityCheckDb(
                        object_id=schema_obj.id,
                        level=getattr(rule_data, 'level', 'object'),
                        name=getattr(rule_data, 'name', None),
                        description=getattr(rule_data, 'description', None),
                        dimension=getattr(rule_data, 'dimension', None),
                        business_impact=getattr(rule_data, 'businessImpact', None),
                        method=getattr(rule_data, 'method', None),
                        schedule=getattr(rule_data, 'schedule', None),
                        scheduler=getattr(rule_data, 'scheduler', None),
                        severity=getattr(rule_data, 'severity', None),
                        type=getattr(rule_data, 'type', 'library'),
                        unit=getattr(rule_data, 'unit', None),
                        tags=getattr(rule_data, 'tags', None),
                        rule=getattr(rule_data, 'rule', None),
                        query=getattr(rule_data, 'query', None),
                        engine=getattr(rule_data, 'engine', None),
                        implementation=getattr(rule_data, 'implementation', None),
                        must_be=getattr(rule_data, 'mustBe', None),
                        must_not_be=getattr(rule_data, 'mustNotBe', None),
                        must_be_gt=getattr(rule_data, 'mustBeGt', None),
                        must_be_ge=getattr(rule_data, 'mustBeGe', None),
                        must_be_lt=getattr(rule_data, 'mustBeLt', None),
                        must_be_le=getattr(rule_data, 'mustBeLe', None),
                        must_be_between_min=getattr(rule_data, 'mustBeBetweenMin', None),
                        must_be_between_max=getattr(rule_data, 'mustBeBetweenMax', None)
                    )
                    db.add(quality_check)

        # Process semantic assignments from authoritativeDefinitions
        from src.controller.semantic_links_manager import SemanticLinksManager
        from src.models.semantic_links import EntitySemanticLinkCreate

        semantic_manager = SemanticLinksManager(db)
        SEMANTIC_ASSIGNMENT_TYPE = "http://databricks.com/ontology/uc/semanticAssignment"

        # Process contract-level semantic assignments
        contract_auth_defs = getattr(contract_data, 'authoritativeDefinitions', []) or []
        if contract_auth_defs:
            for auth_def in contract_auth_defs:
                if hasattr(auth_def, 'type') and auth_def.type == SEMANTIC_ASSIGNMENT_TYPE:
                    url = getattr(auth_def, 'url', None)
                    if url:
                        semantic_link = EntitySemanticLinkCreate(
                            entity_id=created.id,
                            entity_type='data_contract',
                            iri=url,
                            label=None  # Will be resolved by business glossary
                        )
                        semantic_manager.add(semantic_link, created_by=current_user.username if current_user else None)

        # Process schema-level semantic assignments
        schema_objects = db.query(SchemaObjectDb).filter(SchemaObjectDb.contract_id == created.id).all()
        if contract_data.schema:
            for i, schema_obj_data in enumerate(contract_data.schema):
                if i >= len(schema_objects):
                    continue

                schema_obj = schema_objects[i]
                schema_auth_defs = getattr(schema_obj_data, 'authoritativeDefinitions', []) or []
                if schema_auth_defs:
                    for auth_def in schema_auth_defs:
                        if hasattr(auth_def, 'type') and auth_def.type == SEMANTIC_ASSIGNMENT_TYPE:
                            url = getattr(auth_def, 'url', None)
                            if url:
                                entity_id = f"{created.id}#{schema_obj.name}"
                                semantic_link = EntitySemanticLinkCreate(
                                    entity_id=entity_id,
                                    entity_type='data_contract_schema',
                                    iri=url,
                                    label=None
                                )
                                semantic_manager.add(semantic_link, created_by=current_user.username if current_user else None)

                # Process property-level semantic assignments
                properties = getattr(schema_obj_data, 'properties', []) or []
                if properties:
                    for prop_data in properties:
                        prop_name = getattr(prop_data, 'name', 'column')
                        prop_auth_defs = getattr(prop_data, 'authoritativeDefinitions', []) or []
                        if prop_auth_defs:
                            for auth_def in prop_auth_defs:
                                if hasattr(auth_def, 'type') and auth_def.type == SEMANTIC_ASSIGNMENT_TYPE:
                                    url = getattr(auth_def, 'url', None)
                                    if url:
                                        entity_id = f"{created.id}#{schema_obj.name}#{prop_name}"
                                        semantic_link = EntitySemanticLinkCreate(
                                            entity_id=entity_id,
                                            entity_type='data_contract_property',
                                            iri=url,
                                            label=None
                                        )
                                        semantic_manager.add(semantic_link, created_by=current_user.username if current_user else None)

        db.commit()
        
        # Load with relationships for response
        created_with_relations = data_contract_repo.get_with_all(db, id=created.id)
        return _build_contract_read_from_db(db, created_with_relations)
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.put('/data-contracts/{contract_id}', response_model=DataContractRead)
async def update_contract(
    contract_id: str,
    db: DBSessionDep,
    current_user: CurrentUserDep,
    contract_data: DataContractUpdate = Body(...),
    manager: DataContractsManager = Depends(get_data_contracts_manager),
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_WRITE))
):
    """Update a data contract"""
    try:
        db_obj = data_contract_repo.get(db, id=contract_id)
        if not db_obj:
            raise HTTPException(status_code=404, detail="Contract not found")

        # Validate required fields
        if contract_data.name is not None and (not contract_data.name or not contract_data.name.strip()):
            raise HTTPException(status_code=400, detail="Contract name cannot be empty")

        # Handle domain_id properly - convert empty string to None and validate existence
        domain_id = contract_data.domainId
        if domain_id is not None and not domain_id.strip():
            domain_id = None
        elif domain_id is not None:
            # Validate that the domain exists
            from src.repositories.data_domain_repository import data_domain_repo
            domain_obj = data_domain_repo.get(db, id=domain_id)
            if not domain_obj:
                raise HTTPException(status_code=400, detail=f"Domain with ID {domain_id} not found")

        update_payload = {}
        payload_map = {
            'name': contract_data.name,
            'version': contract_data.version,
            'status': contract_data.status,
            'owner': contract_data.owner,
            'tenant': contract_data.tenant,
            'data_product': contract_data.dataProduct,
            'description_usage': contract_data.descriptionUsage,
            'description_purpose': contract_data.descriptionPurpose,
            'description_limitations': contract_data.descriptionLimitations,
            'api_version': contract_data.apiVersion,
            'kind': contract_data.kind,
            'domain_id': domain_id,
        }
        for k, v in payload_map.items():
            if v is not None:
                update_payload[k] = v
        update_payload["updated_by"] = current_user.username if current_user else None
        updated = data_contract_repo.update(db=db, db_obj=db_obj, obj_in=update_payload)
        db.commit()
        
        # Load with relationships for full response
        updated_with_relations = data_contract_repo.get_with_all(db, id=contract_id)
        return _build_contract_read_from_db(db, updated_with_relations)
    except Exception as e:
        error_msg = f"Error updating data contract {contract_id}: {e!s}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@router.delete('/data-contracts/{contract_id}', status_code=204)
async def delete_contract(
    contract_id: str,
    request: Request,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: AuditCurrentUserDep,
    manager: DataContractsManager = Depends(get_data_contracts_manager),
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_WRITE))
):
    """Delete a data contract"""
    success = False
    response_status_code = 500
    details_for_audit = {
        "params": {"contract_id": contract_id}
    }
    try:
        db_obj = data_contract_repo.get(db, id=contract_id)
        if not db_obj:
            response_status_code = 404
            exc = HTTPException(status_code=response_status_code, detail="Contract not found")
            details_for_audit["exception"] = {"type": "HTTPException", "status_code": exc.status_code, "detail": exc.detail}
            raise exc
        data_contract_repo.remove(db=db, id=contract_id)
        db.commit()
        success = True
        response_status_code = 204
        return None
    except HTTPException:
        raise
    except Exception as e:
        success = False
        response_status_code = 500
        error_msg = f"Error deleting data contract {contract_id}: {e!s}"
        details_for_audit["exception"] = {"type": type(e).__name__, "message": str(e)}
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)
    finally:
        if "exception" not in details_for_audit:
            details_for_audit["response_status_code"] = response_status_code
        details_for_audit["deleted_resource_id_attempted"] = contract_id
        audit_manager.log_action(
            db=db,
            username=current_user.username if current_user else "anonymous",
            ip_address=request.client.host if request.client else None,
            feature="data-contracts",
            action="DELETE",
            success=success,
            details=details_for_audit,
        )

@router.post('/data-contracts/upload')
async def upload_contract(
    request: Request,
    db: DBSessionDep,
    current_user: CurrentUserDep,
    file: UploadFile = File(...),
    manager: DataContractsManager = Depends(get_data_contracts_manager),
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_WRITE)),
):
    """Upload a contract file and parse it into normalized ODCS structure"""
    try:
        content_type = file.content_type
        filename = file.filename or 'uploaded_contract'

        # Determine format from content type or extension
        format = 'json'  # default
        if content_type == 'application/x-yaml' or filename.endswith(('.yaml', '.yml')):
            format = 'yaml'
        elif content_type.startswith('text/'):
            format = 'text'

        # Read file content
        contract_text = (await file.read()).decode('utf-8')

        # Parse structured content (JSON/YAML) or handle text
        parsed: dict | None = None
        try:
            if format == 'yaml':
                parsed = yaml.safe_load(contract_text) or None
            elif format == 'json':
                parsed = json.loads(contract_text) or None
            elif format == 'text':
                # For text format, create a minimal structure
                parsed = {
                    "name": filename.replace('.txt', '').replace('.', '_'),
                    "version": "v1.0",
                    "status": "draft", 
                    "owner": current_user.username if current_user else 'unknown',
                    "description": {
                        "purpose": contract_text[:500] + "..." if len(contract_text) > 500 else contract_text
                    }
                }
        except Exception:
            # If parsing fails, treat as text
            parsed = {
                "name": filename.replace('.', '_'),
                "version": "v1.0", 
                "status": "draft",
                "owner": current_user.username if current_user else 'unknown',
                "description": {
                    "purpose": contract_text[:500] + "..." if len(contract_text) > 500 else contract_text
                }
            }

        if not isinstance(parsed, dict):
            raise HTTPException(status_code=400, detail="Could not parse uploaded file")

        # Validate against ODCS schema (optional, but log warnings if validation fails)
        try:
            validate_odcs_contract(parsed, strict=False)
            logger.info("Contract passes ODCS v3.0.2 validation")
        except ODCSValidationError as e:
            # Log validation errors but don't block creation for flexibility
            logger.warning(f"Contract does not fully comply with ODCS v3.0.2: {e.message}")
            if e.validation_errors:
                for error in e.validation_errors[:5]:  # Log first 5 errors
                    logger.warning(f"ODCS validation: {error}")

        # Extract core contract fields with robust fallbacks
        name_val = (
            parsed.get('name') or
            parsed.get('dataProduct') or
            parsed.get('id') or
            filename.replace('.', '_').replace('-', '_')
        )
        version_val = parsed.get('version') or 'v1.0'
        status_val = parsed.get('status') or 'draft'

        # Enhanced owner field extraction with better fallbacks
        owner_val = (
            parsed.get('owner') or
            (current_user.username if current_user else None) or
            'system'  # Final fallback to avoid database constraint violation
        )

        kind_val = parsed.get('kind') or 'DataContract'
        api_version_val = parsed.get('apiVersion') or parsed.get('api_version') or 'v3.0.2'
        
        # Extract description fields
        description = parsed.get('description', {})
        if isinstance(description, str):
            description = {"purpose": description}
        elif not isinstance(description, dict):
            description = {}

        # Resolve domain_id from parsed payload (domainId or domain name)
        resolved_domain_id: str | None = None
        try:
            parsed_domain_id = parsed.get('domainId') or parsed.get('domain_id')
            parsed_domain_name = parsed.get('domain')
            if parsed_domain_id:
                # Validate that the domain exists
                from src.repositories.data_domain_repository import data_domain_repo
                domain_obj = data_domain_repo.get(db, id=parsed_domain_id)
                if not domain_obj:
                    raise HTTPException(status_code=400, detail=f"Domain with ID {parsed_domain_id} not found")
                resolved_domain_id = parsed_domain_id
            elif parsed_domain_name:
                from src.repositories.data_domain_repository import data_domain_repo
                domain_obj = data_domain_repo.get_by_name(db, name=parsed_domain_name)
                if domain_obj:
                    resolved_domain_id = domain_obj.id
        except HTTPException:
            raise  # Re-raise HTTPException for validation errors
        except Exception as e:
            logger.warning(f"Domain resolution failed during upload_contract: {e}")

        # Create main contract record
        db_obj = DataContractDb(
            name=name_val,
            version=version_val,
            status=status_val,
            owner=owner_val,
            kind=kind_val,
            api_version=api_version_val,
            tenant=parsed.get('tenant'),
            data_product=parsed.get('dataProduct') or parsed.get('data_product'),
            domain_id=resolved_domain_id,
            description_usage=description.get('usage'),
            description_purpose=description.get('purpose'),
            description_limitations=description.get('limitations'),
            # ODCS v3.0.2 additional top-level fields
            sla_default_element=parsed.get('slaDefaultElement'),
            contract_created_ts=datetime.fromisoformat(parsed.get('contractCreatedTs').replace('Z', '+00:00')) if parsed.get('contractCreatedTs') else None,
            created_by=current_user.username if current_user else None,
            updated_by=current_user.username if current_user else None,
        )
        created = data_contract_repo.create(db=db, obj_in=db_obj)
        
        # Parse and create schema objects if present
        schema_data = parsed.get('schema', [])
        if isinstance(schema_data, list):
            for schema_obj_data in schema_data:
                if not isinstance(schema_obj_data, dict):
                    continue
                    
                schema_obj = SchemaObjectDb(
                    contract_id=created.id,
                    name=schema_obj_data.get('name', 'table'),
                    physical_name=schema_obj_data.get('physicalName') or schema_obj_data.get('physical_name'),
                    logical_type='object',
                    data_granularity_description=schema_obj_data.get('dataGranularityDescription') or schema_obj_data.get('data_granularity_description'),
                    # ODCS v3.0.2 additional schema object fields
                    business_name=schema_obj_data.get('businessName'),
                    physical_type=schema_obj_data.get('physicalType'),
                    description=schema_obj_data.get('description'),
                    tags=json.dumps(schema_obj_data.get('tags', [])) if schema_obj_data.get('tags') else None
                )
                db.add(schema_obj)
                db.flush()  # Get ID for properties
                
                # Add properties with full ODCS field support
                properties = schema_obj_data.get('properties', [])
                if isinstance(properties, list):
                    for prop_data in properties:
                        if not isinstance(prop_data, dict):
                            continue

                        # Build logical type options (constraints) as JSON
                        logical_type_options = {}
                        # String constraints
                        for field in ['minLength', 'maxLength', 'pattern']:
                            if prop_data.get(field) is not None:
                                logical_type_options[field] = prop_data[field]
                        # Number/Integer constraints
                        for field in ['minimum', 'maximum', 'multipleOf', 'precision', 'exclusiveMinimum', 'exclusiveMaximum']:
                            if prop_data.get(field) is not None:
                                logical_type_options[field] = prop_data[field]
                        # Date constraints
                        for field in ['format', 'timezone', 'customFormat']:
                            if prop_data.get(field) is not None:
                                logical_type_options[field] = prop_data[field]
                        # Array constraints
                        for field in ['itemType', 'minItems', 'maxItems']:
                            if prop_data.get(field) is not None:
                                logical_type_options[field] = prop_data[field]

                        # Handle examples as JSON string
                        examples_json = None
                        if prop_data.get('examples'):
                            if isinstance(prop_data['examples'], list):
                                examples_json = json.dumps(prop_data['examples'])
                            else:
                                examples_json = str(prop_data['examples'])

                        # Handle transformSourceObjects as JSON string
                        transform_source_objects_json = None
                        if prop_data.get('transformSourceObjects'):
                            if isinstance(prop_data['transformSourceObjects'], list):
                                transform_source_objects_json = json.dumps(prop_data['transformSourceObjects'])
                            else:
                                transform_source_objects_json = str(prop_data['transformSourceObjects'])

                        prop = SchemaPropertyDb(
                            object_id=schema_obj.id,
                            name=prop_data.get('name', 'column'),
                            logical_type=prop_data.get('logicalType') or prop_data.get('logical_type', 'string'),
                            physical_type=prop_data.get('physicalType') or prop_data.get('physical_type'),
                            required=prop_data.get('required', False),
                            unique=prop_data.get('unique', False),
                            partitioned=prop_data.get('partitioned', False),
                            primary_key_position=prop_data.get('primaryKeyPosition', -1) if prop_data.get('primaryKey') else -1,
                            partition_key_position=prop_data.get('partitionKeyPosition', -1) if prop_data.get('partitioned') else -1,
                            classification=prop_data.get('classification'),
                            encrypted_name=prop_data.get('encryptedName'),
                            transform_logic=prop_data.get('transformLogic'),
                            transform_source_objects=transform_source_objects_json,
                            transform_description=prop_data.get('description'),
                            examples=examples_json,
                            critical_data_element=prop_data.get('criticalDataElement', False),
                            logical_type_options_json=json.dumps(logical_type_options) if logical_type_options else None,
                            items_logical_type=prop_data.get('itemType'),
                            business_name=prop_data.get('businessName')  # ODCS property-level businessName
                        )
                        db.add(prop)

                        # Parse property-level quality checks (ODCS compliant structure)
                        prop_quality_data = prop_data.get('quality', [])
                        if isinstance(prop_quality_data, list):
                            for rule_data in prop_quality_data:
                                if isinstance(rule_data, dict):
                                    quality_rule_db = DataQualityCheckDb(
                                        object_id=schema_obj.id,  # Associated with schema object
                                        name=rule_data.get('name'),
                                        description=rule_data.get('description'),
                                        level=rule_data.get('level', 'property'),  # Property level
                                        dimension=rule_data.get('dimension'),
                                        business_impact=rule_data.get('business_impact') or rule_data.get('businessImpact'),
                                        severity=rule_data.get('severity'),
                                        type=rule_data.get('type', 'library'),
                                        method=rule_data.get('method'),
                                        schedule=rule_data.get('schedule'),
                                        scheduler=rule_data.get('scheduler'),
                                        unit=rule_data.get('unit'),
                                        tags=rule_data.get('tags'),
                                        rule=rule_data.get('rule'),
                                        query=rule_data.get('query'),
                                        engine=rule_data.get('engine'),
                                        implementation=rule_data.get('implementation'),
                                        must_be=rule_data.get('must_be') or rule_data.get('mustBe'),
                                        must_not_be=rule_data.get('must_not_be') or rule_data.get('mustNotBe'),
                                        must_be_gt=rule_data.get('must_be_gt') or rule_data.get('mustBeGt'),
                                        must_be_ge=rule_data.get('must_be_ge') or rule_data.get('mustBeGe'),
                                        must_be_lt=rule_data.get('must_be_lt') or rule_data.get('mustBeLt'),
                                        must_be_le=rule_data.get('must_be_le') or rule_data.get('mustBeLe'),
                                        must_be_between_min=rule_data.get('must_be_between_min') or rule_data.get('mustBeBetweenMin'),
                                        must_be_between_max=rule_data.get('must_be_between_max') or rule_data.get('mustBeBetweenMax')
                                    )
                                    db.add(quality_rule_db)

                # Parse schema-level quality checks (ODCS compliant structure)
                quality_data = schema_obj_data.get('quality', [])
                if isinstance(quality_data, list):
                    for rule_data in quality_data:
                        if isinstance(rule_data, dict):
                            quality_rule_db = DataQualityCheckDb(
                                object_id=schema_obj.id,  # Correctly associated with schema object
                                name=rule_data.get('name'),
                                description=rule_data.get('description'),
                                level=rule_data.get('level', 'object'),  # Schema level
                                dimension=rule_data.get('dimension'),
                                business_impact=rule_data.get('business_impact') or rule_data.get('businessImpact'),
                                severity=rule_data.get('severity'),
                                type=rule_data.get('type', 'library'),
                                method=rule_data.get('method'),
                                schedule=rule_data.get('schedule'),
                                scheduler=rule_data.get('scheduler'),
                                unit=rule_data.get('unit'),
                                tags=rule_data.get('tags'),
                                rule=rule_data.get('rule'),
                                query=rule_data.get('query'),
                                engine=rule_data.get('engine'),
                                implementation=rule_data.get('implementation'),
                                must_be=rule_data.get('must_be') or rule_data.get('mustBe'),
                                must_not_be=rule_data.get('must_not_be') or rule_data.get('mustNotBe'),
                                must_be_gt=rule_data.get('must_be_gt') or rule_data.get('mustBeGt'),
                                must_be_ge=rule_data.get('must_be_ge') or rule_data.get('mustBeGe'),
                                must_be_lt=rule_data.get('must_be_lt') or rule_data.get('mustBeLt'),
                                must_be_le=rule_data.get('must_be_le') or rule_data.get('mustBeLe'),
                                must_be_between_min=rule_data.get('must_be_between_min') or rule_data.get('mustBeBetweenMin'),
                                must_be_between_max=rule_data.get('must_be_between_max') or rule_data.get('mustBeBetweenMax')
                            )
                            db.add(quality_rule_db)

                # Parse schema-level authoritative definitions
                auth_defs_data = schema_obj_data.get('authoritativeDefinitions', [])
                if isinstance(auth_defs_data, list):
                    for auth_def in auth_defs_data:
                        if isinstance(auth_def, dict) and auth_def.get('url') and auth_def.get('type'):
                            auth_def_db = SchemaObjectAuthorityDb(
                                schema_object_id=schema_obj.id,
                                url=auth_def['url'],
                                type=auth_def['type']
                            )
                            db.add(auth_def_db)

                # Parse schema-level custom properties
                custom_props_data = schema_obj_data.get('customProperties', [])
                if isinstance(custom_props_data, list):
                    for custom_prop in custom_props_data:
                        if isinstance(custom_prop, dict) and custom_prop.get('property'):
                            custom_prop_db = SchemaObjectCustomPropertyDb(
                                schema_object_id=schema_obj.id,
                                property=custom_prop['property'],
                                value=json.dumps(custom_prop['value']) if isinstance(custom_prop.get('value'), (list, dict)) else str(custom_prop['value']) if custom_prop.get('value') is not None else None
                            )
                            db.add(custom_prop_db)

        # Parse team members
        team_data = parsed.get('team', [])
        if isinstance(team_data, list):
            for member_data in team_data:
                if not isinstance(member_data, dict):
                    continue
                team_member = DataContractTeamDb(
                    contract_id=created.id,
                    username=member_data.get('email', member_data.get('username', 'unknown')),
                    role=member_data.get('role', 'member'),
                    date_in=member_data.get('dateIn') or member_data.get('date_in'),
                    date_out=member_data.get('dateOut') or member_data.get('date_out'),
                    replaced_by_username=member_data.get('replacedByUsername') or member_data.get('replaced_by_username')
                )
                db.add(team_member)

        # Parse support channels (ODCS format expects a list)
        support_data = parsed.get('support', [])
        if isinstance(support_data, list):
            for support_item in support_data:
                if isinstance(support_item, dict) and support_item.get('url'):
                    support_channel = DataContractSupportDb(
                        contract_id=created.id,
                        channel=support_item.get('channel', 'support'),
                        url=support_item['url'],
                        description=support_item.get('description'),
                        tool=support_item.get('tool'),
                        scope=support_item.get('scope'),
                        invitation_url=support_item.get('invitationUrl')
                    )
                    db.add(support_channel)
        elif isinstance(support_data, dict):
            # Legacy dict format support
            for channel, url in support_data.items():
                if url and isinstance(url, str):
                    support_channel = DataContractSupportDb(
                        contract_id=created.id,
                        channel=channel,
                        url=url,
                        description=f"{channel.title()} support channel"
                    )
                    db.add(support_channel)

        # Parse pricing information
        price_data = parsed.get('price', {})
        if isinstance(price_data, dict) and price_data:
            pricing = DataContractPricingDb(
                contract_id=created.id,
                price_amount=str(price_data['priceAmount']) if price_data.get('priceAmount') is not None else None,
                price_currency=price_data.get('priceCurrency'),
                price_unit=price_data.get('priceUnit')
            )
            db.add(pricing)

        # Parse custom properties
        custom_props = parsed.get('customProperties') or parsed.get('custom_properties', {})
        if isinstance(custom_props, dict):
            for key, value in custom_props.items():
                custom_prop = DataContractCustomPropertyDb(
                    contract_id=created.id,
                    property=key,
                    value=str(value) if value is not None else None
                )
                db.add(custom_prop)

        # Parse SLA properties (ODCS format)
        sla_properties_data = parsed.get('slaProperties', [])
        if isinstance(sla_properties_data, list):
            for sla_item in sla_properties_data:
                if isinstance(sla_item, dict) and sla_item.get('property'):
                    sla_prop = DataContractSlaPropertyDb(
                        contract_id=created.id,
                        property=sla_item['property'],
                        value=str(sla_item['value']) if sla_item.get('value') is not None else None,
                        value_ext=str(sla_item['valueExt']) if sla_item.get('valueExt') is not None else None,
                        unit=sla_item.get('unit'),
                        element=sla_item.get('element'),
                        driver=sla_item.get('driver')
                    )
                    db.add(sla_prop)

        # Legacy SLA format support (dict format)
        sla_data = parsed.get('sla', {})
        if isinstance(sla_data, dict) and not sla_properties_data:  # Only if slaProperties not present
            for key, value in sla_data.items():
                if value is not None:
                    sla_prop = DataContractSlaPropertyDb(
                        contract_id=created.id,
                        property=key,
                        value=str(value)
                    )
                    db.add(sla_prop)

        # Parse authoritative definitions
        auth_defs_data = parsed.get('authoritativeDefinitions', [])
        if isinstance(auth_defs_data, list):
            for auth_def in auth_defs_data:
                if isinstance(auth_def, dict) and auth_def.get('url') and auth_def.get('type'):
                    auth_def_db = DataContractAuthorityDb(
                        contract_id=created.id,
                        url=auth_def['url'],
                        type=auth_def['type']
                    )
                    db.add(auth_def_db)

        # Parse servers
        servers_data = parsed.get('servers', [])
        if isinstance(servers_data, list):
            for server_data in servers_data:
                if isinstance(server_data, dict):
                    server_db = DataContractServerDb(
                        contract_id=created.id,
                        server=server_data.get('server'),
                        type=server_data.get('type', ''),
                        description=server_data.get('description'),
                        environment=server_data.get('environment')
                    )
                    db.add(server_db)
                    db.flush()  # Get server ID for properties

                    # Parse server properties (host, port, database, etc.)
                    for prop_key in ['host', 'port', 'database', 'schema', 'catalog', 'project', 'account', 'region', 'location']:
                        if prop_key in server_data and server_data[prop_key] is not None:
                            prop_db = DataContractServerPropertyDb(
                                server_id=server_db.id,
                                key=prop_key,
                                value=str(server_data[prop_key])
                            )
                            db.add(prop_db)

                    # Parse additional server properties
                    properties_data = server_data.get('properties', {})
                    if isinstance(properties_data, dict):
                        for prop_key, prop_value in properties_data.items():
                            if prop_value is not None:
                                prop_db = DataContractServerPropertyDb(
                                    server_id=server_db.id,
                                    key=prop_key,
                                    value=str(prop_value)
                                )
                                db.add(prop_db)

        # Legacy: Parse top-level quality rules (non-compliant with ODCS, but supported for backward compatibility)
        # ODCS v3.0.2 specifies quality rules should be nested under schema objects, handled above
        quality_rules_data = parsed.get('qualityRules', [])
        if isinstance(quality_rules_data, list) and quality_rules_data:
            # Try to associate with first schema object if available
            first_schema_obj = None
            for schema_obj_data in schema_data if isinstance(schema_data, list) else []:
                if isinstance(schema_obj_data, dict):
                    # Find the created schema object
                    # SchemaObjectDb already imported at top level
                    first_schema_obj = db.query(SchemaObjectDb).filter(
                        SchemaObjectDb.contract_id == created.id,
                        SchemaObjectDb.name == schema_obj_data.get('name', 'table')
                    ).first()
                    break

            for rule_data in quality_rules_data:
                if isinstance(rule_data, dict):
                    quality_rule_db = DataQualityCheckDb(
                        object_id=first_schema_obj.id if first_schema_obj else None,  # Associate with first schema object if available
                        name=rule_data.get('name'),
                        description=rule_data.get('description'),
                        level=rule_data.get('level', 'contract'),  # Mark as contract-level for legacy rules
                        dimension=rule_data.get('dimension'),
                        business_impact=rule_data.get('business_impact') or rule_data.get('businessImpact'),
                        severity=rule_data.get('severity'),
                        type=rule_data.get('type', 'library'),
                        method=rule_data.get('method'),
                        schedule=rule_data.get('schedule'),
                        scheduler=rule_data.get('scheduler'),
                        unit=rule_data.get('unit'),
                        tags=rule_data.get('tags'),
                        rule=rule_data.get('rule'),
                        query=rule_data.get('query'),
                        engine=rule_data.get('engine'),
                        implementation=rule_data.get('implementation'),
                        must_be=rule_data.get('must_be') or rule_data.get('mustBe'),
                        must_not_be=rule_data.get('must_not_be') or rule_data.get('mustNotBe'),
                        must_be_gt=rule_data.get('must_be_gt') or rule_data.get('mustBeGt'),
                        must_be_ge=rule_data.get('must_be_ge') or rule_data.get('mustBeGe'),
                        must_be_lt=rule_data.get('must_be_lt') or rule_data.get('mustBeLt'),
                        must_be_le=rule_data.get('must_be_le') or rule_data.get('mustBeLe'),
                        must_be_between_min=rule_data.get('must_be_between_min') or rule_data.get('mustBeBetweenMin'),
                        must_be_between_max=rule_data.get('must_be_between_max') or rule_data.get('mustBeBetweenMax')
                    )
                    # Only add if we have a schema object to associate with
                    if first_schema_obj:
                        db.add(quality_rule_db)

        # Parse tags (legacy support)
        tags = parsed.get('tags', [])
        if isinstance(tags, list):
            for tag in tags:
                if isinstance(tag, str):
                    db.add(DataContractTagDb(contract_id=created.id, name=tag))

        # Parse roles
        roles = parsed.get('roles', [])
        if isinstance(roles, list):
            for role_data in roles:
                if isinstance(role_data, dict) and role_data.get('role'):
                    role_db = DataContractRoleDb(
                        contract_id=created.id,
                        role=role_data.get('role'),
                        description=role_data.get('description'),
                        access=role_data.get('access'),
                        first_level_approvers=role_data.get('firstLevelApprovers'),
                        second_level_approvers=role_data.get('secondLevelApprovers')
                    )
                    db.add(role_db)
                    db.flush()  # Get role ID for properties

                    # Parse role custom properties
                    role_props = role_data.get('customProperties', {})
                    if isinstance(role_props, dict):
                        for prop_key, prop_value in role_props.items():
                            if prop_value is not None:
                                prop_db = DataContractRolePropertyDb(
                                    role_id=role_db.id,
                                    property=prop_key,
                                    value=str(prop_value)
                                )
                                db.add(prop_db)

        db.commit()
        
        # Load with relationships for response
        created_with_relations = data_contract_repo.get_with_all(db, id=created.id)
        return _build_contract_read_from_db(db, created_with_relations)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

# Old document-based export removed - use /data-contracts/{contract_id}/odcs/export instead


@router.get('/data-contracts/schema/odcs')
async def get_odcs_schema(_perm: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_ONLY))):
    try:
        from pathlib import Path
        schema_path = Path(__file__).parent.parent / 'schemas' / 'odcs_v3.json'
        with open(schema_path, 'r') as f:
            data = json.load(f)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ODCS import functionality now handled by /data-contracts/upload endpoint


@router.get('/data-contracts/{contract_id}/odcs/export')
async def export_odcs(contract_id: str, db: DBSessionDep, manager: DataContractsManager = Depends(get_data_contracts_manager), _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_ONLY))):
    try:
        from fastapi.responses import Response

        db_obj = data_contract_repo.get_with_all(db, id=contract_id)
        if not db_obj:
            raise HTTPException(status_code=404, detail="Contract not found")
        odcs = manager.build_odcs_from_db(db_obj, db)

        # Convert to YAML format for ODCS compliance
        yaml_content = yaml.dump(odcs, default_flow_style=False, allow_unicode=True, sort_keys=False)
        filename = f"{(db_obj.name or 'contract').lower().replace(' ', '_')}-odcs.yaml"

        return Response(
            content=yaml_content,
            media_type='application/x-yaml',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Content-Type': 'application/x-yaml; charset=utf-8'
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post('/data-contracts/{contract_id}/comments', response_model=dict)
async def add_comment(
    contract_id: str,
    request: Request,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: AuditCurrentUserDep,
    payload: DataContractCommentCreate = Body(...),
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_WRITE))
):
    success = False
    response_status_code = 500
    details_for_audit = {
        "params": {"contract_id": contract_id},
        "body_preview": _extract_details_default(
            request=request,
            response_or_exc=None,
            route_args=(),
            route_kwargs={'contract_id': contract_id, 'payload': payload}
        )
    }
    try:
        if not data_contract_repo.get(db, id=contract_id):
            response_status_code = 404
            exc = HTTPException(status_code=response_status_code, detail="Contract not found")
            details_for_audit["exception"] = {"type": "HTTPException", "status_code": exc.status_code, "detail": exc.detail}
            raise exc
        message = payload.message
        if not message:
            response_status_code = 400
            exc = HTTPException(status_code=response_status_code, detail="message is required")
            details_for_audit["exception"] = {"type": "HTTPException", "status_code": exc.status_code, "detail": exc.detail}
            raise exc
        db.add(DataContractCommentDb(contract_id=contract_id, author=current_user.username if current_user else 'anonymous', message=message))
        db.commit()
        success = True
        response_status_code = 200
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        success = False
        response_status_code = 500
        details_for_audit["exception"] = {"type": type(e).__name__, "message": str(e)}
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if "exception" not in details_for_audit:
            details_for_audit["response_status_code"] = response_status_code
        audit_manager.log_action(
            db=db,
            username=current_user.username if current_user else "anonymous",
            ip_address=request.client.host if request.client else None,
            feature="data-contracts",
            action="COMMENT",
            success=success,
            details=details_for_audit,
        )


@router.get('/data-contracts/{contract_id}/comments', response_model=list[DataContractCommentRead])
async def list_comments(contract_id: str, db: DBSessionDep, _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_ONLY))):
    try:
        comments = db.query(DataContractCommentDb).filter(DataContractCommentDb.contract_id == contract_id).order_by(DataContractCommentDb.created_at.asc()).all()
        return [
            DataContractCommentRead(
                id=c.id,
                author=c.author,
                message=c.message,
                created_at=c.created_at.isoformat() if c.created_at else None,
            )
            for c in comments
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/data-contracts/{contract_id}/versions')
async def create_version(
    contract_id: str,
    request: Request,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: AuditCurrentUserDep,
    payload: dict = Body(...),
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_WRITE))
):
    success = False
    response_status_code = 500
    details_for_audit = {
        "params": {"contract_id": contract_id},
        "body_preview": _extract_details_default(
            request=request,
            response_or_exc=None,
            route_args=(),
            route_kwargs={'contract_id': contract_id, 'payload': payload}
        )
    }
    try:
        original = data_contract_repo.get(db, id=contract_id)
        if not original:
            response_status_code = 404
            exc = HTTPException(status_code=response_status_code, detail="Contract not found")
            details_for_audit["exception"] = {"type": "HTTPException", "status_code": exc.status_code, "detail": exc.detail}
            raise exc
        new_version = payload.get('new_version')
        if not new_version:
            response_status_code = 400
            exc = HTTPException(status_code=response_status_code, detail="new_version is required")
            details_for_audit["exception"] = {"type": "HTTPException", "status_code": exc.status_code, "detail": exc.detail}
            raise exc
        clone = DataContractDb(
            name=original.name,
            version=new_version,
            status='draft',
            owner=original.owner,
            kind=original.kind,
            api_version=original.api_version,
            tenant=original.tenant,
            data_product=original.data_product,
            description_usage=original.description_usage,
            description_purpose=original.description_purpose,
            description_limitations=original.description_limitations,
            domain_id=original.domain_id,
            created_by=current_user.username if current_user else None,
            updated_by=current_user.username if current_user else None,
        )
        db.add(clone)
        db.flush()
        db.commit()
        success = True
        response_status_code = 201
        return {"id": clone.id, "name": clone.name, "version": clone.version, "status": clone.status, "owner": clone.owner}
    except HTTPException:
        raise
    except Exception as e:
        success = False
        response_status_code = 500
        details_for_audit["exception"] = {"type": type(e).__name__, "message": str(e)}
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if "exception" not in details_for_audit:
            details_for_audit["response_status_code"] = response_status_code
        if success:
            details_for_audit["created_version_for_contract_id"] = contract_id
        audit_manager.log_action(
            db=db,
            username=current_user.username if current_user else "anonymous",
            ip_address=request.client.host if request.client else None,
            feature="data-contracts",
            action="VERSION",
            success=success,
            details=details_for_audit,
        )

def register_routes(app):
    """Register routes with the app"""
    app.include_router(router)
    logger.info("Data contract routes registered")
