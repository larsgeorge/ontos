# Tags Frontend Implementation - Remaining Work

## Status: Backend Complete ✅, Frontend Partial

### Completed
- ✅ Backend API models, repository, and routes
- ✅ `TagFormDialog` component created
- ✅ All CRUD endpoints working

### Remaining Work

## 1. Add Tag State Management to `data-contract-details.tsx`

**Location:** After line ~160 (after other dialog states)

```typescript
// Add to existing state declarations
const [isTagFormOpen, setIsTagFormOpen] = useState(false)
const [editingTagIndex, setEditingTagIndex] = useState<number | null>(null)
const [contractTags, setContractTags] = useState<Array<{id: string, name: string}>>([])
```

## 2. Import TagFormDialog

**Location:** Top of file with other imports (around line 28)

```typescript
import TagFormDialog from '@/components/data-contracts/tag-form-dialog'
```

## 3. Add Tag Fetch Function

**Location:** Add to fetch functions (around line 270)

```typescript
const fetchContractTags = async () => {
  if (!contractId) return
  try {
    const response = await fetch(`/api/data-contracts/${contractId}/tags`)
    if (response.ok) {
      const data = await response.json()
      setContractTags(Array.isArray(data) ? data : [])
    } else {
      setContractTags([])
    }
  } catch (e) {
    console.warn('Failed to fetch contract tags:', e)
    setContractTags([])
  }
}
```

## 4. Call fetchContractTags in useEffect

**Location:** In the main useEffect that calls fetchDetails (around line 260)

```typescript
useEffect(() => {
  if (contractId) {
    fetchDetails()
    fetchLinkedProducts()
    fetchContractTags()  // Add this line
    fetchLatestProfilingRun()
  }
}, [contractId])
```

## 5. Add Tag CRUD Handlers

**Location:** Add after other handlers (around line 460)

```typescript
// Tag handlers
const handleAddTag = async (tag: { name: string }) => {
  if (!contractId) return
  try {
    const response = await fetch(`/api/data-contracts/${contractId}/tags`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(tag)
    })

    if (!response.ok) {
      const errorData = await response.json()
      throw new Error(errorData.detail || 'Failed to create tag')
    }

    await fetchContractTags()
    toast({ title: 'Success', description: 'Tag added successfully' })
  } catch (error: any) {
    toast({ title: 'Error', description: error.message, variant: 'destructive' })
    throw error
  }
}

const handleUpdateTag = async (tag: { name: string }) => {
  if (!contractId || editingTagIndex === null) return
  const tagToUpdate = contractTags[editingTagIndex]

  try {
    const response = await fetch(`/api/data-contracts/${contractId}/tags/${tagToUpdate.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(tag)
    })

    if (!response.ok) {
      const errorData = await response.json()
      throw new Error(errorData.detail || 'Failed to update tag')
    }

    await fetchContractTags()
    toast({ title: 'Success', description: 'Tag updated successfully' })
  } catch (error: any) {
    toast({ title: 'Error', description: error.message, variant: 'destructive' })
    throw error
  }
}

const handleDeleteTag = async (index: number) => {
  if (!contractId) return
  const tag = contractTags[index]

  if (!confirm(`Delete tag "${tag.name}"?`)) return

  try {
    const response = await fetch(`/api/data-contracts/${contractId}/tags/${tag.id}`, {
      method: 'DELETE'
    })

    if (!response.ok) {
      throw new Error('Failed to delete tag')
    }

    await fetchContractTags()
    toast({ title: 'Success', description: 'Tag deleted successfully' })
  } catch (error: any) {
    toast({ title: 'Error', description: error.message, variant: 'destructive' })
  }
}

