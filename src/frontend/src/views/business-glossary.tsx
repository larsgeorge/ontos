import React, { useState, useEffect } from 'react';
import type { 
  OntologyTaxonomy, 
  OntologyConcept, 
  ConceptHierarchy, 
  GroupedConcepts,
  TaxonomyStats
} from '@/types/ontology';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { 
  Plus, 
  Pencil, 
  Trash2, 
  AlertCircle, 
  FileText, 
  ChevronRight, 
  ChevronDown, 
  Folder,
  FolderOpen,
  Book,
  Database,
  HardDrive,
  Globe,
  Layers,
  Zap,
  Search
} from 'lucide-react';
import ReactFlow, { Node, Edge, Background, MarkerType, Controls } from 'reactflow';
import 'reactflow/dist/style.css';
import useBreadcrumbStore from '@/stores/breadcrumb-store';

interface ConceptTreeNodeProps {
  concept: OntologyConcept;
  level: number;
  selectedConcept: OntologyConcept | null;
  onSelect: (concept: OntologyConcept) => void;
  isExpanded: boolean;
  onToggle: () => void;
  expandedIds: Set<string>;
  toggleExpanded: (id: string) => void;
}

const ConceptTreeNode: React.FC<ConceptTreeNodeProps> = ({
  concept,
  level,
  selectedConcept,
  onSelect,
  isExpanded,
  onToggle,
  expandedIds,
  toggleExpanded
}) => {
  const hasChildren = concept.child_concepts.length > 0;
  const isSelected = selectedConcept?.iri === concept.iri;

  const getConceptIcon = () => {
    switch (concept.concept_type) {
      case 'class':
        return <Layers className="h-4 w-4 shrink-0 text-blue-500" />;
      case 'concept':
        return <FileText className="h-4 w-4 shrink-0 text-green-500" />;
      default:
        return <Zap className="h-4 w-4 shrink-0 text-yellow-500" />;
    }
  };

  const getDisplayName = () => {
    return concept.label || concept.iri.split(/[/#]/).pop() || concept.iri;
  };

  return (
    <div style={{ paddingLeft: `${level * 16}px` }} className="select-none">
      <div
        className={`
          flex items-center gap-2 px-2 py-1.5 rounded-md cursor-pointer
          hover:bg-accent hover:text-accent-foreground
          ${isSelected ? 'bg-accent text-accent-foreground' : ''}
        `}
        onClick={() => onSelect(concept)}
      >
        {hasChildren && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onToggle();
            }}
            className="p-1 hover:bg-accent/50 rounded-sm transition-colors"
          >
            {isExpanded ? (
              <ChevronDown className="h-4 w-4 shrink-0" />
            ) : (
              <ChevronRight className="h-4 w-4 shrink-0" />
            )}
          </button>
        )}
        <div className="flex items-center gap-2 min-w-0">
          {getConceptIcon()}
          <span className="truncate text-sm font-medium">
            {getDisplayName()}
          </span>
          {concept.source_context && (
            <Badge variant="outline" className="text-xs">
              {concept.source_context}
            </Badge>
          )}
        </div>
      </div>
    </div>
  );
};

interface TaxonomyGroupProps {
  taxonomy: OntologyTaxonomy;
  concepts: OntologyConcept[];
  selectedConcept: OntologyConcept | null;
  onSelectConcept: (concept: OntologyConcept) => void;
  expandedIds: Set<string>;
  toggleExpanded: (id: string) => void;
}

