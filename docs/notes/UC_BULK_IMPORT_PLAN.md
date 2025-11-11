# UC Bulk Import/Export Workflows Implementation Plan

## Prompts

Implement a new workflow in  @workflows which allows to create data contracts and products from existing tagged objects in Unity Catalog 
- See @uc_tag_sync.py for code examples and @dqx_profile_datasets.py for the most up to date database setup
- Allow the user to configure the tags in the general tab of @settings.tsx as two regular expressions
  - Key pattern: Allows to find UC tags that match, for example `data-contract-name` or `data-contract-ABC` etc. The key pattern for those two would latch on the the `data-contract` prefix. But the pattern could also be much more abstract.
  - Value pattern: Here we need to specify on what string it operates, either the key or the value of the tag, and then the pattern to extract the relevant information from, for example, above would find `ABC` in the key string. Again, the pattern could be anything and we can use a regexp match group to extract the information
- The user can also specify an optional pattern to handle specific catalogs, schemas, or datasets only. Again, we use the "Value pattern" approach explained above but call it Filter pattern. We assume filter tags are inherited, so if the schema has the tag, all included child objects are included in the job
- The job then iterates over the catalog and - if specified - filters the datasets by Filter pattern, then checks the catalogs `information_schema` and its `CATALOGS_TAGS`, `SCHEMA_TAGS`, and `TABLE_TAGS` tables to find matching objects based on the above patterns.
- The job groups the matching resources into contracts and products, linking them where the same objects have both kind of tags. It creates those in the apps tables where they fit.

Write a Markdown document that explains this job under @docs in a new `jobs` subdirectory.

The plan shapes up, but I am not happy about the way to define the patterns and configure the jobs. The patterns for the bulk import job are specific to the job, not the user running it (aka the app role, also, only admins can managed this section of the app anyways). Maybe we have to add the option to add configurations to each job in the UI, based on the job's YAML. As in, the YAML could say what the app can configure, like variable name, type, default value, description, optional max/min values or if nullable, and then in the UI in the Workflow/Jobs tab we can click on a new button to configure jobs that need such variables set. The modal that pops up uses the YAML info to populate the form. Upon saving, the app stores the setting in a table for "Job Configuration" that links to the job by name. Then when the job runs, the job runner loads the configuration and passes it on to the job config or ad-hoc run.

## Overview

Create two complementary workflows:

1. **UC Bulk Import**: Scans Unity Catalog tags and creates Contracts, Products, Domains (and other entities) in the app database
2. **UC Bulk Export** (future): Tags Unity Catalog resources with Contract, Product, Domain names/IDs from the app database

Both workflows use a generic job configuration system that allows workflows to declare configurable parameters in YAML, managed through the UI.

## Part 1: Generic Job Configuration System

### Database Schema - Job Configurations Table

**File**: `src/backend/src/db_models/workflow_configurations.py` (new)

Create new table:

```python
class WorkflowConfigurationDb(Base):
    __tablename__ = 'workflow_configurations'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    workflow_id = Column(String, nullable=False, unique=True, index=True)
    configuration = Column(Text, nullable=False)  # JSON configuration values
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())
```

### Backend Models

**File**: `src/backend/src/models/workflow_configurations.py` (new)

```python
class WorkflowParameterDefinition(BaseModel):
    name: str
    type: str  # "string", "integer", "boolean", "select", "entity_patterns"
    default: Any = None
    description: str = ""
    required: bool = False
    options: Optional[List[str]] = None  # For select type
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    pattern: Optional[str] = None  # Regex validation
    entity_types: Optional[List[str]] = None  # For entity_patterns type

class WorkflowConfiguration(BaseModel):
    workflow_id: str
    configuration: Dict[str, Any]

class WorkflowConfigurationUpdate(BaseModel):
    configuration: Dict[str, Any]
```

### Repository

**File**: `src/backend/src/repositories/workflow_configurations_repository.py` (new)

Standard CRUD operations for workflow configurations.

### Jobs Manager Updates

**File**: `src/backend/src/controller/jobs_manager.py`

Add methods:

- `get_workflow_parameter_definitions(workflow_id)`: Parse YAML `configurable_parameters` section
- `get_workflow_configuration(workflow_id)`: Load saved configuration from database
- `update_workflow_configuration(workflow_id, config)`: Validate and save configuration
- Update `start_workflow()` to merge saved configuration with runtime parameters before job submission

### API Routes

**File**: `src/backend/src/routes/jobs_routes.py`

Add endpoints:

- `GET /api/jobs/workflows/{workflow_id}/parameter-definitions` - Get parameter schema from YAML
- `GET /api/jobs/workflows/{workflow_id}/configuration` - Get saved configuration
- `PUT /api/jobs/workflows/{workflow_id}/configuration` - Update and validate configuration