const handleSubmitTag = async (tag: { name: string }) => {
  if (editingTagIndex !== null) {
    await handleUpdateTag(tag)
  } else {
    await handleAddTag(tag)
  }
}
```

## 6. Add Tags UI Section

**Location:** Insert BEFORE the Team Members section (before line 1182)

```tsx
{/* Tags Section (ODCS Compliance) */}
<Card>
  <CardHeader>
    <div className="flex items-center justify-between">
      <div>
        <CardTitle className="text-xl">Tags ({contractTags.length})</CardTitle>
        <CardDescription>ODCS top-level tags for categorization</CardDescription>
      </div>
      <Button
        size="sm"
        onClick={() => {
          setEditingTagIndex(null)
          setIsTagFormOpen(true)
        }}
      >
        <Plus className="h-4 w-4 mr-1.5" />
        Add Tag
      </Button>
    </div>
  </CardHeader>
  <CardContent>
    {contractTags && contractTags.length > 0 ? (
      <div className="flex flex-wrap gap-2">
        {contractTags.map((tag, idx) => (
          <div key={tag.id} className="group relative">
            <Badge
              variant="secondary"
              className="text-sm pr-8"
            >
              {tag.name}
            </Badge>
            <div className="absolute right-1 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity flex gap-1">
              <Button
                size="icon"
                variant="ghost"
                className="h-5 w-5"
                onClick={() => {
                  setEditingTagIndex(idx)
                  setIsTagFormOpen(true)
                }}
              >
                <Pencil className="h-3 w-3" />
              </Button>
              <Button
                size="icon"
                variant="ghost"
                className="h-5 w-5 text-destructive hover:text-destructive"
                onClick={() => handleDeleteTag(idx)}
              >
                <Trash2 className="h-3 w-3" />
              </Button>
            </div>
          </div>
        ))}
      </div>
    ) : (
      <p className="text-sm text-muted-foreground text-center py-8">
        No tags defined. Click "Add Tag" to add one.
      </p>
    )}
  </CardContent>
</Card>
```

## 7. Add TagFormDialog Component

**Location:** Add at the end of the component, with other dialog components (around line 1380)

```tsx
{/* Tag Form Dialog */}
<TagFormDialog
  isOpen={isTagFormOpen}
  onOpenChange={setIsTagFormOpen}
  onSubmit={handleSubmitTag}
  initial={editingTagIndex !== null ? contractTags[editingTagIndex] : undefined}
/>
```

## 8. Schema-Level Tags (Future Enhancement)

**Note:** Schema-level tags are stored as JSON in `SchemaObjectDb.tags` field. To support them:

1. Parse `schema.tags` JSON array in the schema display sections
2. Add inline tag chips under each schema name
3. Add schema-specific tag management in `SchemaFormDialog`
4. Update schema save logic to serialize tags as JSON

**Example schema tags display** (add near line 945 in schema display):

```tsx
{schema.tags && Array.isArray(schema.tags) && schema.tags.length > 0 && (
  <div className="flex flex-wrap gap-1 mt-2">
    {schema.tags.map((tag, idx) => (
      <Badge key={idx} variant="outline" className="text-xs">
        {typeof tag === 'string' ? tag : tag.name}
      </Badge>
    ))}
  </div>
)}
```

## Testing Checklist

- [ ] Create a new tag
- [ ] Edit an existing tag
- [ ] Delete a tag
- [ ] Verify duplicate tag names are prevented (backend validation)
- [ ] Verify tag name validation (alphanumeric, hyphens, underscores only)
- [ ] Verify tags persist after page reload
- [ ] Check empty state message displays correctly
- [ ] Check tags display in list view
- [ ] Test with 0, 1, 5, 20+ tags

## Integration Points

- Tags are fetched via `/api/data-contracts/{id}/tags`
- Tags are separate from the main contract object
- Tags can be used for filtering/searching contracts (future feature)
- Schema-level tags require frontend parsing of JSON field

## File References

- Backend: `src/backend/src/routes/data_contracts_routes.py` (lines 3023-3210)
- API Models: `src/backend/src/models/data_contracts_api.py` (lines 465-483)
- Repository: `src/backend/src/repositories/data_contracts_repository.py` (lines 137-218)
- Form Dialog: `src/frontend/src/components/data-contracts/tag-form-dialog.tsx` (complete)
- Main View: `src/frontend/src/views/data-contract-details.tsx` (needs integration)
