# Authoritative Definitions Implementation - Completion Guide

## Status: Model Refactoring Complete ✅, API Models Complete ✅, Implementation Pending

### Completed
- ✅ Model refactoring (renamed 3 DB models to match ODCS terminology)
  - `DataContractAuthorityDb` → `DataContractAuthoritativeDefinitionDb`
  - `SchemaObjectAuthorityDb` → `SchemaObjectAuthoritativeDefinitionDb`
  - `SchemaPropertyAuthorityDb` → `SchemaPropertyAuthoritativeDefinitionDb`
- ✅ API models created (universal for all 3 levels)
  - `AuthoritativeDefinitionCreate`, `AuthoritativeDefinitionUpdate`, `AuthoritativeDefinitionRead`

### Remaining Work

## 1. Backend Implementation (3 Repositories + 12 Endpoints)

### Repository Implementation

Create 3 repository classes in `data_contracts_repository.py`:

#### Contract-Level Repository

```python
# ===== Contract Authoritative Definition Repository =====
class ContractAuthoritativeDefinitionRepository(CRUDBase[DataContractAuthoritativeDefinitionDb, Dict[str, Any], DataContractAuthoritativeDefinitionDb]):
    def __init__(self):
        super().__init__(DataContractAuthoritativeDefinitionDb)

    def get_by_contract(self, db: Session, *, contract_id: str) -> List[DataContractAuthoritativeDefinitionDb]:
        """Get all authoritative definitions for a contract."""
        try:
            return db.query(self.model).filter(self.model.contract_id == contract_id).all()
        except Exception as e:
            logger.error(f"Error fetching contract authoritative definitions: {e}", exc_info=True)
            db.rollback()
            raise

    def create_definition(self, db: Session, *, contract_id: str, url: str, type: str) -> DataContractAuthoritativeDefinitionDb:
        """Create an authoritative definition for a contract."""
        try:
            definition = DataContractAuthoritativeDefinitionDb(contract_id=contract_id, url=url, type=type)
            db.add(definition)
            db.flush()
            db.refresh(definition)
            return definition
        except Exception as e:
            logger.error(f"Error creating contract authoritative definition: {e}", exc_info=True)
            db.rollback()
            raise

    def update_definition(self, db: Session, *, definition_id: str, url: Optional[str] = None, type: Optional[str] = None) -> Optional[DataContractAuthoritativeDefinitionDb]:
        """Update an authoritative definition."""
        try:
            definition = db.query(self.model).filter(self.model.id == definition_id).first()
            if not definition:
                return None
            if url is not None:
                definition.url = url
            if type is not None:
                definition.type = type
            db.flush()
            db.refresh(definition)
            return definition
        except Exception as e:
            logger.error(f"Error updating contract authoritative definition: {e}", exc_info=True)
            db.rollback()
            raise

    def delete_definition(self, db: Session, *, definition_id: str) -> bool:
        """Delete an authoritative definition."""
        try:
            definition = db.query(self.model).filter(self.model.id == definition_id).first()
            if not definition:
                return False
            db.delete(definition)
            db.flush()
            return True
        except Exception as e:
            logger.error(f"Error deleting contract authoritative definition: {e}", exc_info=True)
            db.rollback()
            raise

contract_authoritative_definition_repo = ContractAuthoritativeDefinitionRepository()
```

#### Schema-Level Repository

Follow the same pattern, replacing:
- Model: `SchemaObjectAuthoritativeDefinitionDb`
- Foreign key field: `schema_object_id` instead of `contract_id`
- Method prefix: `schema` instead of `contract`

```python
# Similar structure with schema_object_id and SchemaObjectAuthoritativeDefinitionDb
schema_authoritative_definition_repo = SchemaAuthoritativeDefinitionRepository()
```

#### Property-Level Repository

Follow the same pattern, replacing:
- Model: `SchemaPropertyAuthoritativeDefinitionDb`
- Foreign key field: `property_id` instead of `contract_id`
- Method prefix: `property` instead of `contract`

