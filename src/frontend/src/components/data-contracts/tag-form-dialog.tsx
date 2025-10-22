import { useEffect, useState } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useToast } from '@/hooks/use-toast'

type ContractTag = {
  id?: string
  name: string
}

type TagFormProps = {
  isOpen: boolean
  onOpenChange: (open: boolean) => void
  onSubmit: (tag: ContractTag) => Promise<void>
  initial?: ContractTag
}

export default function TagFormDialog({ isOpen, onOpenChange, onSubmit, initial }: TagFormProps) {
  const { toast } = useToast()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [name, setName] = useState('')

  useEffect(() => {
    if (isOpen && initial) {
      setName(initial.name || '')
    } else if (isOpen && !initial) {
      setName('')
    }
  }, [isOpen, initial])

  const handleSubmit = async () => {
    if (!name.trim()) {
      toast({ title: 'Validation Error', description: 'Tag name is required', variant: 'destructive' })
      return
    }

    // Validate tag name format (alphanumeric, hyphens, underscores only)
    if (!/^[a-zA-Z0-9_-]+$/.test(name.trim())) {
      toast({
        title: 'Validation Error',
        description: 'Tag name can only contain letters, numbers, hyphens, and underscores',
        variant: 'destructive'
      })
      return
    }

    setIsSubmitting(true)
    try {
      const tag: ContractTag = {
        name: name.trim(),
      }

      await onSubmit(tag)
      onOpenChange(false)
      toast({
        title: 'Success',
        description: initial ? 'Tag updated successfully' : 'Tag created successfully'
      })
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error?.message || 'Failed to save tag',
        variant: 'destructive',
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>{initial ? 'Edit Tag' : 'Add Tag'}</DialogTitle>
          <DialogDescription>
            {initial ? 'Update the tag name' : 'Add a new tag to this data contract (ODCS compliant)'}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="name">
              Tag Name <span className="text-destructive">*</span>
            </Label>
            <Input
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., pii, sensitive, production"
              maxLength={255}
              autoFocus
            />
            <p className="text-sm text-muted-foreground">
              Use letters, numbers, hyphens, and underscores only
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
