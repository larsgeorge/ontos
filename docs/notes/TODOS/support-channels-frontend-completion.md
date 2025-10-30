# Support Channels Frontend Implementation - Remaining Work

## Status: Backend Complete ✅, Frontend Pending

### Completed
- ✅ Backend API models, repository, and routes
- ✅ All CRUD endpoints working (GET, POST, PUT, DELETE)
- ✅ 6-field model: channel, url, description, tool, scope, invitation_url

### Remaining Work

## 1. Create SupportChannelFormDialog Component

**Location:** `src/frontend/src/components/data-contracts/support-channel-form-dialog.tsx` (new file)

```typescript
import { useEffect, useState } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { useToast } from '@/hooks/use-toast'

type SupportChannel = {
  id?: string
  channel: string
  url: string
  description?: string
  tool?: string
  scope?: string
  invitation_url?: string
}

type SupportChannelFormProps = {
  isOpen: boolean
  onOpenChange: (open: boolean) => void
  onSubmit: (channel: SupportChannel) => Promise<void>
  initial?: SupportChannel
}

export default function SupportChannelFormDialog({ isOpen, onOpenChange, onSubmit, initial }: SupportChannelFormProps) {
  const { toast } = useToast()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [channel, setChannel] = useState('')
  const [url, setUrl] = useState('')
  const [description, setDescription] = useState('')
  const [tool, setTool] = useState('')
  const [scope, setScope] = useState('')
  const [invitationUrl, setInvitationUrl] = useState('')

  useEffect(() => {
    if (isOpen && initial) {
      setChannel(initial.channel || '')
      setUrl(initial.url || '')
      setDescription(initial.description || '')
      setTool(initial.tool || '')
      setScope(initial.scope || '')
      setInvitationUrl(initial.invitation_url || '')
    } else if (isOpen && !initial) {
      setChannel('')
      setUrl('')
      setDescription('')
      setTool('')
      setScope('')
      setInvitationUrl('')
    }
  }, [isOpen, initial])

  const handleSubmit = async () => {
    // Validation
    if (!channel.trim()) {
      toast({ title: 'Validation Error', description: 'Channel type is required', variant: 'destructive' })
      return
    }
    if (!url.trim()) {
      toast({ title: 'Validation Error', description: 'URL is required', variant: 'destructive' })
      return
    }

    // Basic URL validation
    try {
      new URL(url.trim())
    } catch {
      toast({ title: 'Validation Error', description: 'Please enter a valid URL', variant: 'destructive' })
      return
    }

    setIsSubmitting(true)
    try {
      const supportChannel: SupportChannel = {
        channel: channel.trim(),
        url: url.trim(),
        description: description.trim() || undefined,
        tool: tool.trim() || undefined,
        scope: scope.trim() || undefined,
        invitation_url: invitationUrl.trim() || undefined,
      }

      await onSubmit(supportChannel)
      onOpenChange(false)
      toast({
        title: 'Success',
        description: initial ? 'Support channel updated successfully' : 'Support channel created successfully'
      })
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error?.message || 'Failed to save support channel',
        variant: 'destructive',
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{initial ? 'Edit Support Channel' : 'Add Support Channel'}</DialogTitle>
          <DialogDescription>
            {initial
              ? 'Update the support channel information'
              : 'Add a new support channel to this data contract (ODCS compliant)'}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="grid grid-cols-2 gap-4">
            {/* Channel Type */}
            <div className="space-y-2">
              <Label htmlFor="channel">
                Channel Type <span className="text-destructive">*</span>
              </Label>
              <Input
                id="channel"
                value={channel}
                onChange={(e) => setChannel(e.target.value)}
                placeholder="e.g., email, slack, teams"
                maxLength={255}
                autoFocus
              />
              <p className="text-xs text-muted-foreground">
                Type of support channel (email, slack, etc.)
              </p>
            </div>

            {/* Tool */}
            <div className="space-y-2">
              <Label htmlFor="tool">Tool</Label>
              <Input
                id="tool"
                value={tool}
                onChange={(e) => setTool(e.target.value)}
                placeholder="e.g., Slack, Microsoft Teams, JIRA"
                maxLength={255}
              />
              <p className="text-xs text-muted-foreground">
                Specific tool or platform name
              </p>
            </div>
          </div>

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
              placeholder="https://support.example.com/channel"
            />
            <p className="text-xs text-muted-foreground">
              Full URL to the support channel
            </p>
          </div>

          <div className="grid grid-cols-2 gap-4">
            {/* Scope */}
            <div className="space-y-2">
              <Label htmlFor="scope">Scope</Label>
              <Input
                id="scope"
                value={scope}
                onChange={(e) => setScope(e.target.value)}
                placeholder="e.g., technical, business, general"
                maxLength={255}
              />
              <p className="text-xs text-muted-foreground">
                Support scope or category
              </p>
            </div>

            {/* Invitation URL */}
            <div className="space-y-2">
              <Label htmlFor="invitation_url">Invitation URL</Label>
              <Input
                id="invitation_url"
                type="url"
                value={invitationUrl}
                onChange={(e) => setInvitationUrl(e.target.value)}
                placeholder="https://invite.example.com/join"
              />
              <p className="text-xs text-muted-foreground">
                Join or invitation link (optional)
              </p>
            </div>
          </div>

          {/* Description */}
          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe this support channel and when to use it..."
              rows={4}
            />
            <p className="text-xs text-muted-foreground">
              Additional details about this support channel
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

## 2. Add Support Channel State Management to `data-contract-details.tsx`

**Location:** After line ~160 (after other dialog states)

```typescript
// Add to existing state declarations
const [isSupportChannelFormOpen, setIsSupportChannelFormOpen] = useState(false)
const [editingSupportChannelIndex, setEditingSupportChannelIndex] = useState<number | null>(null)
const [supportChannels, setSupportChannels] = useState<Array<{
  id: string
  channel: string
  url: string
  description?: string
  tool?: string
  scope?: string
  invitation_url?: string
}>>([]
```

## 3. Import SupportChannelFormDialog

**Location:** Top of file with other imports (around line 28)

```typescript
import SupportChannelFormDialog from '@/components/data-contracts/support-channel-form-dialog'
```

## 4. Add Support Channel Fetch Function

**Location:** Add to fetch functions (around line 270)

```typescript
const fetchSupportChannels = async () => {
  if (!contractId) return
  try {
    const response = await fetch(`/api/data-contracts/${contractId}/support`)
    if (response.ok) {
      const data = await response.json()
      setSupportChannels(Array.isArray(data) ? data : [])
    } else {
      setSupportChannels([])
    }
  } catch (e) {
    console.warn('Failed to fetch support channels:', e)
    setSupportChannels([])
  }
}
```

## 5. Call fetchSupportChannels in useEffect

**Location:** In the main useEffect that calls fetchDetails (around line 260)

```typescript
useEffect(() => {
  if (contractId) {
    fetchDetails()
    fetchLinkedProducts()
    fetchContractTags()
    fetchSupportChannels()  // Add this line
    fetchLatestProfilingRun()
  }
}, [contractId])
```

## 6. Add Support Channel CRUD Handlers

**Location:** Add after other handlers (around line 460)

```typescript
// Support Channel handlers
const handleAddSupportChannel = async (channel: any) => {
  if (!contractId) return
  try {
    const response = await fetch(`/api/data-contracts/${contractId}/support`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(channel)
    })

    if (!response.ok) {
      const errorData = await response.json()
      throw new Error(errorData.detail || 'Failed to create support channel')
    }

    await fetchSupportChannels()
    toast({ title: 'Success', description: 'Support channel added successfully' })
  } catch (error: any) {
    toast({ title: 'Error', description: error.message, variant: 'destructive' })
    throw error
  }
}