```python
# Similar structure with property_id and SchemaPropertyAuthoritativeDefinitionDb
property_authoritative_definition_repo = PropertyAuthoritativeDefinitionRepository()
```

### Routes Implementation (12 Endpoints Total)

Add to `data_contracts_routes.py` after Roles endpoints:

#### Contract-Level Endpoints (4)

```python
# ===== Contract-Level Authoritative Definitions CRUD =====

@router.get('/data-contracts/{contract_id}/authoritative-definitions', response_model=List[dict])
async def get_contract_authoritative_definitions(
    contract_id: str,
    db: DBSessionDep,
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_ONLY))
):
    """Get all authoritative definitions for a contract."""
    from src.repositories.data_contracts_repository import contract_authoritative_definition_repo
    from src.models.data_contracts_api import AuthoritativeDefinitionRead

    contract = data_contract_repo.get(db, id=contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    try:
        definitions = contract_authoritative_definition_repo.get_by_contract(db=db, contract_id=contract_id)
        return [AuthoritativeDefinitionRead.model_validate(d).model_dump() for d in definitions]
    except Exception as e:
        logger.error(f"Error fetching contract authoritative definitions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/data-contracts/{contract_id}/authoritative-definitions', response_model=dict, status_code=201)
async def create_contract_authoritative_definition(
    contract_id: str,
    request: Request,
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    current_user: AuditCurrentUserDep,
    definition_data: dict = Body(...),
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_WRITE))
):
    """Create an authoritative definition for a contract."""
    from src.repositories.data_contracts_repository import contract_authoritative_definition_repo
    from src.models.data_contracts_api import AuthoritativeDefinitionCreate, AuthoritativeDefinitionRead

    contract = data_contract_repo.get(db, id=contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    try:
        definition_create = AuthoritativeDefinitionCreate(**definition_data)
        new_definition = contract_authoritative_definition_repo.create_definition(
            db=db, contract_id=contract_id, url=definition_create.url, type=definition_create.type
        )
        db.commit()

        await audit_manager.log_event(
            db=db, user_email=current_user, entity_type="data_contract", entity_id=contract_id,
            action="CREATE_AUTHORITATIVE_DEFINITION", success=True,
            details={"definition_id": new_definition.id, "url": new_definition.url}
        )

        return AuthoritativeDefinitionRead.model_validate(new_definition).model_dump()
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating contract authoritative definition: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put('/data-contracts/{contract_id}/authoritative-definitions/{definition_id}', response_model=dict)
async def update_contract_authoritative_definition(...):
    """Update an authoritative definition (similar pattern to POST)."""
    # Implementation follows same pattern as other update endpoints


@router.delete('/data-contracts/{contract_id}/authoritative-definitions/{definition_id}', status_code=204)
async def delete_contract_authoritative_definition(...):
    """Delete an authoritative definition (similar pattern to other deletes)."""
    # Implementation follows same pattern as other delete endpoints
```

#### Schema-Level Endpoints (4)

```python
# ===== Schema-Level Authoritative Definitions CRUD =====

@router.get('/data-contracts/{contract_id}/schemas/{schema_id}/authoritative-definitions', response_model=List[dict])
async def get_schema_authoritative_definitions(...):
    """Get all authoritative definitions for a schema object."""
    # Similar to contract-level, using schema_authoritative_definition_repo

@router.post('/data-contracts/{contract_id}/schemas/{schema_id}/authoritative-definitions', response_model=dict, status_code=201)
async def create_schema_authoritative_definition(...):
    """Create an authoritative definition for a schema object."""
    # Similar to contract-level

@router.put('/data-contracts/{contract_id}/schemas/{schema_id}/authoritative-definitions/{definition_id}', response_model=dict)
async def update_schema_authoritative_definition(...):
    """Update an authoritative definition for a schema object."""
    # Similar to contract-level

@router.delete('/data-contracts/{contract_id}/schemas/{schema_id}/authoritative-definitions/{definition_id}', status_code=204)
async def delete_schema_authoritative_definition(...):
    """Delete an authoritative definition for a schema object."""
    # Similar to contract-level
```

