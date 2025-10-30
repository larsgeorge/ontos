# Roles Frontend Implementation - Remaining Work

## Status: Backend Complete ✅, Frontend Pending

### Completed
- ✅ Backend API models, repository, and routes
- ✅ Full CRUD operations with nested custom properties
- ✅ 4 REST endpoints (GET, POST, PUT, DELETE)
- ✅ 5 main fields + dynamic nested properties

### Remaining Work

## 1. Create RoleFormDialog Component

**Location:** `src/frontend/src/components/data-contracts/role-form-dialog.tsx` (new file)

**Pattern:** Follow `ServerConfigFormDialog` pattern for nested properties

```typescript
import { useEffect, useState } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { useToast } from '@/hooks/use-toast'
import { Plus, Trash2 } from 'lucide-react'

type RoleProperty = {
  property: string
  value?: string
}

type Role = {
  id?: string
  role: string
  description?: string
  access?: string
  first_level_approvers?: string
  second_level_approvers?: string
  custom_properties?: RoleProperty[]
}

type RoleFormProps = {
  isOpen: boolean
  onOpenChange: (open: boolean) => void
  onSubmit: (role: Role) => Promise<void>
  initial?: Role
}

export default function RoleFormDialog({ isOpen, onOpenChange, onSubmit, initial }: RoleFormProps) {
  const { toast } = useToast()
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Main fields
  const [role, setRole] = useState('')
  const [description, setDescription] = useState('')
  const [access, setAccess] = useState('')
  const [firstLevelApprovers, setFirstLevelApprovers] = useState('')
  const [secondLevelApprovers, setSecondLevelApprovers] = useState('')

  // Nested properties
  const [customProperties, setCustomProperties] = useState<RoleProperty[]>([])

  useEffect(() => {
    if (isOpen && initial) {
      setRole(initial.role || '')
      setDescription(initial.description || '')
      setAccess(initial.access || '')
      setFirstLevelApprovers(initial.first_level_approvers || '')
      setSecondLevelApprovers(initial.second_level_approvers || '')
      setCustomProperties(initial.custom_properties || [])
    } else if (isOpen && !initial) {
      setRole('')
      setDescription('')
      setAccess('')
      setFirstLevelApprovers('')
      setSecondLevelApprovers('')
      setCustomProperties([])
    }
  }, [isOpen, initial])

  const handleAddProperty = () => {
    setCustomProperties([...customProperties, { property: '', value: '' }])
  }

  const handleRemoveProperty = (index: number) => {
    setCustomProperties(customProperties.filter((_, i) => i !== index))
  }

  const handlePropertyChange = (index: number, field: 'property' | 'value', value: string) => {
    const updated = [...customProperties]
    updated[index][field] = value
    setCustomProperties(updated)
  }

  const handleSubmit = async () => {
    // Validation
    if (!role.trim()) {
      toast({ title: 'Validation Error', description: 'Role name is required', variant: 'destructive' })
      return
    }

    // Validate custom properties
    for (let i = 0; i < customProperties.length; i++) {
      if (!customProperties[i].property.trim()) {
        toast({
          title: 'Validation Error',
          description: `Property name is required for custom property ${i + 1}`,
          variant: 'destructive'
        })
        return
      }
    }

    setIsSubmitting(true)
    try {
      const roleData: Role = {
        role: role.trim(),
        description: description.trim() || undefined,
        access: access.trim() || undefined,
        first_level_approvers: firstLevelApprovers.trim() || undefined,
        second_level_approvers: secondLevelApprovers.trim() || undefined,
        custom_properties: customProperties.filter(p => p.property.trim())
      }

      await onSubmit(roleData)
      onOpenChange(false)
      toast({
        title: 'Success',
        description: initial ? 'Role updated successfully' : 'Role created successfully'
      })
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error?.message || 'Failed to save role',
        variant: 'destructive',
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{initial ? 'Edit Role' : 'Add Role'}</DialogTitle>
          <DialogDescription>
            {initial
              ? 'Update role information and custom properties'
              : 'Add a new role to this data contract (ODCS compliant)'}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Main Role Fields */}
          <div className="space-y-4">
            <h3 className="text-sm font-semibold">Role Information</h3>

            <div className="grid grid-cols-2 gap-4">
              {/* Role Name */}
              <div className="space-y-2">
                <Label htmlFor="role">
                  Role Name <span className="text-destructive">*</span>
                </Label>
                <Input
                  id="role"
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  placeholder="e.g., Data Steward, Consumer, Owner"
                  maxLength={255}
                  autoFocus
                />
              </div>

              {/* Access */}
              <div className="space-y-2">
                <Label htmlFor="access">Access Level</Label>
                <Input
                  id="access"
                  value={access}
                  onChange={(e) => setAccess(e.target.value)}
                  placeholder="e.g., READ, WRITE, ADMIN"
                  maxLength={255}
                />
              </div>
            </div>

            {/* Description */}
            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Describe this role and its responsibilities..."
                rows={3}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              {/* First Level Approvers */}
              <div className="space-y-2">
                <Label htmlFor="first_level_approvers">First-Level Approvers</Label>
                <Input
                  id="first_level_approvers"
                  value={firstLevelApprovers}
                  onChange={(e) => setFirstLevelApprovers(e.target.value)}
                  placeholder="Comma-separated emails or names"
                />
                <p className="text-xs text-muted-foreground">
                  e.g., john@example.com, jane@example.com
                </p>
              </div>

              {/* Second Level Approvers */}
              <div className="space-y-2">
                <Label htmlFor="second_level_approvers">Second-Level Approvers</Label>
                <Input
                  id="second_level_approvers"
                  value={secondLevelApprovers}
                  onChange={(e) => setSecondLevelApprovers(e.target.value)}
                  placeholder="Comma-separated emails or names"
                />
                <p className="text-xs text-muted-foreground">
                  e.g., manager@example.com
                </p>
              </div>
            </div>
          </div>

          {/* Custom Properties Section */}
          <div className="space-y-4 border-t pt-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold">Custom Properties</h3>
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={handleAddProperty}
              >
                <Plus className="h-4 w-4 mr-1.5" />
                Add Property
              </Button>
            </div>

            {customProperties.length > 0 ? (
              <div className="space-y-2">
                {customProperties.map((prop, index) => (
                  <div key={index} className="flex gap-2 items-start">
                    <div className="flex-1 grid grid-cols-2 gap-2">
                      <Input
                        placeholder="Property name"
                        value={prop.property}
                        onChange={(e) => handlePropertyChange(index, 'property', e.target.value)}
                        maxLength={255}
                      />
                      <Input
                        placeholder="Property value (optional)"
                        value={prop.value || ''}
                        onChange={(e) => handlePropertyChange(index, 'value', e.target.value)}
                      />
                    </div>
                    <Button
                      type="button"
                      size="icon"
                      variant="ghost"
                      className="text-destructive hover:text-destructive"
                      onClick={() => handleRemoveProperty(index)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground text-center py-4">
                No custom properties. Click "Add Property" to add key-value pairs.
              </p>
            )}
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

## 2. Add Role State Management to `data-contract-details.tsx`

**Location:** After line ~160 (after other dialog states)

```typescript
// Add to existing state declarations
const [isRoleFormOpen, setIsRoleFormOpen] = useState(false)
const [editingRoleIndex, setEditingRoleIndex] = useState<number | null>(null)
const [roles, setRoles] = useState<Array<{
  id: string
  role: string
  description?: string
  access?: string
  first_level_approvers?: string
  second_level_approvers?: string
  custom_properties?: Array<{ property: string; value?: string }>
}>>([]
```

## 3. Import RoleFormDialog

**Location:** Top of file with other imports (around line 28)

```typescript
import RoleFormDialog from '@/components/data-contracts/role-form-dialog'
```

## 4. Add Role Fetch Function

**Location:** Add to fetch functions (around line 270)

```typescript
const fetchRoles = async () => {
  if (!contractId) return
  try {
    const response = await fetch(`/api/data-contracts/${contractId}/roles`)
    if (response.ok) {
      const data = await response.json()
      setRoles(Array.isArray(data) ? data : [])
    } else {
      setRoles([])
    }
  } catch (e) {
    console.warn('Failed to fetch roles:', e)
    setRoles([])
  }
}
```

## 5. Call fetchRoles in useEffect

**Location:** In the main useEffect that calls fetchDetails (around line 260)

```typescript
useEffect(() => {
  if (contractId) {
    fetchDetails()
    fetchLinkedProducts()
    fetchContractTags()
    fetchSupportChannels()
    fetchPricing()
    fetchRoles()  // Add this line
    fetchLatestProfilingRun()
  }
}, [contractId])
```

## 6. Add Role CRUD Handlers

**Location:** Add after other handlers (around line 460)

```typescript
// Role handlers
const handleAddRole = async (role: any) => {
  if (!contractId) return
  try {
    const response = await fetch(`/api/data-contracts/${contractId}/roles`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(role)
    })

    if (!response.ok) {
      const errorData = await response.json()
      throw new Error(errorData.detail || 'Failed to create role')
    }

    await fetchRoles()
    toast({ title: 'Success', description: 'Role added successfully' })
  } catch (error: any) {
    toast({ title: 'Error', description: error.message, variant: 'destructive' })
    throw error
  }
}

