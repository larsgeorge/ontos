import React, { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { X } from 'lucide-react'
import ConceptSelectDialog from '@/components/semantic/concept-select-dialog'

interface BusinessConcept {
  iri: string
  label?: string
}

interface BusinessConceptsDisplayProps {
  concepts: BusinessConcept[]
  onConceptsChange: (concepts: BusinessConcept[]) => void
  parentConceptIris?: string[]
  entityType?: string
  entityId?: string
  conceptType?: 'class' | 'property'
}

export default function BusinessConceptsDisplay({
  concepts = [],
  onConceptsChange,
  parentConceptIris,
  entityType,
  entityId,
  conceptType = 'class'
}: BusinessConceptsDisplayProps) {
  const [showDialog, setShowDialog] = useState(false)

  const handleAddConcept = (iri: string) => {
    // Extract label from IRI for display
    const label = iri.split('/').pop()?.replace(/[#_]/g, ' ') || iri

    const newConcept: BusinessConcept = { iri, label }
    onConceptsChange([...concepts, newConcept])
    setShowDialog(false)
  }

  const handleRemoveConcept = (iri: string) => {
    onConceptsChange(concepts.filter(c => c.iri !== iri))
  }

  return (
    <div className="space-y-2">
      <div className="text-sm font-medium">Linked Business {conceptType === 'property' ? 'Properties' : 'Concepts'}:</div>

      {concepts.length === 0 ? (
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">No business {conceptType === 'property' ? 'properties' : 'concepts'} linked</span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowDialog(true)}
            className="h-6 px-2 text-xs"
          >
            Add {conceptType === 'property' ? 'Property' : 'Concept'}
          </Button>
        </div>
      ) : (
        <div className="space-y-2">
          <div className="flex flex-wrap gap-1">
            {concepts.map((concept) => (
              <Badge key={concept.iri} variant="secondary" className="flex items-center gap-1">
                <span>{concept.label || concept.iri.split('/').pop()}</span>
                <X
                  className="h-3 w-3 cursor-pointer hover:text-destructive"
                  onClick={() => handleRemoveConcept(concept.iri)}
                />
              </Badge>
            ))}
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowDialog(true)}
            className="h-6 px-2 text-xs"
          >
            Add {conceptType === 'property' ? 'Property' : 'Concept'}
          </Button>
        </div>
      )}

      <ConceptSelectDialog
        isOpen={showDialog}
        onOpenChange={setShowDialog}
        onSelect={handleAddConcept}
        parentConceptIris={parentConceptIris}
        entityType={conceptType}
      />
    </div>
  )
}