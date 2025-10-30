# ODCS v3.0.2 Field Coverage - Gap Analysis & Improvement Plan

## Summary
We've successfully refactored the data contract UI from a complex wizard to a simpler incremental editing approach. We handle the core ODCS fields, but several important governance, discovery, and compliance fields are missing. This document provides a comprehensive analysis and phased improvement plan.

---

## Current Coverage ✓

**Top-level fields we handle well:**
- Basic metadata: version, kind, apiVersion, id, name, status, tenant, dataProduct
- Description: purpose, usage, limitations
- Domain linking
- Full CRUD for: schemas, team, servers, quality rules (contract level)
- Timestamps: created_at

**Schema/Property fields we handle:**
- Schema: name, physicalName, businessName, description, dataGranularityDescription, properties
- Property: name, logicalType, required, unique, description

---

## Missing Fields by Priority

### 🔴 HIGH PRIORITY (Phase 1) - Governance & Discovery
Essential for data governance and discovery in Unity Catalog:

- [ ] **tags** (top-level + schema + property level)
  - Critical for: discovery, data product linking, categorization
  - ODCS: array of strings (e.g., ["finance", "sensitive", "PII"])
  - Implementation: Add tags input to basic form, schema form, property editor

- [ ] **classification** (property level)
  - Critical for: data governance, compliance, PII handling
  - ODCS: string (e.g., "confidential", "restricted", "public", "1-5")
  - Implementation: Add select dropdown to property editor

- [ ] **primaryKey** (property level)
  - Critical for: understanding table structure, joins, relationships
  - ODCS: boolean + primaryKeyPosition
  - Implementation: Add checkbox to property editor

- [ ] **partitioned** / **partitionKeyPosition** (property level)
  - Important for: Databricks/lakehouse performance optimization
  - ODCS: boolean + integer position
  - Implementation: Add checkbox + number input to property editor

- [ ] **criticalDataElement** (property level)
  - Important for: compliance, identifying critical data elements
  - ODCS: boolean CDE flag
  - Implementation: Add checkbox to property editor

- [ ] **authoritativeDefinitions** (top-level + description + schema + property)
  - Important for: linking to business glossary, documentation, training
  - ODCS: array of {url, type} (businessDefinition, videoTutorial, etc.)
  - Implementation: Create new section with array editor for URL + type pairs

**Effort:** ~3-4 days | **Value:** High - unlocks governance workflows

---

### 🟡 MEDIUM PRIORITY (Phase 2) - Access Control & Collaboration

- [ ] **roles** (top-level)
  - Important for: IAM integration, access control workflows
  - ODCS: array of {role, description, access, firstLevelApprovers, secondLevelApprovers}
  - Implementation: Create new CRUD section similar to team members

- [ ] **support** (top-level)
  - Useful for: collaboration channels (Slack, Teams, email, tickets)
  - ODCS: array of {channel, url, tool, scope, description}
  - Implementation: Create new CRUD section for support channels

- [ ] **customProperties** (top-level + multiple nested levels)
  - Flexible: extension mechanism for organization-specific metadata
  - ODCS: array of {property, value}
  - Implementation: Create reusable key-value editor component

- [ ] **quality at schema/property level**
  - Currently: quality rules only at contract level
  - Should add: quality checks at individual schema and property levels
  - Implementation: Add quality array editor to schema and property forms

**Effort:** ~2-3 days | **Value:** Medium-High - enables access control workflows

---

### 🟢 MEDIUM-LOW PRIORITY (Phase 3) - Advanced Schema Metadata

- [ ] **examples** (property level)
  - Helpful for: understanding data, documentation
  - ODCS: array of sample values
  - Implementation: Add array input to property editor

- [ ] **logicalTypeOptions** (property level)
  - Advanced: validation constraints (min/maxLength, pattern, format, ranges)
  - ODCS: complex nested options per type (string/date/number/etc.)
  - Implementation: Conditional form fields based on logicalType selection

- [ ] **Transform fields** (property level)
  - Lineage: transformSourceObjects, transformLogic, transformDescription
  - ODCS: array of source objects + logic string + description
  - Implementation: Add transform section to property editor

- [ ] **physicalType** / **physicalName** (property level)
  - Useful: mapping between logical and physical column names/types
  - Currently: only have these at schema level, not property level
  - Implementation: Add text inputs to property editor

- [ ] **businessName** (property level)
  - Currently: only at schema level, not property level
  - Implementation: Add text input to property editor

**Effort:** ~3-5 days | **Value:** Medium - improves metadata completeness

---

### ⚪ LOWER PRIORITY (Phase 4+) - Specialized Features

- [ ] **price** (top-level)
  - Marketplace: priceAmount, priceCurrency, priceUnit
  - ODCS: Pricing object for data monetization
  - Implementation: Create new pricing section

- [ ] **slaProperties** (top-level)
  - Advanced SLA: flexible array instead of our simplified 4-field SLA
  - ODCS: array of {property, value, unit, element, driver}
  - Implementation: Either replace current SLA or add alongside it

- [ ] **slaDefaultElement** (top-level)
  - Advanced SLA: element path notation for default checks
  - ODCS: string
  - Implementation: Add text input to SLA section

- [ ] **Quality rule enhancements**
  - Missing: unit, schedule, scheduler, method, tags, authoritativeDefinitions
  - Missing type-specific: mustBe/mustBeGreaterThan/etc. (library), engine/implementation (custom)
  - Implementation: Expand quality-rule-form-dialog.tsx with additional fields

- [ ] **encryptedName** (property level)
  - Specialized: link to encrypted column name
  - ODCS: string reference to encrypted field
  - Implementation: Add text input to property editor

