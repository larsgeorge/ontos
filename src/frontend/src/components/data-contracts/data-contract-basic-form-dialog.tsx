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
import type { TeamSummary } from '@/types/team'
import TagSelector from '@/components/ui/tag-selector'
import type { AssignedTag } from '@/components/ui/tag-chip'
import { useProjectContext } from '@/stores/project-store'

type BasicFormProps = {
  isOpen: boolean
  onOpenChange: (open: boolean) => void
  onSubmit: (payload: DataContractCreate) => Promise<void>
  initial?: {
    name?: string
    version?: string
    status?: string
    owner_team_id?: string
    project_id?: string
    domain?: string
    tenant?: string
    dataProduct?: string
    descriptionUsage?: string
    descriptionPurpose?: string
    descriptionLimitations?: string
    tags?: (string | AssignedTag)[]
  }
}

const statuses = ['draft', 'active', 'deprecated', 'archived']

export default function DataContractBasicFormDialog({ isOpen, onOpenChange, onSubmit, initial }: BasicFormProps) {
  const { domains, loading: domainsLoading } = useDomains()
  const { toast } = useToast()
  const { currentProject, availableProjects, fetchUserProjects, isLoading: projectsLoading } = useProjectContext()
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Form state
  const [name, setName] = useState('')
  const [version, setVersion] = useState('0.0.1')
  const [status, setStatus] = useState('draft')
  const [ownerTeamId, setOwnerTeamId] = useState('')
  const [projectId, setProjectId] = useState('')
  const [domain, setDomain] = useState('')
  const [tenant, setTenant] = useState('')
  const [dataProduct, setDataProduct] = useState('')
  const [descriptionUsage, setDescriptionUsage] = useState('')
  const [descriptionPurpose, setDescriptionPurpose] = useState('')
  const [descriptionLimitations, setDescriptionLimitations] = useState('')
  const [tags, setTags] = useState<(string | AssignedTag)[]>([])

  // Teams state
  const [teams, setTeams] = useState<TeamSummary[]>([])
  const [teamsLoading, setTeamsLoading] = useState(false)

  // Fetch teams and projects when dialog opens
  useEffect(() => {
    if (isOpen) {
      setTeamsLoading(true)
      fetch('/api/teams/summary')
        .then(res => res.json())
        .then(data => setTeams(Array.isArray(data) ? data : []))
        .catch(err => {
          console.error('Failed to fetch teams:', err)
          setTeams([])
        })
        .finally(() => setTeamsLoading(false))
      
      // Fetch user projects
      fetchUserProjects()
    }
  }, [isOpen, fetchUserProjects])

  // Initialize form state when dialog opens or initial data changes
  // Only reset state when dialog opens, not when currentProject changes mid-edit
  useEffect(() => {
    if (!isOpen) return; // Don't reset if dialog is closed
    
    if (initial) {
      setName(initial.name || '')
      setVersion(initial.version || '0.0.1')
      setStatus(initial.status || 'draft')
      setOwnerTeamId(initial.owner_team_id || '')
      setProjectId(initial.project_id || '')
      setDomain(initial.domain || '')
      setTenant(initial.tenant || '')
      setDataProduct(initial.dataProduct || '')
      setDescriptionUsage(initial.descriptionUsage || '')
      setDescriptionPurpose(initial.descriptionPurpose || '')
      setDescriptionLimitations(initial.descriptionLimitations || '')
      setTags(initial.tags || [])
    } else {
      // Reset to defaults for new contract, default to current project
      setName('')
      setVersion('0.0.1')
      setStatus('draft')
      setOwnerTeamId('')
      setProjectId(currentProject?.id || '')
      setDomain('')
      setTenant('')
      setDataProduct('')
      setDescriptionUsage('')
      setDescriptionPurpose('')
      setDescriptionLimitations('')
      setTags([])
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen])

  const handleSubmit = async () => {
    // Validate required fields
    if (!name || !name.trim()) {
      toast({ title: 'Validation Error', description: 'Contract name is required', variant: 'destructive' })
      return
    }

    console.log('[DEBUG FORM] State values before submit:')
    console.log('  - projectId:', projectId)
    console.log('  - domain:', domain)
    console.log('  - ownerTeamId:', ownerTeamId)
    
    setIsSubmitting(true)
    try {
      // Normalize tags to tag IDs (strings) for backend compatibility
      const normalizedTags = tags.map((tag: any) => {
        if (typeof tag === 'string') return tag;
        return tag.tag_id || tag.fully_qualified_name || tag.tag_name || tag;
      });

      const payload: DataContractCreate = {
        name: name.trim(),
        version: version.trim() || '0.0.1',
        status: status || 'draft',
        owner_team_id: ownerTeamId && ownerTeamId !== '__none__' ? ownerTeamId : undefined,
        project_id: projectId && projectId !== '__none__' ? projectId : undefined,
        kind: 'DataContract',
        apiVersion: 'v3.0.2',
        domainId: domain && domain !== '__none__' ? domain : undefined,
        tenant: tenant.trim() || undefined,
        dataProduct: dataProduct.trim() || undefined,
        tags: normalizedTags.length > 0 ? normalizedTags as any : undefined,
        description: {
          usage: descriptionUsage.trim() || undefined,
          purpose: descriptionPurpose.trim() || undefined,
          limitations: descriptionLimitations.trim() || undefined,
        },
      }

      console.log('[DEBUG FORM] Final payload:', JSON.stringify(payload, null, 2))
      
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
                placeholder="0.0.1"
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

      {/* Owner Team */}
      <div className="space-y-2">
        <Label htmlFor="ownerTeamId">Owner Team</Label>
        <Select 
          value={ownerTeamId || '__none__'} 
          onValueChange={(value) => {
            console.log('[DEBUG] Owner Team onValueChange fired:', value);
            setOwnerTeamId(value === '__none__' ? '' : value);
          }} 
          disabled={teamsLoading}
        >
          <SelectTrigger id="ownerTeamId">
            <SelectValue placeholder="Select an owner team (optional)" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="__none__">None</SelectItem>
            {teams.map((team) => (
              <SelectItem key={team.id} value={team.id}>
                {team.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Project */}
      <div className="space-y-2">
        <Label htmlFor="projectId">Project</Label>
        <Select 
          value={projectId || '__none__'} 
          onValueChange={(value) => {
            console.log('[DEBUG] Project onValueChange fired:', value);
            setProjectId(value === '__none__' ? '' : value);
          }} 
          disabled={projectsLoading}
        >
          <SelectTrigger id="projectId">
            <SelectValue placeholder="Select a project (optional)" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="__none__">None</SelectItem>
            {availableProjects.map((project) => (
              <SelectItem key={project.id} value={project.id}>
                {project.name} ({project.team_count} teams)
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <p className="text-xs text-muted-foreground">
          You can only select projects you are a member of
        </p>
      </div>

      {/* Domain */}
      <div className="space-y-2">
        <Label htmlFor="domain">Domain</Label>
        <Select 
          value={domain || '__none__'} 
          onValueChange={(value) => {
            console.log('[DEBUG] Domain onValueChange fired:', value);
            setDomain(value === '__none__' ? '' : value);
          }} 
          disabled={domainsLoading}
        >
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

          {/* Tags Section */}
          <div className="space-y-2 border-t pt-4">
            <Label>Tags</Label>
            <TagSelector
              value={tags}
              onChange={setTags}
              placeholder="Search and select tags for this data contract..."
              allowCreate={true}
            />
            <p className="text-xs text-muted-foreground">
              Add tags to categorize and organize this data contract
            </p>
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
