# Job Configuration System

## Overview

The **Job Configuration System** provides a flexible, YAML-driven approach for managing workflow-specific parameters through the Ontos UI. Workflows declare configurable parameters in their YAML files, and users can configure these parameters via a dynamic configuration dialog without modifying code.

## Architecture

### Components

1. **YAML Declaration**: Workflows define `configurable_parameters` in their YAML files
2. **Database Storage**: Configurations stored in `workflow_configurations` table
3. **Backend API**: RESTful endpoints for parameter definitions and configuration CRUD
4. **Frontend UI**: Dynamic form generation based on parameter definitions
5. **Runtime Merging**: Saved configurations merged with ad-hoc parameters when jobs run

### Data Flow

```
1. Workflow YAML → Parameter Definitions
                     ↓
2. UI Form Generation ← Parameter Definitions
                     ↓
3. User Configuration → Database Storage
                     ↓
4. Job Execution → Load Configuration → Merge Parameters → Run Job
```

## Defining Configurable Parameters

### YAML Structure

Add a `configurable_parameters` section to your workflow YAML:

```yaml
name: "My Workflow"
description: "Example workflow with configurable parameters"
format: "MULTI_TASK"
tasks:
  - task_key: "my_task"
    spark_python_task:
      python_file: "my_script.py"

# Standard runtime parameters (can be overridden by configuration)
parameters:
  dry_run: "false"
  verbose: "true"

# Configurable parameters (managed via UI)
configurable_parameters:
  - name: "string_param"
    type: "string"
    description: "A string parameter"
    required: true
    default: "default_value"
    pattern: "^[a-zA-Z0-9_]+$"  # Optional regex validation
  
  - name: "integer_param"
    type: "integer"
    description: "An integer parameter"
    required: false
    default: 100
    min_value: 0
    max_value: 1000
  
  - name: "boolean_param"
    type: "boolean"
    description: "A boolean flag"
    default: false
  
  - name: "select_param"
    type: "select"
    description: "Choose an option"
    required: true
    default: "option1"
    options: ["option1", "option2", "option3"]
  
  - name: "entity_patterns"
    type: "entity_patterns"
    description: "Entity discovery patterns"
    required: true
    entity_types: ["contract", "product", "domain"]
    default:
      - entity_type: "contract"
        enabled: true
        key_pattern: "^data-contract-(.+)$"
        value_extraction_source: "key"
        value_extraction_pattern: "^data-contract-(.+)$"
```

### Parameter Types

#### string

Simple text input field.

**Constraints:**
- `pattern`: Regex validation pattern
- `required`: Whether field is mandatory

**Example:**
```yaml
- name: "catalog_name"
  type: "string"
  description: "Unity Catalog name"
  required: true
  default: "main"
  pattern: "^[a-z0-9_]+$"
```

#### integer

Numeric input field for integers.

**Constraints:**
- `min_value`: Minimum allowed value
- `max_value`: Maximum allowed value
- `required`: Whether field is mandatory

**Example:**
```yaml
- name: "batch_size"
  type: "integer"
  description: "Number of records per batch"
  default: 1000
  min_value: 1
  max_value: 10000
```

#### boolean

Toggle switch for true/false values.

**Example:**
```yaml
- name: "enable_caching"
  type: "boolean"
  description: "Enable result caching"
  default: true
```

#### select

Dropdown menu with predefined options.

**Constraints:**
- `options`: List of available choices (required)
- `required`: Whether selection is mandatory

**Example:**
```yaml
- name: "conflict_strategy"
  type: "select"
  description: "How to handle conflicts"
  required: true
  default: "skip"
  options: ["skip", "update", "error"]
```

#### entity_patterns

Specialized component for configuring entity discovery patterns (used in UC Bulk Import workflow).

**Constraints:**
- `entity_types`: List of entity types to configure (required)

**Structure:**
Each pattern includes:
- `entity_type`: String identifier
- `enabled`: Boolean toggle
- `filter_source`: "key" or "value" (optional)
- `filter_pattern`: Regex string (optional)
- `key_pattern`: Regex string (required)
- `value_extraction_source`: "key" or "value" (required)
- `value_extraction_pattern`: Regex with capture group (required)

