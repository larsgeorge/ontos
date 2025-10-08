import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Checkbox } from '@/components/ui/checkbox'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Plus, Trash2, Edit, Info } from 'lucide-react'
import { useToast } from '@/hooks/use-toast'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import type { ColumnProperty } from '@/types/data-contract'

const LOGICAL_TYPES = ['string', 'date', 'number', 'integer', 'object', 'array', 'boolean']
const CLASSIFICATION_LEVELS = ['public', 'internal', 'confidential', 'restricted', 'pii', '1', '2', '3', '4', '5']

interface SchemaPropertyEditorProps {
  properties: ColumnProperty[]
  onChange: (properties: ColumnProperty[]) => void
  readOnly?: boolean
}

export default function SchemaPropertyEditor({ properties, onChange, readOnly = false }: SchemaPropertyEditorProps) {
  const { toast } = useToast()
  const [editingIndex, setEditingIndex] = useState<number | null>(null)

  // Core fields
  const [name, setName] = useState('')
  const [logicalType, setLogicalType] = useState('string')
  const [description, setDescription] = useState('')

  // Physical fields
  const [physicalType, setPhysicalType] = useState('')
  const [physicalName, setPhysicalName] = useState('')

  // Constraints
  const [required, setRequired] = useState(false)
  const [unique, setUnique] = useState(false)
  const [primaryKey, setPrimaryKey] = useState(false)
  const [primaryKeyPosition, setPrimaryKeyPosition] = useState('')

  // Partitioning
  const [partitioned, setPartitioned] = useState(false)
  const [partitionKeyPosition, setPartitionKeyPosition] = useState('')

  // Governance
  const [classification, setClassification] = useState('')
  const [examples, setExamples] = useState('')

  // Business
  const [businessName, setBusinessName] = useState('')
  const [encryptedName, setEncryptedName] = useState('')
  const [criticalDataElement, setCriticalDataElement] = useState(false)

  // Transformation
  const [transformLogic, setTransformLogic] = useState('')
  const [transformSourceObjects, setTransformSourceObjects] = useState('')
  const [transformDescription, setTransformDescription] = useState('')

  const resetForm = () => {
    setName('')
    setLogicalType('string')
    setDescription('')
    setPhysicalType('')
    setPhysicalName('')
    setRequired(false)
    setUnique(false)
    setPrimaryKey(false)
    setPrimaryKeyPosition('')
    setPartitioned(false)
    setPartitionKeyPosition('')
    setClassification('')
    setExamples('')
    setBusinessName('')
    setEncryptedName('')
    setCriticalDataElement(false)
    setTransformLogic('')
    setTransformSourceObjects('')
    setTransformDescription('')
    setEditingIndex(null)
  }

  const loadProperty = (prop: ColumnProperty) => {
    setName(prop.name)
    setLogicalType(prop.logicalType)
    setDescription(prop.description || '')
    setPhysicalType(prop.physicalType || '')
    setPhysicalName(prop.physicalName || '')
    setRequired(prop.required || false)
    setUnique(prop.unique || false)
    setPrimaryKey(prop.primaryKey || false)
    setPrimaryKeyPosition(prop.primaryKeyPosition !== undefined && prop.primaryKeyPosition !== -1 ? String(prop.primaryKeyPosition) : '')
    setPartitioned(prop.partitioned || false)
    setPartitionKeyPosition(prop.partitionKeyPosition !== undefined && prop.partitionKeyPosition !== -1 ? String(prop.partitionKeyPosition) : '')
    setClassification(prop.classification || '')
    setExamples(prop.examples || '')
    setBusinessName(prop.businessName || '')
    setEncryptedName(prop.encryptedName || '')
    setCriticalDataElement(prop.criticalDataElement || false)
    setTransformLogic(prop.transformLogic || '')
    setTransformSourceObjects(prop.transformSourceObjects || '')
    setTransformDescription(prop.transformDescription || '')
  }

  const handleAddOrUpdate = () => {
    if (!name.trim()) {
      toast({ title: 'Validation Error', description: 'Column name is required', variant: 'destructive' })
      return
    }

    const newProperty: ColumnProperty = {
      name: name.trim(),
      logicalType,
      description: description.trim() || undefined,
      physicalType: physicalType.trim() || undefined,
      physicalName: physicalName.trim() || undefined,
      required: required || undefined,
      unique: unique || undefined,
      primaryKey: primaryKey || undefined,
      primaryKeyPosition: primaryKey && primaryKeyPosition ? parseInt(primaryKeyPosition) : undefined,
      partitioned: partitioned || undefined,
      partitionKeyPosition: partitioned && partitionKeyPosition ? parseInt(partitionKeyPosition) : undefined,
      classification: classification || undefined,
      examples: examples.trim() || undefined,
      businessName: businessName.trim() || undefined,
      encryptedName: encryptedName.trim() || undefined,
      criticalDataElement: criticalDataElement || undefined,
      transformLogic: transformLogic.trim() || undefined,
      transformSourceObjects: transformSourceObjects.trim() || undefined,
      transformDescription: transformDescription.trim() || undefined,
    }

    if (editingIndex !== null) {
      // Update existing
      const updated = [...properties]
      updated[editingIndex] = newProperty
      onChange(updated)
    } else {
      // Add new
      onChange([...properties, newProperty])
    }

    resetForm()
  }

  const handleEdit = (index: number) => {
    loadProperty(properties[index])
    setEditingIndex(index)
  }

  const handleDelete = (index: number) => {
    onChange(properties.filter((_, i) => i !== index))
    if (editingIndex === index) {
      resetForm()
    }
  }

  const FieldTooltip = ({ content }: { content: string }) => (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Info className="h-3 w-3 text-muted-foreground cursor-help inline-block ml-1" />
        </TooltipTrigger>
        <TooltipContent>
          <p className="text-xs max-w-xs">{content}</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )

  return (
    <div className="space-y-4">
      {/* Property Form */}
      {!readOnly && (
        <div className="border rounded-lg p-4 space-y-4 bg-muted/30">
          <Tabs defaultValue="core" className="w-full">
            <TabsList className="grid w-full grid-cols-5">
              <TabsTrigger value="core">Core</TabsTrigger>
              <TabsTrigger value="constraints">Constraints</TabsTrigger>
              <TabsTrigger value="governance">Governance</TabsTrigger>
              <TabsTrigger value="business">Business</TabsTrigger>
              <TabsTrigger value="transform">Transform</TabsTrigger>
            </TabsList>

            {/* Core Tab */}
            <TabsContent value="core" className="space-y-3 mt-4">
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label htmlFor="prop-name" className="text-xs">
                    Column Name <span className="text-destructive">*</span>
                  </Label>
                  <Input
                    id="prop-name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="e.g., customer_id"
                    className="h-9"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="prop-logical-type" className="text-xs">
                    Logical Type <span className="text-destructive">*</span>
                  </Label>
                  <Select value={logicalType} onValueChange={setLogicalType}>
                    <SelectTrigger id="prop-logical-type" className="h-9">
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
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label htmlFor="prop-physical-type" className="text-xs flex items-center">
                    Physical Type
                    <FieldTooltip content="Physical data type like VARCHAR(50), INT, DECIMAL(10,2)" />
                  </Label>
                  <Input
                    id="prop-physical-type"
                    value={physicalType}
                    onChange={(e) => setPhysicalType(e.target.value)}
                    placeholder="e.g., VARCHAR(50)"
                    className="h-9"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="prop-physical-name" className="text-xs flex items-center">
                    Physical Name
                    <FieldTooltip content="Physical column name in the database" />
                  </Label>
                  <Input
                    id="prop-physical-name"
                    value={physicalName}
                    onChange={(e) => setPhysicalName(e.target.value)}
                    placeholder="e.g., cust_id"
                    className="h-9"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="prop-description" className="text-xs">
                  Description
                </Label>
                <Input
                  id="prop-description"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Describe this column"
                  className="h-9"
                />
              </div>
            </TabsContent>

            {/* Constraints Tab */}
            <TabsContent value="constraints" className="space-y-3 mt-4">
              <div className="space-y-3">
                <div className="flex items-center gap-6">
                  <div className="flex items-center gap-2">
                    <Checkbox
                      id="prop-required"
                      checked={required}
                      onCheckedChange={(checked) => setRequired(checked as boolean)}
                    />
                    <Label htmlFor="prop-required" className="text-sm font-normal cursor-pointer">
                      Required (NOT NULL)
                    </Label>
                  </div>
                  <div className="flex items-center gap-2">
                    <Checkbox
                      id="prop-unique"
                      checked={unique}
                      onCheckedChange={(checked) => setUnique(checked as boolean)}
                    />
                    <Label htmlFor="prop-unique" className="text-sm font-normal cursor-pointer">
                      Unique
                    </Label>
                  </div>
                </div>

                <div className="border-t pt-3">
                  <div className="flex items-center gap-2 mb-2">
                    <Checkbox
                      id="prop-primary-key"
                      checked={primaryKey}
                      onCheckedChange={(checked) => setPrimaryKey(checked as boolean)}
                    />
                    <Label htmlFor="prop-primary-key" className="text-sm font-normal cursor-pointer flex items-center">
                      Primary Key
                      <FieldTooltip content="Mark this column as part of the primary key" />
                    </Label>
                  </div>
                  {primaryKey && (
                    <div className="ml-6 space-y-1.5">
                      <Label htmlFor="prop-pk-position" className="text-xs flex items-center">
                        Primary Key Position
                        <FieldTooltip content="Position in composite primary key (starting from 1)" />
                      </Label>
                      <Input
                        id="prop-pk-position"
                        type="number"
                        min="1"
                        value={primaryKeyPosition}
                        onChange={(e) => setPrimaryKeyPosition(e.target.value)}
                        placeholder="e.g., 1"
                        className="h-9 w-32"
                      />
                    </div>
                  )}
                </div>

                <div className="border-t pt-3">
                  <div className="flex items-center gap-2 mb-2">
                    <Checkbox
                      id="prop-partitioned"
                      checked={partitioned}
                      onCheckedChange={(checked) => setPartitioned(checked as boolean)}
                    />
                    <Label htmlFor="prop-partitioned" className="text-sm font-normal cursor-pointer flex items-center">
                      Partition Column
                      <FieldTooltip content="This column is used for table partitioning" />
                    </Label>
                  </div>
                  {partitioned && (
                    <div className="ml-6 space-y-1.5">
                      <Label htmlFor="prop-partition-position" className="text-xs flex items-center">
                        Partition Position
                        <FieldTooltip content="Position in partition key (starting from 1)" />
                      </Label>
                      <Input
                        id="prop-partition-position"
                        type="number"
                        min="1"
                        value={partitionKeyPosition}
                        onChange={(e) => setPartitionKeyPosition(e.target.value)}
                        placeholder="e.g., 1"
                        className="h-9 w-32"
                      />
                    </div>
                  )}
                </div>
              </div>
            </TabsContent>

            {/* Governance Tab */}
            <TabsContent value="governance" className="space-y-3 mt-4">
              <div className="space-y-1.5">
                <Label htmlFor="prop-classification" className="text-xs flex items-center">
                  Classification
                  <FieldTooltip content="Data sensitivity: public, internal, confidential, restricted, pii, or 1-5" />
                </Label>
                <Select value={classification || undefined} onValueChange={setClassification}>
                  <SelectTrigger id="prop-classification" className="h-9">
                    <SelectValue placeholder="Select classification" />
                  </SelectTrigger>
                  <SelectContent>
                    {CLASSIFICATION_LEVELS.map((level) => (
                      <SelectItem key={level} value={level}>
                        {level}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="prop-examples" className="text-xs flex items-center">
                  Examples
                  <FieldTooltip content="Sample values, comma-separated or as JSON array" />
                </Label>
                <Input
                  id="prop-examples"
                  value={examples}
                  onChange={(e) => setExamples(e.target.value)}
                  placeholder='e.g., "John", "Jane" or ["value1", "value2"]'
                  className="h-9"
                />
              </div>
            </TabsContent>

            {/* Business Tab */}
            <TabsContent value="business" className="space-y-3 mt-4">
              <div className="space-y-1.5">
                <Label htmlFor="prop-business-name" className="text-xs flex items-center">
                  Business Name
                  <FieldTooltip content="Human-readable business name for this column" />
                </Label>
                <Input
                  id="prop-business-name"
                  value={businessName}
                  onChange={(e) => setBusinessName(e.target.value)}
                  placeholder="e.g., Customer Identifier"
                  className="h-9"
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="prop-encrypted-name" className="text-xs flex items-center">
                  Encrypted Name
                  <FieldTooltip content="Column name containing encrypted version of this data" />
                </Label>
                <Input
                  id="prop-encrypted-name"
                  value={encryptedName}
                  onChange={(e) => setEncryptedName(e.target.value)}
                  placeholder="e.g., customer_id_encrypted"
                  className="h-9"
                />
              </div>

              <div className="flex items-center gap-2">
                <Checkbox
                  id="prop-cde"
                  checked={criticalDataElement}
                  onCheckedChange={(checked) => setCriticalDataElement(checked as boolean)}
                />
                <Label htmlFor="prop-cde" className="text-sm font-normal cursor-pointer flex items-center">
                  Critical Data Element (CDE)
                  <FieldTooltip content="Mark as critical data element requiring special governance" />
                </Label>
              </div>
            </TabsContent>

            {/* Transform Tab */}
            <TabsContent value="transform" className="space-y-3 mt-4">
              <div className="space-y-1.5">
                <Label htmlFor="prop-transform-logic" className="text-xs flex items-center">
                  Transform Logic
                  <FieldTooltip content="The transformation logic/formula applied to generate this column" />
                </Label>
                <Input
                  id="prop-transform-logic"
                  value={transformLogic}
                  onChange={(e) => setTransformLogic(e.target.value)}
                  placeholder="e.g., UPPER(source_column)"
                  className="h-9"
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="prop-transform-sources" className="text-xs flex items-center">
                  Transform Source Objects
                  <FieldTooltip content="Source tables/columns used in transformation (comma-separated)" />
                </Label>
                <Input
                  id="prop-transform-sources"
                  value={transformSourceObjects}
                  onChange={(e) => setTransformSourceObjects(e.target.value)}
                  placeholder="e.g., source_table.column1, other_table.column2"
                  className="h-9"
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="prop-transform-desc" className="text-xs flex items-center">
                  Transform Description
                  <FieldTooltip content="Simple description of what the transformation does" />
                </Label>
                <Input
                  id="prop-transform-desc"
                  value={transformDescription}
                  onChange={(e) => setTransformDescription(e.target.value)}
                  placeholder="e.g., Converts name to uppercase"
                  className="h-9"
                />
              </div>
            </TabsContent>
          </Tabs>

          <div className="flex gap-2 pt-2">
            <Button type="button" size="sm" onClick={handleAddOrUpdate} className="h-8">
              {editingIndex !== null ? (
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
            {editingIndex !== null && (
              <Button type="button" size="sm" variant="outline" onClick={resetForm} className="h-8">
                Cancel
              </Button>
            )}
          </div>
        </div>
      )}

      {/* Properties List */}
      {properties.length > 0 ? (
        <div className="border rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-muted">
              <tr>
                <th className="text-left p-2 font-medium">Name</th>
                <th className="text-left p-2 font-medium">Type</th>
                <th className="text-left p-2 font-medium">Constraints</th>
                <th className="text-left p-2 font-medium">Governance</th>
                <th className="text-left p-2 font-medium">Description</th>
                {!readOnly && <th className="text-right p-2 font-medium">Actions</th>}
              </tr>
            </thead>
            <tbody>
              {properties.map((prop, idx) => {
                const constraints: string[] = []
                if (prop.required) constraints.push('Required')
                if (prop.unique) constraints.push('Unique')
                if (prop.primaryKey) constraints.push(`PK${prop.primaryKeyPosition ? `(${prop.primaryKeyPosition})` : ''}`)
                if (prop.partitioned) constraints.push(`Part${prop.partitionKeyPosition ? `(${prop.partitionKeyPosition})` : ''}`)

                const governance: string[] = []
                if (prop.classification) governance.push(prop.classification)
                if (prop.criticalDataElement) governance.push('CDE')

                return (
                  <tr key={idx} className="border-t hover:bg-muted/50">
                    <td className="p-2">
                      <div className="font-mono text-xs font-medium">{prop.name}</div>
                      {prop.physicalName && (
                        <div className="text-xs text-muted-foreground mt-0.5">→ {prop.physicalName}</div>
                      )}
                    </td>
                    <td className="p-2">
                      <div className="text-xs bg-secondary px-2 py-0.5 rounded inline-block">
                        {prop.logicalType}
                      </div>
                      {prop.physicalType && (
                        <div className="text-xs text-muted-foreground mt-0.5">{prop.physicalType}</div>
                      )}
                    </td>
                    <td className="p-2">
                      {constraints.length > 0 ? (
                        <div className="flex flex-wrap gap-1">
                          {constraints.map((c, i) => (
                            <span key={i} className="text-xs bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 px-1.5 py-0.5 rounded">
                              {c}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <span className="text-xs text-muted-foreground">-</span>
                      )}
                    </td>
                    <td className="p-2">
                      {governance.length > 0 ? (
                        <div className="flex flex-wrap gap-1">
                          {governance.map((g, i) => (
                            <span key={i} className="text-xs bg-amber-100 dark:bg-amber-900 text-amber-700 dark:text-amber-300 px-1.5 py-0.5 rounded">
                              {g}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <span className="text-xs text-muted-foreground">-</span>
                      )}
                    </td>
                    <td className="p-2 text-xs text-muted-foreground max-w-xs">
                      <div className="truncate">{prop.description || '-'}</div>
                      {prop.businessName && (
                        <div className="text-xs text-muted-foreground italic mt-0.5">
                          {prop.businessName}
                        </div>
                      )}
                    </td>
                    {!readOnly && (
                      <td className="p-2">
                        <div className="flex justify-end gap-1">
                          <Button
                            type="button"
                            size="sm"
                            variant="ghost"
                            onClick={() => handleEdit(idx)}
                            className="h-7 w-7 p-0"
                          >
                            <Edit className="h-3.5 w-3.5" />
                          </Button>
                          <Button
                            type="button"
                            size="sm"
                            variant="ghost"
                            onClick={() => handleDelete(idx)}
                            className="h-7 w-7 p-0 text-destructive hover:text-destructive"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                      </td>
                    )}
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="text-sm text-muted-foreground text-center py-8 border rounded-lg bg-muted/30">
          {readOnly ? 'No columns defined.' : 'No columns added yet. Add at least one column above.'}
        </p>
      )}
    </div>
  )
}