### Frontend Types

**File**: `src/frontend/src/types/workflow-configurations.ts` (new)

TypeScript interfaces matching backend models, including:

```typescript
interface EntityPatternConfig {
  entity_type: string;  // "contract", "product", "domain"
  enabled: boolean;
  filter_source?: string;
  filter_pattern?: string;
  key_pattern: string;
  value_extraction_source: string;  // "key" or "value"
  value_extraction_pattern: string;
}
```

### Frontend Component - Entity Patterns Field

**File**: `src/frontend/src/components/settings/entity-patterns-field.tsx` (new)

Specialized form component for entity discovery patterns:

- Tabbed interface with tabs for each entity type (Contract, Product, Domain, etc.)
- Each tab contains:
                - Enable/disable toggle for that entity type
                - Filter Pattern section (optional, collapsible):
                                - Source dropdown (Key/Value)
                                - Pattern input (regex)
                - Key Pattern input (regex, required)
                - Value Extraction section (required):
                                - Source dropdown (Key/Value)
                                - Pattern input (regex with capture group explanation)
                - Test/validate regex button with example input
- Validation for regex patterns
- Help text explaining pattern syntax

### Frontend Component - Configuration Dialog

**File**: `src/frontend/src/components/settings/workflow-configuration-dialog.tsx` (new)

Dynamic form component:

- Fetches parameter definitions for selected workflow
- Renders appropriate form fields based on parameter types:
                - `string`: Input field with optional regex validation
                - `integer`: Number input with optional min/max
                - `boolean`: Switch/Checkbox
                - `select`: Dropdown with predefined options
                - `entity_patterns`: EntityPatternsField component
- Validation based on constraints (required, min/max, pattern)
- Save/Cancel buttons
- Display validation errors

### Jobs Settings UI Updates

**File**: `src/frontend/src/components/settings/jobs-settings.tsx`

Add "Configure" gear icon button next to each workflow:

- Only shown if workflow has `configurable_parameters` defined in YAML
- Opens WorkflowConfigurationDialog when clicked
- Badge/indicator showing configuration status (Configured/Not Configured)
- Tooltip: "Configure workflow parameters"

## Part 2: UC Bulk Import Workflow

### Workflow YAML

**File**: `src/backend/src/workflows/uc_bulk_import/uc_bulk_import.yaml`

```yaml
name: "UC Bulk Import"
description: "Import Contracts, Products, and Domains from Unity Catalog tags"
format: "MULTI_TASK"
tasks:
 - task_key: "uc_bulk_import"
    spark_python_task:
      python_file: "uc_bulk_import.py"

schedule:
  quartz_cron_expression: "0 0 2 * * ?"  # Daily at 2 AM
  timezone_id: "UTC"
  pause_status: "PAUSED"

# Standard runtime parameters
parameters:
  dry_run: "false"
  verbose: "true"

# Configurable parameters (managed via UI)
configurable_parameters:
 - name: "entity_patterns"
    type: "entity_patterns"
    description: "Tag patterns for discovering and importing entities from Unity Catalog"
    required: true
    entity_types: ["contract", "product", "domain"]
    default:
   - entity_type: "contract"
        enabled: true
        key_pattern: "^data-contract-(.+)$"
        value_extraction_source: "key"
        value_extraction_pattern: "^data-contract-(.+)$"
   - entity_type: "product"
        enabled: true
        key_pattern: "^data-product-(.+)$"
        value_extraction_source: "key"
        value_extraction_pattern: "^data-product-(.+)$"
   - entity_type: "domain"
        enabled: true
        key_pattern: "^data-domain-(.+)$"
        value_extraction_source: "key"
        value_extraction_pattern: "^data-domain-(.+)$"
  
 - name: "default_catalog"
    type: "string"
    description: "Default catalog for unqualified table names"
    required: false
    default: null
  
 - name: "default_schema"
    type: "string"
    description: "Default schema for unqualified table names"
    required: false
    default: null
  
 - name: "conflict_strategy"
    type: "select"
    description: "How to handle existing entities with same name"
    required: true
    default: "skip"
    options: ["skip", "update", "error"]

timeout_seconds: 7200
max_concurrent_runs: 1

tags:
  environment: "production"
  team: "data_governance"
  workflow_type: "import"
  owner: "ontos"
```

### Workflow Python Script

**File**: `src/backend/src/workflows/uc_bulk_import/uc_bulk_import.py`

Implementation structure:

```python
import argparse
import json
import re
import sys
import os
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
from uuid import uuid4

from sqlalchemy import text
from databricks.sdk import WorkspaceClient

# Import shared utilities
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'shared'))
from db import create_engine_from_env

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--entity_patterns", type=str, required=True)  # JSON
    parser.add_argument("--default_catalog", type=str, default=None)
    parser.add_argument("--default_schema", type=str, default=None)
    parser.add_argument("--conflict_strategy", type=str, default="skip")
    parser.add_argument("--dry_run", type=str, default="false")
    parser.add_argument("--verbose", type=str, default="false")
    args = parser.parse_args()
    
    entity_patterns = json.loads(args.entity_patterns)
    dry_run = args.dry_run.lower() == "true"
    verbose = args.verbose.lower() == "true"
    
    ws = WorkspaceClient()
    engine = create_engine_from_env()
    
    results = bulk_import(
        ws=ws,
        engine=engine,
        entity_patterns=entity_patterns,
        default_catalog=args.default_catalog,
        default_schema=args.default_schema,
        conflict_strategy=args.conflict_strategy,
        dry_run=dry_run,
        verbose=verbose
    )
    
    print(json.dumps(results))

def bulk_import(ws, engine, entity_patterns, default_catalog, default_schema, conflict_strategy, dry_run, verbose):
    """
    Main import logic:
  1. Scan UC tags for all enabled entity types
  2. Apply filters and extract entity names
  3. Group objects by entity type and name
  4. Create database records per conflict strategy
  5. Return summary statistics
    """
    stats = {
        "contracts": {"discovered": 0, "created": 0, "skipped": 0, "errors": 0},
        "products": {"discovered": 0, "created": 0, "skipped": 0, "errors": 0},
        "domains": {"discovered": 0, "created": 0, "skipped": 0, "errors": 0},
    }
    
    # Process each enabled entity type
    for pattern_config in entity_patterns:
        if not pattern_config.get("enabled", False):
            continue
        
        entity_type = pattern_config["entity_type"]
        print(f"Processing {entity_type} patterns...")
        
        # Scan and extract
        matched_objects = scan_and_extract(ws, pattern_config, default_catalog, default_schema)
        stats[entity_type + "s"]["discovered"] = len(matched_objects)
        
        # Create entities
        if entity_type == "contract":
            result = create_contracts(engine, matched_objects, conflict_strategy, dry_run)
        elif entity_type == "product":
            result = create_products(engine, matched_objects, conflict_strategy, dry_run)
        elif entity_type == "domain":
            result = create_domains(engine, matched_objects, conflict_strategy, dry_run)
        
        stats[entity_type + "s"].update(result)
    
    # Link products to contracts where both exist on same object
    link_products_to_contracts(engine, dry_run)
    
    return stats

# Key functions:
# - scan_and_extract(ws, pattern_config, default_cat, default_sch)
# - apply_filter(obj, filter_config)
# - extract_name(tag_key, tag_value, extraction_config)
# - create_contracts(engine, objects, strategy, dry_run)
# - create_products(engine, objects, strategy, dry_run)
# - create_domains(engine, objects, strategy, dry_run)
# - link_products_to_contracts(engine, dry_run)
```

### Workflow Directory Structure

```
src/backend/src/workflows/uc_bulk_import/
├── uc_bulk_import.py
└── uc_bulk_import.yaml
```

## Part 3: UC Bulk Export Workflow (Placeholder)

### Workflow YAML

**File**: `src/backend/src/workflows/uc_bulk_export/uc_bulk_export.yaml`

```yaml
name: "UC Bulk Export"
description: "Tag Unity Catalog resources with Contract, Product, and Domain metadata from app"
format: "MULTI_TASK"
tasks:
 - task_key: "uc_bulk_export"
    spark_python_task:
      python_file: "uc_bulk_export.py"

schedule:
  quartz_cron_expression: "0 0 3 * * ?"  # Daily at 3 AM (after import)
  timezone_id: "UTC"
  pause_status: "PAUSED"

parameters:
  dry_run: "false"
  verbose: "true"

configurable_parameters:
 - name: "entity_types"
    type: "select"
    description: "Which entity types to export as tags"
    required: true
    default: ["contract", "product", "domain"]
    options: ["contract", "product", "domain"]
  
 - name: "tag_prefix"
    type: "string"
    description: "Prefix for generated tags (e.g., 'x-ontos-')"
    required: true
    default: "x-ontos-"
  
 - name: "overwrite_existing"
    type: "boolean"
    description: "Overwrite existing tags if present"
    required: true
    default: false

timeout_seconds: 7200
max_concurrent_runs: 1

tags:
  environment: "production"
  team: "data_governance"
  workflow_type: "export"
  owner: "ontos"
```

**Note**: Python implementation deferred to future work, but YAML structure defined.

## Part 4: Documentation

### Job Configuration System Documentation

**File**: `src/docs/jobs/README.md` (update or create)

