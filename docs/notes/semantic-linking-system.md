# Three-Tier Semantic Linking System

The UC Application implements a comprehensive three-tier semantic linking system that connects data contracts, schemas, and properties to business concepts and semantic definitions. This system supports both traditional entity semantic links and ODCS v3.0.2 authoritative definitions.

## Overview

The semantic linking system operates at three distinct levels:

1. **Contract Level** - Links entire data contracts to business domains or concepts
2. **Schema Level** - Links schema objects (tables, views) to business entities
3. **Property Level** - Links individual columns/properties to business properties

This hierarchical approach enables precise semantic annotation at the appropriate granularity level while maintaining clear relationships between business concepts and data assets.

General Notes:
  - The app has its own semantic resource linking functionality
  - In ODCS, these links are represented as authoritative definitions
  - Imported ODCS may already have their own definitions set and these need to be retained roundtrip
  - When importing ODCS, definitions that use our own type (semantic assignment) are converted into app specific links
  - On export of ODCS, the app specific links are exported, along with any other previously existing definitions we just stored
  - Any change of semantics linking in the app rebuilds the in-memory RDF graph so that searching or walking the graph shows the linked resources. This also happens when importing an ODCS contract that has app specific definitions 

## Architecture Components

### 1. Core Managers

#### SemanticLinksManager (`src/controller/semantic_links_manager.py`)
- Manages traditional entity semantic links
- Supports data domains, data products, data contracts, schemas, and properties
- Creates subjects as `urn:ontos:{entity_type}:{entity_id}`. The `entity_id` already encodes schema/property when applicable (e.g., `contractId#schema` or `contractId#schema#property`).
- Handles lifecycle management (create, update, delete, list)

#### DataContractsManager (`src/controller/data_contracts_manager.py`)
- Processes ODCS v3.0.2 authoritative definitions during YAML import
- Exports authoritative definitions to ODCS format
- Manages contract-level, schema-level, and property-level semantic assignments

#### BusinessConceptsManager (`src/controller/business_concepts_manager.py`)
- Loads and manages business taxonomies from RDF/RDFS files
- Provides concept and property lookup services
- Supports both `class` and `property` entity types for semantic assignments

### 2. Database Models

#### Traditional Semantic Links
```python
class EntitySemanticLinkDb(Base):
    __tablename__ = "entity_semantic_links"
    id = Column(UUID, primary_key=True)
    entity_id = Column(String, nullable=False, index=True)
    entity_type = Column(String, nullable=False, index=True)  # data_domain | data_product | data_contract | data_contract_schema | data_contract_property
    iri = Column(Text, nullable=False)
    label = Column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("entity_id", "entity_type", "iri", name="uq_entity_semantic_link"),
    )
```

#### ODCS Authoritative Definitions

**Contract Level:**
```python
class DataContractAuthorityDb(Base):
    __tablename__ = "data_contract_authorities"
    contract_id: Column(String, ForeignKey("data_contracts.id"))
    url: Column(String)             # Business concept IRI
    type: Column(String)            # "http://databricks.com/ontology/uc/semanticAssignment"
```

**Schema Level:**
```python
class SchemaObjectAuthorityDb(Base):
    __tablename__ = "data_contract_schema_object_authorities"
    schema_object_id: Column(String, ForeignKey("data_contract_schema_objects.id"))
    url: Column(String)             # Business concept IRI
    type: Column(String)            # Semantic assignment type
```

**Property Level:**
```python
class SchemaPropertyAuthorityDb(Base):
    __tablename__ = "data_contract_schema_property_authorities"
    property_id: Column(String, ForeignKey("data_contract_schema_properties.id"))
    url: Column(String)             # Business property IRI
    type: Column(String)            # Semantic assignment type
```

### 3. Business Taxonomies

The system uses RDF/RDFS taxonomies stored in `/src/backend/src/data/taxonomies/`:

#### Business Concepts (`business-concepts.ttl`)
- Defines domain classes like `CustomerDomain`, `FinancialDomain`, `SalesDomain`
- Links to organizational entities and business processes
- Used for contract-level and schema-level semantic assignments

#### Business Properties (`business-properties.ttl`)
- Contains 326 business property triples
- Covers personal identifiers, addresses, financial properties, product properties
- Key properties: `email`, `firstName`, `lastName`, `phoneNumber`, `customerId`, `streetAddress`, `city`, `zipCode`, `country`
- Used for property-level semantic assignments

## Implementation Details

### 1. Traditional Entity Semantic Links

