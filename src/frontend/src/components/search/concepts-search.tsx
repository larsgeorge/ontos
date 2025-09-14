import { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useApi } from '@/hooks/use-api';
import { useToast } from '@/hooks/use-toast';

type ConceptItem = { value: string; label: string; type: 'class' };
type Neighbor = {
  direction: 'outgoing' | 'incoming' | 'predicate';
  predicate: string;
  display: string;
  displayType: 'resource' | 'property' | 'literal';
  stepIri?: string | null;
  stepIsResource?: boolean;
};

type SemanticLink = {
  id: string;
  entity_id: string;
  entity_type: string;
  iri: string;
};

type EnrichedSemanticLink = SemanticLink & {
  entity_name?: string;
};

interface ConceptsSearchProps {
  initialQuery?: string;
  initialSelectedConcept?: ConceptItem | null;
}

export default function ConceptsSearch({
  initialQuery = '',
  initialSelectedConcept = null
}: ConceptsSearchProps) {
  const { get, post } = useApi();
  const { toast } = useToast();
  const navigate = useNavigate();
  const location = useLocation();

  const [conceptSearchQuery, setConceptSearchQuery] = useState(initialQuery);
  const [conceptSearchResults, setConceptSearchResults] = useState<ConceptItem[]>([]);
  const [isConceptDropdownOpen, setIsConceptDropdownOpen] = useState(false);
  const [selectedConcept, setSelectedConcept] = useState<ConceptItem | null>(initialSelectedConcept);
  const [conceptIri, setConceptIri] = useState('');
  const [conceptLabel, setConceptLabel] = useState('');
  const [conceptNeighbors, setConceptNeighbors] = useState<Neighbor[]>([]);
  const [semanticLinks, setSemanticLinks] = useState<EnrichedSemanticLink[]>([]);

  // Assign to Object dialog
  const [assignDialogOpen, setAssignDialogOpen] = useState(false);
  const [selectedEntityType, setSelectedEntityType] = useState<string>('');
  const [selectedEntityId, setSelectedEntityId] = useState<string>('');
  const [availableEntities, setAvailableEntities] = useState<any[]>([]);

  // Update URL when state changes
  const updateUrl = (updates: Partial<{
    query: string;
    conceptIri: string;
  }>) => {
    const params = new URLSearchParams(location.search);

    if (updates.query !== undefined) {
      if (updates.query) {
        params.set('concepts_query', updates.query);
      } else {
        params.delete('concepts_query');
      }
    }

    if (updates.conceptIri !== undefined) {
      if (updates.conceptIri) {
        params.set('concepts_iri', updates.conceptIri);
      } else {
        params.delete('concepts_iri');
      }
    }

    const newUrl = `${location.pathname}?${params.toString()}`;
    navigate(newUrl, { replace: true });
  };

  // Load initial state from URL
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const urlQuery = params.get('concepts_query');
    const urlIri = params.get('concepts_iri');

    if (urlQuery && urlQuery !== initialQuery) {
      setConceptSearchQuery(urlQuery);
    }

    if (urlIri && !initialSelectedConcept) {
      // Load concept from IRI
      const loadConceptFromIri = async () => {
        try {
          const res = await get<ConceptItem[]>(`/api/semantic-models/concepts?q=${encodeURIComponent(urlIri)}&limit=1`);
          const concepts = res.data || [];
          if (concepts.length > 0) {
            await selectConcept(concepts[0]);
          }
        } catch (error) {
          console.error('Error loading concept from URL:', error);
        }
      };
      loadConceptFromIri();
    }
  }, [location.search]);

  // Search concepts as user types
  useEffect(() => {
    const searchConcepts = async () => {
      if (!conceptSearchQuery.trim()) {
        setConceptSearchResults([]);
        setIsConceptDropdownOpen(false);
        updateUrl({ query: '' });
        return;
      }

      try {
        const res = await get<ConceptItem[]>(`/api/semantic-models/concepts?q=${encodeURIComponent(conceptSearchQuery)}&limit=50`);
        setConceptSearchResults(res.data || []);
        setIsConceptDropdownOpen((res.data || []).length > 0);
        updateUrl({ query: conceptSearchQuery });
      } catch (error) {
        console.error('Error searching concepts:', error);
        setConceptSearchResults([]);
        setIsConceptDropdownOpen(false);
      }
    };

    const timer = setTimeout(searchConcepts, 250);
    return () => clearTimeout(timer);
  }, [conceptSearchQuery]);

  // Select a concept and load its details
  const selectConcept = async (concept: ConceptItem) => {
    setSelectedConcept(concept);
    setConceptIri(concept.value);

    // Use label if available, otherwise extract last part of IRI
    let displayLabel = concept.label;
    if (!displayLabel || displayLabel.trim() === concept.value) {
      if (concept.value.includes('#')) {
        displayLabel = concept.value.split('#').pop() || concept.value;
      } else if (concept.value.includes('/')) {
        displayLabel = concept.value.split('/').pop() || concept.value;
      } else {
        displayLabel = concept.value;
      }
    }

    setConceptLabel(displayLabel);
    setConceptSearchQuery(`${displayLabel} - ${concept.value}`);
    setIsConceptDropdownOpen(false);
    updateUrl({ conceptIri: concept.value });

    // Load neighbors for this concept
    try {
      const res = await get<Neighbor[]>(`/api/semantic-models/neighbors?iri=${encodeURIComponent(concept.value)}&limit=200`);
      setConceptNeighbors(res.data || []);
    } catch (error) {
      console.error('Error loading neighbors:', error);
      setConceptNeighbors([]);
    }

    // Load semantic links (catalog objects linked to this concept)
    try {
      const res = await get<SemanticLink[]>(`/api/semantic-links/iri/${encodeURIComponent(concept.value)}`);
      const links = res.data || [];

      // Enrich semantic links with entity names
      const enrichedLinks = await enrichSemanticLinksWithNames(links);
      setSemanticLinks(enrichedLinks);
    } catch (error) {
      console.error('Error loading semantic links:', error);
      setSemanticLinks([]);
    }
  };

  // Navigate to a related concept (parent/subclass)
  const navigateToConcept = async (iri: string) => {
    const label = conceptNeighbors.find(n => n.stepIri === iri)?.display || iri.split('/').pop() || iri.split('#').pop() || iri;
    const conceptItem: ConceptItem = {
      value: iri,
      label: label,
      type: 'class'
    };
    await selectConcept(conceptItem);
  };

  // Get parent classes from neighbors
  const getParentClasses = () => {
    return conceptNeighbors.filter(n =>
      n.direction === 'outgoing' &&
      (n.predicate.includes('subClassOf') || n.predicate.includes('rdfs:subClassOf')) &&
      n.stepIsResource
    );
  };

  // Get subclasses from neighbors
  const getSubclasses = () => {
    return conceptNeighbors.filter(n =>
      n.direction === 'incoming' &&
      (n.predicate.includes('subClassOf') || n.predicate.includes('rdfs:subClassOf')) &&
      n.stepIsResource
    );
  };

  // Get related properties
  const getRelatedProperties = () => {
    return conceptNeighbors.filter(n =>
      n.displayType === 'property' ||
      n.predicate.includes('domain') ||
      n.predicate.includes('range')
    );
  };

  // Get linked catalog objects from semantic links
  const getCatalogObjects = () => {
    return semanticLinks;
  };

  // Enrich semantic links with readable entity names
  const enrichSemanticLinksWithNames = async (links: SemanticLink[]): Promise<EnrichedSemanticLink[]> => {
    const enrichedLinks: EnrichedSemanticLink[] = [];

    for (const link of links) {
      try {
        let entityName = link.entity_id;
        let endpoint = '';

        switch (link.entity_type) {
          case 'data_product':
            endpoint = `/api/data-products/${link.entity_id}`;
            break;
          case 'data_contract':
            endpoint = `/api/data-contracts/${link.entity_id}`;
            break;
          case 'data_domain':
            endpoint = `/api/data-domains/${link.entity_id}`;
            break;
          default:
            enrichedLinks.push({ ...link, entity_name: link.entity_id });
            continue;
        }

        const entityRes = await get<any>(endpoint);
        if (entityRes.data && !entityRes.error) {
          entityName = entityRes.data.name || entityRes.data.info?.title || entityRes.data.title || link.entity_id;
        }

        enrichedLinks.push({ ...link, entity_name: entityName });
      } catch (error) {
        console.error(`Error fetching details for ${link.entity_type}:${link.entity_id}`, error);
        enrichedLinks.push({ ...link, entity_name: link.entity_id });
      }
    }

    return enrichedLinks;
  };

  // Load entities for assignment
  const loadEntitiesForType = async (entityType: string) => {
    try {
      let endpoint = '';
      switch (entityType) {
        case 'data_product':
          endpoint = '/api/data-products';
          break;
        case 'data_contract':
          endpoint = '/api/data-contracts';
          break;
        case 'data_domain':
          endpoint = '/api/data-domains';
          break;
        default:
          return;
      }

      const res = await get<any[]>(endpoint);
      setAvailableEntities(res.data || []);
    } catch (error) {
      console.error('Error loading entities:', error);
      setAvailableEntities([]);
    }
  };

  // Handle entity type selection
  const handleEntityTypeChange = (entityType: string) => {
    setSelectedEntityType(entityType);
    setSelectedEntityId('');
    loadEntitiesForType(entityType);
  };

  // Navigate to entity detail page
  const navigateToEntity = (link: SemanticLink) => {
    let path = '';
    switch (link.entity_type) {
      case 'data_product':
        path = `/data-products/${link.entity_id}`;
        break;
      case 'data_contract':
        path = `/data-contracts/${link.entity_id}`;
        break;
      case 'data_domain':
        path = `/data-domains/${link.entity_id}`;
        break;
      default:
        toast({
          title: 'Navigation Error',
          description: `Cannot navigate to ${link.entity_type}`,
          variant: 'destructive'
        });
        return;
    }
    navigate(path);
  };

  // Create semantic link
  const handleAssignToObject = async () => {
    if (!selectedConcept || !selectedEntityType || !selectedEntityId) {
      toast({
        title: 'Error',
        description: 'Please select both an entity type and specific entity.',
        variant: 'destructive'
      });
      return;
    }

    try {
      const res = await post('/api/semantic-links/', {
        entity_id: selectedEntityId,
        entity_type: selectedEntityType,
        iri: selectedConcept.value,
      });

      if (res.error) {
        throw new Error(res.error);
      }

      toast({
        title: 'Linked Successfully',
        description: `Concept "${selectedConcept.label}" linked to ${selectedEntityType.replace('_', ' ')} "${selectedEntityId}".`,
      });

      setAssignDialogOpen(false);
      setSelectedEntityType('');
      setSelectedEntityId('');

      // Reload semantic links
      await selectConcept(selectedConcept);
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Failed to assign concept to object.',
        variant: 'destructive'
      });
    }
  };

  return (
    <div className="space-y-6">
      {/* Search Section */}
      <div className="space-y-2">
        <p className="text-sm text-muted-foreground">Search and select a concept:</p>
        <div className="relative">
          <Input
            value={conceptSearchQuery}
            onChange={(e) => setConceptSearchQuery(e.target.value)}
            onFocus={() => setIsConceptDropdownOpen(conceptSearchResults.length > 0)}
            placeholder="Type to search by name, label, or IRI..."
            className="w-full"
          />

          {/* Search Results Dropdown */}
          {isConceptDropdownOpen && conceptSearchResults.length > 0 && (
            <div className="absolute z-50 w-full mt-1 bg-popover border rounded-md shadow-md max-h-80 overflow-y-auto">
              {conceptSearchResults.map((result) => (
                <div
                  key={result.value}
                  className="px-3 py-2 text-popover-foreground hover:bg-accent hover:text-accent-foreground cursor-pointer border-b border-border last:border-b-0 transition-colors"
                  onClick={() => selectConcept(result)}
                >
                  <div className="text-sm">{result.label} - {result.value}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Selected Concept Details */}
      {selectedConcept && (
        <div className="space-y-4">
          {/* Concept Info - Show ALL assigned properties */}
          <Card>
            <CardContent className="pt-4">
              <div className="space-y-2">
                <div>
                  <span className="text-sm font-medium text-muted-foreground">IRI: </span>
                  <span className="text-sm font-mono text-foreground">{conceptIri}</span>
                </div>
                {conceptNeighbors.filter(n =>
                  n.direction === 'outgoing' &&
                  n.displayType === 'literal' &&
                  !n.predicate.includes('subClassOf') &&
                  !n.predicate.includes('type')
                ).map((prop, idx) => (
                  <div key={idx}>
                    <span className="text-sm font-medium text-muted-foreground">
                      {prop.predicate.split('/').pop()?.split('#').pop() || prop.predicate}:
                    </span>
                    <span className="text-sm text-foreground ml-1">{prop.display}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Three Column Layout */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Concept Hierarchy */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Concept Hierarchy</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <h3 className="text-sm font-medium text-muted-foreground mb-2">Parent Classes:</h3>
                  <div className="space-y-2">
                    {getParentClasses().length === 0 ? (
                      <p className="text-sm text-muted-foreground">No parent classes found</p>
                    ) : (
                      getParentClasses().map((parent, idx) => (
                        <Badge
                          key={idx}
                          variant="outline"
                          className="cursor-pointer hover:bg-accent"
                          onClick={() => parent.stepIri && navigateToConcept(parent.stepIri)}
                        >
                          {parent.display.split('/').pop() || parent.display.split('#').pop() || parent.display}
                        </Badge>
                      ))
                    )}
                  </div>
                </div>

                <div>
                  <h3 className="text-sm font-medium text-muted-foreground mb-2">Subclasses:</h3>
                  <div className="flex flex-wrap gap-2">
                    {getSubclasses().length === 0 ? (
                      <p className="text-sm text-muted-foreground">No subclasses found</p>
                    ) : (
                      getSubclasses().map((sub, idx) => (
                        <Badge
                          key={idx}
                          variant="outline"
                          className="cursor-pointer hover:bg-accent"
                          onClick={() => sub.stepIri && navigateToConcept(sub.stepIri)}
                        >
                          {sub.display.split('/').pop() || sub.display.split('#').pop() || sub.display}
                        </Badge>
                      ))
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Related Properties */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Related Properties</CardTitle>
              </CardHeader>
              <CardContent>
                {getRelatedProperties().length === 0 ? (
                  <p className="text-sm text-center text-muted-foreground">No related properties found.</p>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {getRelatedProperties().map((prop, idx) => (
                      <Badge key={idx} variant="secondary" className="text-xs">
                        {prop.display.split('/').pop() || prop.display.split('#').pop() || prop.display}
                      </Badge>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Linked Catalog Objects */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Linked Catalog Objects</CardTitle>
              </CardHeader>
              <CardContent>
                {getCatalogObjects().length === 0 ? (
                  <p className="text-sm text-center text-muted-foreground">No catalog objects assigned.</p>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {getCatalogObjects().map((link) => (
                      <Badge
                        key={link.id}
                        variant="outline"
                        className="text-xs cursor-pointer hover:bg-accent transition-colors"
                        onClick={() => navigateToEntity(link)}
                        title={`Click to view ${link.entity_type.replace('_', ' ')} details`}
                      >
                        {link.entity_type.replace('_', ' ')}: {link.entity_name || link.entity_id}
                      </Badge>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Assign to Object Button */}
          <div className="pt-4">
            <Button
              variant="outline"
              onClick={() => setAssignDialogOpen(true)}
              disabled={!selectedConcept}
            >
              Assign to Object
            </Button>
          </div>
        </div>
      )}

      {/* Assign to Object Dialog */}
      <Dialog open={assignDialogOpen} onOpenChange={setAssignDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Assign Concept to Object</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            {selectedConcept && (
              <div className="text-sm">
                <p className="font-medium">{selectedConcept.label}</p>
                <p className="text-muted-foreground font-mono text-xs">{selectedConcept.value}</p>
              </div>
            )}

            <div className="space-y-2">
              <label className="text-sm font-medium">Entity Type</label>
              <Select value={selectedEntityType} onValueChange={handleEntityTypeChange}>
                <SelectTrigger>
                  <SelectValue placeholder="Select entity type..." />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="data_product">Data Product</SelectItem>
                  <SelectItem value="data_contract">Data Contract</SelectItem>
                  <SelectItem value="data_domain">Data Domain</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {selectedEntityType && (
              <div className="space-y-2">
                <label className="text-sm font-medium">
                  {selectedEntityType.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                </label>
                <Select value={selectedEntityId} onValueChange={setSelectedEntityId}>
                  <SelectTrigger>
                    <SelectValue placeholder={`Select ${selectedEntityType.replace('_', ' ')}...`} />
                  </SelectTrigger>
                  <SelectContent>
                    {availableEntities.map((entity) => (
                      <SelectItem key={entity.id} value={entity.id}>
                        {entity.name || entity.info?.title || entity.id}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            <div className="flex justify-end space-x-2 pt-4">
              <Button variant="outline" onClick={() => setAssignDialogOpen(false)}>
                Cancel
              </Button>
              <Button
                onClick={handleAssignToObject}
                disabled={!selectedEntityType || !selectedEntityId}
              >
                Assign
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}