const handleUpdateRole = async (role: any) => {
  if (!contractId || editingRoleIndex === null) return
  const roleToUpdate = roles[editingRoleIndex]

  try {
    const response = await fetch(`/api/data-contracts/${contractId}/roles/${roleToUpdate.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(role)
    })

    if (!response.ok) {
      const errorData = await response.json()
      throw new Error(errorData.detail || 'Failed to update role')
    }

    await fetchRoles()
    toast({ title: 'Success', description: 'Role updated successfully' })
  } catch (error: any) {
    toast({ title: 'Error', description: error.message, variant: 'destructive' })
    throw error
  }
}

const handleDeleteRole = async (index: number) => {
  if (!contractId) return
  const role = roles[index]

  if (!confirm(`Delete role "${role.role}"?`)) return

  try {
    const response = await fetch(`/api/data-contracts/${contractId}/roles/${role.id}`, {
      method: 'DELETE'
    })

    if (!response.ok) {
      throw new Error('Failed to delete role')
    }

    await fetchRoles()
    toast({ title: 'Success', description: 'Role deleted successfully' })
  } catch (error: any) {
    toast({ title: 'Error', description: error.message, variant: 'destructive' })
  }
}

const handleSubmitRole = async (role: any) => {
  if (editingRoleIndex !== null) {
    await handleUpdateRole(role)
  } else {
    await handleAddRole(role)
  }
}
```

## 7. Add Roles UI Section

**Location:** Add after Pricing or Team Members section (around line 1100)

```tsx
{/* Roles Section (ODCS Compliance) */}
<Card>
  <CardHeader>
    <div className="flex items-center justify-between">
      <div>
        <CardTitle className="text-xl">Roles ({roles.length})</CardTitle>
        <CardDescription>ODCS roles with access control and approvers</CardDescription>
      </div>
      <Button
        size="sm"
        onClick={() => {
          setEditingRoleIndex(null)
          setIsRoleFormOpen(true)
        }}
      >
        <Plus className="h-4 w-4 mr-1.5" />
        Add Role
      </Button>
    </div>
  </CardHeader>
  <CardContent>
    {roles && roles.length > 0 ? (
      <div className="space-y-3">
        {roles.map((role, idx) => (
          <div
            key={role.id}
            className="group relative border rounded-lg p-4 hover:bg-accent/50 transition-colors"
          >
            <div className="flex items-start justify-between">
              <div className="flex-1 space-y-2">
                {/* Role Header */}
                <div className="flex items-center gap-2">
                  <h4 className="font-semibold">{role.role}</h4>
                  {role.access && (
                    <Badge variant="secondary" className="text-xs">{role.access}</Badge>
                  )}
                </div>

                {/* Description */}
                {role.description && (
                  <p className="text-sm text-muted-foreground">{role.description}</p>
                )}

                {/* Approvers */}
                {(role.first_level_approvers || role.second_level_approvers) && (
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    {role.first_level_approvers && (
                      <div>
                        <span className="text-xs text-muted-foreground">1st Level:</span>
                        <p className="text-xs">{role.first_level_approvers}</p>
                      </div>
                    )}
                    {role.second_level_approvers && (
                      <div>
                        <span className="text-xs text-muted-foreground">2nd Level:</span>
                        <p className="text-xs">{role.second_level_approvers}</p>
                      </div>
                    )}
                  </div>
                )}

                {/* Custom Properties */}
                {role.custom_properties && role.custom_properties.length > 0 && (
                  <div className="mt-2 pt-2 border-t">
                    <p className="text-xs font-medium text-muted-foreground mb-1">Custom Properties:</p>
                    <div className="flex flex-wrap gap-2">
                      {role.custom_properties.map((prop, propIdx) => (
                        <Badge key={propIdx} variant="outline" className="text-xs">
                          {prop.property}: {prop.value || '(empty)'}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Actions */}
              <div className="opacity-0 group-hover:opacity-100 transition-opacity flex gap-1 ml-2">
                <Button
                  size="icon"
                  variant="ghost"
                  className="h-8 w-8"
                  onClick={() => {
                    setEditingRoleIndex(idx)
                    setIsRoleFormOpen(true)
                  }}
                >
                  <Pencil className="h-4 w-4" />
                </Button>
                <Button
                  size="icon"
                  variant="ghost"
                  className="h-8 w-8 text-destructive hover:text-destructive"
                  onClick={() => handleDeleteRole(idx)}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </div>
        ))}
      </div>
    ) : (
      <p className="text-sm text-muted-foreground text-center py-8">
        No roles defined. Click "Add Role" to add one.
      </p>
    )}
  </CardContent>
</Card>
```

## 8. Add RoleFormDialog Component

**Location:** Add at the end of the component, with other dialog components (around line 1380)

```tsx
{/* Role Form Dialog */}
<RoleFormDialog
  isOpen={isRoleFormOpen}
  onOpenChange={setIsRoleFormOpen}
  onSubmit={handleSubmitRole}
  initial={editingRoleIndex !== null ? roles[editingRoleIndex] : undefined}
/>
```

## Testing Checklist

- [ ] Create a new role with all main fields
- [ ] Create a role with only required field (role name)
- [ ] Add custom properties to a role (add/remove rows)
- [ ] Edit an existing role
- [ ] Update role's custom properties
- [ ] Delete a role
- [ ] Verify roles persist after page reload
- [ ] Check empty state displays correctly
- [ ] Test with 0, 1, 5, 10+ roles
- [ ] Verify nested properties display correctly
- [ ] Test approver fields with comma-separated values
- [ ] Check responsive layout on different screen sizes

## Integration Points

- Roles are fetched via `/api/data-contracts/{id}/roles`
- Roles include nested custom properties (loaded via eager loading)
- Custom properties are replaced entirely on update
- Cascade delete removes all nested properties automatically
- Can be used for access control verification (future feature)

## File References

- Backend: `src/backend/src/routes/data_contracts_routes.py` (lines 3466-3662)
- API Models: `src/backend/src/models/data_contracts_api.py` (lines 566-616)
- Repository: `src/backend/src/repositories/data_contracts_repository.py` (lines 454-591)
- Form Dialog: `src/frontend/src/components/data-contracts/role-form-dialog.tsx` (to be created)
- Main View: `src/frontend/src/views/data-contract-details.tsx` (needs integration)

## Additional Notes

- **Nested Structure**: Follows ServerConfigFormDialog pattern for dynamic properties
- **5 Main Fields**: role* (required), description, access, first_level_approvers, second_level_approvers
- **Dynamic Properties**: Add/remove custom key-value pairs
- **ODCS Field**: Maps to `roles[]` array in ODCS v3.0.2 specification
- **Display Format**: Card-based with collapsible custom properties
- **Validation**: Role name required, custom property names required if row added
- **Replace Strategy**: Custom properties are fully replaced on update (not merged)