Overview of all job documentation and links.

**File**: `src/docs/jobs/job-configuration-system.md` (new)

Document the generic configuration system:

- Purpose and architecture
- How to define `configurable_parameters` in workflow YAML
- Supported parameter types and their constraints
- How to configure workflows in the Settings UI
- How configurations are stored and passed to jobs at runtime
- Examples for each parameter type

### UC Bulk Import Documentation

**File**: `src/docs/jobs/uc-bulk-import.md` (new)

Comprehensive guide:

1. **Overview**

                        - Purpose: Discover and import entities from UC tags
                        - Supported entity types: Contracts, Products, Domains
                        - When to use this workflow

2. **Configuration**

                        - Accessing configuration dialog in Jobs tab
                        - Entity Patterns configuration:
                                        - Per-entity enable/disable
                                        - Filter patterns (optional, for scoping)
                                        - Key patterns (regex to match tag keys)
                                        - Value extraction (source and pattern)
                        - Default catalog/schema settings
                        - Conflict strategy options

3. **Pattern Syntax**

                        - Regex primer for non-experts
                        - Capture groups explanation
                        - Common patterns:
                                        - Key-based: `data-contract-ABC` → extract "ABC"
                                        - Value-based: `contract:ABC` → extract "ABC"
                                        - Complex patterns with prefixes/suffixes

4. **Discovery Process**

                        - Step-by-step workflow execution
                        - How UC tags are scanned (information_schema queries)
                        - Filter application and inheritance
                        - Name extraction from matched tags
                        - Grouping objects by entity and name
                        - Record creation logic

5. **Conflict Resolution**

                        - Skip: Ignore if entity name exists (default)
                        - Update: Overwrite existing entity
                        - Error: Fail job if conflict found

6. **Running the Job**

                        - Enabling in Settings > Jobs tab
                        - Configuring patterns
                        - Manual trigger vs scheduled execution
                        - Monitoring run history and logs

7. **Examples**

                        - Example 1: Simple key-based contract discovery
                        - Example 2: Value-based product discovery with filters
                        - Example 3: Multi-entity import with linking
                        - Example 4: Domain discovery from schema tags

8. **Troubleshooting**

                        - Common regex mistakes
                        - Pattern testing strategies
                        - Dry-run mode usage
                        - Log analysis
                        - Handling duplicate names

### UC Bulk Export Documentation (Placeholder)

**File**: `src/docs/jobs/uc-bulk-export.md` (stub)

Placeholder documentation noting future implementation.

## Implementation Order

### Phase 1: Generic Job Configuration System

1. Create `workflow_configurations` database table
2. Create backend Pydantic models for configuration
3. Create repository for configuration CRUD
4. Update JobsManager to parse `configurable_parameters` and manage configs
5. Add API routes for configuration management
6. Create frontend TypeScript types
7. Create `entity-patterns-field.tsx` component
8. Create `workflow-configuration-dialog.tsx` component
9. Update `jobs-settings.tsx` with Configure button
10. Write job configuration system documentation

### Phase 2: UC Bulk Import Workflow

11. Create workflow directory structure
12. Write `uc_bulk_import.yaml` with entity_patterns configuration
13. Implement `uc_bulk_import.py`:

                                - UC tag scanning (information_schema queries)
                                - Pattern matching and filtering
                                - Entity name extraction
                                - Contract creation with schema objects
                                - Product creation with output ports
                                - Domain creation
                                - Product-to-contract linking

14. Write comprehensive `uc-bulk-import.md` documentation

### Phase 3: UC Bulk Export Workflow (Placeholder)

15. Create workflow directory structure
16. Write `uc_bulk_export.yaml` with configuration
17. Create stub Python file (implementation deferred)
18. Write placeholder documentation

### Phase 4: Testing and Validation

19. Unit tests for pattern matching logic
20. Integration test: Configure patterns → Run import → Verify entities created
21. Test conflict strategies (skip/update/error)
22. Test multi-entity import with linking
23. Test filter patterns with inheritance

## Key Design Decisions

- **Generic configuration system**: Any workflow can declare configurable parameters in YAML, not tied to specific settings tables
- **YAML-driven UI**: Configuration forms dynamically generated from parameter definitions
- **Entity-specific patterns**: Each entity type (Contract, Product, Domain) has independent configuration
- **Extensible**: Easy to add new entity types (teams, projects, etc.) in future
- **Conflict strategies**: User controls handling of duplicate names (skip/update/error)
- **Filter inheritance**: Schema-level filter tags apply to child tables
- **Minimal record creation**: Only required fields populated, manual enrichment expected
- **Bidirectional sync**: Import (UC→App) now, Export (App→UC) later
- **Database storage**: Configurations persisted per workflow, loaded at job runtime