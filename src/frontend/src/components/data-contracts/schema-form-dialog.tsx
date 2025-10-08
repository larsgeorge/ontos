import { useEffect, useState } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { Checkbox } from '@/components/ui/checkbox'
import { Plus, Trash2, Edit } from 'lucide-react'
import { useToast } from '@/hooks/use-toast'
import type { SchemaObject, ColumnProperty } from '@/types/data-contract'

type SchemaFormProps = {
  isOpen: boolean
  onOpenChange: (open: boolean) => void
  onSubmit: (schema: SchemaObject) => Promise<void>
  initial?: SchemaObject
}

const LOGICAL_TYPES = ['string', 'date', 'number', 'integer', 'object', 'array', 'boolean']
const PHYSICAL_TYPES = ['table', 'view', 'materialized_view', 'external_table', 'managed_table', 'streaming_table']

export default function SchemaFormDialog({ isOpen, onOpenChange, onSubmit, initial }: SchemaFormProps) {
  const { toast } = useToast()
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Schema-level fields
  const [name, setName] = useState('')
  const [physicalName, setPhysicalName] = useState('')
  const [description, setDescription] = useState('')
  const [businessName, setBusinessName] = useState('')
  const [physicalType, setPhysicalType] = useState('table')
  const [dataGranularityDescription, setDataGranularityDescription] = useState('')

  // Properties (columns)
  const [properties, setProperties] = useState<ColumnProperty[]>([])
  const [editingPropertyIndex, setEditingPropertyIndex] = useState<number | null>(null)

  // Property form state
  const [propName, setPropName] = useState('')
  const [propLogicalType, setPropLogicalType] = useState('string')
  const [propRequired, setPropRequired] = useState(false)
  const [propUnique, setPropUnique] = useState(false)
  const [propDescription, setPropDescription] = useState('')

  // Initialize form when dialog opens
  useEffect(() => {
    if (isOpen && initial) {
      setName(initial.name || '')
      setPhysicalName(initial.physicalName || '')
      setDescription(initial.description || '')
      setBusinessName(initial.businessName || '')
      setPhysicalType(initial.physicalType || 'table')
      setDataGranularityDescription(initial.dataGranularityDescription || '')
      setProperties(initial.properties || [])
    } else if (isOpen && !initial) {
      // Reset for new schema
      setName('')
      setPhysicalName('')
      setDescription('')
      setBusinessName('')
      setPhysicalType('table')
      setDataGranularityDescription('')
      setProperties([])
    }
    // Reset property form
    setEditingPropertyIndex(null)
    setPropName('')
    setPropLogicalType('string')
    setPropRequired(false)
    setPropUnique(false)
    setPropDescription('')
  }, [isOpen, initial])

  const handleAddProperty = () => {
    if (!propName.trim()) {
      toast({ title: 'Validation Error', description: 'Column name is required', variant: 'destructive' })
      return
    }

    const newProperty: ColumnProperty = {
      name: propName.trim(),
      logicalType: propLogicalType,
      required: propRequired,
      unique: propUnique,
      description: propDescription.trim() || undefined,
    }

    if (editingPropertyIndex !== null) {
      // Update existing property
      const updated = [...properties]
      updated[editingPropertyIndex] = newProperty
      setProperties(updated)
      setEditingPropertyIndex(null)
    } else {
      // Add new property
      setProperties([...properties, newProperty])
    }

    // Reset property form
    setPropName('')
    setPropLogicalType('string')
    setPropRequired(false)
    setPropUnique(false)
    setPropDescription('')
  }

  const handleEditProperty = (index: number) => {
    const prop = properties[index]
    setPropName(prop.name)
    setPropLogicalType(prop.logicalType)
    setPropRequired(prop.required || false)
    setPropUnique(prop.unique || false)
    setPropDescription(prop.description || '')
    setEditingPropertyIndex(index)
  }

  const handleDeleteProperty = (index: number) => {
    setProperties(properties.filter((_, i) => i !== index))
    if (editingPropertyIndex === index) {
      setEditingPropertyIndex(null)
      setPropName('')
      setPropLogicalType('string')
      setPropRequired(false)
      setPropUnique(false)
      setPropDescription('')
    }
  }

  const handleCancelPropertyEdit = () => {
    setEditingPropertyIndex(null)
    setPropName('')
    setPropLogicalType('string')
    setPropRequired(false)
    setPropUnique(false)
    setPropDescription('')
  }

  const handleSubmit = async () => {
    // Validate
    if (!name.trim()) {
      toast({ title: 'Validation Error', description: 'Schema name is required', variant: 'destructive' })
      return
    }

    if (properties.length === 0) {
      toast({ title: 'Validation Error', description: 'At least one column is required', variant: 'destructive' })
      return
    }

    setIsSubmitting(true)
    try {
      const schema: SchemaObject = {
        name: name.trim(),
        physicalName: physicalName.trim() || undefined,
        description: description.trim() || undefined,
        businessName: businessName.trim() || undefined,
        physicalType: physicalType || undefined,
        dataGranularityDescription: dataGranularityDescription.trim() || undefined,
        properties,
      }

      await onSubmit(schema)
      onOpenChange(false)
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error?.message || 'Failed to save schema',
        variant: 'destructive',
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{initial ? 'Edit Schema' : 'Add New Schema'}</DialogTitle>
          <DialogDescription>
            Define a schema object (table/view) and its properties (columns).
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Schema-level fields */}
          <div className="space-y-4">
            <h3 className="text-sm font-semibold">Schema Information</h3>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="name">
                  Name <span className="text-destructive">*</span>
                </Label>
                <Input
                  id="name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g., customers"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="physicalName">Physical Name</Label>
                <Input
                  id="physicalName"
                  value={physicalName}
                  onChange={(e) => setPhysicalName(e.target.value)}
                  placeholder="e.g., catalog.schema.customers"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="businessName">Business Name</Label>
                <Input
                  id="businessName"
                  value={businessName}
                  onChange={(e) => setBusinessName(e.target.value)}
                  placeholder="Human-readable name"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="physicalType">Physical Type</Label>
                <Select value={physicalType} onValueChange={setPhysicalType}>
                  <SelectTrigger id="physicalType">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {PHYSICAL_TYPES.map((type) => (
                      <SelectItem key={type} value={type}>
                        {type}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Describe this schema"
                rows={2}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="dataGranularityDescription">Data Granularity</Label>
              <Input
                id="dataGranularityDescription"
                value={dataGranularityDescription}
                onChange={(e) => setDataGranularityDescription(e.target.value)}
                placeholder="e.g., One row per customer"
              />
            </div>
          </div>

          {/* Properties section */}
          <div className="space-y-4 border-t pt-4">
            <h3 className="text-sm font-semibold">
              Properties (Columns) <span className="text-destructive">*</span>
            </h3>

            {/* Property form */}
            <div className="border rounded-lg p-4 space-y-3 bg-muted/50">
              <div className="grid grid-cols-3 gap-3">
                <div className="space-y-1.5">
                  <Label htmlFor="propName" className="text-xs">Column Name</Label>
                  <Input
                    id="propName"
                    value={propName}
                    onChange={(e) => setPropName(e.target.value)}
                    placeholder="e.g., customer_id"
                    className="h-9"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="propLogicalType" className="text-xs">Data Type</Label>
                  <Select value={propLogicalType} onValueChange={setPropLogicalType}>
                    <SelectTrigger id="propLogicalType" className="h-9">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {LOGICAL_TYPES.map((type) => (
                        <SelectItem key={type} value={type}>
                          {type}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs">Constraints</Label>
                  <div className="flex items-center gap-3 h-9">
                    <div className="flex items-center gap-1.5">
                      <Checkbox
                        id="propRequired"
                        checked={propRequired}
                        onCheckedChange={(checked) => setPropRequired(checked as boolean)}
                      />
                      <Label htmlFor="propRequired" className="text-xs font-normal cursor-pointer">
                        Required
                      </Label>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <Checkbox
                        id="propUnique"
                        checked={propUnique}
                        onCheckedChange={(checked) => setPropUnique(checked as boolean)}
                      />
                      <Label htmlFor="propUnique" className="text-xs font-normal cursor-pointer">
                        Unique
                      </Label>
                    </div>
                  </div>
                </div>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="propDescription" className="text-xs">Description</Label>
                <Input
                  id="propDescription"
                  value={propDescription}
                  onChange={(e) => setPropDescription(e.target.value)}
                  placeholder="Describe this column"
                  className="h-9"
                />
              </div>
              <div className="flex gap-2">
                <Button
                  type="button"
                  size="sm"
                  onClick={handleAddProperty}
                  className="h-8"
                >
                  {editingPropertyIndex !== null ? (
                    <>
                      <Edit className="h-3.5 w-3.5 mr-1.5" />
                      Update Column
                    </>
                  ) : (
                    <>
                      <Plus className="h-3.5 w-3.5 mr-1.5" />
                      Add Column
                    </>
                  )}
                </Button>
                {editingPropertyIndex !== null && (
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={handleCancelPropertyEdit}
                    className="h-8"
                  >
                    Cancel
                  </Button>
                )}
              </div>
            </div>

            {/* Properties list */}
            {properties.length > 0 && (
              <div className="border rounded-lg overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="bg-muted">
                    <tr>
                      <th className="text-left p-2 font-medium">Name</th>
                      <th className="text-left p-2 font-medium">Type</th>
                      <th className="text-left p-2 font-medium">Constraints</th>
                      <th className="text-left p-2 font-medium">Description</th>
                      <th className="text-right p-2 font-medium">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {properties.map((prop, idx) => (
                      <tr key={idx} className="border-t">
                        <td className="p-2 font-mono text-xs">{prop.name}</td>
                        <td className="p-2">
                          <span className="text-xs bg-secondary px-2 py-0.5 rounded">
                            {prop.logicalType}
                          </span>
                        </td>
                        <td className="p-2">
                          <div className="flex gap-2 text-xs">
                            {prop.required && <span className="text-green-600">Required</span>}
                            {prop.unique && <span className="text-blue-600">Unique</span>}
                            {!prop.required && !prop.unique && <span className="text-muted-foreground">-</span>}
                          </div>
                        </td>
                        <td className="p-2 text-xs text-muted-foreground max-w-xs truncate">
                          {prop.description || '-'}
                        </td>
                        <td className="p-2">
                          <div className="flex justify-end gap-1">
                            <Button
                              type="button"
                              size="sm"
                              variant="ghost"
                              onClick={() => handleEditProperty(idx)}
                              className="h-7 w-7 p-0"
                            >
                              <Edit className="h-3.5 w-3.5" />
                            </Button>
                            <Button
                              type="button"
                              size="sm"
                              variant="ghost"
                              onClick={() => handleDeleteProperty(idx)}
                              className="h-7 w-7 p-0 text-destructive hover:text-destructive"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {properties.length === 0 && (
              <p className="text-sm text-muted-foreground text-center py-4 border rounded-lg bg-muted/30">
                No columns added yet. Add at least one column above.
              </p>
            )}
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={isSubmitting}>
            {isSubmitting ? 'Saving...' : initial ? 'Save Changes' : 'Add Schema'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
