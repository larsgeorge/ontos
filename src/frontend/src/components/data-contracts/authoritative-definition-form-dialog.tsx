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
  level: 'contract' | 'schema' | 'property'
}

export default function AuthoritativeDefinitionFormDialog({
  isOpen,
  onOpenChange,
  onSubmit,
  initial,
  level
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