const handleUpdateSupportChannel = async (channel: any) => {
  if (!contractId || editingSupportChannelIndex === null) return
  const channelToUpdate = supportChannels[editingSupportChannelIndex]

  try {
    const response = await fetch(`/api/data-contracts/${contractId}/support/${channelToUpdate.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(channel)
    })

    if (!response.ok) {
      const errorData = await response.json()
      throw new Error(errorData.detail || 'Failed to update support channel')
    }

    await fetchSupportChannels()
    toast({ title: 'Success', description: 'Support channel updated successfully' })
  } catch (error: any) {
    toast({ title: 'Error', description: error.message, variant: 'destructive' })
    throw error
  }
}

const handleDeleteSupportChannel = async (index: number) => {
  if (!contractId) return
  const channel = supportChannels[index]

  if (!confirm(`Delete support channel "${channel.channel}"?`)) return

  try {
    const response = await fetch(`/api/data-contracts/${contractId}/support/${channel.id}`, {
      method: 'DELETE'
    })

    if (!response.ok) {
      throw new Error('Failed to delete support channel')
    }

    await fetchSupportChannels()
    toast({ title: 'Success', description: 'Support channel deleted successfully' })
  } catch (error: any) {
    toast({ title: 'Error', description: error.message, variant: 'destructive' })
  }
}

const handleSubmitSupportChannel = async (channel: any) => {
  if (editingSupportChannelIndex !== null) {
    await handleUpdateSupportChannel(channel)
  } else {
    await handleAddSupportChannel(channel)
  }
}
```

## 7. Upgrade Support Channels UI Section

**Location:** Replace existing read-only section (around lines 1069-1090)

```tsx
{/* Support Channels Section (ODCS Compliance) - Upgraded to CRUD */}
<Card>
  <CardHeader>
    <div className="flex items-center justify-between">
      <div>
        <CardTitle className="text-xl">Support Channels ({supportChannels.length})</CardTitle>
        <CardDescription>ODCS support channels for assistance</CardDescription>
      </div>
      <Button
        size="sm"
        onClick={() => {
          setEditingSupportChannelIndex(null)
          setIsSupportChannelFormOpen(true)
        }}
      >
        <Plus className="h-4 w-4 mr-1.5" />
        Add Support Channel
      </Button>
    </div>
  </CardHeader>
  <CardContent>
    {supportChannels && supportChannels.length > 0 ? (
      <div className="space-y-3">
        {supportChannels.map((channel, idx) => (
          <div
            key={channel.id}
            className="group relative border rounded-lg p-4 hover:bg-accent/50 transition-colors"
          >
            <div className="flex items-start justify-between">
              <div className="flex-1 space-y-1">
                <div className="flex items-center gap-2">
                  <Badge variant="secondary">{channel.channel}</Badge>
                  {channel.tool && (
                    <Badge variant="outline" className="text-xs">{channel.tool}</Badge>
                  )}
                  {channel.scope && (
                    <Badge variant="outline" className="text-xs">{channel.scope}</Badge>
                  )}
                </div>
                <div className="flex items-center gap-2 text-sm">
                  <LinkIcon className="h-3.5 w-3.5 text-muted-foreground" />
                  <a
                    href={channel.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary hover:underline"
                  >
                    {channel.url}
                  </a>
                </div>
                {channel.description && (
                  <p className="text-sm text-muted-foreground mt-2">
                    {channel.description}
                  </p>
                )}
                {channel.invitation_url && (
                  <div className="flex items-center gap-2 text-sm text-muted-foreground mt-1">
                    <span className="text-xs">Invitation:</span>
                    <a
                      href={channel.invitation_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary hover:underline text-xs"
                    >
                      {channel.invitation_url}
                    </a>
                  </div>
                )}
              </div>
              <div className="opacity-0 group-hover:opacity-100 transition-opacity flex gap-1 ml-2">
                <Button
                  size="icon"
                  variant="ghost"
                  className="h-8 w-8"
                  onClick={() => {
                    setEditingSupportChannelIndex(idx)
                    setIsSupportChannelFormOpen(true)
                  }}
                >
                  <Pencil className="h-4 w-4" />
                </Button>
                <Button
                  size="icon"
                  variant="ghost"
                  className="h-8 w-8 text-destructive hover:text-destructive"
                  onClick={() => handleDeleteSupportChannel(idx)}
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
        No support channels defined. Click "Add Support Channel" to add one.
      </p>
    )}
  </CardContent>
</Card>
```

## 8. Add SupportChannelFormDialog Component

**Location:** Add at the end of the component, with other dialog components (around line 1380)

```tsx
{/* Support Channel Form Dialog */}
<SupportChannelFormDialog
  isOpen={isSupportChannelFormOpen}
  onOpenChange={setIsSupportChannelFormOpen}
  onSubmit={handleSubmitSupportChannel}
  initial={editingSupportChannelIndex !== null ? supportChannels[editingSupportChannelIndex] : undefined}
/>
```

## 9. Import LinkIcon

**Location:** Add to icon imports at top of file

```typescript
import { Plus, Pencil, Trash2, LinkIcon } from 'lucide-react'
```

## Testing Checklist

- [ ] Create a new support channel with all fields
- [ ] Create a support channel with only required fields (channel, url)
- [ ] Edit an existing support channel
- [ ] Delete a support channel
- [ ] Verify URL validation works (requires valid URL format)
- [ ] Verify support channels persist after page reload
- [ ] Check empty state message displays correctly
- [ ] Verify external links open in new tab
- [ ] Test with 0, 1, 5, 10+ support channels
- [ ] Verify invitation URL displays correctly when provided
- [ ] Check responsive layout on different screen sizes

## Integration Points

- Support channels are fetched via `/api/data-contracts/{id}/support`
- Support channels are separate from the main contract object
- Replaces existing read-only display (lines 1069-1090 in data-contract-details.tsx)
- Can be used for user notifications and help desk routing (future feature)

## File References

- Backend: `src/backend/src/routes/data_contracts_routes.py` (lines 3184-3370)
- API Models: `src/backend/src/models/data_contracts_api.py` (lines 510-543)
- Repository: `src/backend/src/repositories/data_contracts_repository.py` (lines 286-386)
- Form Dialog: `src/frontend/src/components/data-contracts/support-channel-form-dialog.tsx` (to be created)
- Main View: `src/frontend/src/views/data-contract-details.tsx` (needs integration)

## Additional Notes

- **6 fields total**: 2 required (channel, url), 4 optional (description, tool, scope, invitation_url)
- **Validation**: URL format validation for both url and invitation_url
- **UI Pattern**: Card-based display with hover actions (similar to team members)
- **ODCS Field**: Maps to `support[]` array in ODCS v3.0.2 specification
- **External Links**: All URLs should open in new tab with `target="_blank" rel="noopener noreferrer"`
