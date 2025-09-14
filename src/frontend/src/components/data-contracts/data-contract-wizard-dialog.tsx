import { useEffect, useRef, useState } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import DatasetLookupDialog from './dataset-lookup-dialog'
import { useDomains } from '@/hooks/use-domains'
import { useToast } from '@/hooks/use-toast'

type WizardProps = {
  isOpen: boolean
  onOpenChange: (open: boolean) => void
  onSubmit: (payload: any) => Promise<void>
  initial?: any
}

const statuses = ['draft', 'active', 'deprecated', 'archived']
// ODCS v3.0.2 compliant logical types (exact match with spec)
const LOGICAL_TYPES = [
  'string',
  'date',
  'number',
  'integer',
  'object',
  'array',
  'boolean'
]

// ODCS v3.0.2 quality framework constants
const QUALITY_DIMENSIONS = ['accuracy', 'completeness', 'conformity', 'consistency', 'coverage', 'timeliness', 'uniqueness']
const QUALITY_TYPES = ['text', 'library', 'sql', 'custom']
const QUALITY_SEVERITIES = ['info', 'warning', 'error']
const BUSINESS_IMPACTS = ['operational', 'regulatory']

// ODCS v3.0.2 server types
const ODCS_SERVER_TYPES = [
  'api', 'athena', 'azure', 'bigquery', 'clickhouse', 'databricks', 'denodo', 'dremio',
  'duckdb', 'glue', 'cloudsql', 'db2', 'informix', 'kafka', 'kinesis', 'local',
  'mysql', 'oracle', 'postgresql', 'postgres', 'presto', 'pubsub',
  'redshift', 's3', 'sftp', 'snowflake', 'sqlserver', 'synapse', 'trino', 'vertica', 'custom'
]
const ENVIRONMENTS = ['production', 'staging', 'development', 'test']

