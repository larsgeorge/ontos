import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { AlertCircle, Download, Pencil, Trash2, Loader2, ArrowLeft, FileText, KeyRound, Shapes, Columns2, CopyPlus, Database, Plus } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Label } from '@/components/ui/label'
import { useToast } from '@/hooks/use-toast'
import EntityMetadataPanel from '@/components/metadata/entity-metadata-panel'
import { CommentSidebar } from '@/components/comments'
import ConceptSelectDialog from '@/components/semantic/concept-select-dialog'
import LinkedConceptChips from '@/components/semantic/linked-concept-chips'
import { useDomains } from '@/hooks/use-domains'
import type { EntitySemanticLink } from '@/types/semantic-link'
import type { DataContract, SchemaObject, QualityRule, TeamMember, ServerConfig, SLARequirements } from '@/types/data-contract'
import useBreadcrumbStore from '@/stores/breadcrumb-store'
import RequestAccessDialog from '@/components/access/request-access-dialog'
import CreateVersionDialog from '@/components/data-products/create-version-dialog'
import DataContractBasicFormDialog from '@/components/data-contracts/data-contract-basic-form-dialog'
import SchemaFormDialog from '@/components/data-contracts/schema-form-dialog'
import QualityRuleFormDialog from '@/components/data-contracts/quality-rule-form-dialog'
import TeamMemberFormDialog from '@/components/data-contracts/team-member-form-dialog'
import ServerConfigFormDialog from '@/components/data-contracts/server-config-form-dialog'
import SLAFormDialog from '@/components/data-contracts/sla-form-dialog'

