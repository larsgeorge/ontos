import React, { useEffect, useMemo, useState } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import DatasetLookupDialog from './dataset-lookup-dialog'
import { useDomains } from '@/hooks/use-domains'

type WizardProps = {
  isOpen: boolean
  onOpenChange: (open: boolean) => void
  onSubmit: (payload: any) => Promise<void>
  initial?: any
}

const statuses = ['draft', 'active', 'deprecated', 'archived']

export default function DataContractWizardDialog({ isOpen, onOpenChange, onSubmit, initial }: WizardProps) {
  const { domains, loading: domainsLoading } = useDomains()
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

  type Column = { name: string; logicalType: string; required?: boolean; unique?: boolean; description?: string }
  type SchemaObject = { name: string; physicalName?: string; properties: Column[] }
  const [schemaObjects, setSchemaObjects] = useState<SchemaObject[]>(initial?.schemaObjects || [])
  const [lookupOpen, setLookupOpen] = useState(false)

  // Reset wizard state when opening for new contract
  useEffect(() => {
    if (isOpen && !initial) {
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
      setIsSubmitting(false)
    } else if (isOpen && initial) {
      // Initialize from provided data for editing
      console.log('Wizard initializing with data:', initial)
      console.log('Initial domain value:', initial.domain)
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
      console.log('Domain state set to:', initial.domain || '')
      setIsSubmitting(false)
    }
  }, [isOpen, initial])

  const addObject = () => setSchemaObjects((prev) => [...prev, { name: '', properties: [] }])
  const removeObject = (idx: number) => setSchemaObjects((prev) => prev.filter((_, i) => i !== idx))
  const addColumn = (objIdx: number) => setSchemaObjects((prev) => prev.map((o, i) => i === objIdx ? { ...o, properties: [...o.properties, { name: '', logicalType: 'string' }] } : o))
  const removeColumn = (objIdx: number, colIdx: number) => setSchemaObjects((prev) => prev.map((o, i) => i === objIdx ? { ...o, properties: o.properties.filter((_, j) => j !== colIdx) } : o))

  const handleInferFromDataset = (table: { full_name: string }) => {
    // Minimal inference stub: create object with physicalName
    setSchemaObjects((prev) => [...prev, { name: table.full_name.split('.').pop() || table.full_name, physicalName: table.full_name, properties: [] }])
  }

  const handleNext = () => { if (step < totalSteps) setStep(step + 1) }
  const handlePrev = () => { if (step > 1) setStep(step - 1) }

  const handleSubmit = async () => {
    console.log('HandleSubmit called - domain state:', domain)
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
      }
      console.log('Submitting payload from wizard:', payload)
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

    console.log('HandleSaveDraft called - domain state:', domain)
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
      }
      console.log('Submitting draft payload from wizard:', payload)
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
          <div className={step === 2 ? 'block space-y-6' : 'hidden'}>
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
                  <div key={objIndex} className="border rounded-lg p-6 bg-card">
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
                        <div className="font-medium">Columns ({obj.properties.length})</div>
                        <Button type="button" variant="outline" size="sm" onClick={() => addColumn(objIndex)} className="gap-2">
                          ➕ Add Column
                        </Button>
                      </div>

                      {obj.properties.length === 0 ? (
                        <div className="text-center py-6 border border-dashed border-muted-foreground/25 rounded">
                          <div className="text-sm text-muted-foreground">No columns defined</div>
                        </div>
                      ) : (
                        <div className="space-y-3">
                          {obj.properties.map((col, colIndex) => (
                            <div key={colIndex} className="grid grid-cols-1 lg:grid-cols-12 gap-3 p-3 border rounded bg-muted/30">
                              <div className="lg:col-span-3">
                                <Label className="text-xs">Column Name *</Label>
                                <Input 
                                  placeholder="column_name" 
                                  value={col.name} 
                                  onChange={(e) => setSchemaObjects((prev) => prev.map((x, i) => i === objIndex ? { ...x, properties: x.properties.map((y, j) => j === colIndex ? { ...y, name: e.target.value } : y) } : x))}
                                  className="mt-1 text-sm"
                                />
                              </div>
                              <div className="lg:col-span-2">
                                <Label className="text-xs">Type *</Label>
                                <Input 
                                  placeholder="string" 
                                  value={col.logicalType} 
                                  onChange={(e) => setSchemaObjects((prev) => prev.map((x, i) => i === objIndex ? { ...x, properties: x.properties.map((y, j) => j === colIndex ? { ...y, logicalType: e.target.value } : y) } : x))}
                                  className="mt-1 text-sm"
                                />
                              </div>
                              <div className="lg:col-span-4">
                                <Label className="text-xs">Description</Label>
                                <Input 
                                  placeholder="Column description..." 
                                  value={col.description || ''} 
                                  onChange={(e) => setSchemaObjects((prev) => prev.map((x, i) => i === objIndex ? { ...x, properties: x.properties.map((y, j) => j === colIndex ? { ...y, description: e.target.value } : y) } : x))}
                                  className="mt-1 text-sm"
                                />
                              </div>
                              <div className="lg:col-span-2 flex items-end gap-2">
                                <label className="flex items-center gap-1 text-xs">
                                  <input 
                                    type="checkbox" 
                                    checked={!!col.required} 
                                    onChange={(e) => setSchemaObjects((prev) => prev.map((x, i) => i === objIndex ? { ...x, properties: x.properties.map((y, j) => j === colIndex ? { ...y, required: e.target.checked } : y) } : x))} 
                                  /> 
                                  Required
                                </label>
                                <label className="flex items-center gap-1 text-xs">
                                  <input 
                                    type="checkbox" 
                                    checked={!!col.unique} 
                                    onChange={(e) => setSchemaObjects((prev) => prev.map((x, i) => i === objIndex ? { ...x, properties: x.properties.map((y, j) => j === colIndex ? { ...y, unique: e.target.checked } : y) } : x))} 
                                  /> 
                                  Unique
                                </label>
                              </div>
                              <div className="lg:col-span-1 flex items-end">
                                <Button 
                                  type="button" 
                                  variant="ghost" 
                                  size="sm"
                                  onClick={() => removeColumn(objIndex, colIndex)}
                                  className="text-destructive hover:text-destructive p-2"
                                >
                                  🗑️
                                </Button>
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
          <div className={step === 3 ? 'block space-y-6' : 'hidden'}>
            <div className="text-lg font-semibold text-foreground mb-4">Data Quality & Validation</div>
            
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Quality Rules */}
              <div className="space-y-4">
                <div className="font-medium">Quality Rules</div>
                <div className="space-y-3">
                  <div className="p-4 border rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <div className="font-medium text-sm">Completeness Checks</div>
                      <div className="text-xs text-muted-foreground">Required</div>
                    </div>
                    <div className="space-y-2">
                      <label className="flex items-center gap-2 text-sm">
                        <input type="checkbox" className="rounded" />
                        Non-null validation for required fields
                      </label>
                      <label className="flex items-center gap-2 text-sm">
                        <input type="checkbox" className="rounded" />
                        Empty string validation
                      </label>
                      <label className="flex items-center gap-2 text-sm">
                        <input type="checkbox" className="rounded" />
                        Missing value detection
                      </label>
                    </div>
                  </div>

                  <div className="p-4 border rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <div className="font-medium text-sm">Accuracy Checks</div>
                      <div className="text-xs text-muted-foreground">Optional</div>
                    </div>
                    <div className="space-y-2">
                      <label className="flex items-center gap-2 text-sm">
                        <input type="checkbox" className="rounded" />
                        Data format validation (emails, phone numbers, etc.)
                      </label>
                      <label className="flex items-center gap-2 text-sm">
                        <input type="checkbox" className="rounded" />
                        Range and boundary checks
                      </label>
                      <label className="flex items-center gap-2 text-sm">
                        <input type="checkbox" className="rounded" />
                        Business rule validation
                      </label>
                    </div>
                  </div>

                  <div className="p-4 border rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <div className="font-medium text-sm">Consistency Checks</div>
                      <div className="text-xs text-muted-foreground">Optional</div>
                    </div>
                    <div className="space-y-2">
                      <label className="flex items-center gap-2 text-sm">
                        <input type="checkbox" className="rounded" />
                        Cross-field validation
                      </label>
                      <label className="flex items-center gap-2 text-sm">
                        <input type="checkbox" className="rounded" />
                        Referential integrity checks
                      </label>
                      <label className="flex items-center gap-2 text-sm">
                        <input type="checkbox" className="rounded" />
                        Duplicate detection
                      </label>
                    </div>
                  </div>
                </div>
              </div>

              {/* Quality Thresholds & Metrics */}
              <div className="space-y-4">
                <div className="font-medium">Quality Thresholds</div>
                <div className="space-y-4">
                  <div>
                    <Label className="text-sm font-medium">Minimum Data Quality Score</Label>
                    <div className="flex items-center gap-2 mt-1">
                      <Input type="number" placeholder="85" className="w-20" />
                      <span className="text-sm text-muted-foreground">% (0-100)</span>
                    </div>
                  </div>
                  <div>
                    <Label className="text-sm font-medium">Completeness Threshold</Label>
                    <div className="flex items-center gap-2 mt-1">
                      <Input type="number" placeholder="95" className="w-20" />
                      <span className="text-sm text-muted-foreground">% (0-100)</span>
                    </div>
                  </div>
                  <div>
                    <Label className="text-sm font-medium">Accuracy Threshold</Label>
                    <div className="flex items-center gap-2 mt-1">
                      <Input type="number" placeholder="90" className="w-20" />
                      <span className="text-sm text-muted-foreground">% (0-100)</span>
                    </div>
                  </div>
                </div>

                <div className="border-t pt-4">
                  <div className="font-medium mb-3">Monitoring & Alerts</div>
                  <div className="space-y-3">
                    <div>
                      <Label className="text-sm font-medium">Validation Frequency</Label>
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
                      <Label className="text-sm font-medium">Alert Recipients</Label>
                      <Input placeholder="team@company.com, alerts@company.com" className="mt-1" />
                    </div>
                    <div className="flex items-center gap-2">
                      <input type="checkbox" className="rounded" />
                      <Label className="text-sm">Send alerts on quality threshold violations</Label>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Custom Quality Rules */}
            <div className="border-t pt-6">
              <div className="font-medium mb-4">Custom Quality Rules</div>
              <div className="space-y-3">
                <Textarea 
                  placeholder="Define custom quality rules or SQL-based validation queries..."
                  className="min-h-[100px]"
                />
                <div className="text-xs text-muted-foreground">
                  Example: SELECT COUNT(*) FROM table WHERE email NOT LIKE '%@%.%' -- Invalid email format
                </div>
              </div>
            </div>
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
                          <Input type="number" placeholder="99.9" className="w-20" />
                          <span className="text-sm text-muted-foreground">% availability</span>
                        </div>
                      </div>
                      <div>
                        <Label className="text-sm font-medium">Maximum Downtime per Month</Label>
                        <div className="flex items-center gap-2 mt-1">
                          <Input type="number" placeholder="43" className="w-20" />
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
                          <Input type="number" placeholder="2" className="w-20" />
                          <Select>
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
                          <Input type="number" placeholder="15" className="w-20" />
                          <Select>
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
                <div className="font-medium">Infrastructure & Servers</div>
                
                <div className="space-y-4">
                  <div className="p-4 border rounded-lg">
                    <div className="font-medium text-sm mb-3">Data Source Configuration</div>
                    <div className="space-y-3">
                      <div>
                        <Label className="text-sm font-medium">Server Type</Label>
                        <Select>
                          <SelectTrigger className="mt-1">
                            <SelectValue placeholder="Select server type" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="databricks">Databricks</SelectItem>
                            <SelectItem value="snowflake">Snowflake</SelectItem>
                            <SelectItem value="postgresql">PostgreSQL</SelectItem>
                            <SelectItem value="mysql">MySQL</SelectItem>
                            <SelectItem value="api">REST API</SelectItem>
                            <SelectItem value="file">File System</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div>
                        <Label className="text-sm font-medium">Connection String / Endpoint</Label>
                        <Input placeholder="jdbc:databricks://..." className="mt-1" />
                      </div>
                      <div>
                        <Label className="text-sm font-medium">Environment</Label>
                        <Select>
                          <SelectTrigger className="mt-1">
                            <SelectValue placeholder="Select environment" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="production">Production</SelectItem>
                            <SelectItem value="staging">Staging</SelectItem>
                            <SelectItem value="development">Development</SelectItem>
                            <SelectItem value="test">Test</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                  </div>

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


