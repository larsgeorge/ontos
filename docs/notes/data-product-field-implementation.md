# Data Product Field Implementation

## Overview
This document explains the implementation of hiding the `dataProduct` field from the UI while maintaining ODCS compliance through auto-population on export.

## Problem Statement
The ODCS v3.0.2 standard includes a `dataProduct` field (simple string), but our application uses a more sophisticated relational model where:
- Data Products have **Output Ports**
- Output Ports link to Data Contracts via `contract_id` (proper FK relationship)

Showing the `dataProduct` field in the UI created confusion since users might:
1. Enter a product name that doesn't match the actual linked product
2. Not understand the relationship with Output Ports
3. Have inconsistent data between the string field and the actual relationships

## Solution Architecture

### 1. Database Schema
- **KEPT**: `data_contracts.data_product` column (for backward compatibility and ODCS import)
- **PRIMARY**: `output_ports.contract_id` → `data_contracts.id` FK (source of truth)

### 2. UI Changes
**Removed** the "Data Product" field from:
- `src/frontend/src/components/data-contracts/data-contract-basic-form-dialog.tsx`
- `src/frontend/src/views/data-contract-details.tsx` (edit flow)

Users now link contracts to products via the proper Output Port mechanism.

### 3. Backend Export Logic
**Modified**: `build_odcs_from_db()` in `src/backend/src/controller/data_contracts_manager.py`

On ODCS YAML export, the `dataProduct` field is now auto-populated by:
1. Querying for Data Products with Output Ports linked to this contract
2. Using the first linked product's name
3. Falling back to stored value if no linked product found (backward compatibility)

```python
# Auto-populate dataProduct from linked output ports in Data Products
if db_session is not None:
    try:
        from src.db_models.data_products import DataProductDb, OutputPortDb
        linked_product = (
            db_session.query(DataProductDb)
            .join(OutputPortDb, OutputPortDb.product_id == DataProductDb.id)
            .filter(OutputPortDb.contract_id == db_obj.id)
            .first()
        )
        if linked_product:
            odcs['dataProduct'] = linked_product.name
        elif db_obj.data_product:
            odcs['dataProduct'] = db_obj.data_product
    except Exception as e:
        logger.warning(f"Failed to auto-populate dataProduct: {e}")
```

### 4. Import Handling
**KEPT**: `create_from_upload()` continues to store the `dataProduct` string from imported ODCS contracts.

This preserves the value for reference, but the actual operational linkage is via Output Ports.

## Benefits

### For Users
- **Clearer UX**: No confusion about which field controls product linkage
- **Data Integrity**: Single source of truth (Output Ports)
- **Proper Relationships**: Uses the relational model as designed

### For Compliance
- **ODCS Compatible**: Exported YAML includes the `dataProduct` field as required
- **Dynamic Export**: Field is populated based on actual relationships, not stale data
- **Backward Compatible**: Can still import and store ODCS contracts with `dataProduct` string

### For Development
- **Maintainable**: Clear separation between UI model and export format
- **Extensible**: Easy to support multiple products per contract (via multiple ports)
- **Robust**: Fallback handling for edge cases

## Data Flow

### Creating a Contract
1. User creates contract (no `dataProduct` field shown)
2. User creates/links to Data Product with Output Port
3. Output Port references contract via `contract_id` FK
4. **Relationship established via relational model**

### Exporting to ODCS YAML
1. Export endpoint calls `build_odcs_from_db()`
2. Query finds linked Data Product via Output Port
3. Product name auto-populates `dataProduct` field
4. YAML file includes ODCS-compliant `dataProduct` field

### Importing from ODCS YAML
1. Parser reads `dataProduct` string value
2. Stored in `data_product` column for reference
3. User can later create proper Output Port linkage
4. On next export, uses actual linkage (not stored string)

## Migration Notes

### Existing Data
No migration needed. Existing contracts with `data_product` values:
- Continue to work
- Export will use linked product if available
- Fall back to stored value if no linkage exists

### Testing Scenarios
1. ✅ Create new contract without `dataProduct` field
2. ✅ Link contract to product via Output Port
3. ✅ Export contract to ODCS YAML (should include `dataProduct`)
4. ✅ Import ODCS YAML with `dataProduct` (should store value)
5. ✅ Edit existing contract (field not shown)

## Related Files

### Frontend
- `src/frontend/src/components/data-contracts/data-contract-basic-form-dialog.tsx`
- `src/frontend/src/views/data-contract-details.tsx`

### Backend
- `src/backend/src/controller/data_contracts_manager.py`
- `src/backend/src/db_models/data_contracts.py` (schema unchanged)
- `src/backend/src/models/data_contracts_api.py` (API model unchanged)
- `src/backend/src/routes/data_contracts_routes.py` (export endpoint)

### Database
- `data_contracts.data_product` - String field (kept for compatibility)
- `output_ports.contract_id` - FK to contracts (source of truth)

## Future Enhancements

### Multiple Products per Contract
Current implementation uses `first()` to select one product. Could be enhanced to:
- Support comma-separated list of product names
- Create array field in ODCS export
- Show all linked products in UI (read-only)

### UI Display
Consider adding a "Linked Products" section in contract details:
- Shows all Data Products with ports linking to this contract
- Read-only display based on query
- Provides visibility into the relationship

### Validation
Add validation to warn users if:
- Contract has no linked products (orphaned)
- Stored `dataProduct` string doesn't match any linked product name
- Contract is linked to multiple products (potential ambiguity)

## Implementation Date
2025-11-12

## Authors
- Claude (AI Assistant)
- Lars George (Product Owner)