**Example:**
```yaml
- name: "entity_patterns"
  type: "entity_patterns"
  description: "Tag patterns for entity discovery"
  entity_types: ["contract", "product"]
  default:
    - entity_type: "contract"
      enabled: true
      key_pattern: "^data-contract-(.+)$"
      value_extraction_source: "key"
      value_extraction_pattern: "^data-contract-(.+)$"
```

## Using the Configuration UI

### Accessing Configuration

1. Navigate to **Settings > Jobs** tab
2. Locate your workflow in the list
3. Click the **gear icon (⚙️)** next to the workflow name
4. Configuration dialog opens

**Note:** The gear icon only appears for workflows with `configurable_parameters` defined.

### Configuration Dialog

The dialog dynamically generates form fields based on the parameter definitions:

- **String fields**: Text input with optional validation
- **Integer fields**: Number input with min/max constraints
- **Boolean fields**: Toggle switches
- **Select fields**: Dropdown menus
- **Entity patterns**: Tabbed interface for multi-entity configuration

### Saving Configuration

1. Fill in parameter values
2. Click **Save Configuration**
3. Configuration persists in database
4. Configuration applies to all future job runs

### Validation

The UI validates inputs based on constraints:
- Required fields must be filled
- Integer values must be within min/max range
- String values must match regex patterns
- Select values must be from predefined options

Invalid configurations cannot be saved.

## Backend Implementation

### Database Schema

Configurations stored in `workflow_configurations` table:

```sql
CREATE TABLE workflow_configurations (
    id VARCHAR PRIMARY KEY,
    workflow_id VARCHAR UNIQUE NOT NULL,
    configuration TEXT NOT NULL,  -- JSON
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### API Endpoints

**Get Parameter Definitions:**
```
GET /api/jobs/workflows/{workflow_id}/parameter-definitions
```
Returns parameter schema from YAML file.

**Get Configuration:**
```
GET /api/jobs/workflows/{workflow_id}/configuration
```
Returns saved configuration for workflow.

**Update Configuration:**
```
PUT /api/jobs/workflows/{workflow_id}/configuration
Body: { "configuration": { "param1": "value1", ... } }
```
Saves configuration to database.

### JobsManager Methods

**Load Parameter Definitions:**
```python
definitions = jobs_manager.get_workflow_parameter_definitions(workflow_id)
```

**Load Configuration:**
```python
config = jobs_manager.get_workflow_configuration(workflow_id)
```

**Update Configuration:**
```python
jobs_manager.update_workflow_configuration(workflow_id, configuration)
```

**Merge Parameters:**
```python
merged_params = jobs_manager.get_merged_job_parameters(workflow_id, ad_hoc_params)
```

## Runtime Behavior

### Parameter Merging

When a job runs:

1. **Load saved configuration** from database
2. **Convert to strings** (Databricks jobs require string parameters)
   - Complex types (lists, dicts) serialized to JSON
   - Nulls converted to empty strings
3. **Merge with ad-hoc parameters** (ad-hoc takes precedence)
4. **Pass to Databricks job**

### Workflow Script Access

In your Python workflow script, access parameters via argparse:

```python
import argparse
import json

parser = argparse.ArgumentParser()
parser.add_argument("--string_param", type=str, required=True)
parser.add_argument("--integer_param", type=int, default=100)
parser.add_argument("--boolean_param", type=str, default="false")
parser.add_argument("--entity_patterns", type=str, required=True)
args = parser.parse_args()

# Parse boolean
enable_feature = args.boolean_param.lower() == "true"

# Parse JSON (for complex types)
entity_patterns = json.loads(args.entity_patterns)