const TaxonomyGroup: React.FC<TaxonomyGroupProps> = ({
  taxonomy,
  concepts,
  selectedConcept,
  onSelectConcept,
  expandedIds,
  toggleExpanded
}) => {
  const [isGroupExpanded, setIsGroupExpanded] = useState(true);

  const getTaxonomyIcon = () => {
    switch (taxonomy.source_type) {
      case 'file':
        return <HardDrive className="h-4 w-4 text-blue-600" />;
      case 'database':
        return <Database className="h-4 w-4 text-green-600" />;
      case 'schema':
        return <Layers className="h-4 w-4 text-purple-600" />;
      default:
        return <Globe className="h-4 w-4 text-gray-600" />;
    }
  };

  // Build concept hierarchy
  const buildConceptTree = (concepts: OntologyConcept[]) => {
    const conceptMap = new Map<string, { concept: OntologyConcept; children: OntologyConcept[] }>();
    const roots: OntologyConcept[] = [];

    // Create nodes for all concepts
    concepts.forEach(concept => {
      conceptMap.set(concept.iri, { concept, children: [] });
    });

    // Build tree structure
    concepts.forEach(concept => {
      if (concept.parent_concepts.length === 0) {
        // Top-level concept
        roots.push(concept);
      } else {
        // Child concept - add to parent(s)
        concept.parent_concepts.forEach(parentIri => {
          const parentNode = conceptMap.get(parentIri);
          if (parentNode) {
            parentNode.children.push(concept);
          }
        });
      }
    });

    return { conceptMap, roots };
  };

  const renderConceptTree = (concepts: OntologyConcept[], level: number = 1): React.ReactNode => {
    return concepts.map(concept => {
      const hasChildren = concept.child_concepts.length > 0;
      const isExpanded = expandedIds.has(concept.iri);
      
      // Get children concepts that exist in our current concept list
      const childConcepts = concepts.filter(c => 
        concept.child_concepts.includes(c.iri)
      );

      return (
        <div key={concept.iri}>
          <ConceptTreeNode
            concept={concept}
            level={level}
            selectedConcept={selectedConcept}
            onSelect={onSelectConcept}
            isExpanded={isExpanded}
            onToggle={() => toggleExpanded(concept.iri)}
            expandedIds={expandedIds}
            toggleExpanded={toggleExpanded}
          />
          {isExpanded && childConcepts.length > 0 && (
            <div>
              {renderConceptTree(childConcepts, level + 1)}
            </div>
          )}
        </div>
      );
    });
  };

  const { roots } = buildConceptTree(concepts);

  return (
    <div className="mb-2">
      <div
        className="flex items-center gap-2 p-2 bg-muted/50 rounded-md cursor-pointer hover:bg-muted/70"
        onClick={() => setIsGroupExpanded(!isGroupExpanded)}
      >
        {isGroupExpanded ? (
          <FolderOpen className="h-4 w-4 shrink-0" />
        ) : (
          <Folder className="h-4 w-4 shrink-0" />
        )}
        {getTaxonomyIcon()}
        <span className="font-medium">{taxonomy.name}</span>
        <Badge variant="secondary" className="text-xs">
          {concepts.length}
        </Badge>
        <Badge variant="outline" className="text-xs">
          {taxonomy.source_type}
        </Badge>
      </div>
      {isGroupExpanded && (
        <div className="mt-2">
          {renderConceptTree(roots)}
        </div>
      )}
    </div>
  );
};

interface ConceptDetailsProps {
  concept: OntologyConcept;
  hierarchy?: ConceptHierarchy;
}