export default function DataContractDetails() {
  const { contractId } = useParams<{ contractId: string }>()
  const navigate = useNavigate()
  const { toast } = useToast()
  const { getDomainName } = useDomains()

  const setStaticSegments = useBreadcrumbStore((state) => state.setStaticSegments)
  const setDynamicTitle = useBreadcrumbStore((state) => state.setDynamicTitle)

  const [contract, setContract] = useState<DataContract | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isCommentSidebarOpen, setIsCommentSidebarOpen] = useState(false)
  const [iriDialogOpen, setIriDialogOpen] = useState(false)
  const [isRequestAccessDialogOpen, setIsRequestAccessDialogOpen] = useState(false)
  const [isVersionDialogOpen, setIsVersionDialogOpen] = useState(false)
  const [links, setLinks] = useState<EntitySemanticLink[]>([])

  // Dialog states for CRUD operations
  const [isBasicFormOpen, setIsBasicFormOpen] = useState(false)
  const [isSchemaFormOpen, setIsSchemaFormOpen] = useState(false)
  const [isQualityRuleFormOpen, setIsQualityRuleFormOpen] = useState(false)
  const [isTeamMemberFormOpen, setIsTeamMemberFormOpen] = useState(false)
  const [isServerConfigFormOpen, setIsServerConfigFormOpen] = useState(false)
  const [isSLAFormOpen, setIsSLAFormOpen] = useState(false)

  // Editing states
  const [editingSchemaIndex, setEditingSchemaIndex] = useState<number | null>(null)
  const [editingQualityRuleIndex, setEditingQualityRuleIndex] = useState<number | null>(null)
  const [editingTeamMemberIndex, setEditingTeamMemberIndex] = useState<number | null>(null)
  const [editingServerIndex, setEditingServerIndex] = useState<number | null>(null)

  const fetchDetails = async () => {
    if (!contractId) return
    setLoading(true)
    setError(null)
    setDynamicTitle('Loading...')
    try {
      const [contractRes, linksRes] = await Promise.all([
        fetch(`/api/data-contracts/${contractId}`),
        fetch(`/api/semantic-links/entity/data_contract/${contractId}`)
      ])

      if (!contractRes.ok) throw new Error('Failed to load contract')
      const contractData: DataContract = await contractRes.json()
      setContract(contractData)
      setDynamicTitle(contractData.name)

      if (linksRes.ok) {
        const linksData = await linksRes.json()
        setLinks(Array.isArray(linksData) ? linksData : [])
      } else {
        setLinks([])
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load')
      setDynamicTitle('Error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    setStaticSegments([{ label: 'Data Contracts', path: '/data-contracts' }])
    fetchDetails()

    return () => {
      setStaticSegments([])
      setDynamicTitle(null)
    }
  }, [contractId, setStaticSegments, setDynamicTitle])

  const handleDelete = async () => {
    if (!contractId) return
    if (!confirm('Delete this contract?')) return
    try {
      const res = await fetch(`/api/data-contracts/${contractId}`, { method: 'DELETE' })
      if (!res.ok) throw new Error('Delete failed')
      toast({ title: 'Deleted', description: 'Contract deleted.' })
      navigate('/data-contracts')
    } catch (e) {
      toast({ title: 'Error', description: e instanceof Error ? e.message : 'Failed to delete', variant: 'destructive' })
    }
  }

  const exportOdcs = async () => {
    if (!contractId || !contract) return
    try {
      const res = await fetch(`/api/data-contracts/${contractId}/odcs/export`)
      if (!res.ok) throw new Error('Export ODCS failed')
      const text = await res.text()
      const contentDisposition = res.headers.get('Content-Disposition') || ''
      const filenameMatch = contentDisposition.match(/filename="?([^";]+)"?/i)
      const suggestedName = filenameMatch?.[1]
      const blob = new Blob([text], { type: 'application/x-yaml; charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = suggestedName || `${contract.name.toLowerCase().replace(/\s+/g, '_')}-odcs.yaml`
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      toast({ title: 'Export failed', description: e instanceof Error ? e.message : 'Unable to export', variant: 'destructive' })
    }
  }

  const addIri = async (iri: string) => {
    if (!contractId) return
    try {
      const res = await fetch(`/api/semantic-links/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          entity_id: contractId,
          entity_type: 'data_contract',
          iri,
        })
      })
      if (!res.ok) throw new Error('Failed to add concept')
      await fetchDetails()
      setIriDialogOpen(false)
      toast({ title: 'Linked', description: 'Business concept linked to data contract.' })
    } catch (e) {
      toast({ title: 'Error', description: e instanceof Error ? e.message : 'Failed to link business concept', variant: 'destructive' })
    }
  }

  const removeLink = async (linkId: string) => {
    try {
      const res = await fetch(`/api/semantic-links/${linkId}`, { method: 'DELETE' })
      if (!res.ok) throw new Error('Failed to remove concept')
      await fetchDetails()
      toast({ title: 'Unlinked', description: 'Business concept unlinked from data contract.' })
    } catch (e) {
      toast({ title: 'Error', description: e instanceof Error ? e.message : 'Failed to unlink business concept', variant: 'destructive' })
    }
  }

  const handleCreateNewVersion = () => {
    if (!contractId || !contract) {
      toast({ title: 'Permission Denied or Data Missing', description: 'Cannot create new version.', variant: 'destructive' })
      return
    }
    setIsVersionDialogOpen(true)
  }

  const submitNewVersion = async (newVersionString: string) => {
    if (!contractId) return
    toast({ title: 'Creating New Version', description: `Creating version ${newVersionString}...` })
    try {
      const res = await fetch(`/api/data-contracts/${contractId}/versions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ new_version: newVersionString.trim() })
      })
      if (!res.ok) {
        const text = await res.text().catch(() => '')
        throw new Error(text || 'Failed to create new version.')
      }
      const data = await res.json()
      const newId = data?.id
      if (!newId) throw new Error('Invalid response when creating version.')
      toast({ title: 'Success', description: `Version ${newVersionString} created successfully!` })
      setIsVersionDialogOpen(false)
      navigate(`/data-contracts/${newId}`)
    } catch (e: any) {
      toast({ title: 'Error', description: e?.message || 'Failed to create new version.', variant: 'destructive' })
    }
  }

  // CRUD handlers for main metadata
  const handleUpdateMetadata = async (payload: any) => {
    try {
      const res = await fetch(`/api/data-contracts/${contractId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: payload.name,
          version: payload.version,
          status: payload.status,
          owner_team_id: payload.owner_team_id,
          tenant: payload.tenant,
          dataProduct: payload.dataProduct,
          domainId: payload.domainId,
          descriptionUsage: payload.description?.usage,
          descriptionPurpose: payload.description?.purpose,
          descriptionLimitations: payload.description?.limitations,
        })
      })
      if (!res.ok) throw new Error('Update failed')
      await fetchDetails()
      toast({ title: 'Updated', description: 'Contract metadata updated.' })
    } catch (e) {
      toast({ title: 'Error', description: e instanceof Error ? e.message : 'Failed to update', variant: 'destructive' })
      throw e
    }
  }

  // Schema CRUD handlers
  const handleAddSchema = async (schema: SchemaObject) => {
    if (!contract) return
    const updatedSchemas = [...(contract.schema || []), schema]
    await updateContract({ schema: updatedSchemas })
  }

  const handleUpdateSchema = async (schema: SchemaObject) => {
    if (!contract || editingSchemaIndex === null) return
    const updatedSchemas = [...(contract.schema || [])]
    updatedSchemas[editingSchemaIndex] = schema
    await updateContract({ schema: updatedSchemas })
    setEditingSchemaIndex(null)
  }

  const handleDeleteSchema = async (index: number) => {
    if (!contract) return
    if (!confirm('Delete this schema?')) return
    const updatedSchemas = (contract.schema || []).filter((_, i) => i !== index)
    await updateContract({ schema: updatedSchemas })
  }

  // Quality Rule CRUD handlers
  const handleAddQualityRule = async (rule: QualityRule) => {
    if (!contract) return
    const updatedRules = [...(contract.qualityRules || []), rule]
    await updateContract({ qualityRules: updatedRules })
  }

  const handleUpdateQualityRule = async (rule: QualityRule) => {
    if (!contract || editingQualityRuleIndex === null) return
    const updatedRules = [...(contract.qualityRules || [])]
    updatedRules[editingQualityRuleIndex] = rule
    await updateContract({ qualityRules: updatedRules })
    setEditingQualityRuleIndex(null)
  }

  const handleDeleteQualityRule = async (index: number) => {
    if (!contract) return
    if (!confirm('Delete this quality rule?')) return
    const updatedRules = (contract.qualityRules || []).filter((_, i) => i !== index)
    await updateContract({ qualityRules: updatedRules })
  }

  // Team Member CRUD handlers
  const handleAddTeamMember = async (member: TeamMember) => {
    if (!contract) return
    const updatedTeam = [...(contract.team || []), member]
    await updateContract({ team: updatedTeam })
  }

  const handleUpdateTeamMember = async (member: TeamMember) => {
    if (!contract || editingTeamMemberIndex === null) return
    const updatedTeam = [...(contract.team || [])]
    updatedTeam[editingTeamMemberIndex] = member
    await updateContract({ team: updatedTeam })
    setEditingTeamMemberIndex(null)
  }

  const handleDeleteTeamMember = async (index: number) => {
    if (!contract) return
    if (!confirm('Remove this team member?')) return
    const updatedTeam = (contract.team || []).filter((_, i) => i !== index)
    await updateContract({ team: updatedTeam })
  }

  // Server Config CRUD handlers
  const handleAddServer = async (server: ServerConfig) => {
    if (!contract) return
    const currentServers = Array.isArray(contract.servers) ? contract.servers : (contract.servers ? [contract.servers] : [])
    const updatedServers = [...currentServers, server]
    await updateContract({ servers: updatedServers })
  }

  const handleUpdateServer = async (server: ServerConfig) => {
    if (!contract || editingServerIndex === null) return
    const currentServers = Array.isArray(contract.servers) ? contract.servers : (contract.servers ? [contract.servers] : [])
    const updatedServers = [...currentServers]
    updatedServers[editingServerIndex] = server
    await updateContract({ servers: updatedServers })
    setEditingServerIndex(null)
  }

  const handleDeleteServer = async (index: number) => {
    if (!contract) return
    if (!confirm('Delete this server configuration?')) return
    const currentServers = Array.isArray(contract.servers) ? contract.servers : (contract.servers ? [contract.servers] : [])
    const updatedServers = currentServers.filter((_, i) => i !== index)
    await updateContract({ servers: updatedServers })
  }

  // SLA handler
  const handleUpdateSLA = async (sla: SLARequirements) => {
    await updateContract({ sla })
  }

  // Helper to update contract (read-modify-write pattern)
  const updateContract = async (updates: Partial<any>) => {
    try {
      const res = await fetch(`/api/data-contracts/${contractId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates)
      })
      if (!res.ok) throw new Error('Update failed')
      await fetchDetails()
      toast({ title: 'Updated', description: 'Contract updated successfully.' })
    } catch (e) {
      toast({ title: 'Error', description: e instanceof Error ? e.message : 'Failed to update', variant: 'destructive' })
      throw e
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="h-12 w-12 animate-spin text-primary" />
      </div>
    )
  }
  if (error || !contract) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>{error || 'Contract not found.'}</AlertDescription>
      </Alert>
    )
  }

  const serversList = Array.isArray(contract.servers) ? contract.servers : (contract.servers ? [contract.servers] : [])

  return (
    <div className="py-6 space-y-6">
      <div className="flex items-center justify-between">
        <Button variant="outline" onClick={() => navigate('/data-contracts')} size="sm">
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to List
        </Button>
        <div className="flex items-center gap-2">
          <CommentSidebar
            entityType="data_contract"
            entityId={contractId!}
            isOpen={isCommentSidebarOpen}
            onToggle={() => setIsCommentSidebarOpen(!isCommentSidebarOpen)}
            className="h-8"
          />
          <Button variant="outline" onClick={() => setIsRequestAccessDialogOpen(true)} size="sm"><KeyRound className="mr-2 h-4 w-4" /> Request Access</Button>
          <Button variant="outline" onClick={handleCreateNewVersion} size="sm"><CopyPlus className="mr-2 h-4 w-4" /> Create New Version</Button>
          <Button variant="outline" onClick={() => setIsBasicFormOpen(true)} size="sm"><Pencil className="mr-2 h-4 w-4" /> Edit Metadata</Button>
          <Button variant="outline" onClick={exportOdcs} size="sm"><Download className="mr-2 h-4 w-4" /> Export ODCS</Button>
          <Button variant="destructive" onClick={handleDelete} size="sm"><Trash2 className="mr-2 h-4 w-4" /> Delete</Button>
        </div>
      </div>

      {/* Core Metadata Card */}
      <Card>
        <CardHeader>
          <CardTitle className="text-2xl font-bold flex items-center">
            <FileText className="mr-3 h-7 w-7 text-primary" />{contract.name}
          </CardTitle>
          <CardDescription className="pt-1">Core contract metadata</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid md:grid-cols-4 gap-4">
            <div className="space-y-1"><Label>Owner:</Label> <span className="text-sm block">{contract.owner_team_id || 'N/A'}</span></div>
            <div className="space-y-1"><Label>Status:</Label> <Badge variant="secondary" className="ml-1">{contract.status}</Badge></div>
            <div className="space-y-1"><Label>Version:</Label> <Badge variant="outline" className="ml-1">{contract.version}</Badge></div>
            <div className="space-y-1"><Label>API Version:</Label> <span className="text-sm block">{contract.apiVersion}</span></div>
            <div className="space-y-1">
              <Label>Domain:</Label>
              {(() => {
                const domainId = contract.domainId;
                const domainName = getDomainName(domainId) || contract.domain;
                return domainName && domainId ? (
                  <span
                    className="text-sm block cursor-pointer text-primary hover:underline"
                    onClick={() => navigate(`/data-domains/${domainId}`)}
                  >
                    {domainName}
                  </span>
                ) : (
                  <span className="text-sm block">{contract.domain || 'N/A'}</span>
                );
              })()}
            </div>
            <div className="space-y-1"><Label>Tenant:</Label> <span className="text-sm block">{contract.tenant || 'N/A'}</span></div>
            <div className="space-y-1"><Label>Data Product:</Label> <span className="text-sm block">{contract.dataProduct || 'N/A'}</span></div>
            <div className="space-y-1"><Label>Kind:</Label> <span className="text-sm block">{contract.kind}</span></div>
            <div className="space-y-1"><Label>Created:</Label> <span className="text-sm block">{contract.created || 'N/A'}</span></div>
            <div className="space-y-1"><Label>Updated:</Label> <span className="text-sm block">{contract.updated || 'N/A'}</span></div>
          </div>

          {/* Description */}
          {contract.description && (
            <div className="space-y-3">
              <Label className="text-base font-semibold">Description</Label>
              <div className="grid md:grid-cols-1 gap-3 pl-4">
                {contract.description.purpose && (
                  <div className="space-y-1">
                    <Label>Purpose:</Label>
                    <p className="text-sm text-muted-foreground">{contract.description.purpose}</p>
                  </div>
                )}
                {contract.description.usage && (
                  <div className="space-y-1">
                    <Label>Usage:</Label>
                    <p className="text-sm text-muted-foreground">{contract.description.usage}</p>
                  </div>
                )}
                {contract.description.limitations && (
                  <div className="space-y-1">
                    <Label>Limitations:</Label>
                    <p className="text-sm text-muted-foreground">{contract.description.limitations}</p>
                  </div>
                )}
              </div>
            </div>
          )}

          <div className="space-y-1">
            <Label>Linked Business Concepts:</Label>
            <LinkedConceptChips
              links={links}
              onRemove={(id) => removeLink(id)}
              trailing={<Button size="sm" variant="outline" onClick={() => setIriDialogOpen(true)}>Add Concept</Button>}
            />
          </div>
        </CardContent>
      </Card>

      {/* Schemas Section */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-xl">Schemas ({contract.schema?.length || 0})</CardTitle>
              <CardDescription>Database schema definitions</CardDescription>
            </div>
            <Button size="sm" onClick={() => { setEditingSchemaIndex(null); setIsSchemaFormOpen(true); }}>
              <Plus className="h-4 w-4 mr-1.5" />
              Add Schema
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {contract.schema && contract.schema.length > 0 ? (
            <div className="space-y-4">
              {contract.schema.map((schema, idx) => (
                <div key={idx} className="border rounded-lg p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="font-semibold">{schema.name}</h4>
                      {schema.physicalName && (
                        <p className="text-sm text-muted-foreground">{schema.physicalName}</p>
                      )}
                    </div>
                    <div className="flex gap-2">
                      <Button size="sm" variant="ghost" onClick={() => { setEditingSchemaIndex(idx); setIsSchemaFormOpen(true); }}>
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => handleDeleteSchema(idx)} className="text-destructive hover:text-destructive">
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                  <div className="text-sm text-muted-foreground">
                    {schema.properties?.length || 0} columns • {schema.physicalType || 'table'}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-8">No schemas defined. Click "Add Schema" to create one.</p>
          )}
        </CardContent>
      </Card>

      {/* Quality Rules Section */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-xl">Quality Rules ({contract.qualityRules?.length || 0})</CardTitle>
              <CardDescription>Data quality checks and validations</CardDescription>
            </div>
            <Button size="sm" onClick={() => { setEditingQualityRuleIndex(null); setIsQualityRuleFormOpen(true); }}>
              <Plus className="h-4 w-4 mr-1.5" />
              Add Rule
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {contract.qualityRules && contract.qualityRules.length > 0 ? (
            <div className="space-y-3">
              {contract.qualityRules.map((rule, idx) => (
                <div key={idx} className="border rounded-lg p-3 flex items-center justify-between">
                  <div>
                    <div className="font-medium">{rule.name}</div>
                    <div className="text-sm text-muted-foreground flex gap-2 mt-1">
                      <Badge variant="outline" className="text-xs">{rule.dimension}</Badge>
                      <Badge variant="secondary" className="text-xs">{rule.severity}</Badge>
                      <span>{rule.type}</span>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button size="sm" variant="ghost" onClick={() => { setEditingQualityRuleIndex(idx); setIsQualityRuleFormOpen(true); }}>
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button size="sm" variant="ghost" onClick={() => handleDeleteQualityRule(idx)} className="text-destructive hover:text-destructive">
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-8">No quality rules defined. Click "Add Rule" to create one.</p>
          )}
        </CardContent>
      </Card>

      {/* Team & Roles Section */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-xl">Team Members ({contract.team?.length || 0})</CardTitle>
              <CardDescription>Team responsible for this contract</CardDescription>
            </div>
            <Button size="sm" onClick={() => { setEditingTeamMemberIndex(null); setIsTeamMemberFormOpen(true); }}>
              <Plus className="h-4 w-4 mr-1.5" />
              Add Member
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {contract.team && contract.team.length > 0 ? (
            <div className="space-y-2">
              {contract.team.map((member, idx) => (
                <div key={idx} className="flex items-center justify-between p-3 border rounded-lg">
                  <div className="flex items-center gap-3">
                    <Badge variant="outline">{member.role}</Badge>
                    <span className="text-sm">{member.name || member.email}</span>
                  </div>
                  <div className="flex gap-2">
                    <Button size="sm" variant="ghost" onClick={() => { setEditingTeamMemberIndex(idx); setIsTeamMemberFormOpen(true); }}>
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button size="sm" variant="ghost" onClick={() => handleDeleteTeamMember(idx)} className="text-destructive hover:text-destructive">
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-8">No team members defined. Click "Add Member" to add one.</p>
          )}
        </CardContent>
      </Card>

      {/* SLA & Infrastructure Section */}
      <Card>
        <CardHeader>
          <CardTitle className="text-xl">SLA & Infrastructure</CardTitle>
          <CardDescription>Service level agreements and server configurations</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* SLA Requirements */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <Label className="text-base font-semibold">SLA Requirements</Label>
              <Button size="sm" variant="outline" onClick={() => setIsSLAFormOpen(true)}>
                <Pencil className="h-4 w-4 mr-1.5" />
                Edit SLA
              </Button>
            </div>
            {contract.sla && Object.keys(contract.sla).length > 0 ? (
              <div className="grid grid-cols-2 gap-3 pl-4">
                {contract.sla.uptimeTarget !== undefined && (
                  <div className="space-y-1">
                    <Label className="text-sm">Uptime Target:</Label>
                    <span className="text-sm text-muted-foreground block">{contract.sla.uptimeTarget}%</span>
                  </div>
                )}
                {contract.sla.maxDowntimeMinutes !== undefined && (
                  <div className="space-y-1">
                    <Label className="text-sm">Max Downtime:</Label>
                    <span className="text-sm text-muted-foreground block">{contract.sla.maxDowntimeMinutes} min</span>
                  </div>
                )}
                {contract.sla.queryResponseTimeMs !== undefined && (
                  <div className="space-y-1">
                    <Label className="text-sm">Query Response Time:</Label>
                    <span className="text-sm text-muted-foreground block">{contract.sla.queryResponseTimeMs} ms</span>
                  </div>
                )}
                {contract.sla.dataFreshnessMinutes !== undefined && (
                  <div className="space-y-1">
                    <Label className="text-sm">Data Freshness:</Label>
                    <span className="text-sm text-muted-foreground block">{contract.sla.dataFreshnessMinutes} min</span>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground pl-4">No SLA requirements defined.</p>
            )}
          </div>

          {/* Server Configurations */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <Label className="text-base font-semibold">Server Configurations ({serversList.length})</Label>
              <Button size="sm" onClick={() => { setEditingServerIndex(null); setIsServerConfigFormOpen(true); }}>
                <Plus className="h-4 w-4 mr-1.5" />
                Add Server
              </Button>
            </div>
            {serversList.length > 0 ? (
              <div className="space-y-2 pl-4">
                {serversList.map((server, idx) => (
                  <div key={idx} className="flex items-center justify-between p-3 border rounded-lg">
                    <div>
                      <div className="font-medium">{server.server}</div>
                      <div className="text-sm text-muted-foreground flex gap-2 mt-1">
                        <Badge variant="outline" className="text-xs">{server.type}</Badge>
                        <Badge variant="secondary" className="text-xs">{server.environment}</Badge>
                        {server.host && <span>{server.host}</span>}
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <Button size="sm" variant="ghost" onClick={() => { setEditingServerIndex(idx); setIsServerConfigFormOpen(true); }}>
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => handleDeleteServer(idx)} className="text-destructive hover:text-destructive">
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground pl-4">No server configurations defined.</p>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Access Control (read-only for now, can add edit later) */}
      {contract.accessControl && (
        <Card>
          <CardHeader>
            <CardTitle className="text-xl">Access Control</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid md:grid-cols-2 gap-3">
              {contract.accessControl.classification && (
                <div className="space-y-1">
                  <Label>Classification:</Label>
                  <Badge variant="secondary">{contract.accessControl.classification}</Badge>
                </div>
              )}
              <div className="space-y-1">
                <Label>Contains PII:</Label>
                <span className="text-sm">{contract.accessControl.containsPii ? 'Yes' : 'No'}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Custom Properties (read-only for now) */}
      {contract.customProperties && Object.keys(contract.customProperties).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-xl">Custom Properties</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {Object.entries(contract.customProperties).map(([key, value]) => (
                <div key={key} className="flex items-center gap-3">
                  <Label className="min-w-24">{key}:</Label>
                  <span className="text-sm text-muted-foreground">{String(value)}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Support Channels (read-only for now) */}
      {contract.support && Object.keys(contract.support).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-xl">Support</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {Object.entries(contract.support).map(([channel, url]) => (
                <div key={channel} className="flex items-center gap-3">
                  <Badge variant="outline" className="text-xs capitalize">{channel}</Badge>
                  {url ? (
                    <a href={url} target="_blank" rel="noreferrer" className="text-sm text-primary hover:underline break-all">{url}</a>
                  ) : (
                    <span className="text-sm text-muted-foreground">N/A</span>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Metadata Panel */}
      {contract.id && (
        <EntityMetadataPanel entityId={contract.id} entityType="data_contract" />
      )}

      {/* Dialogs */}
      <DataContractBasicFormDialog
        isOpen={isBasicFormOpen}
        onOpenChange={setIsBasicFormOpen}
        initial={{
          name: contract.name,
          version: contract.version,
          status: contract.status,
          owner_team_id: contract.owner_team_id,
          domain: contract.domainId,
          tenant: contract.tenant,
          dataProduct: contract.dataProduct,
          descriptionUsage: contract.description?.usage,
          descriptionPurpose: contract.description?.purpose,
          descriptionLimitations: contract.description?.limitations,
        }}
        onSubmit={handleUpdateMetadata}
      />

      <SchemaFormDialog
        isOpen={isSchemaFormOpen}
        onOpenChange={setIsSchemaFormOpen}
        initial={editingSchemaIndex !== null ? contract.schema?.[editingSchemaIndex] : undefined}
        onSubmit={editingSchemaIndex !== null ? handleUpdateSchema : handleAddSchema}
      />

      <QualityRuleFormDialog
        isOpen={isQualityRuleFormOpen}
        onOpenChange={setIsQualityRuleFormOpen}
        initial={editingQualityRuleIndex !== null ? contract.qualityRules?.[editingQualityRuleIndex] : undefined}
        onSubmit={editingQualityRuleIndex !== null ? handleUpdateQualityRule : handleAddQualityRule}
      />

      <TeamMemberFormDialog
        isOpen={isTeamMemberFormOpen}
        onOpenChange={setIsTeamMemberFormOpen}
        initial={editingTeamMemberIndex !== null ? contract.team?.[editingTeamMemberIndex] : undefined}
        onSubmit={editingTeamMemberIndex !== null ? handleUpdateTeamMember : handleAddTeamMember}
      />

      <ServerConfigFormDialog
        isOpen={isServerConfigFormOpen}
        onOpenChange={setIsServerConfigFormOpen}
        initial={editingServerIndex !== null ? serversList[editingServerIndex] : undefined}
        onSubmit={editingServerIndex !== null ? handleUpdateServer : handleAddServer}
      />

      <SLAFormDialog
        isOpen={isSLAFormOpen}
        onOpenChange={setIsSLAFormOpen}
        initial={contract.sla}
        onSubmit={handleUpdateSLA}
      />

      <ConceptSelectDialog
        isOpen={iriDialogOpen}
        onOpenChange={setIriDialogOpen}
        onSelect={addIri}
      />

      {contract && (
        <CreateVersionDialog
          isOpen={isVersionDialogOpen}
          onOpenChange={setIsVersionDialogOpen}
          currentVersion={contract.version}
          productTitle={contract.name}
          onSubmit={submitNewVersion}
        />
      )}

      {contract && (
        <RequestAccessDialog
          isOpen={isRequestAccessDialogOpen}
          onOpenChange={setIsRequestAccessDialogOpen}
          entityType="data_contract"
          entityId={contractId!}
          entityName={contract.name}
        />
      )}
    </div>
  )
}