#### Property-Level Endpoints (4)

```python
# ===== Property-Level Authoritative Definitions CRUD =====

@router.get('/data-contracts/{contract_id}/schemas/{schema_id}/properties/{property_id}/authoritative-definitions', response_model=List[dict])
async def get_property_authoritative_definitions(...):
    """Get all authoritative definitions for a schema property."""
    # Similar to contract-level, using property_authoritative_definition_repo

@router.post('/data-contracts/{contract_id}/schemas/{schema_id}/properties/{property_id}/authoritative-definitions', response_model=dict, status_code=201)
async def create_property_authoritative_definition(...):
    """Create an authoritative definition for a schema property."""
    # Similar to contract-level

@router.put('/data-contracts/{contract_id}/schemas/{schema_id}/properties/{property_id}/authoritative-definitions/{definition_id}', response_model=dict)
async def update_property_authoritative_definition(...):
    """Update an authoritative definition for a schema property."""
    # Similar to contract-level

@router.delete('/data-contracts/{contract_id}/schemas/{schema_id}/properties/{property_id}/authoritative-definitions/{definition_id}', status_code=204)
async def delete_property_authoritative_definition(...):
    """Delete an authoritative definition for a schema property."""
    # Similar to contract-level
```

## 2. Frontend Implementation

### Reusable Form Component

Create `authoritative-definition-form-dialog.tsx`:

```typescript
import { useEffect, useState } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useToast } from '@/hooks/use-toast'

type AuthoritativeDefinition = {
  id?: string
  url: string
  type: string
}

type AuthoritativeDefinitionFormProps = {
  isOpen: boolean
  onOpenChange: (open: boolean) => void
  onSubmit: (definition: AuthoritativeDefinition) => Promise<void>
  initial?: AuthoritativeDefinition
  level: 'contract' | 'schema' | 'property'  // Context indicator
}

export default function AuthoritativeDefinitionFormDialog({
  isOpen, onOpenChange, onSubmit, initial, level
}: AuthoritativeDefinitionFormProps) {
  const { toast } = useToast()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [url, setUrl] = useState('')
  const [type, setType] = useState('')

  useEffect(() => {
    if (isOpen && initial) {
      setUrl(initial.url || '')
      setType(initial.type || '')
    } else if (isOpen && !initial) {
      setUrl('')
      setType('')
    }
  }, [isOpen, initial])

  const handleSubmit = async () => {
    if (!url.trim()) {
      toast({ title: 'Validation Error', description: 'URL is required', variant: 'destructive' })
      return
    }
    if (!type.trim()) {
      toast({ title: 'Validation Error', description: 'Type is required', variant: 'destructive' })
      return
    }

    // URL validation
    try {
      new URL(url.trim())
    } catch {
      toast({ title: 'Validation Error', description: 'Please enter a valid URL', variant: 'destructive' })
      return
    }

    setIsSubmitting(true)
    try {
      const definition: AuthoritativeDefinition = {
        url: url.trim(),
        type: type.trim(),
      }

      await onSubmit(definition)
      onOpenChange(false)
      toast({
        title: 'Success',
        description: initial ? 'Authoritative definition updated' : 'Authoritative definition created'
      })
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error?.message || 'Failed to save authoritative definition',
        variant: 'destructive',
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  const levelLabels = {
    contract: 'Contract',
    schema: 'Schema',
    property: 'Property'
  }

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{initial ? 'Edit' : 'Add'} Authoritative Definition</DialogTitle>
          <DialogDescription>
            {levelLabels[level]}-level authoritative source (ODCS compliant)
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* URL */}
          <div className="space-y-2">
            <Label htmlFor="url">
              URL <span className="text-destructive">*</span>
            </Label>
            <Input
              id="url"
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://glossary.example.com/term/123"
              autoFocus
            />
            <p className="text-xs text-muted-foreground">
              Full URL to the authoritative source
            </p>
          </div>

          {/* Type */}
          <div className="space-y-2">
            <Label htmlFor="type">
              Type <span className="text-destructive">*</span>
            </Label>
            <Input
              id="type"
              value={type}
              onChange={(e) => setType(e.target.value)}
              placeholder="e.g., glossary, standard, documentation"
              maxLength={255}
            />
            <p className="text-xs text-muted-foreground">
              Type of authoritative source
            </p>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={isSubmitting}>
            {isSubmitting ? 'Saving...' : initial ? 'Update' : 'Add'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
```

