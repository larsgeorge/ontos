import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { AlertCircle, Download, Pencil, Trash2, Loader2, ArrowLeft, FileText, KeyRound, CopyPlus, Plus, Shapes, Columns2, Database, Sparkles } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { DataTable } from '@/components/ui/data-table'
import { ColumnDef } from '@tanstack/react-table'
import { useToast } from '@/hooks/use-toast'
import EntityMetadataPanel from '@/components/metadata/entity-metadata-panel'
import { CommentSidebar } from '@/components/comments'
import ConceptSelectDialog from '@/components/semantic/concept-select-dialog'
import LinkedConceptChips from '@/components/semantic/linked-concept-chips'
import { useDomains } from '@/hooks/use-domains'
import type { EntitySemanticLink } from '@/types/semantic-link'
import type { DataContract, SchemaObject, QualityRule, TeamMember, ServerConfig, SLARequirements } from '@/types/data-contract'
import useBreadcrumbStore from '@/stores/breadcrumb-store'
import RequestContractActionDialog from '@/components/data-contracts/request-contract-action-dialog'
import CreateVersionDialog from '@/components/data-products/create-version-dialog'
import DataContractBasicFormDialog from '@/components/data-contracts/data-contract-basic-form-dialog'
import SchemaFormDialog from '@/components/data-contracts/schema-form-dialog'
import QualityRuleFormDialog from '@/components/data-contracts/quality-rule-form-dialog'
import TeamMemberFormDialog from '@/components/data-contracts/team-member-form-dialog'
import ServerConfigFormDialog from '@/components/data-contracts/server-config-form-dialog'
import SLAFormDialog from '@/components/data-contracts/sla-form-dialog'
import DatasetLookupDialog from '@/components/data-contracts/dataset-lookup-dialog'
import CreateFromContractDialog from '@/components/data-products/create-from-contract-dialog'
import DqxSchemaSelectDialog from '@/components/data-contracts/dqx-schema-select-dialog'
import DqxSuggestionsDialog from '@/components/data-contracts/dqx-suggestions-dialog'
import type { DataProduct } from '@/types/data-product'
import type { DataProfilingRun } from '@/types/data-contract'

// Define column structure for schema properties
type SchemaProperty = {
  name: string
  logicalType?: string
  logical_type?: string  // API response uses underscore
  required: boolean
  unique: boolean
  description?: string
}