const ConceptDetails: React.FC<ConceptDetailsProps> = ({ concept, hierarchy }) => {
  const DetailItem: React.FC<{ label: string; value: React.ReactNode }> = ({ label, value }) => (
    <div className="mb-4">
      <div className="text-sm text-muted-foreground mb-1">{label}</div>
      <div className="text-sm">{value}</div>
    </div>
  );

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">Details</h3>
      
      <DetailItem 
        label="IRI" 
        value={
          <code className="text-xs bg-muted p-1 rounded break-all">
            {concept.iri}
          </code>
        } 
      />
      
      <DetailItem 
        label="Type" 
        value={<Badge variant="outline">{concept.concept_type}</Badge>} 
      />
      
      {concept.source_context && (
        <DetailItem label="Source Taxonomy" value={concept.source_context} />
      )}
      
      {concept.comment && (
        <DetailItem label="Description" value={concept.comment} />
      )}
      
      {concept.parent_concepts.length > 0 && (
        <div className="mb-4">
          <div className="text-sm text-muted-foreground mb-1">Parent Concepts</div>
          <div className="space-y-1">
            {concept.parent_concepts.map(parentIri => (
              <div key={parentIri} className="text-xs bg-muted p-2 rounded font-mono">
                {parentIri.split(/[/#]/).pop() || parentIri}
              </div>
            ))}
          </div>
        </div>
      )}
      
      {concept.child_concepts.length > 0 && (
        <div className="mb-4">
          <div className="text-sm text-muted-foreground mb-1">Child Concepts</div>
          <div className="space-y-1">
            {concept.child_concepts.map(childIri => (
              <div key={childIri} className="text-xs bg-muted p-2 rounded font-mono">
                {childIri.split(/[/#]/).pop() || childIri}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default function BusinessGlossary() {
  const [taxonomies, setTaxonomies] = useState<OntologyTaxonomy[]>([]);
  const [groupedConcepts, setGroupedConcepts] = useState<GroupedConcepts>({});
  const [selectedConcept, setSelectedConcept] = useState<OntologyConcept | null>(null);
  const [selectedHierarchy, setSelectedHierarchy] = useState<ConceptHierarchy | null>(null);
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeTab, setActiveTab] = useState('details');
  const [stats, setStats] = useState<TaxonomyStats | null>(null);

  // Legacy form state (for backwards compatibility)
  const [openDialog, setOpenDialog] = useState(false);
  const [dialogType, setDialogType] = useState<'glossary' | 'term'>('glossary');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [scope, setScope] = useState('');
  const [orgUnit, setOrgUnit] = useState('');
  const [domain, setDomain] = useState('');
  const [owner, setOwner] = useState('');
  const [tags, setTags] = useState('');
  const [status, setStatus] = useState('draft');

  const setStaticSegments = useBreadcrumbStore((state) => state.setStaticSegments);
  const setDynamicTitle = useBreadcrumbStore((state) => state.setDynamicTitle);

  useEffect(() => {
    fetchData();
    
    // Set breadcrumbs
    setStaticSegments([]);
    setDynamicTitle('Business Glossary');

    // Cleanup breadcrumbs on unmount
    return () => {
      setStaticSegments([]);
      setDynamicTitle(null);
    };
  }, [setStaticSegments, setDynamicTitle]);

  const fetchData = async () => {
    try {
      setLoading(true);
      
      // Fetch taxonomies
      const taxonomiesResponse = await fetch('/api/business-glossaries');
      if (!taxonomiesResponse.ok) throw new Error('Failed to fetch taxonomies');
      const taxonomiesData = await taxonomiesResponse.json();
      setTaxonomies(taxonomiesData.taxonomies || []);
      
      // Fetch grouped concepts
      const conceptsResponse = await fetch('/api/business-glossaries/concepts-grouped');
      if (!conceptsResponse.ok) throw new Error('Failed to fetch concepts');
      const conceptsData = await conceptsResponse.json();
      setGroupedConcepts(conceptsData.grouped_concepts || {});
      
      // Fetch stats
      const statsResponse = await fetch('/api/business-glossaries/stats');
      if (statsResponse.ok) {
        const statsData = await statsResponse.json();
        setStats(statsData.stats);
      }
      
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch data');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectConcept = async (concept: OntologyConcept) => {
    setSelectedConcept(concept);
    setActiveTab('details');
    
    // Fetch hierarchy information
    try {
      const response = await fetch(`/api/business-glossaries/concepts/${encodeURIComponent(concept.iri)}/hierarchy`);
      if (response.ok) {
        const data = await response.json();
        setSelectedHierarchy(data.hierarchy);
      }
    } catch (err) {
      console.error('Failed to fetch concept hierarchy:', err);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      fetchData();
      return;
    }

    try {
      setLoading(true);
      const response = await fetch(
        `/api/business-glossaries/search?q=${encodeURIComponent(searchQuery)}`
      );
      if (!response.ok) throw new Error('Search failed');
      const data = await response.json();
      
      // Group search results by taxonomy
      const grouped: GroupedConcepts = {};
      data.results.forEach((result: any) => {
        const concept = result.concept;
        const source = concept.source_context || 'Unassigned';
        if (!grouped[source]) {
          grouped[source] = [];
        }
        grouped[source].push(concept);
      });
      
      setGroupedConcepts(grouped);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed');
    } finally {
      setLoading(false);
    }
  };

  const toggleExpanded = (id: string) => {
    setExpandedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const renderLineage = (hierarchy: ConceptHierarchy) => {
    const nodes: Node[] = [];
    const edges: Edge[] = [];
    let yOffset = 100;

    // Add current concept as center node
    nodes.push({
      id: hierarchy.concept.iri,
      data: { label: hierarchy.concept.label || hierarchy.concept.iri.split(/[/#]/).pop() },
      position: { x: 300, y: yOffset },
      type: 'default',
      style: {
        background: '#fff',
        border: '2px solid #2563eb',
        borderRadius: '8px',
        padding: '10px',
        fontSize: '12px',
        fontWeight: 'bold'
      }
    });

    yOffset += 120;

    // Add ancestors
    hierarchy.ancestors.forEach((ancestor, index) => {
      const nodeId = ancestor.iri;
      nodes.push({
        id: nodeId,
        data: { label: ancestor.label || ancestor.iri.split(/[/#]/).pop() },
        position: { x: 300 - (index * 50), y: yOffset },
        style: {
          background: '#dbeafe',
          border: '1px solid #93c5fd',
          borderRadius: '6px',
          padding: '8px',
          fontSize: '10px'
        }
      });
      
      edges.push({
        id: `${nodeId}-${hierarchy.concept.iri}`,
        source: nodeId,
        target: hierarchy.concept.iri,
        type: 'smoothstep'
      });
    });

    yOffset += 120;

    // Add descendants
    hierarchy.descendants.forEach((descendant, index) => {
      const nodeId = descendant.iri;
      nodes.push({
        id: nodeId,
        data: { label: descendant.label || descendant.iri.split(/[/#]/).pop() },
        position: { x: 300 + (index * 50), y: yOffset },
        style: {
          background: '#dcfce7',
          border: '1px solid #86efac',
          borderRadius: '6px',
          padding: '8px',
          fontSize: '10px'
        }
      });
      
      edges.push({
        id: `${hierarchy.concept.iri}-${nodeId}`,
        source: hierarchy.concept.iri,
        target: nodeId,
        type: 'smoothstep'
      });
    });

    return (
      <div className="h-[500px] border rounded-lg">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          fitView
          minZoom={0.5}
          maxZoom={1.5}
          style={{ background: '#F7F9FB' }}
          defaultEdgeOptions={{
            style: { strokeWidth: 1.5 },
            markerEnd: { type: MarkerType.ArrowClosed }
          }}
          nodesDraggable={false}
          nodesConnectable={false}
          elementsSelectable={false}
        >
          <Controls />
          <Background />
        </ReactFlow>
      </div>
    );
  };

  // Legacy create handlers (for backwards compatibility)
  const handleCreateGlossary = () => {
    setDialogType('glossary');
    setName('');
    setDescription('');
    setScope('');
    setOrgUnit('');
    setDomain('');
    setOwner('');
    setTags('');
    setStatus('draft');
    setOpenDialog(true);
  };

  const handleCreateTerm = () => {
    setDialogType('term');
    setName('');
    setDescription('');
    setDomain('');
    setOwner('');
    setTags('');
    setStatus('draft');
    setOpenDialog(true);
  };

  const handleSave = async (event: React.FormEvent) => {
    event.preventDefault();
    // This would need to be implemented if we want to support creation
    setError('Creating new glossaries and terms is not supported in the ontology-based system.');
    setOpenDialog(false);
  };

  if (loading && !taxonomies.length) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
          <p>Loading business glossary data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="py-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold mb-6 flex items-center gap-2">
          <Book className="w-8 h-8" /> Business Glossary
        </h1>
        <div className="flex items-center gap-4">
          {stats && (
            <div className="text-sm text-muted-foreground">
              {stats.total_concepts} concepts across {stats.taxonomies.length} taxonomies
            </div>
          )}
          <div className="flex space-x-2">
            <Button onClick={handleCreateTerm}>
              <Plus className="h-4 w-4 mr-2" />
              Add Term
            </Button>
            <Button onClick={handleCreateGlossary} variant="outline">
              <Plus className="h-4 w-4 mr-2" />
              Add Glossary
            </Button>
          </div>
        </div>
      </div>

      {error && (
        <Alert variant="destructive" className="mb-6">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="grid grid-cols-12 gap-6">
        {/* Left Panel - Taxonomy Tree */}
        <div className="col-span-4 border rounded-lg">
          <div className="p-4 border-b">
            <div className="flex gap-2">
              <Input
                type="search"
                placeholder="Search concepts and terms..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              />
              <Button onClick={handleSearch} size="sm">
                <Search className="h-4 w-4" />
              </Button>
            </div>
          </div>
          <ScrollArea className="h-[calc(100vh-350px)]">
            <div className="p-4">
              {Object.entries(groupedConcepts).map(([taxonomyName, concepts]) => {
                const taxonomy = taxonomies.find(t => t.name === taxonomyName) || {
                  name: taxonomyName,
                  source_type: 'external' as const,
                  concepts_count: concepts.length,
                  properties_count: 0
                };
                
                return (
                  <TaxonomyGroup
                    key={taxonomyName}
                    taxonomy={taxonomy}
                    concepts={concepts}
                    selectedConcept={selectedConcept}
                    onSelectConcept={handleSelectConcept}
                    expandedIds={expandedIds}
                    toggleExpanded={toggleExpanded}
                  />
                );
              })}
              {Object.keys(groupedConcepts).length === 0 && !loading && (
                <div className="text-center text-muted-foreground py-8">
                  No concepts found
                </div>
              )}
            </div>
          </ScrollArea>
        </div>

        {/* Right Panel - Concept Details */}
        <div className="col-span-8 border rounded-lg">
          {selectedConcept ? (
            <div className="h-full">
              <div className="p-6 border-b">
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h2 className="text-2xl font-semibold mb-2">
                      {selectedConcept.label || selectedConcept.iri.split(/[/#]/).pop()}
                    </h2>
                    <p className="text-muted-foreground">
                      {selectedConcept.comment || 'No description available'}
                    </p>
                  </div>
                  <div className="flex space-x-2">
                    <Button variant="ghost" size="sm" disabled>
                      <Trash2 className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="sm" disabled>
                      <Pencil className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </div>

              <Tabs value={activeTab} onValueChange={setActiveTab} className="p-6">
                <TabsList>
                  <TabsTrigger value="details">Details</TabsTrigger>
                  <TabsTrigger value="hierarchy">Hierarchy</TabsTrigger>
                  <TabsTrigger value="tagged">Tagged Assets</TabsTrigger>
                </TabsList>
                
                <TabsContent value="details">
                  <ConceptDetails concept={selectedConcept} hierarchy={selectedHierarchy || undefined} />
                </TabsContent>
                
                <TabsContent value="hierarchy">
                  {selectedHierarchy ? (
                    <div className="space-y-4">
                      <h3 className="text-lg font-semibold">Concept Hierarchy</h3>
                      {renderLineage(selectedHierarchy)}
                    </div>
                  ) : (
                    <div className="text-muted-foreground">Loading hierarchy...</div>
                  )}
                </TabsContent>
                
                <TabsContent value="tagged">
                  {selectedConcept.tagged_assets.length > 0 ? (
                    <div className="space-y-4">
                      <h3 className="text-lg font-semibold">Tagged Assets</h3>
                      <div className="space-y-3">
                        {selectedConcept.tagged_assets.map(asset => (
                          <div key={asset.id} className="p-4 border rounded-lg">
                            <div className="font-medium">{asset.name}</div>
                            {asset.type && (
                              <Badge variant="outline" className="text-xs mt-1">
                                {asset.type}
                              </Badge>
                            )}
                            {asset.path && (
                              <div className="text-sm text-muted-foreground font-mono mt-1">
                                {asset.path}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <div className="text-muted-foreground">No tagged assets found</div>
                  )}
                </TabsContent>
              </Tabs>
            </div>
          ) : (
            <div className="h-full flex items-center justify-center text-muted-foreground">
              Select a concept or term to view details
            </div>
          )}
        </div>
      </div>

      {/* Legacy Dialog (for backwards compatibility) */}
      <Dialog open={openDialog} onOpenChange={setOpenDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              Create New {dialogType === 'glossary' ? 'Glossary' : 'Term'}
            </DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSave} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">Name</Label>
              <Input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">
                {dialogType === 'glossary' ? 'Description' : 'Definition'}
              </Label>
              <Input
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                required
              />
            </div>
            {dialogType === 'glossary' && (
              <>
                <div className="space-y-2">
                  <Label htmlFor="scope">Scope</Label>
                  <Select value={scope} onValueChange={setScope}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select scope" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="company">Company</SelectItem>
                      <SelectItem value="division">Division</SelectItem>
                      <SelectItem value="department">Department</SelectItem>
                      <SelectItem value="team">Team</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="orgUnit">Organizational Unit</Label>
                  <Input
                    id="orgUnit"
                    value={orgUnit}
                    onChange={(e) => setOrgUnit(e.target.value)}
                    required
                  />
                </div>
              </>
            )}
            <div className="space-y-2">
              <Label htmlFor="domain">Domain</Label>
              <Input
                id="domain"
                value={domain}
                onChange={(e) => setDomain(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="owner">Owner</Label>
              <Input
                id="owner"
                value={owner}
                onChange={(e) => setOwner(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="tags">Tags (comma-separated)</Label>
              <Input
                id="tags"
                value={tags}
                onChange={(e) => setTags(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="status">Status</Label>
              <Select value={status} onValueChange={setStatus}>
                <SelectTrigger>
                  <SelectValue placeholder="Select status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="draft">Draft</SelectItem>
                  <SelectItem value="active">Active</SelectItem>
                  <SelectItem value="deprecated">Deprecated</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <DialogFooter>
              <Button type="submit">Create</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}