**Creation Process:**
```python
# Via SemanticLinksManager
link = EntitySemanticLinkCreate(
    entity_type="data_contract",
    entity_id="contract-uuid",
    iri="http://example.com/business/concepts#Customer",
    semantic_type="business_concept"
)
semantic_links_manager.create_link(link)
```

**URI Format:**
- Entity references use URIRef format
- Pattern: `urn:ontos:{entity_type}:{entity_id}#{schema}#{property}`
- Example: `urn:ontos:data_contract:123-uuid#customers#email`

### 2. ODCS Authoritative Definitions

**YAML Structure:**
```yaml
id: customer-contract-uuid
kind: DataContract
apiVersion: v3.0.2
authoritativeDefinitions:
  - url: "http://example.com/business/concepts#Customer"
    type: "http://databricks.com/ontology/uc/semanticAssignment"
schema:
  - name: customers
    authoritativeDefinitions:
      - url: "http://example.com/business/concepts#Customer"
        type: "http://databricks.com/ontology/uc/semanticAssignment"
    properties:
      - name: email
        authoritativeDefinitions:
          - url: "http://example.com/business/properties#email"
            type: "http://databricks.com/ontology/uc/semanticAssignment"
```

**Import Process:**
1. DataContractsManager parses YAML authoritativeDefinitions
2. Creates database records at all three levels
3. Processes contract-level, schema-level, and property-level assignments
4. Validates IRI format and semantic assignment type

**Export Process:**
1. DataContractsManager reads from database models
2. Includes authoritative definitions in ODCS export
3. Maintains hierarchical structure (contract → schema → property)
4. Preserves semantic assignment types and URLs

### 3. UI Integration

#### ConceptSelectDialog Component
- Supports both `'class'` and `'property'` entity types
- Integrates with business concepts and properties taxonomies
- Provides search and selection interface for semantic assignments
- Used in ODCS wizard for creating authoritative definitions

#### BusinessConceptsDisplay Component
- Renders semantic links in data contract details
- Accepts `conceptType` parameter (`'class'` or `'property'`)
- Displays business concept labels and descriptions
- Supports navigation to concept definitions

## Usage Examples

### 1. Contract-Level Semantic Assignment

**Purpose:** Link entire data contract to business domain
```yaml
# Customer Data Contract
authoritativeDefinitions:
  - url: "http://example.com/business/concepts#Customer"
    type: "http://databricks.com/ontology/uc/semanticAssignment"
```

**Database Storage:**
```sql
INSERT INTO data_contract_authorities (contract_id, url, type)
VALUES ('contract-uuid', 'http://example.com/business/concepts#Customer',
        'http://databricks.com/ontology/uc/semanticAssignment');
```

### 2. Schema-Level Semantic Assignment

**Purpose:** Link schema object to specific business entity
```yaml
schema:
  - name: customer_addresses
    authoritativeDefinitions:
      - url: "http://example.com/business/concepts#CustomerProfile"
        type: "http://databricks.com/ontology/uc/semanticAssignment"
```

### 3. Property-Level Semantic Assignment

**Purpose:** Link individual property to business property definition
```yaml
properties:
  - name: email
    authoritativeDefinitions:
      - url: "http://example.com/business/properties#email"
        type: "http://databricks.com/ontology/uc/semanticAssignment"
  - name: first_name
    authoritativeDefinitions:
      - url: "http://example.com/business/properties#firstName"
        type: "http://databricks.com/ontology/uc/semanticAssignment"
```

## Processing Flow

### 1. Data Loading (Startup)

1. **Taxonomy Loading:**
   - BusinessConceptsManager loads RDF/RDFS files
   - Parses business concepts and properties
   - Builds in-memory lookup structures

2. **Contract Processing:**
   - DataContractsManager processes demo YAML files
   - Creates database records for contracts, schemas, properties
   - Processes authoritative definitions at all levels
   - Creates traditional semantic links for demo data

3. **Semantic Link Processing:**
   - SemanticLinksManager processes entity semantic links
   - Creates bidirectional relationships
   - Validates IRI references against loaded taxonomies

### 2. ODCS Export

1. **Database Query:**
   - Retrieve contract with all relationships
   - Include authoritative definitions at all levels
   - Load related semantic links

2. **Hierarchical Assembly:**
   - Build contract-level authoritative definitions
   - Process schema objects with their authoritative definitions
   - Include property-level authoritative definitions
   - Inject traditional semantic links as authoritative definitions

3. **Format Conversion:**
   - Convert database models to ODCS format
   - Preserve semantic assignment types
   - Maintain hierarchical structure

