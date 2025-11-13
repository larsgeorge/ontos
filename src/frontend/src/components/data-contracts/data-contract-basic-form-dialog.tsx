import { useEffect, useState, useMemo } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
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
  const [showDiscardConfirm, setShowDiscardConfirm] = useState(false)

  // Form state
  const [name, setName] = useState('')
  const [version, setVersion] = useState('0.0.1')
  const [status, setStatus] = useState('draft')
  const [ownerTeamId, setOwnerTeamId] = useState('')
  const [projectId, setProjectId] = useState('')
  const [domain, setDomain] = useState('')
  const [tenant, setTenant] = useState('')
  const [descriptionUsage, setDescriptionUsage] = useState('')
  const [descriptionPurpose, setDescriptionPurpose] = useState('')
  const [descriptionLimitations, setDescriptionLimitations] = useState('')
  const [tags, setTags] = useState<(string | AssignedTag)[]>([])

  // Teams state
  const [teams, setTeams] = useState<TeamSummary[]>([])
  const [teamsLoading, setTeamsLoading] = useState(false)

  // Track initial form values to detect changes
  const [initialFormValues, setInitialFormValues] = useState<any>(null)

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
    
    const initValues = initial ? {
      name: initial.name || '',
      version: initial.version || '0.0.1',
      status: initial.status || 'draft',
      ownerTeamId: initial.owner_team_id || '',
      projectId: initial.project_id || '',
      domain: initial.domain || '',
      tenant: initial.tenant || '',
      descriptionUsage: initial.descriptionUsage || '',
      descriptionPurpose: initial.descriptionPurpose || '',
      descriptionLimitations: initial.descriptionLimitations || '',
      tags: initial.tags || [],
    } : {
      name: '',
      version: '0.0.1',
      status: 'draft',
      ownerTeamId: '',
      projectId: currentProject?.id || '',
      domain: '',
      tenant: '',
      descriptionUsage: '',
      descriptionPurpose: '',
      descriptionLimitations: '',
      tags: [],
    }
    
    setName(initValues.name)
    setVersion(initValues.version)
    setStatus(initValues.status)
    setOwnerTeamId(initValues.ownerTeamId)
    setProjectId(initValues.projectId)
    setDomain(initValues.domain)
    setTenant(initValues.tenant)
    setDescriptionUsage(initValues.descriptionUsage)
    setDescriptionPurpose(initValues.descriptionPurpose)
    setDescriptionLimitations(initValues.descriptionLimitations)
    setTags(initValues.tags)
    setInitialFormValues(initValues)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen])

  // Check if form has been modified
  const isFormDirty = useMemo(() => {
    if (!initialFormValues) return false
    
    // Normalize tags for comparison
    const normalizeTag = (tag: any) => typeof tag === 'string' ? tag : (tag.tag_id || tag.fully_qualified_name || tag.tag_name || tag)
    const currentTagsNormalized = tags.map(normalizeTag).sort().join(',')
    const initialTagsNormalized = initialFormValues.tags.map(normalizeTag).sort().join(',')
    
    return (
      name !== initialFormValues.name ||
      version !== initialFormValues.version ||
      status !== initialFormValues.status ||
      ownerTeamId !== initialFormValues.ownerTeamId ||
      projectId !== initialFormValues.projectId ||
      domain !== initialFormValues.domain ||
      tenant !== initialFormValues.tenant ||
      descriptionUsage !== initialFormValues.descriptionUsage ||
      descriptionPurpose !== initialFormValues.descriptionPurpose ||
      descriptionLimitations !== initialFormValues.descriptionLimitations ||
      currentTagsNormalized !== initialTagsNormalized
    )
  }, [initialFormValues, name, version, status, ownerTeamId, projectId, domain, tenant, descriptionUsage, descriptionPurpose, descriptionLimitations, tags])

  const handleCloseAttempt = () => {
    if (isFormDirty && !isSubmitting) {
      setShowDiscardConfirm(true)
    } else {
      onOpenChange(false)
    }
  }

  const handleConfirmDiscard = () => {
    setShowDiscardConfirm(false)
    onOpenChange(false)
  }

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
    <>
      <Dialog open={isOpen} onOpenChange={handleCloseAttempt}>
        <DialogContent 
          className="max-w-2xl max-h-[90vh] overflow-y-auto"
          onInteractOutside={(e) => {
            // Prevent closing on outside click
            e.preventDefault()
          }}
          onEscapeKeyDown={(e) => {
            // Prevent closing on Escape key
            e.preventDefault()
            handleCloseAttempt()
          }}
        >
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

          {/* Tenant */}
          <div className="space-y-2">
            <Label htmlFor="tenant">Tenant</Label>
            <Input
              id="tenant"
              value={tenant}
              onChange={(e) => setTenant(e.target.value)}
              placeholder="e.g., retail-demo"
            />
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
          <Button variant="outline" onClick={handleCloseAttempt} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={isSubmitting}>
            {isSubmitting ? 'Saving...' : initial ? 'Save Changes' : 'Create Contract'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <AlertDialog open={showDiscardConfirm} onOpenChange={setShowDiscardConfirm}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Discard unsaved changes?</AlertDialogTitle>
          <AlertDialogDescription>
            You have unsaved changes that will be lost if you close this dialog. Are you sure you want to discard them?
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Continue Editing</AlertDialogCancel>
          <AlertDialogAction onClick={handleConfirmDiscard}>Discard Changes</AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
    </>
  )
}