export default function DataContractWizardDialog({ isOpen, onOpenChange, onSubmit, initial }: WizardProps) {
  const { domains, loading: domainsLoading } = useDomains()
  const { toast } = useToast()
  const [step, setStep] = useState(1)
  const totalSteps = 5
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isSavingDraft, setIsSavingDraft] = useState(false)

  // Step fields
  const [name, setName] = useState(initial?.name || '')
  const [version, setVersion] = useState(initial?.version || 'v1.0')
  const [status, setStatus] = useState(initial?.status || 'draft')
  const [owner, setOwner] = useState(initial?.owner || '')
  const [domain, setDomain] = useState(initial?.domain || '')
  const [tenant, setTenant] = useState(initial?.tenant || '')
  const [dataProduct, setDataProduct] = useState(initial?.dataProduct || '')
  const [descriptionUsage, setDescriptionUsage] = useState(initial?.descriptionUsage || '')
  const [descriptionPurpose, setDescriptionPurpose] = useState(initial?.descriptionPurpose || '')
  const [descriptionLimitations, setDescriptionLimitations] = useState(initial?.descriptionLimitations || '')

  type Column = {
    name: string;
    physicalType?: string;
    logicalType: string;
    required?: boolean;
    unique?: boolean;
    primaryKey?: boolean;
    primaryKeyPosition?: number;
    partitioned?: boolean;
    partitionKeyPosition?: number;
    description?: string;
    classification?: string;
    examples?: string;
  }
  type SchemaObject = { name: string; physicalName?: string; properties: Column[] }
  const [schemaObjects, setSchemaObjects] = useState<SchemaObject[]>(initial?.schemaObjects || [])

  type QualityRule = {
    name: string;
    dimension: string;
    type: string;
    severity: string;
    businessImpact: string;
    description?: string;
    query?: string; // for SQL-based rules
  }
  const [qualityRules, setQualityRules] = useState<QualityRule[]>(initial?.qualityRules || [])

  type ServerConfig = {
    server: string;
    type: string;
    description?: string;
    environment: string;
    host?: string;
    port?: number;
    database?: string;
    schema?: string;
    location?: string;
    properties?: Record<string, string>;
  }
  const [serverConfigs, setServerConfigs] = useState<ServerConfig[]>(initial?.serverConfigs || [])

  // SLA Requirements state
  const [slaRequirements, setSlaRequirements] = useState({
    uptimeTarget: initial?.sla?.uptimeTarget || 0,
    maxDowntimeMinutes: initial?.sla?.maxDowntimeMinutes || 0,
    queryResponseTimeMs: initial?.sla?.queryResponseTimeMs || 0,
    dataFreshnessMinutes: initial?.sla?.dataFreshnessMinutes || 0,
    queryResponseTimeUnit: 'seconds',
    dataFreshnessUnit: 'minutes'
  })

  const [lookupOpen, setLookupOpen] = useState(false)
  const wasOpenRef = useRef(false)

  // Initialize wizard state only when the dialog transitions from closed -> open
  useEffect(() => {
    if (isOpen && !wasOpenRef.current) {
      wasOpenRef.current = true
      if (!initial) {
        // Reset to defaults for new contract
        setStep(1)
        setName('')
        setVersion('v1.0')
        setStatus('draft')
        setOwner('')
        setDomain('')
        setTenant('')
        setDataProduct('')
        setDescriptionUsage('')
        setDescriptionPurpose('')
        setDescriptionLimitations('')
        setSchemaObjects([])
        setQualityRules([])
        setServerConfigs([])
        setSlaRequirements({
          uptimeTarget: 0,
          maxDowntimeMinutes: 0,
          queryResponseTimeMs: 0,
          dataFreshnessMinutes: 0,
          queryResponseTimeUnit: 'seconds',
          dataFreshnessUnit: 'minutes'
        })
        setIsSubmitting(false)
      } else {
        // Initialize from provided data for editing
        setStep(1)
        setName(initial.name || '')
        setVersion(initial.version || 'v1.0')
        setStatus(initial.status || 'draft')
        setOwner(initial.owner || '')
        setDomain(initial.domain || '')
        setTenant(initial.tenant || '')
        setDataProduct(initial.dataProduct || '')
        setDescriptionUsage(initial.descriptionUsage || '')
        setDescriptionPurpose(initial.descriptionPurpose || '')
        setDescriptionLimitations(initial.descriptionLimitations || '')
        setSchemaObjects(initial.schemaObjects || [])
        setQualityRules(initial.qualityRules || [])
        setServerConfigs(initial.serverConfigs || [])
        setSlaRequirements({
          uptimeTarget: initial.sla?.uptimeTarget || 0,
          maxDowntimeMinutes: initial.sla?.maxDowntimeMinutes || 0,
          queryResponseTimeMs: initial.sla?.queryResponseTimeMs || 0,
          dataFreshnessMinutes: initial.sla?.dataFreshnessMinutes || 0,
          queryResponseTimeUnit: 'seconds',
          dataFreshnessUnit: 'minutes'
        })
        setIsSubmitting(false)
      }
    } else if (!isOpen && wasOpenRef.current) {
      // Mark as closed to allow re-initialization on next open
      wasOpenRef.current = false
    }
  }, [isOpen, initial])

  const addObject = () => setSchemaObjects((prev) => [...prev, { name: '', properties: [] }])
  const removeObject = (idx: number) => setSchemaObjects((prev) => prev.filter((_, i) => i !== idx))
  const addColumn = (objIdx: number) => setSchemaObjects((prev) => prev.map((o, i) => i === objIdx ? { ...o, properties: [...o.properties, { name: '', physicalType: '', logicalType: 'string', classification: '', examples: '' }] } : o))
  const removeColumn = (objIdx: number, colIdx: number) => setSchemaObjects((prev) => prev.map((o, i) => i === objIdx ? { ...o, properties: o.properties.filter((_, j) => j !== colIdx) } : o))

  const addQualityRule = () => setQualityRules((prev) => [...prev, { name: '', dimension: 'completeness', type: 'library', severity: 'warning', businessImpact: 'operational' }])
  const removeQualityRule = (idx: number) => setQualityRules((prev) => prev.filter((_, i) => i !== idx))

  const addServerConfig = () => setServerConfigs((prev) => [...prev, { server: '', type: 'postgresql', environment: 'production' }])
  const removeServerConfig = (idx: number) => setServerConfigs((prev) => prev.filter((_, i) => i !== idx))

  const handleInferFromDataset = async (table: { full_name: string }) => {
    const datasetPath = table.full_name
    const logicalName = datasetPath.split('.').pop() || datasetPath

    // Create schema immediately so user sees progress
    const newIndex = schemaObjects.length
    setSchemaObjects((prev) => [...prev, { name: logicalName, physicalName: datasetPath, properties: [] }])
    setStep(2)
    setTimeout(() => {
      const el = document.getElementById(`schema-object-${newIndex}`)
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'center' })
        const input = el.querySelector('input') as HTMLInputElement | null
        if (input) input.focus()
      }
    }, 0)

    // Try to fetch columns asynchronously
    try {
      const res = await fetch(`/api/catalogs/dataset/${encodeURIComponent(datasetPath)}`)
      if (!res.ok) throw new Error('Failed to load dataset schema')
      const data = await res.json()
      const columns = Array.isArray(data?.schema)
        ? data.schema.map((c: any) => ({
            name: String(c.name || ''),
            logicalType: String(c.logicalType || c.logical_type || c.type || 'string'),
            required: c.nullable === undefined ? undefined : !Boolean(c.nullable),
          }))
        : []

      setSchemaObjects((prev) => prev.map((o, i) => i === newIndex ? { ...o, properties: columns } : o))
      toast({ title: 'Schema inferred', description: `Columns loaded from ${datasetPath}` })
    } catch (e) {
      toast({ title: 'Schema added without columns', description: 'Could not fetch columns. Configure SQL warehouse to enable inference.', variant: 'warning' as any })
    }
  }

  const handleNext = () => { if (step < totalSteps) setStep(step + 1) }
  const handlePrev = () => { if (step > 1) setStep(step - 1) }

  const handleSubmit = async () => {
    setIsSubmitting(true)
    try {
      const payload = {
        name,
        version,
        status: 'active', // Final submission should be active
        owner,
        domain,
        tenant,
        dataProduct,
        description: { usage: descriptionUsage, purpose: descriptionPurpose, limitations: descriptionLimitations },
        schema: schemaObjects.map((o) => ({ name: o.name, physicalName: o.physicalName, properties: o.properties })),
        qualityRules: qualityRules,
        serverConfigs: serverConfigs,
        sla: {
          uptimeTarget: slaRequirements.uptimeTarget,
          maxDowntimeMinutes: slaRequirements.maxDowntimeMinutes,
          queryResponseTimeMs: slaRequirements.queryResponseTimeMs,
          dataFreshnessMinutes: slaRequirements.dataFreshnessMinutes
        },
      }
      await onSubmit(payload)
      // Don't close here - let the parent component handle closing on success
    } catch (error) {
      // Error handling - stay open on error so user can retry
      console.error('Failed to submit contract:', error)
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleSaveDraft = async () => {
    // Validate minimum required fields
    if (!name.trim()) {
      alert('Contract name is required to save a draft')
      return
    }
    if (!owner.trim()) {
      alert('Contract owner is required to save a draft')
      return
    }

    setIsSavingDraft(true)
    try {
      const payload = {
        name,
        version,
        status: 'draft', // Draft status for partial saves
        owner,
        domain,
        tenant,
        dataProduct,
        description: { usage: descriptionUsage, purpose: descriptionPurpose, limitations: descriptionLimitations },
        schema: schemaObjects.map((o) => ({ name: o.name, physicalName: o.physicalName, properties: o.properties })),
        qualityRules: qualityRules,
        serverConfigs: serverConfigs,
        sla: {
          uptimeTarget: slaRequirements.uptimeTarget,
          maxDowntimeMinutes: slaRequirements.maxDowntimeMinutes,
          queryResponseTimeMs: slaRequirements.queryResponseTimeMs,
          dataFreshnessMinutes: slaRequirements.dataFreshnessMinutes
        },
      }
      await onSubmit(payload)
      // Don't close here - let the parent component handle closing on success
    } catch (error) {
      // Error handling - stay open on error so user can retry
      console.error('Failed to save draft:', error)
    } finally {
      setIsSavingDraft(false)
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="w-[90vw] h-[90vh] max-w-none max-h-none flex flex-col">
        <DialogHeader className="flex-shrink-0 pb-4 border-b">
          <DialogTitle className="text-2xl">Data Contract Wizard</DialogTitle>
          <DialogDescription className="text-base">Build a contract incrementally according to ODCS v3.0.2</DialogDescription>
          
          {/* Progress Indicator */}
          <div className="mt-4">
            <div className="flex items-center justify-between text-sm text-muted-foreground mb-2">
              <span>Step {step} of {totalSteps}</span>
              <span>{Math.round((step / totalSteps) * 100)}% Complete</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div 
                className="bg-primary h-2 rounded-full transition-all duration-300 ease-out" 
                style={{ width: `${(step / totalSteps) * 100}%` }}
              />
            </div>
            <div className="flex justify-between mt-2 text-xs text-muted-foreground">
              <span className={step === 1 ? 'text-primary font-medium' : ''}>Fundamentals</span>
              <span className={step === 2 ? 'text-primary font-medium' : ''}>Schema</span>
              <span className={step === 3 ? 'text-primary font-medium' : ''}>Quality</span>
              <span className={step === 4 ? 'text-primary font-medium' : ''}>Team & Roles</span>
              <span className={step === 5 ? 'text-primary font-medium' : ''}>SLA & Infrastructure</span>
            </div>
          </div>
        </DialogHeader>

        <div className="flex-grow overflow-y-auto p-6">
          {/* Step 1: Fundamentals */}
          <div className={step === 1 ? 'block space-y-6' : 'hidden'}>
            <div className="text-lg font-semibold text-foreground mb-4">Contract Fundamentals</div>
            
            {/* Basic Information Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="space-y-4">
                <div>
                  <Label htmlFor="dc-name" className="text-sm font-medium">Contract Name *</Label>
                  <Input 
                    id="dc-name" 
                    value={name} 
                    onChange={(e) => setName(e.target.value)} 
                    placeholder="e.g., Customer Data Contract"
                    className="mt-1"
                  />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label htmlFor="dc-version" className="text-sm font-medium">Version *</Label>
                    <Input 
                      id="dc-version" 
                      value={version} 
                      onChange={(e) => setVersion(e.target.value)} 
                      placeholder="e.g., v1.0"
                      className="mt-1"
                    />
                  </div>
                  <div>
                    <Label className="text-sm font-medium">Status</Label>
                    <Select value={status} onValueChange={setStatus}>
                      <SelectTrigger className="mt-1">
                        <SelectValue placeholder="Select status" />
                      </SelectTrigger>
                      <SelectContent>
                        {statuses.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <div>
                  <Label htmlFor="dc-owner" className="text-sm font-medium">Contract Owner *</Label>
                  <Input 
                    id="dc-owner" 
                    value={owner} 
                    onChange={(e) => setOwner(e.target.value)} 
                    placeholder="e.g., data-team@company.com"
                    className="mt-1"
                  />
                </div>
              </div>

              {/* Metadata Panel */}
              <div className="space-y-4">
                <div>
                  <Label className="text-sm font-medium">Domain</Label>
                  <Select value={domain} onValueChange={setDomain} disabled={domainsLoading}>
                    <SelectTrigger className="mt-1">
                      <SelectValue placeholder={domainsLoading ? "Loading domains..." : "Select a data domain"} />
                    </SelectTrigger>
                    <SelectContent>
                      {domains.length === 0 && !domainsLoading && (
                        <SelectItem value="no-domains" disabled>No domains available</SelectItem>
                      )}
                      {domains.map((domainOption) => (
                        <SelectItem key={domainOption.id} value={domainOption.id}>
                          {domainOption.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label className="text-sm font-medium">Tenant</Label>
                  <Input 
                    placeholder="e.g., production, staging" 
                    value={tenant}
                    onChange={(e) => setTenant(e.target.value)}
                    className="mt-1"
                  />
                </div>
                <div>
                  <Label className="text-sm font-medium">Data Product</Label>
                  <Input 
                    placeholder="Associated data product name" 
                    value={dataProduct}
                    onChange={(e) => setDataProduct(e.target.value)}
                    className="mt-1"
                  />
                </div>
              </div>
            </div>

            {/* Description Section */}
            <div className="border-t pt-6">
              <div className="text-base font-medium mb-4">Contract Description</div>
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                <div>
                  <Label className="text-sm font-medium">Usage</Label>
                  <Textarea 
                    value={descriptionUsage} 
                    onChange={(e) => setDescriptionUsage(e.target.value)} 
                    placeholder="Describe how this data should be used..."
                    className="mt-1 min-h-[100px]"
                  />
                </div>
                <div>
                  <Label className="text-sm font-medium">Purpose</Label>
                  <Textarea 
                    value={descriptionPurpose} 
                    onChange={(e) => setDescriptionPurpose(e.target.value)} 
                    placeholder="Describe the business purpose and goals..."
                    className="mt-1 min-h-[100px]"
                  />
                </div>
                <div>
                  <Label className="text-sm font-medium">Limitations</Label>
                  <Textarea 
                    value={descriptionLimitations} 
                    onChange={(e) => setDescriptionLimitations(e.target.value)} 
                    placeholder="Describe any limitations or constraints..."
                    className="mt-1 min-h-[100px]"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Step 2: Schema Definition */}
          <div className={step === 2 ? 'block space-y-4' : 'hidden'}>
            <div className="text-lg font-semibold text-foreground mb-4">Data Schema Definition</div>
            
            <div className="flex justify-between items-center p-4 bg-muted/50 rounded-lg">
              <div>
                <div className="font-medium">Define your data structure</div>
                <div className="text-sm text-muted-foreground">Add schema objects that represent tables, views, or data assets</div>
              </div>
              <div className="flex gap-3">
                <Button type="button" variant="outline" onClick={() => setLookupOpen(true)} className="gap-2">
                  <span>🔍</span> Infer from Dataset
                </Button>
                <Button type="button" variant="default" onClick={addObject} className="gap-2">
                  <span>➕</span> Add Schema Object
                </Button>
              </div>
            </div>

            {schemaObjects.length === 0 ? (
              <div className="text-center py-12 border-2 border-dashed border-muted-foreground/25 rounded-lg">
                <div className="text-muted-foreground mb-2">No schema objects defined yet</div>
                <div className="text-sm text-muted-foreground">Start by adding a schema object or inferring from an existing dataset</div>
              </div>
            ) : (
              <div className="space-y-6">
                {schemaObjects.map((obj, objIndex) => (
                  <div key={objIndex} id={`schema-object-${objIndex}`} className="border rounded-lg p-6 bg-card">
                    {/* Object Header */}
                    <div className="flex items-center justify-between mb-4">
                      <div className="text-base font-medium">Schema Object {objIndex + 1}</div>
                      <Button 
                        type="button" 
                        variant="ghost" 
                        size="sm"
                        onClick={() => removeObject(objIndex)}
                        className="text-destructive hover:text-destructive"
                      >
                        Remove Object
                      </Button>
                    </div>

                    {/* Object Names */}
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
                      <div>
                        <Label className="text-sm font-medium">Logical Name *</Label>
                        <Input 
                          placeholder="e.g., customers, orders" 
                          value={obj.name} 
                          onChange={(e) => setSchemaObjects((prev) => prev.map((x, i) => i === objIndex ? { ...x, name: e.target.value } : x))}
                          className="mt-1"
                        />
                      </div>
                      <div>
                        <Label className="text-sm font-medium">Physical Name (Optional)</Label>
                        <Input 
                          placeholder="e.g., catalog.schema.table_name" 
                          value={obj.physicalName || ''} 
                          onChange={(e) => setSchemaObjects((prev) => prev.map((x, i) => i === objIndex ? { ...x, physicalName: e.target.value } : x))}
                          className="mt-1"
                        />
                      </div>
                    </div>

                    {/* Columns Section */}
                    <div className="border-t pt-4">
                      <div className="flex justify-between items-center mb-4">
                        <div className="font-medium text-sm">Columns ({obj.properties.length})</div>
                        <Button type="button" variant="outline" size="sm" onClick={() => addColumn(objIndex)} className="gap-1 h-8 px-2 text-xs">
                          ➕ Add Column
                        </Button>
                      </div>

                      {obj.properties.length === 0 ? (
                        <div className="text-center py-6 border border-dashed border-muted-foreground/25 rounded">
                          <div className="text-sm text-muted-foreground">No columns defined</div>
                        </div>
                      ) : (
                        <div className="space-y-2">
                          {obj.properties.map((col, colIndex) => (
                            <div key={colIndex} className="space-y-2">
                              <div className="grid grid-cols-1 lg:grid-cols-12 gap-2 p-2 border rounded bg-muted/30">
                                <div className="lg:col-span-3">
                                  <Label className="text-[11px]">Column Name *</Label>
                                  <div className="mt-0.5 flex items-center gap-[3px]">
                                    <span className="text-[11px] text-muted-foreground select-none">#{colIndex + 1}</span>
                                    <Input 
                                      placeholder="column_name" 
                                      value={col.name} 
                                      onChange={(e) => setSchemaObjects((prev) => prev.map((x, i) => i === objIndex ? { ...x, properties: x.properties.map((y, j) => j === colIndex ? { ...y, name: e.target.value } : y) } : x))}
                                      className="h-8 text-xs w-full flex-1"
                                    />
                                  </div>
                                </div>
                                <div className="lg:col-span-3">
                                  <Label className="text-[11px]">Physical Type</Label>
                                  <Input 
                                    placeholder="e.g., VARCHAR(255), BIGINT" 
                                    value={(col as any).physicalType || ''}
                                    onChange={(e) => setSchemaObjects((prev) => prev.map((x, i) => i === objIndex ? { ...x, properties: x.properties.map((y, j) => j === colIndex ? { ...y, physicalType: e.target.value } : y) } : x))}
                                    className="mt-0.5 h-8 text-xs"
                                  />
                                </div>
                                <div className="lg:col-span-3">
                                  <Label className="text-[11px]">Logical Type *</Label>
                                  <Select value={(col as any).logicalType} onValueChange={(v) => setSchemaObjects((prev) => prev.map((x, i) => i === objIndex ? { ...x, properties: x.properties.map((y, j) => j === colIndex ? { ...y, logicalType: v } : y) } : x))}>
                                    <SelectTrigger className="mt-0.5 h-8 text-xs">
                                      <SelectValue placeholder="Select type" />
                                    </SelectTrigger>
                                    <SelectContent>
                                      {LOGICAL_TYPES.map((t) => (
                                        <SelectItem key={t} value={t} className="text-xs h-7">{t}</SelectItem>
                                      ))}
                                    </SelectContent>
                                  </Select>
                                </div>
                                <div className="lg:col-span-2 flex items-end justify-end">
                                  <Button 
                                    type="button" 
                                    variant="ghost" 
                                    size="sm"
                                    onClick={() => removeColumn(objIndex, colIndex)}
                                    className="text-destructive hover:text-destructive p-1 h-8"
                                  >
                                    🗑️
                                  </Button>
                                </div>

                                {/* Row 2: Description + Flags */}
                                <div className="lg:col-span-8">
                                  <Label className="text-[11px]">Description</Label>
                                  <Input 
                                    placeholder="Column description..." 
                                    value={col.description || ''} 
                                    onChange={(e) => setSchemaObjects((prev) => prev.map((x, i) => i === objIndex ? { ...x, properties: x.properties.map((y, j) => j === colIndex ? { ...y, description: e.target.value } : y) } : x))}
                                    className="mt-0.5 h-8 text-xs"
                                  />
                                </div>
                                <div className="lg:col-span-4 flex items-end gap-2">
                                  <label className="flex items-center gap-1 text-[11px]">
                                    <input
                                      type="checkbox"
                                      checked={!!col.required}
                                      onChange={(e) => setSchemaObjects((prev) => prev.map((x, i) => i === objIndex ? { ...x, properties: x.properties.map((y, j) => j === colIndex ? { ...y, required: e.target.checked } : y) } : x))}
                                    />
                                    Required
                                  </label>
                                  <label className="flex items-center gap-1 text-[11px]">
                                    <input
                                      type="checkbox"
                                      checked={!!col.unique}
                                      onChange={(e) => setSchemaObjects((prev) => prev.map((x, i) => i === objIndex ? { ...x, properties: x.properties.map((y, j) => j === colIndex ? { ...y, unique: e.target.checked } : y) } : x))}
                                    />
                                    Unique
                                  </label>
                                  <label className="flex items-center gap-1 text-[11px]">
                                    <input
                                      type="checkbox"
                                      checked={!!col.primaryKey}
                                      onChange={(e) => setSchemaObjects((prev) => prev.map((x, i) => i === objIndex ? { ...x, properties: x.properties.map((y, j) => j === colIndex ? { ...y, primaryKey: e.target.checked, primaryKeyPosition: e.target.checked ? j + 1 : -1 } : y) } : x))}
                                    />
                                    Primary Key
                                  </label>
                                  <label className="flex items-center gap-1 text-[11px]">
                                    <input
                                      type="checkbox"
                                      checked={!!col.partitioned}
                                      onChange={(e) => setSchemaObjects((prev) => prev.map((x, i) => i === objIndex ? { ...x, properties: x.properties.map((y, j) => j === colIndex ? { ...y, partitioned: e.target.checked, partitionKeyPosition: e.target.checked ? j + 1 : -1 } : y) } : x))}
                                    />
                                    Partition Key
                                  </label>
                                </div>

                                {/* Row 3: Advanced */}
                                <div className="lg:col-span-12 col-span-1 pt-1">
                                  <details>
                                    <summary className="text-[11px] text-muted-foreground cursor-pointer select-none">Advanced</summary>
                                    <div className="mt-2 grid grid-cols-1 lg:grid-cols-12 gap-2">
                                      <div className="lg:col-span-3">
                                        <Label className="text-[11px]">Classification</Label>
                                        <Input 
                                          placeholder="confidential, pii, internal" 
                                          value={(col as any).classification || ''}
                                          onChange={(e) => setSchemaObjects((prev) => prev.map((x, i) => i === objIndex ? { ...x, properties: x.properties.map((y, j) => j === colIndex ? { ...y, classification: e.target.value } : y) } : x))}
                                          className="mt-0.5 h-8 text-xs"
                                        />
                                      </div>
                                      <div className="lg:col-span-9">
                                        <Label className="text-[11px]">Examples (comma-separated)</Label>
                                        <Input 
                                          placeholder="123, 456, 789" 
                                          value={(col as any).examples || ''}
                                          onChange={(e) => setSchemaObjects((prev) => prev.map((x, i) => i === objIndex ? { ...x, properties: x.properties.map((y, j) => j === colIndex ? { ...y, examples: e.target.value } : y) } : x))}
                                          className="mt-0.5 h-8 text-xs"
                                        />
                                      </div>
                                    </div>
                                  </details>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Step 3: Data Quality */}
          <div className={step === 3 ? 'block space-y-4' : 'hidden'}>
            <div className="text-lg font-semibold text-foreground mb-4">Data Quality & Validation</div>

            <div className="flex justify-between items-center p-4 bg-muted/50 rounded-lg">
              <div>
                <div className="font-medium">ODCS Quality Framework</div>
                <div className="text-sm text-muted-foreground">Define quality rules using ODCS v3.0.2 dimensions and types</div>
              </div>
              <Button type="button" variant="default" onClick={addQualityRule} className="gap-2">
                <span>➕</span> Add Quality Rule
              </Button>
            </div>

            {qualityRules.length === 0 ? (
              <div className="text-center py-12 border-2 border-dashed border-muted-foreground/25 rounded-lg">
                <div className="text-muted-foreground mb-2">No quality rules defined yet</div>
                <div className="text-sm text-muted-foreground">Start by adding quality rules to ensure data integrity</div>
              </div>
            ) : (
              <div className="space-y-4">
                {qualityRules.map((rule, index) => (
                  <div key={index} className="border rounded-lg p-4 bg-card">
                    <div className="flex items-center justify-between mb-4">
                      <div className="text-base font-medium">Quality Rule {index + 1}</div>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => removeQualityRule(index)}
                        className="text-destructive hover:text-destructive"
                      >
                        Remove Rule
                      </Button>
                    </div>

                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                      <div>
                        <Label className="text-sm font-medium">Rule Name *</Label>
                        <Input
                          placeholder="e.g., Email Format Validation"
                          value={rule.name}
                          onChange={(e) => setQualityRules((prev) => prev.map((r, i) => i === index ? { ...r, name: e.target.value } : r))}
                          className="mt-1"
                        />
                      </div>
                      <div>
                        <Label className="text-sm font-medium">Quality Dimension *</Label>
                        <Select
                          value={rule.dimension}
                          onValueChange={(v) => setQualityRules((prev) => prev.map((r, i) => i === index ? { ...r, dimension: v } : r))}
                        >
                          <SelectTrigger className="mt-1">
                            <SelectValue placeholder="Select dimension" />
                          </SelectTrigger>
                          <SelectContent>
                            {QUALITY_DIMENSIONS.map((dim) => (
                              <SelectItem key={dim} value={dim}>{dim}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      <div>
                        <Label className="text-sm font-medium">Rule Type *</Label>
                        <Select
                          value={rule.type}
                          onValueChange={(v) => setQualityRules((prev) => prev.map((r, i) => i === index ? { ...r, type: v } : r))}
                        >
                          <SelectTrigger className="mt-1">
                            <SelectValue placeholder="Select type" />
                          </SelectTrigger>
                          <SelectContent>
                            {QUALITY_TYPES.map((type) => (
                              <SelectItem key={type} value={type}>{type}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      <div>
                        <Label className="text-sm font-medium">Severity *</Label>
                        <Select
                          value={rule.severity}
                          onValueChange={(v) => setQualityRules((prev) => prev.map((r, i) => i === index ? { ...r, severity: v } : r))}
                        >
                          <SelectTrigger className="mt-1">
                            <SelectValue placeholder="Select severity" />
                          </SelectTrigger>
                          <SelectContent>
                            {QUALITY_SEVERITIES.map((sev) => (
                              <SelectItem key={sev} value={sev}>{sev}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      <div>
                        <Label className="text-sm font-medium">Business Impact *</Label>
                        <Select
                          value={rule.businessImpact}
                          onValueChange={(v) => setQualityRules((prev) => prev.map((r, i) => i === index ? { ...r, businessImpact: v } : r))}
                        >
                          <SelectTrigger className="mt-1">
                            <SelectValue placeholder="Select impact" />
                          </SelectTrigger>
                          <SelectContent>
                            {BUSINESS_IMPACTS.map((impact) => (
                              <SelectItem key={impact} value={impact}>{impact}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      <div>
                        <Label className="text-sm font-medium">Description</Label>
                        <Input
                          placeholder="Describe the quality rule..."
                          value={rule.description || ''}
                          onChange={(e) => setQualityRules((prev) => prev.map((r, i) => i === index ? { ...r, description: e.target.value } : r))}
                          className="mt-1"
                        />
                      </div>
                    </div>

                    {rule.type === 'sql' && (
                      <div className="mt-4">
                        <Label className="text-sm font-medium">SQL Query *</Label>
                        <Textarea
                          placeholder="SELECT COUNT(*) FROM table WHERE condition..."
                          value={rule.query || ''}
                          onChange={(e) => setQualityRules((prev) => prev.map((r, i) => i === index ? { ...r, query: e.target.value } : r))}
                          className="mt-1 min-h-[80px]"
                        />
                        <div className="text-xs text-muted-foreground mt-1">
                          SQL query should return a numeric result for validation
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Step 4: Team & Roles */}
          <div className={step === 4 ? 'block space-y-6' : 'hidden'}>
            <div className="text-lg font-semibold text-foreground mb-4">Team & Access Control</div>
            
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Team Members */}
              <div className="space-y-4">
                <div className="font-medium">Team Members</div>
                
                <div className="space-y-3">
                  <div className="p-4 border rounded-lg">
                    <div className="flex items-center justify-between mb-3">
                      <div className="font-medium text-sm">Data Stewards</div>
                      <Button variant="outline" size="sm">+ Add</Button>
                    </div>
                    <div className="space-y-2">
                      <div className="flex items-center justify-between p-2 bg-muted/30 rounded">
                        <div className="text-sm">{owner || 'Contract Owner'}</div>
                        <div className="text-xs text-muted-foreground">Owner</div>
                      </div>
                    </div>
                  </div>

                  <div className="p-4 border rounded-lg">
                    <div className="flex items-center justify-between mb-3">
                      <div className="font-medium text-sm">Data Consumers</div>
                      <Button variant="outline" size="sm">+ Add</Button>
                    </div>
                    <div className="space-y-2">
                      <Input placeholder="consumer-team@company.com" className="text-sm" />
                      <div className="text-xs text-muted-foreground">
                        Add stakeholders who will consume this data
                      </div>
                    </div>
                  </div>

                  <div className="p-4 border rounded-lg">
                    <div className="flex items-center justify-between mb-3">
                      <div className="font-medium text-sm">Subject Matter Experts</div>
                      <Button variant="outline" size="sm">+ Add</Button>
                    </div>
                    <div className="space-y-2">
                      <Input placeholder="expert@company.com" className="text-sm" />
                      <div className="text-xs text-muted-foreground">
                        Domain experts for business context and validation
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Access Controls */}
              <div className="space-y-4">
                <div className="font-medium">Access Control & Permissions</div>
                
                <div className="space-y-3">
                  <div className="p-4 border rounded-lg">
                    <div className="font-medium text-sm mb-3">Read Access</div>
                    <div className="space-y-2">
                      <Input placeholder="data-consumers-group" className="text-sm" />
                      <Input placeholder="analytics-team" className="text-sm" />
                      <Button variant="ghost" size="sm" className="text-primary">+ Add Group</Button>
                    </div>
                  </div>

                  <div className="p-4 border rounded-lg">
                    <div className="font-medium text-sm mb-3">Write Access</div>
                    <div className="space-y-2">
                      <Input placeholder="data-engineers-group" className="text-sm" />
                      <Button variant="ghost" size="sm" className="text-primary">+ Add Group</Button>
                    </div>
                  </div>

                  <div className="p-4 border rounded-lg">
                    <div className="font-medium text-sm mb-3">Admin Access</div>
                    <div className="space-y-2">
                      <div className="flex items-center justify-between p-2 bg-muted/30 rounded">
                        <div className="text-sm">{owner || 'Contract Owner'}</div>
                        <div className="text-xs text-muted-foreground">Owner</div>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="border-t pt-4">
                  <div className="font-medium mb-3">Security Classifications</div>
                  <div className="space-y-3">
                    <div>
                      <Label className="text-sm font-medium">Data Classification</Label>
                      <Select>
                        <SelectTrigger className="mt-1">
                          <SelectValue placeholder="Select classification" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="public">Public</SelectItem>
                          <SelectItem value="internal">Internal</SelectItem>
                          <SelectItem value="confidential">Confidential</SelectItem>
                          <SelectItem value="restricted">Restricted</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="flex items-center gap-2">
                      <input type="checkbox" className="rounded" />
                      <Label className="text-sm">Contains PII (Personally Identifiable Information)</Label>
                    </div>
                    <div className="flex items-center gap-2">
                      <input type="checkbox" className="rounded" />
                      <Label className="text-sm">Requires encryption at rest</Label>
                    </div>
                    <div className="flex items-center gap-2">
                      <input type="checkbox" className="rounded" />
                      <Label className="text-sm">Subject to regulatory compliance (GDPR, HIPAA, etc.)</Label>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Support & Communication */}
            <div className="border-t pt-6">
              <div className="font-medium mb-4">Support & Communication Channels</div>
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                <div>
                  <Label className="text-sm font-medium">Primary Support Email</Label>
                  <Input placeholder="data-support@company.com" className="mt-1" />
                </div>
                <div>
                  <Label className="text-sm font-medium">Slack Channel</Label>
                  <Input placeholder="#data-contracts-support" className="mt-1" />
                </div>
                <div>
                  <Label className="text-sm font-medium">Documentation URL</Label>
                  <Input placeholder="https://company.com/data-docs" className="mt-1" />
                </div>
              </div>
            </div>
          </div>

          {/* Step 5: SLA & Infrastructure */}
          <div className={step === 5 ? 'block space-y-6' : 'hidden'}>
            <div className="text-lg font-semibold text-foreground mb-4">Service Level Agreement & Infrastructure</div>
            
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* SLA Requirements */}
              <div className="space-y-4">
                <div className="font-medium">Service Level Agreement</div>
                
                <div className="space-y-4">
                  <div className="p-4 border rounded-lg">
                    <div className="font-medium text-sm mb-3">Availability Requirements</div>
                    <div className="space-y-3">
                      <div>
                        <Label className="text-sm font-medium">Uptime Target</Label>
                        <div className="flex items-center gap-2 mt-1">
                          <Input
                            type="number"
                            placeholder="99.9"
                            className="w-20"
                            value={slaRequirements.uptimeTarget || ''}
                            onChange={(e) => setSlaRequirements(prev => ({ ...prev, uptimeTarget: parseFloat(e.target.value) || 0 }))}
                          />
                          <span className="text-sm text-muted-foreground">% availability</span>
                        </div>
                      </div>
                      <div>
                        <Label className="text-sm font-medium">Maximum Downtime per Month</Label>
                        <div className="flex items-center gap-2 mt-1">
                          <Input
                            type="number"
                            placeholder="43"
                            className="w-20"
                            value={slaRequirements.maxDowntimeMinutes || ''}
                            onChange={(e) => setSlaRequirements(prev => ({ ...prev, maxDowntimeMinutes: parseInt(e.target.value) || 0 }))}
                          />
                          <span className="text-sm text-muted-foreground">minutes</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="p-4 border rounded-lg">
                    <div className="font-medium text-sm mb-3">Performance Requirements</div>
                    <div className="space-y-3">
                      <div>
                        <Label className="text-sm font-medium">Query Response Time (P95)</Label>
                        <div className="flex items-center gap-2 mt-1">
                          <Input
                            type="number"
                            placeholder="2"
                            className="w-20"
                            value={slaRequirements.queryResponseTimeMs ? (
                              slaRequirements.queryResponseTimeUnit === 'ms' ? slaRequirements.queryResponseTimeMs :
                              slaRequirements.queryResponseTimeUnit === 'seconds' ? Math.round(slaRequirements.queryResponseTimeMs / 1000) :
                              Math.round(slaRequirements.queryResponseTimeMs / 60000)
                            ) : ''}
                            onChange={(e) => {
                              const value = parseInt(e.target.value) || 0
                              // Convert to milliseconds based on unit
                              let ms = value
                              if (slaRequirements.queryResponseTimeUnit === 'seconds') ms = value * 1000
                              else if (slaRequirements.queryResponseTimeUnit === 'minutes') ms = value * 60000
                              setSlaRequirements(prev => ({ ...prev, queryResponseTimeMs: ms }))
                            }}
                          />
                          <Select
                            value={slaRequirements.queryResponseTimeUnit}
                            onValueChange={(value) => setSlaRequirements(prev => ({ ...prev, queryResponseTimeUnit: value }))}
                          >
                            <SelectTrigger className="w-24">
                              <SelectValue placeholder="seconds" />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="ms">ms</SelectItem>
                              <SelectItem value="seconds">seconds</SelectItem>
                              <SelectItem value="minutes">minutes</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                      </div>
                      <div>
                        <Label className="text-sm font-medium">Data Freshness</Label>
                        <div className="flex items-center gap-2 mt-1">
                          <Input
                            type="number"
                            placeholder="15"
                            className="w-20"
                            value={slaRequirements.dataFreshnessMinutes ? (
                              slaRequirements.dataFreshnessUnit === 'minutes' ? slaRequirements.dataFreshnessMinutes :
                              slaRequirements.dataFreshnessUnit === 'hours' ? Math.round(slaRequirements.dataFreshnessMinutes / 60) :
                              Math.round(slaRequirements.dataFreshnessMinutes / 1440)
                            ) : ''}
                            onChange={(e) => {
                              const value = parseInt(e.target.value) || 0
                              // Convert to minutes based on unit
                              let minutes = value
                              if (slaRequirements.dataFreshnessUnit === 'hours') minutes = value * 60
                              else if (slaRequirements.dataFreshnessUnit === 'days') minutes = value * 1440
                              setSlaRequirements(prev => ({ ...prev, dataFreshnessMinutes: minutes }))
                            }}
                          />
                          <Select
                            value={slaRequirements.dataFreshnessUnit}
                            onValueChange={(value) => setSlaRequirements(prev => ({ ...prev, dataFreshnessUnit: value }))}
                          >
                            <SelectTrigger className="w-24">
                              <SelectValue placeholder="minutes" />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="minutes">minutes</SelectItem>
                              <SelectItem value="hours">hours</SelectItem>
                              <SelectItem value="days">days</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="p-4 border rounded-lg">
                    <div className="font-medium text-sm mb-3">Support Response Times</div>
                    <div className="space-y-3">
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <Label className="text-sm">Critical Issues</Label>
                          <div className="flex items-center gap-1 mt-1">
                            <Input type="number" placeholder="2" className="w-16 text-sm" />
                            <span className="text-xs text-muted-foreground">hours</span>
                          </div>
                        </div>
                        <div>
                          <Label className="text-sm">Standard Issues</Label>
                          <div className="flex items-center gap-1 mt-1">
                            <Input type="number" placeholder="24" className="w-16 text-sm" />
                            <span className="text-xs text-muted-foreground">hours</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Infrastructure & Servers */}
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <div className="font-medium">ODCS Server Configuration</div>
                  <Button type="button" variant="default" onClick={addServerConfig} className="gap-2">
                    <span>➕</span> Add Server
                  </Button>
                </div>

                {serverConfigs.length === 0 ? (
                  <div className="text-center py-12 border-2 border-dashed border-muted-foreground/25 rounded-lg">
                    <div className="text-muted-foreground mb-2">No servers configured yet</div>
                    <div className="text-sm text-muted-foreground">Add server configurations to define data sources</div>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {serverConfigs.map((server, index) => (
                      <div key={index} className="p-4 border rounded-lg">
                        <div className="flex items-center justify-between mb-4">
                          <div className="font-medium text-sm">Server {index + 1}</div>
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            onClick={() => removeServerConfig(index)}
                            className="text-destructive hover:text-destructive"
                          >
                            Remove
                          </Button>
                        </div>

                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                          <div>
                            <Label className="text-sm font-medium">Server Identifier *</Label>
                            <Input
                              placeholder="e.g., production-db, analytics-warehouse"
                              value={server.server}
                              onChange={(e) => setServerConfigs((prev) => prev.map((s, i) => i === index ? { ...s, server: e.target.value } : s))}
                              className="mt-1"
                            />
                          </div>
                          <div>
                            <Label className="text-sm font-medium">Server Type *</Label>
                            <Select
                              value={server.type}
                              onValueChange={(v) => setServerConfigs((prev) => prev.map((s, i) => i === index ? { ...s, type: v } : s))}
                            >
                              <SelectTrigger className="mt-1">
                                <SelectValue placeholder="Select server type" />
                              </SelectTrigger>
                              <SelectContent>
                                {ODCS_SERVER_TYPES.map((type) => (
                                  <SelectItem key={type} value={type}>{type}</SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          </div>
                          <div>
                            <Label className="text-sm font-medium">Environment *</Label>
                            <Select
                              value={server.environment}
                              onValueChange={(v) => setServerConfigs((prev) => prev.map((s, i) => i === index ? { ...s, environment: v } : s))}
                            >
                              <SelectTrigger className="mt-1">
                                <SelectValue placeholder="Select environment" />
                              </SelectTrigger>
                              <SelectContent>
                                {ENVIRONMENTS.map((env) => (
                                  <SelectItem key={env} value={env}>{env}</SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          </div>
                          <div>
                            <Label className="text-sm font-medium">Description</Label>
                            <Input
                              placeholder="Describe this server..."
                              value={server.description || ''}
                              onChange={(e) => setServerConfigs((prev) => prev.map((s, i) => i === index ? { ...s, description: e.target.value } : s))}
                              className="mt-1"
                            />
                          </div>

                          {/* Common server properties */}
                          {(server.type === 'postgresql' || server.type === 'mysql' || server.type === 'databricks' || server.type === 'snowflake') && (
                            <>
                              <div>
                                <Label className="text-sm font-medium">Host</Label>
                                <Input
                                  placeholder="server.example.com"
                                  value={server.host || ''}
                                  onChange={(e) => setServerConfigs((prev) => prev.map((s, i) => i === index ? { ...s, host: e.target.value } : s))}
                                  className="mt-1"
                                />
                              </div>
                              <div>
                                <Label className="text-sm font-medium">Database</Label>
                                <Input
                                  placeholder="database_name"
                                  value={server.database || ''}
                                  onChange={(e) => setServerConfigs((prev) => prev.map((s, i) => i === index ? { ...s, database: e.target.value } : s))}
                                  className="mt-1"
                                />
                              </div>
                            </>
                          )}

                          {(server.type === 'api') && (
                            <div className="lg:col-span-2">
                              <Label className="text-sm font-medium">API Location</Label>
                              <Input
                                placeholder="https://api.example.com/v1"
                                value={server.location || ''}
                                onChange={(e) => setServerConfigs((prev) => prev.map((s, i) => i === index ? { ...s, location: e.target.value } : s))}
                                className="mt-1"
                              />
                            </div>
                          )}

                          {(server.type === 's3') && (
                            <div className="lg:col-span-2">
                              <Label className="text-sm font-medium">S3 Location</Label>
                              <Input
                                placeholder="s3://bucket-name/path/*.json"
                                value={server.location || ''}
                                onChange={(e) => setServerConfigs((prev) => prev.map((s, i) => i === index ? { ...s, location: e.target.value } : s))}
                                className="mt-1"
                              />
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Additional Infrastructure Settings */}
            <div className="space-y-4">
              <div className="font-medium">Infrastructure Management</div>

              <div className="space-y-4">
                <div className="p-4 border rounded-lg">
                  <div className="font-medium text-sm mb-3">Backup & Recovery</div>
                    <div className="space-y-3">
                      <div>
                        <Label className="text-sm font-medium">Backup Frequency</Label>
                        <Select>
                          <SelectTrigger className="mt-1">
                            <SelectValue placeholder="Select frequency" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="realtime">Real-time</SelectItem>
                            <SelectItem value="hourly">Hourly</SelectItem>
                            <SelectItem value="daily">Daily</SelectItem>
                            <SelectItem value="weekly">Weekly</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div>
                        <Label className="text-sm font-medium">Retention Period</Label>
                        <div className="flex items-center gap-2 mt-1">
                          <Input type="number" placeholder="30" className="w-20" />
                          <Select>
                            <SelectTrigger className="w-24">
                              <SelectValue placeholder="days" />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="days">days</SelectItem>
                              <SelectItem value="months">months</SelectItem>
                              <SelectItem value="years">years</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="p-4 border rounded-lg">
                    <div className="font-medium text-sm mb-3">Cost & Pricing</div>
                    <div className="space-y-3">
                      <div>
                        <Label className="text-sm font-medium">Pricing Model</Label>
                        <Select>
                          <SelectTrigger className="mt-1">
                            <SelectValue placeholder="Select pricing model" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="free">Free</SelectItem>
                            <SelectItem value="per-query">Per Query</SelectItem>
                            <SelectItem value="per-user">Per User</SelectItem>
                            <SelectItem value="per-gb">Per GB</SelectItem>
                            <SelectItem value="monthly">Monthly Subscription</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div>
                        <Label className="text-sm font-medium">Cost Center / Budget Code</Label>
                        <Input placeholder="DEPT-DATA-001" className="mt-1" />
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

        <DialogFooter className="mt-4">
          <div className="flex justify-between w-full">
            <div className="flex gap-2">
              <Button type="button" variant="outline" onClick={handlePrev} disabled={step === 1}>Previous</Button>
              <Button 
                type="button" 
                variant="secondary" 
                onClick={handleSaveDraft} 
                disabled={isSavingDraft || isSubmitting}
                className="flex items-center gap-2"
              >
                {isSavingDraft ? 'Saving...' : (initial ? 'Save' : 'Save Draft')}
              </Button>
            </div>
            <div className="flex gap-2">
              {step < totalSteps ? (
                <Button type="button" onClick={handleNext}>Next</Button>
              ) : (
                <Button type="button" onClick={handleSubmit} disabled={isSubmitting || isSavingDraft}>{isSubmitting ? 'Saving...' : 'Save Contract'}</Button>
              )}
            </div>
          </div>
        </DialogFooter>

        <DatasetLookupDialog isOpen={lookupOpen} onOpenChange={setLookupOpen} onSelect={handleInferFromDataset} />
      </DialogContent>
    </Dialog>
  )
}