// Define this as a function to access component state
const createSchemaPropertyColumns = (
  contract: DataContract | null,
  selectedSchemaIndex: number,
  propertyLinks: Record<string, EntitySemanticLink[]>
): ColumnDef<SchemaProperty>[] => [
  {
    accessorKey: 'name',
    header: 'Column Name',
    cell: ({ row }) => {
      const property = row.original
      const schemaName = contract?.schema?.[selectedSchemaIndex]?.name || ''
      const propertyKey = `${schemaName}#${property.name}`
      const links = propertyLinks[propertyKey] || []

      const getLabel = (iri: string, label?: string) => (label && !/^https?:\/\//.test(label) && !/^urn:/.test(label)) ? label : (iri.split(/[\/#]/).pop() || iri)
      return (
        <div>
          <span className="font-mono font-medium">{property.name}</span>
          {links.length > 0 && (
            <div className="text-xs text-muted-foreground mt-1 flex flex-wrap gap-2">
              {links.map((link, idx) => (
                <span key={idx} className="inline-flex items-center gap-1">
                  <Columns2 className="h-3 w-3" />
                  <span
                    className="cursor-pointer hover:underline"
                    onClick={() => window.open(`/search?startIri=${encodeURIComponent(link.iri)}`, '_blank')}
                    title={link.iri}
                  >
                    {getLabel(link.iri, link.label)}
                  </span>
                </span>
              ))}
            </div>
          )}
        </div>
      )
    },
  },
  {
    accessorKey: 'logicalType',
    header: 'Data Type',
    cell: ({ row }) => {
      const property = row.original
      const logicalType = property.logicalType || (property as any).logical_type
      return (
        <Badge variant="secondary" className="text-xs">
          {logicalType || 'N/A'}
        </Badge>
      )
    },
  },
  {
    accessorKey: 'required',
    header: 'Required',
    cell: ({ row }) => (
      <span className="text-center block">
        {row.getValue('required') ? '✓' : '✗'}
      </span>
    ),
  },
  {
    accessorKey: 'unique',
    header: 'Unique',
    cell: ({ row }) => (
      <span className="text-center block">
        {row.getValue('unique') ? '✓' : '✗'}
      </span>
    ),
  },
  {
    accessorKey: 'description',
    header: 'Description',
    cell: ({ row }) => (
      <span className="text-muted-foreground text-sm">
        {row.getValue('description') || '-'}
      </span>
    ),
  },
]

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
  const [isRequestDialogOpen, setIsRequestDialogOpen] = useState(false)
  const [isVersionDialogOpen, setIsVersionDialogOpen] = useState(false)
  const [links, setLinks] = useState<EntitySemanticLink[]>([])
  const [selectedSchemaIndex, setSelectedSchemaIndex] = useState(0)
  const [schemaLinks, setSchemaLinks] = useState<Record<string, EntitySemanticLink[]>>({})
  const [propertyLinks, setPropertyLinks] = useState<Record<string, EntitySemanticLink[]>>({})

  // Linked products state
  const [linkedProducts, setLinkedProducts] = useState<DataProduct[]>([])
  const [loadingProducts, setLoadingProducts] = useState(false)
  const [isCreateProductDialogOpen, setIsCreateProductDialogOpen] = useState(false)

  // Dialog states for CRUD operations
  const [isDatasetLookupOpen, setIsDatasetLookupOpen] = useState(false)
  const [isBasicFormOpen, setIsBasicFormOpen] = useState(false)
  const [isSchemaFormOpen, setIsSchemaFormOpen] = useState(false)
  const [isQualityRuleFormOpen, setIsQualityRuleFormOpen] = useState(false)
  const [isTeamMemberFormOpen, setIsTeamMemberFormOpen] = useState(false)
  const [isServerConfigFormOpen, setIsServerConfigFormOpen] = useState(false)
  const [isSLAFormOpen, setIsSLAFormOpen] = useState(false)

  // DQX Profiling states
  const [isDqxSchemaSelectOpen, setIsDqxSchemaSelectOpen] = useState(false)
  const [isDqxSuggestionsOpen, setIsDqxSuggestionsOpen] = useState(false)
  const [selectedProfileRunId, setSelectedProfileRunId] = useState<string | null>(null)
  const [latestProfileRun, setLatestProfileRun] = useState<DataProfilingRun | null>(null)
  const [pendingSuggestionsCount, setPendingSuggestionsCount] = useState(0)

  // Editing states
  const [editingSchemaIndex, setEditingSchemaIndex] = useState<number | null>(null)
  const [editingQualityRuleIndex, setEditingQualityRuleIndex] = useState<number | null>(null)
  const [editingTeamMemberIndex, setEditingTeamMemberIndex] = useState<number | null>(null)
  const [editingServerIndex, setEditingServerIndex] = useState<number | null>(null)

  const fetchLinkedProducts = async () => {
    if (!contractId) return
    setLoadingProducts(true)
    try {
      const response = await fetch(`/api/data-products/by-contract/${contractId}`)
      if (response.ok) {
        const data = await response.json()
        setLinkedProducts(Array.isArray(data) ? data : [])
      } else {
        setLinkedProducts([])
      }
    } catch (e) {
      console.warn('Failed to fetch linked products:', e)
      setLinkedProducts([])
    } finally {
      setLoadingProducts(false)
    }
  }

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

      // Fetch schema and property semantic links if contract has schemas
      if (contractData?.schema) {
        const schemaLinksMap: Record<string, EntitySemanticLink[]> = {}
        const propertyLinksMap: Record<string, EntitySemanticLink[]> = {}

        for (const schema of contractData.schema) {
          // Fetch schema-level semantic links
          const schemaEntityId = `${contractId}#${schema.name}`
          try {
            const schemaLinksRes = await fetch(`/api/semantic-links/entity/data_contract_schema/${encodeURIComponent(schemaEntityId)}`)
            if (schemaLinksRes.ok) {
              const schemaLinksData = await schemaLinksRes.json()
              schemaLinksMap[schema.name] = Array.isArray(schemaLinksData) ? schemaLinksData : []
            }
          } catch (e) {
            console.warn(`Failed to fetch schema links for ${schema.name}:`, e)
          }

          // Fetch property-level semantic links
          if (schema.properties) {
            for (const property of schema.properties) {
              const propertyEntityId = `${contractId}#${schema.name}#${property.name}`
              const propertyKey = `${schema.name}#${property.name}`
              try {
                const propertyLinksRes = await fetch(`/api/semantic-links/entity/data_contract_property/${encodeURIComponent(propertyEntityId)}`)
                if (propertyLinksRes.ok) {
                  const propertyLinksData = await propertyLinksRes.json()
                  propertyLinksMap[propertyKey] = Array.isArray(propertyLinksData) ? propertyLinksData : []
                }
              } catch (e) {
                console.warn(`Failed to fetch property links for ${propertyKey}:`, e)
              }
            }
          }
        }

        setSchemaLinks(schemaLinksMap)
        setPropertyLinks(propertyLinksMap)
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
    fetchLinkedProducts()
    fetchProfileRuns()

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

  // Handler for inferring schema from Unity Catalog dataset
  const handleInferFromDataset = async (table: { full_name: string }) => {
    const datasetPath = table.full_name
    const logicalName = datasetPath.split('.').pop() || datasetPath

    try {
      // Fetch columns from Unity Catalog
      const res = await fetch(`/api/catalogs/dataset/${encodeURIComponent(datasetPath)}`)
      if (!res.ok) throw new Error('Failed to load dataset schema')
      const data = await res.json()

      // Map Unity Catalog columns to ODCS schema properties
      const properties = Array.isArray(data?.schema)
        ? data.schema.map((c: any) => ({
            name: String(c.name || ''),
            physicalType: String(c.physicalType || c.type || ''),
            logicalType: String(c.logicalType || c.logical_type || 'string'),
            required: c.nullable === undefined ? undefined : !Boolean(c.nullable),
            description: String(c.comment || ''),
            partitioned: Boolean(c.partitioned),
            partitionKeyPosition: c.partitionKeyPosition || undefined,
          }))
        : []

      // Create new schema object with Unity Catalog metadata
      const newSchema: SchemaObject = {
        name: logicalName,
        physicalName: datasetPath, // Use Unity Catalog three-part name (catalog.schema.table)
        properties: properties,
        description: data.table_info?.comment || undefined,
        physicalType: data.table_info?.table_type || 'table',
      }

      // Add schema to contract
      await handleAddSchema(newSchema)
      
      const columnCount = properties.length
      toast({ 
        title: 'Schema inferred successfully', 
        description: `Added ${logicalName} with ${columnCount} columns from Unity Catalog` 
      })
      
      setIsDatasetLookupOpen(false)
    } catch (e) {
      toast({ 
        title: 'Failed to infer schema', 
        description: e instanceof Error ? e.message : 'Could not fetch dataset metadata', 
        variant: 'destructive' 
      })
    }
  }

  const handleSubmitForReview = async () => {
    if (!contractId) return;
    try {
      const res = await fetch(`/api/data-contracts/${contractId}/submit`, { method: 'POST' });
      if (!res.ok) throw new Error(`Submit failed (${res.status})`);
      await fetchDetails();
      toast({ title: 'Submitted', description: 'Contract submitted for review.' });
    } catch (e: any) {
      toast({ title: 'Error', description: e?.message || 'Submit failed', variant: 'destructive' });
    }
  };

  const handleApprove = async () => {
    if (!contractId) return;
    try {
      const res = await fetch(`/api/data-contracts/${contractId}/approve`, { method: 'POST' });
      if (!res.ok) throw new Error(`Approve failed (${res.status})`);
      await fetchDetails();
      toast({ title: 'Approved', description: 'Contract approved.' });
    } catch (e: any) {
      toast({ title: 'Error', description: e?.message || 'Approve failed', variant: 'destructive' });
    }
  };

  const handleReject = async () => {
    if (!contractId) return;
    try {
      const res = await fetch(`/api/data-contracts/${contractId}/reject`, { method: 'POST' });
      if (!res.ok) throw new Error(`Reject failed (${res.status})`);
      await fetchDetails();
      toast({ title: 'Rejected', description: 'Contract rejected.' });
    } catch (e: any) {
      toast({ title: 'Error', description: e?.message || 'Reject failed', variant: 'destructive' });
    }
  };

  // DQX Profiling handlers
  const fetchProfileRuns = async () => {
    if (!contractId) return
    try {
      const res = await fetch(`/api/data-contracts/${contractId}/profile-runs`)
      if (res.ok) {
        const runs: DataProfilingRun[] = await res.json()
        if (runs.length > 0) {
          const latest = runs[0]
          setLatestProfileRun(latest)
          setPendingSuggestionsCount(latest.suggestion_counts?.pending || 0)
        }
      }
    } catch (e) {
      console.warn('Failed to fetch profile runs:', e)
    }
  }

  const handleStartProfiling = async (selectedSchemaNames: string[]) => {
    if (!contractId) return
    try {
      const res = await fetch(`/api/data-contracts/${contractId}/profile`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ schema_names: selectedSchemaNames })
      })
      if (!res.ok) {
        const errorText = await res.text()
        throw new Error(errorText || 'Failed to start profiling')
      }
      await res.json()
      toast({ 
        title: 'DQX Profiling Started', 
        description: 'The profiler is analyzing your data. You will be notified when complete.' 
      })
      setIsDqxSchemaSelectOpen(false)
      // Poll for updates after a delay
      setTimeout(fetchProfileRuns, 5000)
    } catch (e) {
      toast({ 
        title: 'Failed to start profiling', 
        description: e instanceof Error ? e.message : 'Could not start DQX profiling', 
        variant: 'destructive' 
      })
    }
  }

  const handleOpenSuggestions = (runId?: string) => {
    const profileId = runId || latestProfileRun?.id
    if (profileId) {
      setSelectedProfileRunId(profileId)
      setIsDqxSuggestionsOpen(true)
    }
  }

  const handleSuggestionsSuccess = () => {
    fetchDetails()
    fetchProfileRuns()
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
          {/* Lifecycle actions */}
          {contract && (contract.status?.toLowerCase() === 'draft') && (
            <Button size="sm" onClick={handleSubmitForReview}>Submit for Review</Button>
          )}
          {contract && (['proposed','under_review'].includes((contract.status || '').toLowerCase())) && (
            <>
              <Button size="sm" variant="outline" onClick={handleApprove}>Approve</Button>
              <Button size="sm" variant="destructive" onClick={handleReject}>Reject</Button>
            </>
          )}
          <CommentSidebar
            entityType="data_contract"
            entityId={contractId!}
            isOpen={isCommentSidebarOpen}
            onToggle={() => setIsCommentSidebarOpen(!isCommentSidebarOpen)}
            className="h-8"
          />
          <Button variant="outline" onClick={() => setIsRequestDialogOpen(true)} size="sm"><KeyRound className="mr-2 h-4 w-4" /> Request...</Button>
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
            <div className="space-y-1">
              <Label>Status:</Label> 
              <Badge variant="secondary" className="ml-1">{contract.status}</Badge>
              {contract.published && (
                <Badge variant="default" className="ml-1 bg-green-600">Published</Badge>
              )}
            </div>
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

      {/* Linked Data Products Section */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-xl flex items-center gap-2">
                <Shapes className="h-5 w-5 text-primary" />
                Linked Data Products ({linkedProducts.length})
              </CardTitle>
              <CardDescription>Data Products using this contract for output ports</CardDescription>
            </div>
            <Button
              size="sm"
              onClick={() => setIsCreateProductDialogOpen(true)}
              disabled={!contract || !['active', 'approved', 'certified'].includes((contract.status || '').toLowerCase())}
            >
              <Plus className="h-4 w-4 mr-1.5" />
              Create Data Product
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {loadingProducts ? (
            <div className="flex justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
            </div>
          ) : linkedProducts.length === 0 ? (
            <div className="text-center py-12 border-2 border-dashed border-muted-foreground/25 rounded-lg">
              <Shapes className="h-12 w-12 mx-auto text-muted-foreground/50 mb-3" />
              <div className="text-muted-foreground mb-2">No linked data products yet</div>
              <div className="text-sm text-muted-foreground mb-4">
                Create a data product that uses this contract to govern an output port
              </div>
              {contract && ['active', 'approved', 'certified'].includes((contract.status || '').toLowerCase()) ? (
                <Button onClick={() => setIsCreateProductDialogOpen(true)}>
                  <Plus className="h-4 w-4 mr-2" />
                  Create Data Product
                </Button>
              ) : (
                <div className="text-sm text-muted-foreground italic">
                  Contract must be in 'active', 'approved', or 'certified' status
                </div>
              )}
            </div>
          ) : (
            <div className="space-y-3">
              {linkedProducts.map((product) => (
                <div
                  key={product.id}
                  className="p-4 border rounded-lg hover:bg-muted/50 transition-colors cursor-pointer"
                  onClick={() => navigate(`/data-products/${product.id}`)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="font-medium text-base">{product.info?.title || 'Untitled Product'}</div>
                      {product.info?.description && (
                        <p className="text-sm text-muted-foreground mt-1">{product.info.description}</p>
                      )}
                      <div className="flex items-center gap-3 mt-2">
                        <Badge variant="secondary" className="text-xs">
                          {product.productType || 'N/A'}
                        </Badge>
                        <Badge variant="outline" className="text-xs">
                          {product.version}
                        </Badge>
                        {product.info?.status && (
                          <Badge variant="secondary" className="text-xs">
                            {product.info.status}
                          </Badge>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
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
            <div className="flex gap-2">
              <Button 
                size="sm" 
                variant="outline" 
                onClick={() => setIsDqxSchemaSelectOpen(true)}
                disabled={!contract.schema || contract.schema.length === 0}
              >
                <Sparkles className="h-4 w-4 mr-1.5" />
                Profile with DQX
              </Button>
              <Button size="sm" variant="outline" onClick={() => setIsDatasetLookupOpen(true)}>
                <Database className="h-4 w-4 mr-1.5" />
                Infer from Unity Catalog
              </Button>
              <Button size="sm" onClick={() => { setEditingSchemaIndex(null); setIsSchemaFormOpen(true); }}>
                <Plus className="h-4 w-4 mr-1.5" />
                Add Schema
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {pendingSuggestionsCount > 0 && (
            <Alert className="mb-4">
              <Sparkles className="h-4 w-4" />
              <AlertDescription className="flex items-center justify-between">
                <span>
                  {pendingSuggestionsCount} quality check {pendingSuggestionsCount === 1 ? 'suggestion' : 'suggestions'} available from DQX profiling
                </span>
                <Button 
                  size="sm" 
                  variant="outline" 
                  onClick={() => handleOpenSuggestions()}
                >
                  Review Suggestions
                </Button>
              </AlertDescription>
            </Alert>
          )}
          {!contract.schema || contract.schema.length === 0 ? (
            <div className="text-center py-12 border-2 border-dashed border-muted-foreground/25 rounded-lg">
              <div className="text-muted-foreground mb-2">No schemas defined yet</div>
              <div className="text-sm text-muted-foreground mb-4">Define the structure of your data by adding schemas</div>
              <div className="flex gap-3 justify-center">
                <Button variant="outline" onClick={() => setIsDatasetLookupOpen(true)}>
                  <Database className="h-4 w-4 mr-2" />
                  Infer from Unity Catalog
                </Button>
                <Button onClick={() => { setEditingSchemaIndex(null); setIsSchemaFormOpen(true); }}>
                  <Plus className="h-4 w-4 mr-2" />
                  Add Schema Manually
                </Button>
              </div>
            </div>
          ) : contract.schema.length === 1 ? (
              // Single schema - simple view
              <div className="space-y-4">
                <div className="flex items-center gap-4 justify-between">
                  <div>
                    <Label className="text-base font-semibold">{contract.schema[0].name || 'Table 1'}</Label>
                    {contract.schema[0].name && schemaLinks[contract.schema[0].name] && schemaLinks[contract.schema[0].name].length > 0 && (
                      <div className="text-xs text-muted-foreground mt-1 flex flex-wrap gap-2">
                        {schemaLinks[contract.schema[0].name].map((link, idx) => (
                          <span key={idx} className="inline-flex items-center gap-1">
                            <Shapes className="h-3 w-3" />
                            <span
                              className="cursor-pointer hover:underline"
                              onClick={() => window.open(`/search?startIri=${encodeURIComponent(link.iri)}`, '_blank')}
                              title={link.iri}
                            >
                              {(link.label && !/^https?:\/\//.test(link.label) && !/^urn:/.test(link.label)) ? link.label : (link.iri.split(/[\/#]/).pop() || link.iri)}
                            </span>
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                  <div className="flex gap-2">
                    {contract.schema[0].physicalName && (
                      <a
                        href={`/catalog-explorer?table=${encodeURIComponent(contract.schema[0].physicalName)}`}
                        className="flex items-center gap-1.5 text-sm text-primary hover:underline"
                        target="_blank"
                        rel="noopener noreferrer"
                        title={`Open ${contract.schema[0].physicalName} in Catalog Explorer`}
                      >
                        <Database className="h-4 w-4" />
                        {contract.schema[0].physicalName}
                      </a>
                    )}
                    <Button size="sm" variant="ghost" onClick={() => { setEditingSchemaIndex(0); setIsSchemaFormOpen(true); }}>
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button size="sm" variant="ghost" onClick={() => handleDeleteSchema(0)} className="text-destructive hover:text-destructive">
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
                {contract.schema[0].properties && contract.schema[0].properties.length > 0 && (
                  <DataTable
                    columns={createSchemaPropertyColumns(contract, 0, propertyLinks)}
                    data={contract.schema[0].properties as SchemaProperty[]}
                    searchColumn="name"
                  />
                )}
              </div>
            ) : contract.schema.length > 6 ? (
              // Many schemas - use dropdown selector
              <div className="space-y-4">
                <div className="flex items-center gap-4">
                  <Label>Select Schema:</Label>
                  <Select value={selectedSchemaIndex.toString()} onValueChange={(value) => setSelectedSchemaIndex(parseInt(value))}>
                    <SelectTrigger className="w-80">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="max-h-[40vh] overflow-y-auto" position="popper" sideOffset={5}>
                      {contract.schema.map((schemaObj, idx) => (
                        <SelectItem key={idx} value={idx.toString()}>
                          {schemaObj.name || `Table ${idx + 1}`} ({schemaObj.properties?.length || 0} columns)
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-4">
                  <div className="flex items-center gap-4 justify-between">
                    <div>
                      <Label className="text-base font-semibold">{contract.schema[selectedSchemaIndex]?.name || `Table ${selectedSchemaIndex + 1}`}</Label>
                      {contract.schema[selectedSchemaIndex]?.name && schemaLinks[contract.schema[selectedSchemaIndex].name] && schemaLinks[contract.schema[selectedSchemaIndex].name].length > 0 && (
                        <div className="text-xs text-muted-foreground mt-1 flex flex-wrap gap-2">
                          {schemaLinks[contract.schema[selectedSchemaIndex].name].map((link, idx) => (
                            <span key={idx} className="inline-flex items-center gap-1">
                              <Shapes className="h-3 w-3" />
                              <span
                                className="cursor-pointer hover:underline"
                                onClick={() => window.open(`/search?startIri=${encodeURIComponent(link.iri)}`, '_blank')}
                                title={link.iri}
                              >
                                {(link.label && !/^https?:\/\//.test(link.label) && !/^urn:/.test(link.label)) ? link.label : (link.iri.split(/[\/#]/).pop() || link.iri)}
                              </span>
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                    <div className="flex gap-2">
                      {contract.schema[selectedSchemaIndex]?.physicalName && (
                        <a
                          href={`/catalog-explorer?table=${encodeURIComponent(contract.schema[selectedSchemaIndex].physicalName)}`}
                          className="flex items-center gap-1.5 text-sm text-primary hover:underline"
                          target="_blank"
                          rel="noopener noreferrer"
                          title={`Open ${contract.schema[selectedSchemaIndex].physicalName} in Catalog Explorer`}
                        >
                          <Database className="h-4 w-4" />
                          {contract.schema[selectedSchemaIndex].physicalName}
                        </a>
                      )}
                      <Button size="sm" variant="ghost" onClick={() => { setEditingSchemaIndex(selectedSchemaIndex); setIsSchemaFormOpen(true); }}>
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => handleDeleteSchema(selectedSchemaIndex)} className="text-destructive hover:text-destructive">
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                  {contract.schema[selectedSchemaIndex]?.properties && contract.schema[selectedSchemaIndex].properties.length > 0 && (
                    <DataTable
                      columns={createSchemaPropertyColumns(contract, selectedSchemaIndex, propertyLinks)}
                      data={contract.schema[selectedSchemaIndex].properties as SchemaProperty[]}
                      searchColumn="name"
                    />
                  )}
                </div>
              </div>
            ) : (
              // Few schemas - use tabs with custom scrollable container
              <div className="space-y-4">
                <div className="w-full overflow-x-auto">
                  <div className="flex border-b border-border">
                    {contract.schema.map((schemaObj, idx) => (
                      <button
                        key={idx}
                        onClick={() => setSelectedSchemaIndex(idx)}
                        className={`flex-shrink-0 px-4 py-2 text-sm font-medium whitespace-nowrap border-b-2 transition-colors ${
                          selectedSchemaIndex === idx
                            ? 'border-primary text-primary'
                            : 'border-transparent text-muted-foreground hover:text-foreground hover:border-muted-foreground'
                        }`}
                      >
                        {schemaObj.name || `Table ${idx + 1}`}
                        <span className="ml-2 text-xs">
                          ({schemaObj.properties?.length || 0})
                        </span>
                      </button>
                    ))}
                  </div>
                </div>
                <div className="space-y-4">
                  <div className="flex items-center gap-4 justify-between">
                    <div>
                      <Label className="text-base font-semibold">{contract.schema[selectedSchemaIndex]?.name || `Table ${selectedSchemaIndex + 1}`}</Label>
                      {contract.schema[selectedSchemaIndex]?.name && schemaLinks[contract.schema[selectedSchemaIndex].name] && schemaLinks[contract.schema[selectedSchemaIndex].name].length > 0 && (
                        <div className="text-xs text-muted-foreground mt-1 flex flex-wrap gap-2">
                          {schemaLinks[contract.schema[selectedSchemaIndex].name].map((link, idx) => (
                            <span key={idx} className="inline-flex items-center gap-1">
                              <Shapes className="h-3 w-3" />
                              <span
                                className="cursor-pointer hover:underline"
                                onClick={() => window.open(`/search?startIri=${encodeURIComponent(link.iri)}`, '_blank')}
                                title={link.iri}
                              >
                                {(link.label && !/^https?:\/\//.test(link.label) && !/^urn:/.test(link.label)) ? link.label : (link.iri.split(/[\/#]/).pop() || link.iri)}
                              </span>
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                    <div className="flex gap-2">
                      {contract.schema[selectedSchemaIndex]?.physicalName && (
                        <a
                          href={`/catalog-explorer?table=${encodeURIComponent(contract.schema[selectedSchemaIndex].physicalName)}`}
                          className="flex items-center gap-1.5 text-sm text-primary hover:underline"
                          target="_blank"
                          rel="noopener noreferrer"
                          title={`Open ${contract.schema[selectedSchemaIndex].physicalName} in Catalog Explorer`}
                        >
                          <Database className="h-4 w-4" />
                          {contract.schema[selectedSchemaIndex].physicalName}
                        </a>
                      )}
                      <Button size="sm" variant="ghost" onClick={() => { setEditingSchemaIndex(selectedSchemaIndex); setIsSchemaFormOpen(true); }}>
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => handleDeleteSchema(selectedSchemaIndex)} className="text-destructive hover:text-destructive">
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                  {contract.schema[selectedSchemaIndex]?.properties && contract.schema[selectedSchemaIndex].properties.length > 0 && (
                    <DataTable
                      columns={createSchemaPropertyColumns(contract, selectedSchemaIndex, propertyLinks)}
                      data={contract.schema[selectedSchemaIndex].properties as SchemaProperty[]}
                      searchColumn="name"
                    />
                  )}
                </div>
              </div>
            )
          }
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
        <RequestContractActionDialog
          isOpen={isRequestDialogOpen}
          onOpenChange={setIsRequestDialogOpen}
          contractId={contractId!}
          contractName={contract.name}
          contractStatus={contract.status}
          onSuccess={() => fetchDetails()}
        />
      )}

      <DatasetLookupDialog
        isOpen={isDatasetLookupOpen}
        onOpenChange={setIsDatasetLookupOpen}
        onSelect={handleInferFromDataset}
      />

      {contract && (
        <CreateFromContractDialog
          isOpen={isCreateProductDialogOpen}
          onOpenChange={setIsCreateProductDialogOpen}
          contractId={contractId!}
          contractName={contract.name}
          onSuccess={(productId) => {
            fetchLinkedProducts()
            navigate(`/data-products/${productId}`)
          }}
        />
      )}

      {/* DQX Profiling Dialogs */}
      <DqxSchemaSelectDialog
        isOpen={isDqxSchemaSelectOpen}
        onOpenChange={setIsDqxSchemaSelectOpen}
        contract={contract}
        onConfirm={handleStartProfiling}
      />

      {selectedProfileRunId && (
        <DqxSuggestionsDialog
          isOpen={isDqxSuggestionsOpen}
          onOpenChange={setIsDqxSuggestionsOpen}
          contractId={contractId!}
          contract={contract}
          profileRunId={selectedProfileRunId}
          onSuccess={handleSuggestionsSuccess}
        />
      )}
    </div>
  )
}