### UI Integration (3 Locations)

#### 1. Contract-Level Section

Add to `data-contract-details.tsx` (around line 1150):

```tsx
{/* Authoritative Definitions - Contract Level (ODCS) */}
<Card>
  <CardHeader>
    <div className="flex items-center justify-between">
      <div>
        <CardTitle className="text-xl">Authoritative Definitions ({contractAuthDefs.length})</CardTitle>
        <CardDescription>ODCS authoritative sources for this contract</CardDescription>
      </div>
      <Button size="sm" onClick={() => { setEditingContractAuthDefIndex(null); setIsContractAuthDefFormOpen(true); }}>
        <Plus className="h-4 w-4 mr-1.5" />
        Add Definition
      </Button>
    </div>
  </CardHeader>
  <CardContent>
    {/* Display list with Edit/Delete buttons */}
  </CardContent>
</Card>
```

#### 2. Schema-Level Integration

Add to schema display section (within schema tabs/cards):

```tsx
{/* Schema Authoritative Definitions */}
<div className="mt-4">
  <div className="flex items-center justify-between mb-2">
    <h4 className="text-sm font-semibold">Authoritative Definitions</h4>
    <Button size="sm" variant="outline" onClick={() => handleAddSchemaAuthDef(schema.id)}>
      <Plus className="h-3 w-3 mr-1" />
      Add
    </Button>
  </div>
  {/* Display list */}
</div>
```

#### 3. Property-Level Integration

Add to schema properties table (as a new column or expandable row):

```tsx
{/* In properties table */}
<TableCell>
  <Button
    size="sm"
    variant="ghost"
    onClick={() => handleManagePropertyAuthDefs(property.id)}
  >
    Defs ({property.authoritative_definitions?.length || 0})
  </Button>
</TableCell>
```

## Testing Checklist

### Contract-Level
- [ ] Create authoritative definition
- [ ] Edit authoritative definition
- [ ] Delete authoritative definition
- [ ] Verify URL validation
- [ ] Test with multiple definitions

### Schema-Level
- [ ] Create definition for schema
- [ ] Edit schema-level definition
- [ ] Delete schema-level definition
- [ ] Verify independent from contract-level

### Property-Level
- [ ] Create definition for property
- [ ] Edit property-level definition
- [ ] Delete property-level definition
- [ ] Verify cascade through nested properties

## File References

- DB Models: `src/backend/src/db_models/data_contracts.py` (lines 155-162, 358-365, 378-385)
- API Models: `src/backend/src/models/data_contracts_api.py` (lines 619-643)
- Repositories: `src/backend/src/repositories/data_contracts_repository.py` (to be added)
- Routes: `src/backend/src/routes/data_contracts_routes.py` (to be added, 12 endpoints)
- Form Dialog: `src/frontend/src/components/data-contracts/authoritative-definition-form-dialog.tsx` (to be created)
- Main View: `src/frontend/src/views/data-contract-details.tsx` (3 integration points)

## Additional Notes

- **3 Levels**: Contract, Schema, Property
- **12 Endpoints**: 3 levels × 4 operations (GET, POST, PUT, DELETE)
- **Shared Structure**: All levels have url + type fields
- **ODCS Field**: Maps to `authoritativeDefinitions[]` array at each level
- **Reusable Component**: Single form dialog with `level` prop
- **Independent Management**: Each level managed separately
- **Cascade Delete**: DB cascade handles cleanup