## Testing and Validation

### 1. Database Tests

**Integration Tests (`test_data_contracts_db.py`):**
- `test_property_with_authoritative_definitions()` - Property-level authoritative definitions
- `test_schema_with_authoritative_definitions()` - Schema-level authoritative definitions
- `test_cascade_delete_contract()` - Cascade deletion including property authoritative definitions

**Unit Tests (`test_data_contracts_manager.py`):**
- `test_build_odcs_property_authoritative_definitions()` - ODCS export with property-level assignments
- Semantic assignment injection in ODCS export
- Contract creation from ODCS with authoritative definitions

### 2. UI Testing

**Playwright Tests:**
- Navigate to data contracts page
- Verify semantic links display in contract details
- Test concept selection dialog functionality
- Validate ODCS export includes authoritative definitions

## Configuration and Setup

### 1. Taxonomy Files

**Location:** `/src/backend/src/data/taxonomies/`
- `business-concepts.ttl` - Business domain concepts
- `business-properties.ttl` - Business property definitions
- `README.md` - Taxonomy structure documentation

### 2. Database Tables

**Creation:** Managed via SQLAlchemy models and Alembic migrations
- Traditional semantic links: `entity_semantic_links`
- Contract authoritative definitions: `data_contract_authorities`
- Schema authoritative definitions: `data_contract_schema_object_authorities`
- Property authoritative definitions: `data_contract_schema_property_authorities`

### 3. Demo Data

**YAML Files:** `/src/backend/src/data/`
- `data_contracts.yaml` - Contains Customer Data Contract with all three levels of semantic assignments
- Example shows 14 semantic assignments: 1 contract-level, 2 schema-level, 11 property-level

## Best Practices

### 1. Semantic Assignment Guidelines

**Contract Level:**
- Use for overall domain classification
- Link to high-level business domains (`CustomerDomain`, `FinancialDomain`)
- Keep assignments broad and stable

**Schema Level:**
- Use for specific business entities within the domain
- Link to concrete business concepts (`Customer`, `CustomerProfile`)
- Consider schema purpose and primary entity

**Property Level:**
- Use for individual data elements
- Link to specific business properties (`email`, `firstName`, `lastName`)
- Maintain consistency across similar properties

### 2. IRI Management

**Business Concepts:**
- Format: `http://example.com/business/concepts#{ConceptName}`
- Use PascalCase for concept names
- Ensure concepts exist in business-concepts.ttl

**Business Properties:**
- Format: `http://example.com/business/properties#{propertyName}`
- Use camelCase for property names
- Ensure properties exist in business-properties.ttl

**Semantic Assignment Type:**
- Always use: `http://databricks.com/ontology/uc/semanticAssignment`
- Consistent across all three levels
- Required for ODCS v3.0.2 compliance

### 3. Maintenance

**Adding New Concepts:**
1. Add to appropriate taxonomy file (concepts or properties)
2. Restart application to reload taxonomies
3. Update existing contracts to use new concepts
4. Validate assignments through UI or API

**Schema Updates:**
1. Update database models for new relationship types
2. Create migrations for schema changes
3. Update YAML processing logic
4. Add corresponding tests

## Troubleshooting

### Common Issues

1. **Missing Semantic Links in UI:**
   - Check if authoritative definitions are stored in database
   - Verify semantic link processing runs on startup
   - Validate IRI format and taxonomy loading

2. **ODCS Export Missing Authoritative Definitions:**
   - Confirm database models include relationships
   - Check YAML processing logic for all three levels
   - Verify export function includes authoritative definitions

3. **Concept Selection Not Working:**
   - Validate taxonomy files are loaded successfully
   - Check business concepts manager initialization
   - Verify IRI format matches taxonomy definitions

### Diagnostic Commands

**Check Semantic Links:**
```sql
SELECT * FROM entity_semantic_links WHERE entity_type = 'data_contract';
```

**Check Authoritative Definitions:**
```sql
-- Contract level
SELECT * FROM data_contract_authorities;

-- Schema level
SELECT * FROM data_contract_schema_object_authorities;

-- Property level
SELECT * FROM data_contract_schema_property_authorities;
```

**Verify Taxonomy Loading:**
```python
# In application logs
BusinessConceptsManager: Loaded X business concepts
BusinessConceptsManager: Loaded Y business properties
```

This three-tier semantic linking system provides comprehensive semantic annotation capabilities while maintaining flexibility and ODCS v3.0.2 compliance. The hierarchical approach ensures semantic assignments can be made at the appropriate granularity level for optimal business value.