> We are working on the redesign of the UI for Data Contracts.\
\
Status: We are missing a few fields in the schema property editor, like "partitioned", "physical 
type" etc. see @WIZARD_VS_CURRENT_DETAILED_COMPARISON.md and the old 
@src/frontend/src/components/data-products/data-product-wizard-dialog.tsx what is needed for each 
schema property (and of course @src/backend/src/db_models/data_contracts.py and 
@src/backend/src/schemas/odcs-json-schema-v3.0.2-strict.json for the ultimate reference).\
\
- Add the missing fields\
- Add back the ability to assign business properties to each schema property\
- Extract the schema editor into a separate, reusable component as we want to use it in the Data 
Curation feature as well. No need to wrap it into a tile or visible container since it is embedded 
into one of those usually. 
  ⎿  Read WIZARD_VS_CURRENT_DETAILED_COMPARISON.md (540 lines)
  ⎿  Read src/frontend/src/components/data-products/data-product-wizard-dialog.tsx (843 lines)
  ⎿  Read src/backend/src/db_models/data_contracts.py (312 lines)
  ⎿  Read src/backend/src/schemas/odcs-json-schema-v3.0.2-strict.json (2395 lines)

⏺ Based on my analysis of the comparison document, database models, ODCS schema, and wizard implementation, I can now present a comprehensive plan to address the missing schema property fields and create a
  reusable schema editor component.

  Current Status Analysis

  Missing Schema Property Fields (from comparison doc):

  1. ✅ Already in DB: physicalType, primaryKey, primaryKeyPosition, partitioned, partitionKeyPosition, classification, examples
  2. ❌ Missing UI: These fields exist in the database but are not exposed in the current schema property editor

  Critical Missing Feature:

  - Semantic Concepts / Business Properties: The old wizard had full integration with BusinessConceptsDisplay component for linking business glossary terms at property level. This is currently completely
  removed.

  Implementation Plan

  1. Analyze Current Schema Property Editor

  - Locate the existing schema property form/editor component
  - Identify current field coverage
  - Review validation logic

  2. Create Reusable Schema Property Editor Component

  - New file: src/frontend/src/components/data-contracts/schema-property-editor.tsx
  - Features:
    - Tabbed interface (similar to property editor pattern shown in comparison doc):
        - Core Tab: name, logicalType, physicalType, physicalName, description
      - Constraints Tab: required, unique, primaryKey, primaryKeyPosition, partitioned, partitionKeyPosition
      - Governance Tab: classification, examples
      - Business Tab: businessName, encryptedName, criticalDataElement, semantic concepts/authoritative definitions
      - Transform Tab: transformLogic, transformSourceObjects, transformDescription
  - Props interface:
  interface SchemaPropertyEditorProps {
    value: SchemaProperty;
    onChange: (property: SchemaProperty) => void;
    mode?: 'create' | 'edit';
    onCancel?: () => void;
    onSave?: () => void;
  }
  - Make it work as both controlled component (for embedding) and with internal dialog state

  3. Add Missing Fields to Schema Property Type

  - Update src/frontend/src/types/data-contract.ts:
    - Ensure all 21 fields from comparison doc are present
    - Add authoritativeDefinitions array for business concepts
    - Match ODCS v3.0.2 schema structure

  4. Restore Business Concepts Integration

  - Re-import and integrate BusinessConceptsDisplay component (referenced in wizard line 9)
  - Add semantic concepts field to SchemaProperty type
  - Implement conversion to authoritativeDefinitions format (as in wizard lines 414-418)
  - Add UI in Business tab for:
    - Linking to business glossary terms
    - Managing authoritative definitions (type + URL pairs)

  5. Update Schema Object Form Dialog

  - Replace inline property editor with new reusable component
  - Ensure proper data flow between parent form and property editor

  6. Create Validation Schema

  - Zod schema for all 21 property fields
  - Conditional validation based on field relationships (e.g., primaryKeyPosition only when primaryKey is true)

  7. Update Backend Integration

  - Verify API models handle all fields correctly
  - Test serialization/deserialization of authoritative definitions

  8. Testing Plan

  - Create property with all field combinations
  - Test business concepts linking
  - Verify classification dropdown values
  - Test partition and primary key position logic
  - Ensure examples field accepts multi-value input

  Files to Modify/Create

  New Files:

  1. src/frontend/src/components/data-contracts/schema-property-editor.tsx - Main reusable component
  2. src/frontend/src/types/schema-property.ts (optional) - Dedicated type definitions

  Modified Files:

  1. src/frontend/src/types/data-contract.ts - Update SchemaProperty type
  2. src/frontend/src/components/data-contracts/schema-form-dialog.tsx - Integrate new editor
  3. src/frontend/src/components/data-contracts/data-contract-details.tsx - Use new editor if inline editing exists

  Fields Reference (21 total):

  interface SchemaProperty {
    // Core (5)
    name: string
    logicalType: string
    physicalType?: string
    physicalName?: string
    description?: string

    // Constraints (6)
    required?: boolean
    unique?: boolean
    primaryKey?: boolean
    primaryKeyPosition?: number
    partitioned?: boolean
    partitionKeyPosition?: number

    // Governance (2)
    classification?: string
    examples?: string

    // Business (3)
    businessName?: string
    encryptedName?: string
    criticalDataElement?: boolean

    // Transform (3)
    transformLogic?: string
    transformSourceObjects?: string
    transformDescription?: string

    // Semantic (2 - MISSING)
    authoritativeDefinitions?: AuthoritativeDefinition[]
    tags?: string[]
  }

  Next Steps After Approval

  1. Search for existing schema property editor component
  2. Create new reusable component with tabbed interface
  3. Add all 21 fields with proper form controls
  4. Restore BusinessConceptsDisplay integration
  5. Update parent components to use new editor
  6. Test complete flow from UI to database

  Would you like me to proceed with this implementation plan?