- [ ] **Server type-specific fields**
  - Current: generic host/port/database/schema
  - ODCS: many type-specific fields per server type (33 types!)
  - Implementation: Conditional server form fields based on type selection

**Effort:** ~2-3 days | **Value:** Low-Medium - specialized use cases

---

## Recommended Implementation Order

### Phase 1: Governance Essentials (Highest ROI)
Focus on fields that enable better governance and discovery:
1. Add tags input to basic form, schema form, property editor
2. Add classification select to property editor
3. Add primaryKey checkbox to property editor
4. Add partitioned/partitionKeyPosition to property editor
5. Add criticalDataElement checkbox to property editor
6. Add authoritativeDefinitions section with URL + type pairs

**Effort:** ~3-4 days | **Value:** High - unlocks governance workflows

### Phase 2: Access & Collaboration
1. Add roles CRUD section (similar to team members)
2. Add support CRUD section for support channels
3. Add customProperties key-value editor (reusable component)
4. Add quality to schema and property forms

**Effort:** ~2-3 days | **Value:** Medium-High - enables access control workflows

### Phase 3: Advanced Schema Features
1. Add examples array to property editor
2. Add transform fields to property editor
3. Add physicalType/physicalName/businessName to property editor
4. Add logicalTypeOptions (complex - conditional forms per type)

**Effort:** ~3-5 days | **Value:** Medium - improves metadata completeness

### Phase 4: Marketplace & Polish
1. Add price section
2. Replace simplified SLA with slaProperties array (or keep both)
3. Enhance quality rules form with missing fields
4. Add encryptedName and other specialized fields
5. Add server type-specific fields

**Effort:** ~2-3 days | **Value:** Low-Medium - specialized use cases

---

## TypeScript Type Updates Needed

All missing fields need to be added to `src/frontend/src/types/data-contract.ts`:

**DataContract type additions:**
```typescript
tags?: string[]
support?: SupportItem[]
price?: Pricing
roles?: Role[]
slaProperties?: ServiceLevelAgreementProperty[]
slaDefaultElement?: string
authoritativeDefinitions?: AuthoritativeDefinition[]
customProperties?: CustomProperty[]
```

**SchemaObject type additions:**
```typescript
tags?: string[]
authoritativeDefinitions?: AuthoritativeDefinition[]
customProperties?: CustomProperty[]
quality?: QualityRule[]
logicalType?: 'object'
```

**SchemaProperty type additions:**
```typescript
// From SchemaElement
tags?: string[]
authoritativeDefinitions?: AuthoritativeDefinition[]
customProperties?: CustomProperty[]
businessName?: string
physicalType?: string
physicalName?: string

// From SchemaBaseProperty
primaryKey?: boolean
primaryKeyPosition?: number
logicalTypeOptions?: LogicalTypeOptions
partitioned?: boolean
partitionKeyPosition?: number
classification?: string
encryptedName?: string
transformSourceObjects?: string[]
transformLogic?: string
transformDescription?: string
examples?: any[]
criticalDataElement?: boolean
quality?: QualityRule[]
```

**New types to add:**
```typescript
type SupportItem = {
  channel: string
  url: string
  tool?: string
  scope?: string
  description?: string
  invitationUrl?: string
}

type Pricing = {
  priceAmount?: number
  priceCurrency?: string
  priceUnit?: string
}

type Role = {
  role: string
  description?: string
  access?: string
  firstLevelApprovers?: string
  secondLevelApprovers?: string
  customProperties?: CustomProperty[]
}

type ServiceLevelAgreementProperty = {
  property: string
  value: string | number | boolean | null
  valueExt?: string | number | boolean | null
  unit?: string
  element?: string
  driver?: string
}

type AuthoritativeDefinition = {
  url: string
  type: string  // businessDefinition, transformationImplementation, videoTutorial, tutorial, implementation
}

type CustomProperty = {
  property: string
  value: any
}

type LogicalTypeOptions = {
  // String options
  minLength?: number
  maxLength?: number
  pattern?: string
  format?: string

  // Numeric options
  multipleOf?: number
  maximum?: number
  exclusiveMaximum?: boolean
  minimum?: number
  exclusiveMinimum?: boolean

  // Object/Array options
  maxProperties?: number
  minProperties?: number
  maxItems?: number
  minItems?: number
  uniqueItems?: boolean
  required?: string[]
}
```

Backend types likely already support most of these via ODCS validation.

---

## Questions to Consider

1. **Which phase should we start with?** Phase 1 (governance essentials) recommended
2. **Do we want marketplace features (price)?** Depends on use case
3. **Should we replace simplified SLA or keep both?** Keep both initially
4. **How important are transform/lineage fields?** Medium - depends on whether lineage is tracked elsewhere
5. **Should we implement logicalTypeOptions fully?** Complex feature - consider if validation is needed

---

## Current Status

✅ **Completed:**
- Core ODCS v3.0.2 implementation with basic metadata
- Full CRUD for schemas, team, servers, quality rules
- Refactored from wizard to incremental editing approach
- Read-modify-write pattern for all updates

⏭️ **Next Steps:**
1. Decide which phase to implement first (recommend Phase 1)
2. Update TypeScript types in data-contract.ts
3. Create form components for new fields
4. Test with backend API to ensure compatibility
5. Update demo data to include new fields

---

## References

- ODCS v3.0.2 Schema: `src/backend/src/schemas/odcs-json-schema-v3.0.2-strict.json`
- Frontend Types: `src/frontend/src/types/data-contract.ts`
- Backend API Models: `src/backend/src/models/data_contracts_api.py`
- Current Implementation: `src/frontend/src/views/data-contract-details.tsx`