# Use parameters
print(f"String param: {args.string_param}")
print(f"Integer param: {args.integer_param}")
print(f"Feature enabled: {enable_feature}")
```

## Best Practices

### Parameter Design

1. **Use defaults**: Provide sensible defaults for optional parameters
2. **Clear descriptions**: Explain what each parameter does and its impact
3. **Validate inputs**: Use constraints (min/max, patterns, options) to prevent invalid values
4. **Group related params**: Use consistent naming (e.g., `db_host`, `db_port`, `db_name`)

### Naming Conventions

- **Use snake_case**: `default_catalog`, not `defaultCatalog`
- **Be descriptive**: `max_retry_count`, not `retries`
- **Avoid abbreviations**: `source_database`, not `src_db`

### Default Values

- **Production-ready defaults**: Defaults should work out-of-the-box for most users
- **Safe defaults**: Prefer conservative values (e.g., smaller batch sizes)
- **Document defaults**: Explain why the default was chosen

### Complex Types

For lists and dictionaries:

- **Use entity_patterns type** for entity discovery patterns
- **Consider select type** for small lists of options
- **Document JSON structure** in description for custom JSON parameters

## Troubleshooting

### Configuration Not Showing

**Issue:** Gear icon doesn't appear for workflow

**Causes:**
- No `configurable_parameters` section in YAML
- YAML syntax error
- Workflow not refreshed after adding parameters

**Solutions:**
1. Verify `configurable_parameters` section exists
2. Validate YAML syntax
3. Reload Settings page to refresh workflow list

### Parameter Not Passed to Job

**Issue:** Job doesn't receive configured parameter value

**Causes:**
- Parameter name mismatch between YAML and script
- Configuration not saved before running job
- Parameter not defined in workflow YAML `parameters` section

**Solutions:**
1. Ensure parameter names match exactly (case-sensitive)
2. Save configuration and wait for confirmation
3. Add parameter to both `parameters` (for job) and `configurable_parameters` (for UI)

### Validation Errors

**Issue:** Cannot save configuration due to validation error

**Causes:**
- Required field empty
- Value outside min/max range
- String doesn't match regex pattern
- Invalid select option

**Solutions:**
1. Fill all required fields
2. Adjust values to meet constraints
3. Check regex pattern requirements
4. Choose from available select options

## Migration Guide

### Adding Configuration to Existing Workflow

1. **Add configurable_parameters section** to workflow YAML
2. **Define parameter schema** with types and constraints
3. **Update Python script** to accept parameters via argparse
4. **Test with defaults** before enabling in production
5. **Document parameters** for users

**Example Migration:**

Before:
```yaml
name: "My Workflow"
tasks:
  - task_key: "task1"
    spark_python_task:
      python_file: "script.py"
```

After:
```yaml
name: "My Workflow"
tasks:
  - task_key: "task1"
    spark_python_task:
      python_file: "script.py"

configurable_parameters:
  - name: "catalog"
    type: "string"
    description: "Target catalog"
    required: true
    default: "main"
```

### Versioning Considerations

- **Backwards compatibility**: Add new parameters as optional with defaults
- **Deprecated parameters**: Keep accepting but ignore in code
- **Breaking changes**: Document and notify users before deploying

## Examples

### Simple Configuration

Workflow with basic string and boolean parameters:

```yaml
configurable_parameters:
  - name: "target_catalog"
    type: "string"
    description: "Catalog to process"
    default: "main"
  
  - name: "dry_run"
    type: "boolean"
    description: "Preview changes without applying"
    default: true
```

### Advanced Configuration

Workflow with multiple parameter types and constraints:

```yaml
configurable_parameters:
  - name: "environment"
    type: "select"
    description: "Target environment"
    required: true
    options: ["dev", "staging", "prod"]
    default: "dev"
  
  - name: "batch_size"
    type: "integer"
    description: "Records per batch"
    default: 1000
    min_value: 100
    max_value: 10000
  
  - name: "table_pattern"
    type: "string"
    description: "Regex pattern for table names"
    pattern: "^[a-z0-9_]+$"
    default: ".*"
  
  - name: "enable_notifications"
    type: "boolean"
    description: "Send completion notifications"
    default: false
```

## Related Documentation

- [UC Bulk Import Workflow](./uc-bulk-import.md) - Example workflow using configuration system
- [Workflows Directory](../../backend/src/workflows/) - Workflow implementation examples
- [Jobs Settings UI](../../frontend/src/components/settings/jobs-settings.tsx) - Configuration UI code

