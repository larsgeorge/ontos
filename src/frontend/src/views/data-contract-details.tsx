import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { AlertCircle, Download, Pencil, Trash2, Loader2, ArrowLeft, FileText, KeyRound, Shapes, Columns2 } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { DataTable } from '@/components/ui/data-table'
import { ColumnDef } from '@tanstack/react-table'
import DataContractWizardDialog from '@/components/data-contracts/data-contract-wizard-dialog'
import { useToast } from '@/hooks/use-toast'
import EntityMetadataPanel from '@/components/metadata/entity-metadata-panel'
import { CommentSidebar } from '@/components/comments'
import ConceptSelectDialog from '@/components/semantic/concept-select-dialog'
import LinkedConceptChips from '@/components/semantic/linked-concept-chips'
import { useDomains } from '@/hooks/use-domains'
import type { EntitySemanticLink } from '@/types/semantic-link'
import type { DataContract } from '@/types/data-contract'
import useBreadcrumbStore from '@/stores/breadcrumb-store'

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
  const [isWizardOpen, setIsWizardOpen] = useState(false)
  const [isCommentSidebarOpen, setIsCommentSidebarOpen] = useState(false)
  const [iriDialogOpen, setIriDialogOpen] = useState(false)
  const [links, setLinks] = useState<EntitySemanticLink[]>([])
  const [selectedSchemaIndex, setSelectedSchemaIndex] = useState(0)
  const [schemaLinks, setSchemaLinks] = useState<Record<string, EntitySemanticLink[]>>({})
  const [propertyLinks, setPropertyLinks] = useState<Record<string, EntitySemanticLink[]>>({})

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
      
      let contractData: DataContract | null = null
      if (contractRes.ok) {
        contractData = await contractRes.json()
      } else {
        // Fallback: try list endpoint and hydrate a minimal model
        const listRes = await fetch('/api/data-contracts')
        if (listRes.ok) {
          const items: any[] = await listRes.json()
          const found = items.find((i) => i.id === contractId)
          if (found) {
            contractData = {
              id: found.id,
              kind: 'DataContract',
              apiVersion: 'v3.0.2',
              version: found.version,
              status: found.status,
              name: found.name,
              owner: found.owner,
              tenant: found.tenant,
              domain: undefined,
              dataProduct: found.dataProduct,
              description: undefined,
              schema: [],
              qualityRules: [],
              team: [],
              accessControl: undefined,
              support: undefined,
              sla: undefined,
              servers: undefined,
              customProperties: {},
              created: found.created,
              updated: found.updated,
            } as DataContract
          }
        }
      }

      if (!contractData) throw new Error('Failed to load contract')

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

  // Legacy export removed - ODCS export is the primary method

  const exportOdcs = async () => {
    if (!contractId || !contract) return
    try {
      const res = await fetch(`/api/data-contracts/${contractId}/odcs/export`)
      if (!res.ok) throw new Error('Export ODCS failed')
      // Backend returns YAML; read as text and download as .yaml
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

  const requestAccess = async () => {
    if (!contractId || !contract) return
    try {
      const res = await fetch(`/api/access-requests`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ entity_type: 'data_contract', entity_ids: [contractId] })
      })
      if (!res.ok) throw new Error('Failed to submit access request')
      toast({ title: 'Request Sent', description: 'Access request submitted. You will be notified.' })
    } catch (e) {
      toast({ title: 'Error', description: e instanceof Error ? e.message : 'Failed to submit request', variant: 'destructive' })
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
          <Button variant="outline" onClick={requestAccess} size="sm"><KeyRound className="mr-2 h-4 w-4" /> Request Access</Button>
          <Button variant="outline" onClick={() => setIsWizardOpen(true)} size="sm"><Pencil className="mr-2 h-4 w-4" /> Edit</Button>
          <Button variant="outline" onClick={exportOdcs} size="sm"><Download className="mr-2 h-4 w-4" /> Export ODCS</Button>
          <Button variant="destructive" onClick={handleDelete} size="sm"><Trash2 className="mr-2 h-4 w-4" /> Delete</Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-2xl font-bold flex items-center">
            <FileText className="mr-3 h-7 w-7 text-primary" />{contract.name}
          </CardTitle>
          <CardDescription className="pt-1">Core contract metadata</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Core Metadata */}
          <div className="grid md:grid-cols-4 gap-4">
            <div className="space-y-1"><Label>Owner:</Label> <span className="text-sm block">{contract.owner}</span></div>
            <div className="space-y-1"><Label>Status:</Label> <Badge variant="secondary" className="ml-1">{contract.status}</Badge></div>
            <div className="space-y-1"><Label>Version:</Label> <Badge variant="outline" className="ml-1">{contract.version}</Badge></div>
            <div className="space-y-1"><Label>API Version:</Label> <span className="text-sm block">{contract.apiVersion}</span></div>
            <div className="space-y-1">
              <Label>Domain:</Label>
              {(() => {
                const domainId = (contract as any).domain_id || (contract as any).domainId;
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


          {/* Team */}
          {contract.team && contract.team.length > 0 && (
            <div className="space-y-3">
              <Label className="text-base font-semibold">Team</Label>
              <div className="space-y-2 pl-4">
                {contract.team.map((member, idx) => (
                  <div key={idx} className="flex items-center gap-3">
                    <Badge variant="outline">{member.role}</Badge>
                    <span className="text-sm">{member.name || member.email}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Access Control */}
          {contract.accessControl && (
            <div className="space-y-3">
              <Label className="text-base font-semibold">Access Control</Label>
              <div className="grid md:grid-cols-2 gap-3 pl-4">
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
                <div className="space-y-1">
                  <Label>Requires Encryption:</Label>
                  <span className="text-sm">{contract.accessControl.requiresEncryption ? 'Yes' : 'No'}</span>
                </div>
                {contract.accessControl.readGroups && contract.accessControl.readGroups.length > 0 && (
                  <div className="space-y-1">
                    <Label>Read Groups:</Label>
                    <div className="flex flex-wrap gap-1">
                      {contract.accessControl.readGroups.map((group, idx) => (
                        <Badge key={idx} variant="outline" className="text-xs">{group}</Badge>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Custom Properties */}
          {contract.customProperties && Object.keys(contract.customProperties).length > 0 && (
            <div className="space-y-3">
              <Label className="text-base font-semibold">Custom Properties</Label>
              <div className="space-y-2 pl-4">
                {Object.entries(contract.customProperties).map(([key, value]) => (
                  <div key={key} className="flex items-center gap-3">
                    <Label className="min-w-24">{key}:</Label>
                    <span className="text-sm text-muted-foreground">{String(value)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Support Channels */}
          {contract.support && Object.keys(contract.support).length > 0 && (
            <div className="space-y-3">
              <Label className="text-base font-semibold">Support</Label>
              <div className="space-y-2 pl-4">
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
            </div>
          )}

          {/* SLA */}
          {contract.sla && Object.keys(contract.sla as any).length > 0 && (
            <div className="space-y-3">
              <Label className="text-base font-semibold">SLA</Label>
              <div className="space-y-2 pl-4">
                {Object.entries(contract.sla as any).map(([k, v]) => (
                  <div key={k} className="flex items-center gap-3">
                    <Label className="min-w-32 capitalize">{k}:</Label>
                    <span className="text-sm text-muted-foreground">{String(v)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Servers / Ports */}
          {contract.servers && (
            Array.isArray(contract.servers) ? contract.servers.length > 0 : true
          ) && (
            <div className="space-y-3">
              <Label className="text-base font-semibold">Ports / Servers</Label>
              <div className="space-y-2 pl-4">
                {(Array.isArray(contract.servers) ? contract.servers : [contract.servers]).map((s, idx) => (
                  <div key={idx} className="flex items-center gap-3">
                    {s.serverType && <Badge variant="outline" className="text-xs">{s.serverType}</Badge>}
                    {s.environment && <Badge variant="secondary" className="text-xs">{s.environment}</Badge>}
                    {s.connectionString && (
                      <span className="text-sm text-muted-foreground break-all">{s.connectionString}</span>
                    )}
                  </div>
                ))}
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

      {/* Schema Section */}
      {contract.schema && contract.schema.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-xl flex items-center gap-2">
              Schemas
            </CardTitle>
            <CardDescription>
              Database schema definitions for this contract ({contract.schema.length} table{contract.schema.length !== 1 ? 's' : ''})
            </CardDescription>
          </CardHeader>
          <CardContent>
            {contract.schema.length === 1 ? (
              // Single schema - no tabs needed
              <div className="space-y-4">
                <div className="flex items-center gap-4">
                  <div>
                    <Label className="text-base font-semibold">{contract.schema[0].name}</Label>
                    {schemaLinks[contract.schema[0].name] && schemaLinks[contract.schema[0].name].length > 0 && (
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
                  {contract.schema[0].physicalName && (
                    <Badge variant="outline" className="text-xs">
                      Physical: {contract.schema[0].physicalName}
                    </Badge>
                  )}
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
                  <div className="flex items-center gap-4">
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
                    {contract.schema[selectedSchemaIndex]?.physicalName && (
                      <Badge variant="outline" className="text-xs">
                        Physical: {contract.schema[selectedSchemaIndex].physicalName}
                      </Badge>
                    )}
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
                  <div className="flex items-center gap-4">
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
                    {contract.schema[selectedSchemaIndex]?.physicalName && (
                      <Badge variant="outline" className="text-xs">
                        Physical: {contract.schema[selectedSchemaIndex].physicalName}
                      </Badge>
                    )}
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
            )}
          </CardContent>
        </Card>
      )}

      {/* Metadata Panel */}
      {contract.id && (
        <EntityMetadataPanel entityId={contract.id} entityType="data_contract" />
      )}

      <DataContractWizardDialog
        isOpen={isWizardOpen}
        onOpenChange={setIsWizardOpen}
        initial={{
          name: contract.name,
          version: contract.version,
          status: contract.status,
          owner: contract.owner,
          domain: (contract as any).domain_id || contract.domainId, // Use domain_id (backend) or domainId (frontend)
          tenant: contract.tenant,
          dataProduct: contract.dataProduct,
          // Flatten description for wizard compatibility
          descriptionUsage: contract.description?.usage,
          descriptionPurpose: contract.description?.purpose,
          descriptionLimitations: contract.description?.limitations,
          // Rename schema to schemaObjects for wizard compatibility and include semantic concepts
          schemaObjects: contract.schema?.map(schema => ({
            ...schema,
            semanticConcepts: (schemaLinks[schema.name] || [])
              .map(link => ({
                iri: link.iri,
                label: link.label || link.iri.split('#')[1] || link.iri,
                type: 'class'
              })),
            properties: schema.properties?.map(property => ({
              ...property,
              semanticConcepts: (propertyLinks[`${schema.name}#${property.name}`] || [])
                .map(link => ({
                  iri: link.iri,
                  label: link.label || link.iri.split('#')[1] || link.iri,
                  type: 'class'
                }))
            })) || []
          })) || [],
          // Convert contract-level semantic links to wizard format
          contractSemanticConcepts: (links || []).map(link => ({
            iri: link.iri,
            label: link.label || link.iri.split('#')[1] || link.iri,
            type: 'class'
          })),
          team: contract.team,
          accessControl: contract.accessControl,
          support: contract.support,
          sla: contract.sla,
          servers: contract.servers,
          customProperties: contract.customProperties,
        }}
        onSubmit={async (payload) => {
          try {
            // Transform payload to match backend expectations - include ALL fields from wizard
            const transformedPayload = {
              name: payload.name,
              version: payload.version,
              status: payload.status,
              owner: payload.owner,
              kind: payload.kind,
              apiVersion: payload.apiVersion,
              tenant: payload.tenant,
              dataProduct: payload.dataProduct,
              domain_id: payload.domainId, // Use the domainId from wizard payload
              // Flatten description object
              descriptionUsage: payload.description?.usage,
              descriptionPurpose: payload.description?.purpose,
              descriptionLimitations: payload.description?.limitations,
              // Include schema and other important fields that the wizard sends
              schema: payload.schema,
              authoritativeDefinitions: payload.authoritativeDefinitions,
              qualityRules: payload.qualityRules,
              serverConfigs: payload.serverConfigs,
              sla: payload.sla,
            }
            
            
            const res = await fetch(`/api/data-contracts/${contract.id}`, {
              method: 'PUT',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(transformedPayload)
            })
            if (!res.ok) throw new Error('Update failed')
            // Ensure details (including semantic links) are refreshed BEFORE closing the dialog
            await fetchDetails()
            setIsWizardOpen(false)
            toast({ title: 'Updated', description: 'Contract updated.' })
          } catch (e) {
            toast({ title: 'Error', description: e instanceof Error ? e.message : 'Failed to update', variant: 'destructive' })
          }
        }}
      />

      <ConceptSelectDialog
        isOpen={iriDialogOpen}
        onOpenChange={setIriDialogOpen}
        onSelect={addIri}
      />
    </div>
  )
}


