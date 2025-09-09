import json
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
import os
from pathlib import Path

import yaml

from src.models.data_contracts import (
    ColumnDefinition,
    DataContract,
    Dataset,
    DatasetSchema,
    DataType,
    Metadata,
    Quality,
    SecurityClassification,
    Security,
    DatasetLifecycle,
)

# Import Search Interfaces
from src.common.search_interfaces import SearchableAsset, SearchIndexItem
# Import the registry decorator
from src.common.search_registry import searchable_asset

from src.common.logging import get_logger
from src.db_models.data_contracts import (
    DataContractDb,
    DataContractTagDb,
    DataContractRoleDb,
    DataContractServerDb,
    SchemaObjectDb,
    SchemaPropertyDb,
)
from src.repositories.data_contracts_repository import data_contract_repo

logger = get_logger(__name__)

# Inherit from SearchableAsset
@searchable_asset
class DataContractsManager(SearchableAsset):
    def __init__(self, data_dir: Path):
        self._contracts: Dict[str, DataContract] = {}
        self._data_dir = data_dir

    def _load_initial_data(self):
        """Loads initial data from the YAML file if it exists."""
        yaml_path = self._data_dir / 'data_contracts.yaml'
        if yaml_path.exists():
            try:
                self.load_from_yaml(str(yaml_path))
                logger.info(f"Successfully loaded initial data contracts from {yaml_path}")
            except Exception as e:
                logger.error(f"Error loading initial data contracts from {yaml_path}: {e!s}")
        else:
            logger.warning(f"Initial data contracts YAML file not found at {yaml_path}")

    def create_contract(self, name: str, contract_text: str, format: str, version: str,
                       owner: str, description: Optional[str] = None) -> DataContract:
        """Create a new contract"""
        # Validate format
        if not DataContract.validate_contract_text(contract_text, format):
            raise ValueError(f"Invalid {format} format")

        contract = DataContract(
            id=str(uuid.uuid4()),
            name=name,
            contract_text=contract_text,
            format=format.lower(),
            version=version,
            owner=owner,
            description=description
        )

        self._contracts[contract.id] = contract
        return contract

    def get_contract(self, contract_id: str) -> Optional[DataContract]:
        """Get a contract by ID"""
        return self._contracts.get(contract_id)

    def list_contracts(self) -> List[DataContract]:
        """List all contracts"""
        return list(self._contracts.values())

    def update_contract(self, contract_id: str, name: Optional[str] = None,
                       contract_text: Optional[str] = None, format: Optional[str] = None,
                       version: Optional[str] = None, owner: Optional[str] = None,
                       description: Optional[str] = None, status: Optional[str] = None) -> Optional[DataContract]:
        """Update an existing contract"""
        contract = self._contracts.get(contract_id)
        if not contract:
            return None

        if name is not None:
            contract.name = name
        if contract_text is not None:
            if format is not None:
                if not DataContract.validate_contract_text(contract_text, format):
                    raise ValueError(f"Invalid {format} format")
                contract.format = format.lower()
            contract.contract_text = contract_text
        if version is not None:
            contract.version = version
        if owner is not None:
            contract.owner = owner
        if description is not None:
            contract.description = description
        if status is not None:
            contract.status = status

        contract.updated_at = datetime.utcnow()
        return contract

    def delete_contract(self, contract_id: str) -> bool:
        """Delete a contract"""
        if contract_id in self._contracts:
            del self._contracts[contract_id]
            return True
        return False

    def save_to_yaml(self, file_path: str):
        """Save contracts to YAML file"""
        data = {
            'contracts': [
                {
                    'id': c.id,
                    'name': c.name,
                    'contract_text': c.contract_text,
                    'format': c.format,
                    'version': c.version,
                    'owner': c.owner,
                    'description': c.description,
                    'status': c.status,
                    'created_at': c.created_at.isoformat(),
                    'updated_at': c.updated_at.isoformat()
                }
                for c in self._contracts.values()
            ]
        }

        with open(file_path, 'w') as f:
            yaml.dump(data, f, sort_keys=False)

    def load_from_yaml(self, file_path: str):
        """Load contracts from YAML file"""
        with open(file_path) as f:
            data = yaml.safe_load(f)

        if not data or 'contracts' not in data:
            raise ValueError("Invalid YAML file format: missing 'contracts' key")

        self._contracts.clear()
        for c in data['contracts']:
            contract = DataContract(
                id=c['id'],
                name=c['name'],
                contract_text=c['contract_text'],
                format=c['format'],
                version=c['version'],
                owner=c['owner'],
                description=c.get('description'),
                status=c.get('status', 'draft'),
                created_at=datetime.fromisoformat(c['created_at']),
                updated_at=datetime.fromisoformat(c['updated_at'])
            )
            self._contracts[contract.id] = contract

    def validate_schema(self, schema: DatasetSchema) -> List[str]:
        errors = []
        column_names = set()

        for column in schema.columns:
            if column.name in column_names:
                errors.append(f"Duplicate column name: {column.name}")
            column_names.add(column.name)

            if schema.primary_key and column.name in schema.primary_key and column.nullable:
                errors.append(
                    f"Primary key column {column.name} cannot be nullable")

        if schema.primary_key:
            for pk_column in schema.primary_key:
                if pk_column not in column_names:
                    errors.append(
                        f"Primary key column {pk_column} not found in schema")

        if schema.partition_columns:
            for part_column in schema.partition_columns:
                if part_column not in column_names:
                    errors.append(
                        f"Partition column {part_column} not found in schema")

        return errors

    def validate_contract(self, contract: DataContract) -> List[str]:
        errors = []

        # Validate metadata
        if not contract.metadata.domain:
            errors.append("Domain is required in metadata")
        if not contract.metadata.owner:
            errors.append("Owner is required in metadata")

        # Validate datasets
        dataset_names = set()
        for dataset in contract.datasets:
            if dataset.name in dataset_names:
                errors.append(f"Duplicate dataset name: {dataset.name}")
            dataset_names.add(dataset.name)

            # Validate schema
            schema_errors = self.validate_schema(dataset.schema)
            errors.extend(
                [f"Dataset {dataset.name}: {error}" for error in schema_errors])

            # Validate security
            if dataset.security.classification == SecurityClassification.RESTRICTED:
                if not dataset.security.access_control:
                    errors.append(
                        f"Dataset {dataset.name}: Access control required for restricted data")

        # Validate contract dates
        if contract.effective_until and contract.effective_from:
            if contract.effective_until < contract.effective_from:
                errors.append(
                    "Effective until date must be after effective from date")

        return errors

    def validate_odcs_format(self, data: Dict) -> bool:
        """Validate if the data follows ODCS v3 format"""
        required_fields = ['name', 'version', 'datasets']
        if not all(field in data for field in required_fields):
            return False

        # Add more validation as needed
        return True

    def create_from_odcs(self, data: Dict) -> DataContract:
        """Create a data contract from ODCS v3 format"""
        # Convert ODCS metadata
        metadata = Metadata(
            domain=data.get('domain', 'default'),
            owner=data.get('owner', 'Unknown'),
            tags=data.get('tags', {}),
            business_description=data.get('description', '')
        )

        # Convert ODCS datasets
        datasets = []
        for ds_data in data.get('datasets', []):
            # Convert schema
            columns = []
            for col in ds_data.get('schema', {}).get('columns', []):
                columns.append(ColumnDefinition(
                    name=col['name'],
                    data_type=self._map_odcs_type(col['type']),
                    comment=col.get('description', ''),
                    nullable=col.get('nullable', True),
                    is_unique=col.get('unique', False)
                ))

            schema = DatasetSchema(
                columns=columns,
                primary_key=ds_data.get('schema', {}).get('primaryKey', []),
                version=ds_data.get('version', '1.0')
            )

            # Convert quality rules
            quality = Quality(
                rules=ds_data.get('quality', {}).get('rules', []),
                scores=ds_data.get('quality', {}).get('scores', {}),
                metrics=ds_data.get('quality', {}).get('metrics', {})
            )

            # Convert security
            security = Security(
                classification=self._map_odcs_classification(
                    ds_data.get('security', {}).get('classification', 'INTERNAL')
                ),
                pii_data=ds_data.get('security', {}).get('containsPII', False),
                compliance_labels=ds_data.get('security', {}).get('complianceLabels', [])
            )

            # Create dataset
            datasets.append(Dataset(
                name=ds_data['name'],
                type=ds_data.get('type', 'table'),
                schema=schema,
                metadata=metadata,
                quality=quality,
                security=security,
                lifecycle=DatasetLifecycle(),
                description=ds_data.get('description', '')
            ))

        # Create and return contract
        return self.create_contract(
            name=data['name'],
            contract_text=json.dumps(data),
            format='json',
            version=data['version'],
            metadata=metadata,
            datasets=datasets,
            validation_rules=data.get('validationRules', []),
            effective_from=self._parse_odcs_date(data.get('effectiveFrom')),
            effective_until=self._parse_odcs_date(data.get('effectiveUntil')),
            terms_and_conditions=data.get('termsAndConditions', '')
        )

    def _map_odcs_type(self, odcs_type: str) -> DataType:
        """Map ODCS data types to internal types"""
        type_mapping = {
            'string': DataType.STRING,
            'integer': DataType.INTEGER,
            'number': DataType.DOUBLE,
            'boolean': DataType.BOOLEAN,
            'date': DataType.DATE,
            'timestamp': DataType.TIMESTAMP
        }
        return type_mapping.get(odcs_type.lower(), DataType.STRING)

    def _map_odcs_classification(self, classification: str) -> SecurityClassification:
        """Map ODCS security classifications"""
        class_mapping = {
            'public': SecurityClassification.PUBLIC,
            'internal': SecurityClassification.INTERNAL,
            'confidential': SecurityClassification.CONFIDENTIAL,
            'restricted': SecurityClassification.RESTRICTED
        }
        return class_mapping.get(classification.lower(), SecurityClassification.INTERNAL)

    def _parse_odcs_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse ODCS date format"""
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except ValueError:
            return None

    def to_odcs_format(self, contract: DataContract) -> Dict:
        """Convert a data contract to ODCS v3 format"""

        def map_type_to_odcs(data_type: DataType) -> str:
            """Reverse mapping of data types to ODCS format"""
            mapping = {
                DataType.STRING: 'string',
                DataType.INTEGER: 'integer',
                DataType.DOUBLE: 'number',
                DataType.BOOLEAN: 'boolean',
                DataType.DATE: 'date',
                DataType.TIMESTAMP: 'timestamp'
            }
            return mapping.get(data_type, 'string')

        def map_classification_to_odcs(classification: SecurityClassification) -> str:
            """Reverse mapping of security classifications to ODCS format"""
            mapping = {
                SecurityClassification.PUBLIC: 'public',
                SecurityClassification.INTERNAL: 'internal',
                SecurityClassification.CONFIDENTIAL: 'confidential',
                SecurityClassification.RESTRICTED: 'restricted'
            }
            return mapping.get(classification, 'internal')

        # Convert datasets
        datasets = []
        for ds in contract.datasets:
            # Convert columns to ODCS schema
            columns = []
            for col in ds.schema.columns:
                columns.append({
                    'name': col.name,
                    'type': map_type_to_odcs(col.data_type),
                    'description': col.comment,
                    'nullable': col.nullable,
                    'unique': col.is_unique,
                    'tags': col.tags
                })

            datasets.append({
                'name': ds.name,
                'type': ds.type,
                'description': ds.description,
                'schema': {
                    'columns': columns,
                    'primaryKey': ds.schema.primary_key,
                    'version': ds.schema.version
                },
                'quality': {
                    'rules': ds.quality.rules,
                    'scores': ds.quality.scores,
                    'metrics': ds.quality.metrics
                },
                'security': {
                    'classification': map_classification_to_odcs(ds.security.classification),
                    'containsPII': ds.security.pii_data,
                    'complianceLabels': ds.security.compliance_labels
                }
            })

        # Build ODCS contract
        return {
            'name': contract.name,
            'version': contract.version,
            'status': getattr(contract.status, 'value', contract.status),
            'description': contract.metadata.business_description,
            'owner': contract.metadata.owner,
            'domain': contract.metadata.domain,
            'tags': contract.metadata.tags,
            'datasets': datasets,
            'validationRules': contract.validation_rules,
            'effectiveFrom': contract.effective_from.isoformat() + 'Z' if contract.effective_from else None,
            'effectiveUntil': contract.effective_until.isoformat() + 'Z' if contract.effective_until else None,
            'termsAndConditions': contract.terms_and_conditions,
            'created': contract.created_at.isoformat() + 'Z',
            'updated': contract.updated_at.isoformat() + 'Z'
        }

    # --- Implementation of SearchableAsset --- 
    def get_search_index_items(self) -> List[SearchIndexItem]:
        """Fetches data contracts and maps them to SearchIndexItem format."""
        logger.info("Fetching data contracts for search indexing...")
        items = []
        try:
            # Use the existing list_contracts method
            contracts = self.list_contracts()
            
            for contract in contracts:
                # Adapt field access based on DataContract model structure
                if not contract.id or not contract.name:
                    logger.warning(f"Skipping contract due to missing id or name: {contract}")
                    continue
                
                # Assuming DataContract has .tags attribute (add if missing)
                tags = getattr(contract, 'tags', []) 
                    
                items.append(
                    SearchIndexItem(
                        id=f"contract::{contract.id}",
                        type="data-contract",
                        feature_id="data-contracts",
                        title=contract.name,
                        description=contract.description or "",
                        link=f"/data-contracts/{contract.id}",
                        tags=tags
                    )
                )
            logger.info(f"Prepared {len(items)} data contracts for search index.")
            return items
        except Exception as e:
            logger.error(f"Error fetching or mapping data contracts for search: {e}", exc_info=True)
            return [] # Return empty list on error

    # --- ODCS Helpers ---
    def create_from_odcs_dict(self, db, odcs: Dict[str, Any], current_username: Optional[str]) -> DataContractDb:
        name = odcs.get('name') or 'contract'
        version = odcs.get('version') or 'v1.0'
        status = odcs.get('status') or 'draft'
        owner = odcs.get('owner') or (current_username or 'unknown')
        kind = odcs.get('kind') or 'DataContract'
        api_version = odcs.get('apiVersion') or 'v3.0.1'
        description = odcs.get('description') or {}
        db_obj = DataContractDb(
            name=name,
            version=version,
            status=status,
            owner=owner,
            kind=kind,
            api_version=api_version,
            description_usage=description.get('usage'),
            description_purpose=description.get('purpose'),
            description_limitations=description.get('limitations'),
            raw_format='json',
            raw_text=json.dumps(odcs),
            created_by=current_username,
            updated_by=current_username,
        )
        created = data_contract_repo.create(db=db, obj_in=db_obj)  # type: ignore[arg-type]

        # tags
        tags = odcs.get('tags') or []
        if isinstance(tags, list):
            for t in tags:
                if isinstance(t, str):
                    db.add(DataContractTagDb(contract_id=created.id, name=t))
        # roles
        for r in odcs.get('roles', []) or []:
            if isinstance(r, dict) and r.get('role'):
                db.add(DataContractRoleDb(
                    contract_id=created.id,
                    role=r.get('role'),
                    description=r.get('description'),
                    access=r.get('access'),
                    first_level_approvers=r.get('firstLevelApprovers'),
                    second_level_approvers=r.get('secondLevelApprovers'),
                ))
        # servers (minimal)
        for s in odcs.get('servers', []) or []:
            if isinstance(s, dict) and s.get('type'):
                db.add(DataContractServerDb(
                    contract_id=created.id,
                    server=s.get('server'),
                    type=s.get('type'),
                    description=s.get('description'),
                    environment=s.get('environment'),
                ))
        return created

    def build_odcs_from_db(self, db_obj: DataContractDb) -> Dict[str, Any]:
        odcs: Dict[str, Any] = {
            'id': db_obj.id,
            'kind': db_obj.kind or 'DataContract',
            'apiVersion': db_obj.api_version or 'v3.0.2',
            'version': db_obj.version,
            'status': db_obj.status,
            'name': db_obj.name,
            'owner': db_obj.owner,
            'created': db_obj.created_at.isoformat() if db_obj.created_at else None,
            'updated': db_obj.updated_at.isoformat() if db_obj.updated_at else None,
        }
        
        # Add optional top-level fields
        if db_obj.tenant:
            odcs['tenant'] = db_obj.tenant
        if db_obj.domain:
            odcs['domain'] = db_obj.domain
        if db_obj.data_product:
            odcs['dataProduct'] = db_obj.data_product
            
        # Build description object
        description: Dict[str, Any] = {}
        if db_obj.description_usage:
            description['usage'] = db_obj.description_usage
        if db_obj.description_purpose:
            description['purpose'] = db_obj.description_purpose
        if db_obj.description_limitations:
            description['limitations'] = db_obj.description_limitations
        if description:
            odcs['description'] = description
            
        # Build schema array from relationships
        if hasattr(db_obj, 'schema_objects') and db_obj.schema_objects:
            schema = []
            for schema_obj in db_obj.schema_objects:
                schema_dict = {
                    'name': schema_obj.name,
                    'properties': []
                }
                if schema_obj.physical_name:
                    schema_dict['physicalName'] = schema_obj.physical_name
                    
                # Add properties
                if hasattr(schema_obj, 'properties') and schema_obj.properties:
                    for prop in schema_obj.properties:
                        prop_dict = {
                            'name': prop.name,
                            'logicalType': prop.logical_type,
                        }
                        if prop.required is not None:
                            prop_dict['required'] = prop.required
                        if prop.unique is not None:
                            prop_dict['unique'] = prop.unique
                        if prop.transform_description:
                            prop_dict['description'] = prop.transform_description
                        schema_dict['properties'].append(prop_dict)
                        
                schema.append(schema_dict)
            odcs['schema'] = schema
            
        # Build team array from relationships
        if hasattr(db_obj, 'team_members') and db_obj.team_members:
            team = []
            for member in db_obj.team_members:
                member_dict = {
                    'role': member.role,
                    'email': member.username,
                }
                if member.date_in:
                    member_dict['dateIn'] = member.date_in
                if member.date_out:
                    member_dict['dateOut'] = member.date_out
                team.append(member_dict)
            odcs['team'] = team
            
        # Build access control from quality checks (this is a simplified mapping)
        if hasattr(db_obj, 'quality_checks') and db_obj.quality_checks:
            quality_rules = []
            for check in db_obj.quality_checks:
                rule_dict = {
                    'type': check.check_type,
                    'enabled': check.enabled,
                }
                if check.threshold is not None:
                    rule_dict['threshold'] = check.threshold
                if check.query:
                    rule_dict['query'] = check.query
                quality_rules.append(rule_dict)
            odcs['qualityRules'] = quality_rules
            
        # Build support channels
        if hasattr(db_obj, 'support_channels') and db_obj.support_channels:
            support = {}
            for channel in db_obj.support_channels:
                support[channel.channel] = channel.url
            odcs['support'] = support
            
        # Build SLA properties
        if hasattr(db_obj, 'sla_properties') and db_obj.sla_properties:
            sla = {}
            for prop in db_obj.sla_properties:
                # Try to convert numeric values
                value = prop.value
                try:
                    if '.' in value:
                        sla[prop.property] = float(value)
                    else:
                        sla[prop.property] = int(value)
                except (ValueError, TypeError):
                    sla[prop.property] = value
            odcs['sla'] = sla
            
        # Build custom properties
        if hasattr(db_obj, 'custom_properties') and db_obj.custom_properties:
            custom_props = {}
            for prop in db_obj.custom_properties:
                custom_props[prop.property] = prop.value
            odcs['customProperties'] = custom_props
            
        # Legacy support for tags and roles
        if hasattr(db_obj, 'tags') and db_obj.tags:
            odcs['tags'] = [t.name for t in db_obj.tags]
            
        if hasattr(db_obj, 'roles') and db_obj.roles:
            odcs['roles'] = [
                {
                    'role': r.role,
                    'description': r.description,
                    'access': r.access,
                    'firstLevelApprovers': r.first_level_approvers,
                    'secondLevelApprovers': r.second_level_approvers,
                }
                for r in db_obj.roles
            ]
            
        return odcs

    # --- App startup data loader ---
    def load_initial_data(self, db) -> None:
        """Load example contracts from YAML into the database if not present.

        Supports both legacy entries (with embedded contract_text) and the new
        normalized ODCS-like structure (top-level fields + schema list).
        """
        try:
            yaml_path = self._data_dir / 'data_contracts.yaml'
            if not yaml_path.exists():
                logger.info("No data_contracts.yaml found; skipping initial contract load.")
                return
            with open(yaml_path, 'r') as f:
                data = yaml.safe_load(f) or {}
            contracts = data.get('contracts') or []
            created_count = 0
            for c in contracts:
                name = c.get('name')
                version = c.get('version') or 'v1.0'
                if not name:
                    continue

                # If an entry with same name+version exists, enrich if needed
                existing = db.query(DataContractDb).filter(
                    DataContractDb.name == name,
                    DataContractDb.version == version
                ).first()
                if existing:
                    try:
                        updated_any = False
                        # Enrich description fields if present in YAML but missing in DB
                        if description:
                            if (not existing.description_usage) and description.get('usage'):
                                existing.description_usage = description.get('usage')
                                updated_any = True
                            if (not existing.description_purpose) and description.get('purpose'):
                                existing.description_purpose = description.get('purpose')
                                updated_any = True
                            if (not existing.description_limitations) and description.get('limitations'):
                                existing.description_limitations = description.get('limitations')
                                updated_any = True

                        # Enrich schema if none present
                        schema_list = c.get('schema') or []
                        if (not getattr(existing, 'schema_objects', None) or len(existing.schema_objects) == 0) and isinstance(schema_list, list):
                            for obj in schema_list:
                                if not isinstance(obj, dict):
                                    continue
                                so = SchemaObjectDb(
                                    contract_id=existing.id,
                                    name=obj.get('name') or 'object',
                                    physical_name=obj.get('physicalName') or obj.get('physical_name'),
                                    logical_type='object',
                                )
                                db.add(so)
                                db.flush()
                                props = obj.get('properties') or []
                                if isinstance(props, list):
                                    for p in props:
                                        if not isinstance(p, dict):
                                            continue
                                        db.add(SchemaPropertyDb(
                                            object_id=so.id,
                                            name=p.get('name') or 'column',
                                            logical_type=p.get('logicalType') or p.get('logical_type') or 'string',
                                            required=bool(p.get('required', False)),
                                            unique=bool(p.get('unique', False)),
                                            transform_description=p.get('description'),
                                        ))
                            updated_any = True

                        if updated_any:
                            existing.updated_by = 'system@startup'
                            db.add(existing)
                            created_count += 1  # Count as processed/enriched
                        continue
                    except Exception:
                        continue

                # Determine if entry is legacy (embedded doc) or normalized (ODCS-like)
                contract_text = c.get('contract_text')
                format_val = c.get('format')
                description = c.get('description') or {}

                if contract_text is not None or format_val is not None:
                    # Legacy path present; create minimal top-level record without raw_* storage
                    db_obj = DataContractDb(
                        name=name,
                        version=version,
                        status=c.get('status') or 'draft',
                        owner=c.get('owner') or 'unknown@local',
                        kind=c.get('kind') or 'DataContract',
                        api_version=c.get('apiVersion') or 'v3.0.2',
                        description_usage=description.get('usage'),
                        description_purpose=description.get('purpose'),
                        description_limitations=description.get('limitations'),
                        created_by='system@startup',
                        updated_by='system@startup',
                    )
                    created = data_contract_repo.create(db=db, obj_in=db_obj)  # type: ignore[arg-type]
                    # If legacy content had schema-like info, it's ignored here by design (no raw docs)
                    created_count += 1
                    continue

                # Normalized path: create top-level record + schema objects/properties
                db_obj = DataContractDb(
                    name=name,
                    version=version,
                    status=c.get('status') or 'draft',
                    owner=c.get('owner') or 'unknown@local',
                    kind=c.get('kind') or 'DataContract',
                    api_version=c.get('apiVersion') or 'v3.0.2',
                    description_usage=description.get('usage'),
                    description_purpose=description.get('purpose'),
                    description_limitations=description.get('limitations'),
                    created_by='system@startup',
                    updated_by='system@startup',
                )
                created = data_contract_repo.create(db=db, obj_in=db_obj)  # type: ignore[arg-type]

                # Schema objects
                schema_list = c.get('schema') or []
                if isinstance(schema_list, list):
                    for obj in schema_list:
                        if not isinstance(obj, dict):
                            continue
                        so = SchemaObjectDb(
                            contract_id=created.id,
                            name=obj.get('name') or 'object',
                            physical_name=obj.get('physicalName') or obj.get('physical_name'),
                            logical_type='object',
                        )
                        db.add(so)
                        db.flush()

                        # Properties
                        props = obj.get('properties') or []
                        if isinstance(props, list):
                            for p in props:
                                if not isinstance(p, dict):
                                    continue
                                db.add(SchemaPropertyDb(
                                    object_id=so.id,
                                    name=p.get('name') or 'column',
                                    logical_type=p.get('logicalType') or p.get('logical_type') or 'string',
                                    required=bool(p.get('required', False)),
                                    unique=bool(p.get('unique', False)),
                                    transform_description=p.get('description'),
                                ))

                created_count += 1

            if created_count:
                db.commit()
                logger.info(f"Loaded {created_count} data contracts from YAML into DB.")
            else:
                logger.info("No new data contracts loaded from YAML (existing entries found).")
        except Exception as e:
            logger.error(f"Failed to load initial data contracts into DB: {e}", exc_info=True)
