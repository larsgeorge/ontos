import { useEffect, useState } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { useDomains } from '@/hooks/use-domains'
import { useToast } from '@/hooks/use-toast'
import type { DataContractCreate } from '@/types/data-contract'

type BasicFormProps = {
  isOpen: boolean
  onOpenChange: (open: boolean) => void
  onSubmit: (payload: DataContractCreate) => Promise<void>
  initial?: {
    name?: string
    version?: string
    status?: string
    owner_team_id?: string
    domain?: string
    tenant?: string
    dataProduct?: string
    descriptionUsage?: string
    descriptionPurpose?: string
    descriptionLimitations?: string
  }
}

const statuses = ['draft', 'active', 'deprecated', 'archived']

export default function DataContractBasicFormDialog({ isOpen, onOpenChange, onSubmit, initial }: BasicFormProps) {
  const { domains, loading: domainsLoading } = useDomains()
  const { toast } = useToast()
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Form state
  const [name, setName] = useState('')
  const [version, setVersion] = useState('1.0.0')
  const [status, setStatus] = useState('draft')
  const [ownerTeamId, setOwnerTeamId] = useState('')
  const [domain, setDomain] = useState('')
  const [tenant, setTenant] = useState('')
  const [dataProduct, setDataProduct] = useState('')
  const [descriptionUsage, setDescriptionUsage] = useState('')
  const [descriptionPurpose, setDescriptionPurpose] = useState('')
  const [descriptionLimitations, setDescriptionLimitations] = useState('')

  // Initialize form state when dialog opens or initial data changes
  useEffect(() => {
    if (isOpen && initial) {
      setName(initial.name || '')
      setVersion(initial.version || '1.0.0')
      setStatus(initial.status || 'draft')
      setOwnerTeamId(initial.owner_team_id || '')
      setDomain(initial.domain || '')
      setTenant(initial.tenant || '')
      setDataProduct(initial.dataProduct || '')
      setDescriptionUsage(initial.descriptionUsage || '')
      setDescriptionPurpose(initial.descriptionPurpose || '')
      setDescriptionLimitations(initial.descriptionLimitations || '')
    } else if (isOpen && !initial) {
      // Reset to defaults for new contract
      setName('')
      setVersion('1.0.0')
      setStatus('draft')
      setOwnerTeamId('')
      setDomain('')
      setTenant('')
      setDataProduct('')
      setDescriptionUsage('')
      setDescriptionPurpose('')
      setDescriptionLimitations('')
    }
  }, [isOpen, initial])

  const handleSubmit = async () => {
    // Validate required fields
    if (!name || !name.trim()) {
      toast({ title: 'Validation Error', description: 'Contract name is required', variant: 'destructive' })
      return
    }

    setIsSubmitting(true)
    try {
      const payload: DataContractCreate = {
        name: name.trim(),
        version: version.trim() || '1.0.0',
        status: status || 'draft',
        owner_team_id: ownerTeamId.trim() || undefined,
        kind: 'DataContract',
        apiVersion: 'v3.0.2',
        domainId: domain && domain !== '__none__' ? domain : undefined,
        tenant: tenant.trim() || undefined,
        dataProduct: dataProduct.trim() || undefined,
        description: {
          usage: descriptionUsage.trim() || undefined,
          purpose: descriptionPurpose.trim() || undefined,
          limitations: descriptionLimitations.trim() || undefined,
        },
      }

      await onSubmit(payload)
      onOpenChange(false)
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error?.message || 'Failed to save contract',
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
          <DialogTitle>{initial ? 'Edit Contract Metadata' : 'Create New Data Contract'}</DialogTitle>
          <DialogDescription>
            {initial
              ? 'Update the core metadata for this data contract.'
              : 'Enter basic information to create a new data contract. You can add schemas, quality rules, and other details after creation.'}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Name */}
          <div className="space-y-2">
            <Label htmlFor="name">
              Name <span className="text-destructive">*</span>
            </Label>
            <Input
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Customer Data Contract"
            />
          </div>

          {/* Version & Status */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="version">Version</Label>
              <Input
                id="version"
                value={version}
                onChange={(e) => setVersion(e.target.value)}
                placeholder="1.0.0"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="status">Status</Label>
              <Select value={status} onValueChange={setStatus}>
                <SelectTrigger id="status">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {statuses.map((s) => (
                    <SelectItem key={s} value={s}>
                      {s}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Owner Team ID */}
          <div className="space-y-2">
            <Label htmlFor="ownerTeamId">Owner Team ID</Label>
            <Input
              id="ownerTeamId"
              value={ownerTeamId}
              onChange={(e) => setOwnerTeamId(e.target.value)}
              placeholder="UUID of the owning team"
            />
          </div>

          {/* Domain */}
          <div className="space-y-2">
            <Label htmlFor="domain">Domain</Label>
            <Select value={domain} onValueChange={setDomain} disabled={domainsLoading}>
              <SelectTrigger id="domain">
                <SelectValue placeholder="Select a domain (optional)" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__none__">None</SelectItem>
                {domains.map((d) => (
                  <SelectItem key={d.id} value={d.id}>
                    {d.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Tenant & Data Product */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="tenant">Tenant</Label>
              <Input
                id="tenant"
                value={tenant}
                onChange={(e) => setTenant(e.target.value)}
                placeholder="e.g., production"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="dataProduct">Data Product</Label>
              <Input
                id="dataProduct"
                value={dataProduct}
                onChange={(e) => setDataProduct(e.target.value)}
                placeholder="e.g., Customer 360"
              />
            </div>
          </div>

          {/* Description sections */}
          <div className="space-y-4 pt-2">
            <Label className="text-base font-semibold">Description</Label>

            <div className="space-y-2">
              <Label htmlFor="descriptionPurpose">Purpose</Label>
              <Textarea
                id="descriptionPurpose"
                value={descriptionPurpose}
                onChange={(e) => setDescriptionPurpose(e.target.value)}
                placeholder="What is the purpose of this data contract?"
                rows={2}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="descriptionUsage">Usage</Label>
              <Textarea
                id="descriptionUsage"
                value={descriptionUsage}
                onChange={(e) => setDescriptionUsage(e.target.value)}
                placeholder="How should this data be used?"
                rows={2}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="descriptionLimitations">Limitations</Label>
              <Textarea
                id="descriptionLimitations"
                value={descriptionLimitations}
                onChange={(e) => setDescriptionLimitations(e.target.value)}
                placeholder="What are the limitations or restrictions?"
                rows={2}
              />
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={isSubmitting}>
            {isSubmitting ? 'Saving...' : initial ? 'Save Changes' : 'Create Contract'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
