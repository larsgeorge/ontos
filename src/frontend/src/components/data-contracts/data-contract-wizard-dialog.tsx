import React, { useEffect, useMemo, useState } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import DatasetLookupDialog from './dataset-lookup-dialog'

type WizardProps = {
  isOpen: boolean
  onOpenChange: (open: boolean) => void
  onSubmit: (payload: any) => Promise<void>
  initial?: any
}

const statuses = ['draft', 'active', 'deprecated', 'archived']

export default function DataContractWizardDialog({ isOpen, onOpenChange, onSubmit, initial }: WizardProps) {
  const [step, setStep] = useState(1)
  const totalSteps = 5
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Step fields
  const [name, setName] = useState(initial?.name || '')
  const [version, setVersion] = useState(initial?.version || 'v1.0')
  const [status, setStatus] = useState(initial?.status || 'draft')
  const [owner, setOwner] = useState(initial?.owner || '')
  const [descriptionUsage, setDescriptionUsage] = useState(initial?.descriptionUsage || '')
  const [descriptionPurpose, setDescriptionPurpose] = useState(initial?.descriptionPurpose || '')
  const [descriptionLimitations, setDescriptionLimitations] = useState(initial?.descriptionLimitations || '')

  type Column = { name: string; logicalType: string; required?: boolean; unique?: boolean; description?: string }
  type SchemaObject = { name: string; physicalName?: string; properties: Column[] }
  const [schemaObjects, setSchemaObjects] = useState<SchemaObject[]>(initial?.schemaObjects || [])
  const [lookupOpen, setLookupOpen] = useState(false)

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
    setIsSubmitting(true)
    try {
      await onSubmit({
        name,
        version,
        status,
        owner,
        description: { usage: descriptionUsage, purpose: descriptionPurpose, limitations: descriptionLimitations },
        schema: schemaObjects.map((o) => ({ name: o.name, physicalName: o.physicalName, properties: o.properties })),
      })
      onOpenChange(false)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px] md:max-w-[800px] max-h-[90vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>Data Contract Wizard (Step {step} of {totalSteps})</DialogTitle>
          <DialogDescription>Build a contract incrementally according to ODCS.</DialogDescription>
        </DialogHeader>

        <div className="flex-grow overflow-y-auto space-y-4 pr-4">
          {/* Step 1: Basics */}
          <div className={step === 1 ? 'block space-y-3' : 'hidden'}>
            <div>
              <Label htmlFor="dc-name">Name *</Label>
              <Input id="dc-name" value={name} onChange={(e) => setName(e.target.value)} />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="dc-version">Version *</Label>
                <Input id="dc-version" value={version} onChange={(e) => setVersion(e.target.value)} />
              </div>
              <div>
                <Label>Status</Label>
                <Select value={status} onValueChange={setStatus}>
                  <SelectTrigger><SelectValue placeholder="Select status" /></SelectTrigger>
                  <SelectContent>
                    {statuses.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div>
              <Label htmlFor="dc-owner">Owner *</Label>
              <Input id="dc-owner" value={owner} onChange={(e) => setOwner(e.target.value)} />
            </div>
          </div>

          {/* Step 2: Description */}
          <div className={step === 2 ? 'block space-y-3' : 'hidden'}>
            <div>
              <Label>Usage</Label>
              <Textarea value={descriptionUsage} onChange={(e) => setDescriptionUsage(e.target.value)} />
            </div>
            <div>
              <Label>Purpose</Label>
              <Textarea value={descriptionPurpose} onChange={(e) => setDescriptionPurpose(e.target.value)} />
            </div>
            <div>
              <Label>Limitations</Label>
              <Textarea value={descriptionLimitations} onChange={(e) => setDescriptionLimitations(e.target.value)} />
            </div>
          </div>

          {/* Step 3: Schema Objects */}
          <div className={step === 3 ? 'block space-y-3' : 'hidden'}>
            <div className="flex justify-between items-center">
              <div className="text-sm font-medium">Schema Objects</div>
              <div className="flex gap-2">
                <Button type="button" variant="outline" onClick={() => setLookupOpen(true)}>Infer from existing dataset</Button>
                <Button type="button" variant="outline" onClick={addObject}>Add Object</Button>
              </div>
            </div>
            {schemaObjects.length === 0 ? (
              <div className="text-sm text-muted-foreground">No objects added.</div>
            ) : (
              schemaObjects.map((o, oi) => (
                <div key={oi} className="border rounded p-3 space-y-2">
                  <div className="flex gap-2">
                    <Input placeholder="Logical name" value={o.name} onChange={(e) => setSchemaObjects((prev) => prev.map((x, i) => i === oi ? { ...x, name: e.target.value } : x))} />
                    <Input placeholder="Physical name (optional)" value={o.physicalName || ''} onChange={(e) => setSchemaObjects((prev) => prev.map((x, i) => i === oi ? { ...x, physicalName: e.target.value } : x))} />
                    <Button type="button" variant="ghost" onClick={() => removeObject(oi)}>Remove</Button>
                  </div>
                  <div className="space-y-2">
                    <div className="flex justify-between items-center">
                      <div className="text-xs text-muted-foreground">Columns</div>
                      <Button type="button" variant="outline" size="sm" onClick={() => addColumn(oi)}>Add Column</Button>
                    </div>
                    {o.properties.length === 0 ? (
                      <div className="text-xs text-muted-foreground">No columns.</div>
                    ) : (
                      o.properties.map((c, ci) => (
                        <div key={ci} className="grid grid-cols-1 md:grid-cols-4 gap-2">
                          <Input placeholder="Name" value={c.name} onChange={(e) => setSchemaObjects((prev) => prev.map((x, i) => i === oi ? { ...x, properties: x.properties.map((y, j) => j === ci ? { ...y, name: e.target.value } : y) } : x))} />
                          <Input placeholder="Logical Type (e.g., string, number)" value={c.logicalType} onChange={(e) => setSchemaObjects((prev) => prev.map((x, i) => i === oi ? { ...x, properties: x.properties.map((y, j) => j === ci ? { ...y, logicalType: e.target.value } : y) } : x))} />
                          <Input placeholder="Description" value={c.description || ''} onChange={(e) => setSchemaObjects((prev) => prev.map((x, i) => i === oi ? { ...x, properties: x.properties.map((y, j) => j === ci ? { ...y, description: e.target.value } : y) } : x))} />
                          <div className="flex items-center gap-2">
                            <label className="text-xs flex items-center gap-1"><input type="checkbox" checked={!!c.required} onChange={(e) => setSchemaObjects((prev) => prev.map((x, i) => i === oi ? { ...x, properties: x.properties.map((y, j) => j === ci ? { ...y, required: e.target.checked } : y) } : x))} /> required</label>
                            <label className="text-xs flex items-center gap-1"><input type="checkbox" checked={!!c.unique} onChange={(e) => setSchemaObjects((prev) => prev.map((x, i) => i === oi ? { ...x, properties: x.properties.map((y, j) => j === ci ? { ...y, unique: e.target.checked } : y) } : x))} /> unique</label>
                            <Button type="button" variant="ghost" onClick={() => removeColumn(oi, ci)}>Remove</Button>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Step 4 / 5 placeholders for roles/servers/SLA/quality */}
          <div className={step === 4 ? 'block space-y-3' : 'hidden'}>
            <div className="text-sm text-muted-foreground">Configure roles, team, and support (to be expanded).</div>
          </div>
          <div className={step === 5 ? 'block space-y-3' : 'hidden'}>
            <div className="text-sm text-muted-foreground">Configure SLA and quality checks (to be expanded).</div>
          </div>
        </div>

        <DialogFooter className="mt-4">
          <div className="flex justify-between w-full">
            <Button type="button" variant="outline" onClick={handlePrev} disabled={step === 1}>Previous</Button>
            {step < totalSteps ? (
              <Button type="button" onClick={handleNext}>Next</Button>
            ) : (
              <Button type="button" onClick={handleSubmit} disabled={isSubmitting}>{isSubmitting ? 'Saving...' : 'Save Contract'}</Button>
            )}
          </div>
        </DialogFooter>

        <DatasetLookupDialog isOpen={lookupOpen} onOpenChange={setLookupOpen} onSelect={handleInferFromDataset} />
      </DialogContent>
    </Dialog>
  )
}


