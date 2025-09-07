import React, { useState, useEffect, useMemo } from 'react';
import type { 
  OntologyTaxonomy, 
  OntologyConcept, 
  ConceptHierarchy, 
  GroupedConcepts,
  TaxonomyStats
} from '@/types/ontology';
import type { EntitySemanticLink } from '@/types/semantic-link';
import { useTree } from '@headless-tree/react';
import { 
  syncDataLoaderFeature,
  selectionFeature,
  hotkeysCoreFeature,
  searchFeature
} from '@headless-tree/core';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { DataTable } from '@/components/ui/data-table';
import { ColumnDef } from '@tanstack/react-table';
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
  Search,
  Network,
  TreePine,
} from 'lucide-react';
import ReactFlow, { Node, Edge, Background, MarkerType, Controls } from 'reactflow';
import 'reactflow/dist/style.css';
import useBreadcrumbStore from '@/stores/breadcrumb-store';
import { cn } from '@/lib/utils';

// Define concept item type for Headless Tree
type ConceptTreeItem = {
  id: string;
  concept: OntologyConcept;
  name: string;
  children: ConceptTreeItem[];
};

interface ConceptTreeItemProps {
  item: any;
  selectedConcept: OntologyConcept | null;
  onSelectConcept: (concept: OntologyConcept) => void;
}

const ConceptTreeItem: React.FC<ConceptTreeItemProps> = ({ item, selectedConcept, onSelectConcept }) => {
  const concept = item.getItemData() as OntologyConcept;
  const isSelected = selectedConcept?.iri === concept.iri;
  const level = item.getItemMeta().level;
  
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
    <div
      {...item.getProps()}
      className={cn(
        "flex items-center gap-2 px-2 py-1.5 rounded-md cursor-pointer w-full text-left",
        "hover:bg-accent hover:text-accent-foreground transition-colors",
        isSelected && "bg-accent text-accent-foreground"
      )}
      style={{ paddingLeft: `${level * 12 + 8}px` }}
      onClick={() => onSelectConcept(concept)}
    >
      <div className="flex items-center w-5 justify-center">
        {item.isFolder() && (
          <button
            className="p-0.5 hover:bg-muted rounded"
            onClick={(e) => {
              e.stopPropagation();
              if (item.isExpanded()) {
                item.collapse();
              } else {
                item.expand();
              }
            }}
          >
            {item.isExpanded() ? (
              <ChevronDown className="h-3.5 w-3.5 shrink-0" />
            ) : (
              <ChevronRight className="h-3.5 w-3.5 shrink-0" />
            )}
          </button>
        )}
      </div>
      <div className="flex items-center gap-2 min-w-0 flex-1">
        {getConceptIcon()}
        <span 
          className="truncate text-sm font-medium" 
          title={`${getDisplayName()}${concept.source_context ? ` (${concept.source_context})` : ''}`}
        >
          {getDisplayName()}
        </span>
      </div>
    </div>
  );
};

interface UnifiedConceptTreeProps {
  concepts: OntologyConcept[];
  selectedConcept: OntologyConcept | null;
  onSelectConcept: (concept: OntologyConcept) => void;
  searchQuery: string;
  onShowKnowledgeGraph?: () => void;
}

const UnifiedConceptTree: React.FC<UnifiedConceptTreeProps> = ({
  concepts,
  selectedConcept,
  onSelectConcept,
  searchQuery,
  onShowKnowledgeGraph
}) => {
  // Build hierarchical data structure for Headless Tree
  const treeData = useMemo(() => {
    const conceptMap = new Map<string, OntologyConcept>();
    const hierarchy = new Map<string, string[]>();
    
    // Filter out ConceptSchemes and individuals, but keep classes and concepts
    const baseConcepts = concepts.filter(concept => 
      concept.concept_type !== 'individual' && concept.concept_type !== 'concept_scheme'
    );
    
    // Build concept map and hierarchy
    baseConcepts.forEach(concept => {
      conceptMap.set(concept.iri, concept);
      
      // Debug key concepts to understand the hierarchy structure
      if (concept.iri.includes('Quality')) {
        console.log('[DEBUG Quality concept]:', {
          iri: concept.iri,
          label: concept.label,
          parent_concepts: concept.parent_concepts,
          child_concepts: concept.child_concepts
        });
      }
      
      
      // Build parent-child relationships from parent_concepts
      concept.parent_concepts.forEach(parentIri => {
        if (!hierarchy.has(parentIri)) {
          hierarchy.set(parentIri, []);
        }
        // Only add if not already present to avoid duplicates
        const parentChildren = hierarchy.get(parentIri)!;
        if (!parentChildren.includes(concept.iri)) {
          parentChildren.push(concept.iri);
        }
      });
      
      // Ensure concept is in the map even if it has no children
      if (!hierarchy.has(concept.iri)) {
        hierarchy.set(concept.iri, []);
      }
    });
    
    return { conceptMap, hierarchy };
  }, [concepts]);
  
  const tree = useTree<OntologyConcept>({
    rootItemId: 'root',
    getItemName: (item) => {
      const concept = item.getItemData();
      return concept.label || concept.iri.split(/[/#]/).pop() || concept.iri;
    },
    isItemFolder: (item) => {
      const concept = item.getItemData();
      const children = treeData.hierarchy.get(concept.iri) || [];
      const hasChildConcepts = concept.child_concepts && concept.child_concepts.length > 0;
      return children.length > 0 || hasChildConcepts;
    },
    dataLoader: {
      getItem: (itemId: string) => {
        if (itemId === 'root') {
          return { iri: 'root', label: 'Root', concept_type: 'root' } as OntologyConcept;
        }
        return treeData.conceptMap.get(itemId) || null;
      },
      getChildren: (itemId: string) => {
        if (itemId === 'root') {
          // Return root-level concepts (those with no parents or parents not in our dataset)
          const rootConcepts = Array.from(treeData.conceptMap.values())
            .filter(concept => {
              return concept.parent_concepts.length === 0 || 
                     !concept.parent_concepts.some(parentIri => treeData.conceptMap.has(parentIri));
            })
            .map(concept => concept.iri);
          return rootConcepts;
        }
        return treeData.hierarchy.get(itemId) || [];
      },
    },
    initialState: {
      expandedItems: ['root'],
    },
    features: [
      syncDataLoaderFeature,
      selectionFeature,
      hotkeysCoreFeature,
      ...(searchQuery ? [searchFeature] : [])
    ],
  });

  return (
    <div className="space-y-1">
      <div 
        className="flex items-center gap-2 p-2 bg-muted/30 rounded-md mb-4 cursor-pointer hover:bg-muted/50 transition-colors"
        onClick={() => {
          if (onShowKnowledgeGraph) {
            onShowKnowledgeGraph();
          }
        }}
      >
        <Network className="h-4 w-4 text-blue-600" />
        <span className="font-medium">Knowledge Graph</span>
        <Badge variant="secondary" className="text-xs">
          {treeData.conceptMap.size} concepts
        </Badge>
      </div>
      
      <div {...tree.getContainerProps()} className="space-y-1" key={treeData.conceptMap.size}>
        {tree.getItems().map((item) => {
          // Skip rendering the root item
          if (item.getId() === 'root') {
            return null;
          }
          
          return (
            <ConceptTreeItem
              key={item.getId()}
              item={item}
              selectedConcept={selectedConcept}
              onSelectConcept={onSelectConcept}
            />
          );
        })}
        
        {tree.getItems().filter(item => item.getId() !== 'root').length === 0 && (
          <div className="text-center text-muted-foreground py-4">
            No concepts found
          </div>
        )}
      </div>
    </div>
  );
};

// Note: TaxonomyGroup component is kept for potential future use but not currently used in the main UI
// The UnifiedConceptTree now handles all concept display
interface TaxonomyGroupProps {
  taxonomy: OntologyTaxonomy;
  concepts: OntologyConcept[];
  selectedConcept: OntologyConcept | null;
  onSelectConcept: (concept: OntologyConcept) => void;
}

const TaxonomyGroup: React.FC<TaxonomyGroupProps> = ({
  taxonomy,
  concepts,
  selectedConcept,
  onSelectConcept
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
          <UnifiedConceptTree
            concepts={concepts}
            selectedConcept={selectedConcept}
            onSelectConcept={onSelectConcept}
            searchQuery=""
          />
        </div>
      )}
    </div>
  );
};

interface ConceptDetailsProps {
  concept: OntologyConcept;
  concepts: OntologyConcept[];
}

const ConceptDetails: React.FC<ConceptDetailsProps> = ({ concept, concepts }) => {
  // Helper function to resolve IRI to concept label
  const getConceptLabel = (iri: string): string => {
    const foundConcept = concepts.find(c => c.iri === iri);
    return foundConcept?.label || iri.split(/[/#]/).pop() || iri;
  };
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
      
      <DetailItem 
        label="Source Taxonomy" 
        value={
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="text-xs">
              {concept.source_context}
            </Badge>
            <span className="text-xs text-muted-foreground">
              ({concept.concept_type})
            </span>
          </div>
        } 
      />
      
      {concept.comment && (
        <DetailItem label="Description" value={concept.comment} />
      )}
      
      {concept.parent_concepts.length > 0 && (
        <DetailItem 
          label="Parent Concepts" 
          value={
            <div className="flex flex-wrap gap-2">
              {concept.parent_concepts.map(parentIri => (
                <Badge key={parentIri} variant="secondary" className="text-xs">
                  {getConceptLabel(parentIri)}
                </Badge>
              ))}
            </div>
          } 
        />
      )}
      
      {concept.child_concepts.length > 0 && (
        <DetailItem 
          label="Child Concepts" 
          value={
            <div className="flex flex-wrap gap-2">
              {concept.child_concepts.map(childIri => (
                <Badge key={childIri} variant="outline" className="text-xs">
                  {getConceptLabel(childIri)}
                </Badge>
              ))}
            </div>
          } 
        />
      )}
    </div>
  );
};

interface ConceptHierarchyViewProps {
  concept: OntologyConcept;
  concepts: OntologyConcept[];
}

const ConceptHierarchyView: React.FC<ConceptHierarchyViewProps> = ({ concept, concepts }) => {
  // Helper function to resolve IRI to concept
  const getConceptByIri = (iri: string): OntologyConcept | undefined => {
    return concepts.find(c => c.iri === iri);
  };

  // Get parent concepts
  const parentConcepts = concept.parent_concepts
    .map(parentIri => getConceptByIri(parentIri))
    .filter((parent): parent is OntologyConcept => parent !== undefined);

  // Get child concepts  
  const childConcepts = concept.child_concepts
    .map(childIri => getConceptByIri(childIri))
    .filter((child): child is OntologyConcept => child !== undefined);

  return (
    <div className="space-y-6">
      {/* Parent Concepts */}
      {parentConcepts.length > 0 && (
        <div>
          <h4 className="font-medium text-sm text-muted-foreground mb-3">Parent Concepts</h4>
          <div className="space-y-2">
            {parentConcepts.map(parent => (
              <div key={parent.iri} className="flex items-center gap-3 p-3 border rounded-lg hover:bg-muted/50">
                <div className="w-2 h-2 rounded-full bg-green-500" />
                <div className="flex-1">
                  <div className="font-medium">{parent.label}</div>
                  <div className="text-sm text-muted-foreground">
                    from {parent.source_context}
                  </div>
                  {parent.comment && (
                    <div className="text-sm text-muted-foreground mt-1">
                      {parent.comment}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Current Concept */}
      <div>
        <h4 className="font-medium text-sm text-muted-foreground mb-3">Current Concept</h4>
        <div className="flex items-center gap-3 p-3 border-2 border-blue-200 bg-blue-50 rounded-lg">
          <div className="w-3 h-3 rounded-full bg-blue-500" />
          <div className="flex-1">
            <div className="font-semibold text-blue-900">{concept.label}</div>
            <div className="text-sm text-blue-700">
              from {concept.source_context}
            </div>
            {concept.comment && (
              <div className="text-sm text-blue-700 mt-1">
                {concept.comment}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Child Concepts */}
      {childConcepts.length > 0 && (
        <div>
          <h4 className="font-medium text-sm text-muted-foreground mb-3">Child Concepts</h4>
          <div className="space-y-2">
            {childConcepts.map(child => (
              <div key={child.iri} className="flex items-center gap-3 p-3 border rounded-lg hover:bg-muted/50">
                <div className="w-2 h-2 rounded-full bg-orange-500" />
                <div className="flex-1">
                  <div className="font-medium">{child.label}</div>
                  <div className="text-sm text-muted-foreground">
                    from {child.source_context}
                  </div>
                  {child.comment && (
                    <div className="text-sm text-muted-foreground mt-1">
                      {child.comment}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {parentConcepts.length === 0 && childConcepts.length === 0 && (
        <div className="text-center text-muted-foreground py-8">
          This concept has no immediate parent or child relationships
        </div>
      )}
    </div>
  );
};

interface TaggedAssetsViewProps {
  concept: OntologyConcept;
}

// Define the asset type for better type safety
type TaggedAsset = {
  id: string;
  name: string;
  type?: string;
  path?: string;
};

const TaggedAssetsView: React.FC<TaggedAssetsViewProps> = ({ concept }) => {
  // Define columns for the data table
  const columns: ColumnDef<TaggedAsset>[] = [
    {
      accessorKey: "name",
      header: "Asset Name",
      cell: ({ row }) => (
        <div className="font-medium">{row.getValue("name")}</div>
      ),
    },
    {
      accessorKey: "type",
      header: "Type",
      cell: ({ row }) => {
        const type = row.getValue("type") as string;
        return (
          <Badge variant="outline" className="text-xs">
            {type?.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase()) || 'Unknown'}
          </Badge>
        );
      },
      filterFn: (row, id, value) => {
        return value === 'all' || row.getValue(id) === value;
      },
    },
    {
      accessorKey: "path",
      header: "Path",
      cell: ({ row }) => {
        const path = row.getValue("path") as string;
        return path ? (
          <code className="text-sm text-muted-foreground bg-muted px-2 py-1 rounded">
            {path}
          </code>
        ) : null;
      },
    },
  ];

  if (concept.tagged_assets.length === 0) {
    return <div className="text-muted-foreground">No tagged assets found</div>;
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold">Tagged Assets</h3>
        <Badge variant="secondary" className="text-xs">
          {concept.tagged_assets.length} total
        </Badge>
      </div>

      <DataTable
        columns={columns}
        data={concept.tagged_assets}
        searchColumn="name"
      />
    </div>
  );
};

export default function BusinessGlossary() {
  const [taxonomies, setTaxonomies] = useState<OntologyTaxonomy[]>([]);
  const [groupedConcepts, setGroupedConcepts] = useState<GroupedConcepts>({});
  const [selectedConcept, setSelectedConcept] = useState<OntologyConcept | null>(null);
  const [selectedHierarchy, setSelectedHierarchy] = useState<ConceptHierarchy | null>(null);
  const [treeExpandedIds, setTreeExpandedIds] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeTab, setActiveTab] = useState('details');
  const [stats, setStats] = useState<TaxonomyStats | null>(null);
  const [showKnowledgeGraph, setShowKnowledgeGraph] = useState(false);

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
  }, []); // Empty dependency array to run only once on mount

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
    setShowKnowledgeGraph(false);
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

    // Fetch semantic links (tagged assets)
    try {
      const response = await fetch(`/api/semantic-links/iri/${encodeURIComponent(concept.iri)}`);
      if (response.ok) {
        const semanticLinks: EntitySemanticLink[] = await response.json();
        
        // Update the concept with tagged assets
        const updatedConcept = {
          ...concept,
          tagged_assets: semanticLinks.map((link) => ({
            id: link.entity_id,
            name: link.label || link.entity_id,
            type: link.entity_type,
            description: `${link.entity_type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}: ${link.label || link.entity_id}`
          }))
        };
        setSelectedConcept(updatedConcept);
      }
    } catch (err) {
      console.error('Failed to fetch semantic links:', err);
    }
  };

  const handleShowKnowledgeGraph = () => {
    setShowKnowledgeGraph(true);
    setSelectedConcept(null);
    setActiveTab('knowledge-graph');
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

  const toggleTreeExpanded = (id: string) => {
    setTreeExpandedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const renderKnowledgeGraph = (concepts: OntologyConcept[]) => {
    const nodes: Node[] = [];
    const edges: Edge[] = [];
    
    // Position configuration
    const nodeWidth = 140;
    const nodeHeight = 80;
    const horizontalSpacing = 200;
    const verticalSpacing = 120;
    const columnsPerRow = 6;
    
    // Create nodes for all concepts
    concepts.forEach((concept, index) => {
      const row = Math.floor(index / columnsPerRow);
      const col = index % columnsPerRow;
      
      nodes.push({
        id: concept.iri,
        data: { 
          label: concept.label || concept.iri.split(/[/#]/).pop(),
          sourceContext: concept.source_context
        },
        position: { 
          x: col * horizontalSpacing, 
          y: row * verticalSpacing 
        },
        type: 'default',
        style: {
          background: '#f8fafc',
          border: '1px solid #cbd5e1',
          borderRadius: '8px',
          padding: '8px',
          fontSize: '11px',
          minWidth: nodeWidth + 'px',
          minHeight: nodeHeight + 'px',
          textAlign: 'center',
          cursor: 'pointer'
        }
      });
    });
    
    // Create edges for hierarchical relationships
    concepts.forEach(concept => {
      concept.child_concepts.forEach(childIri => {
        const childExists = concepts.find(c => c.iri === childIri);
        if (childExists) {
          edges.push({
            id: `${concept.iri}-${childIri}`,
            source: concept.iri,
            target: childIri,
            type: 'smoothstep',
            style: { 
              stroke: '#94a3b8', 
              strokeWidth: 1,
              opacity: 0.7
            },
            markerEnd: {
              type: MarkerType.ArrowClosed,
              color: '#94a3b8'
            }
          });
        }
      });
    });

    return (
      <div className="h-[600px] border rounded-lg">
        <style>
          {`
            .react-flow__handle {
              opacity: 0 !important;
              pointer-events: none !important;
              width: 1px !important;
              height: 1px !important;
            }
            .react-flow__node {
              cursor: pointer;
            }
            .react-flow__node:hover {
              transform: scale(1.05);
              transition: transform 0.2s ease;
              z-index: 1000;
            }
          `}
        </style>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          fitView
          minZoom={0.3}
          maxZoom={1.5}
          style={{ background: '#F7F9FB' }}
          defaultEdgeOptions={{
            style: { strokeWidth: 1 },
            markerEnd: { type: MarkerType.ArrowClosed }
          }}
          nodesDraggable={true}
          nodesConnectable={false}
          elementsSelectable={true}
          onNodeClick={(event, node) => {
            // Find and select the concept in the tree
            const concept = concepts.find(c => c.iri === node.id);
            if (concept) {
              handleSelectConcept(concept);
            }
          }}
          connectionMode="strict"
        >
          <Controls />
          <Background />
        </ReactFlow>
      </div>
    );
  };

  const renderLineage = (hierarchy: ConceptHierarchy) => {
    const nodes: Node[] = [];
    const edges: Edge[] = [];
    const allConcepts = Object.values(groupedConcepts).flat();
    
    // Helper function to find concept by IRI
    const findConceptByIri = (iri: string) => allConcepts.find(c => c.iri === iri);

    // Add current concept as center node
    const centerY = 250;
    nodes.push({
      id: hierarchy.concept.iri,
      data: { 
        label: hierarchy.concept.label || hierarchy.concept.iri.split(/[/#]/).pop(),
        sourceContext: hierarchy.concept.source_context
      },
      position: { x: 400, y: centerY },
      type: 'default',
      style: {
        background: '#fff',
        border: '2px solid #2563eb',
        borderRadius: '8px',
        padding: '12px',
        fontSize: '14px',
        fontWeight: 'bold',
        minWidth: '140px',
        textAlign: 'center'
      }
    });

    // Add immediate parents
    hierarchy.concept.parent_concepts.forEach((parentIri, index) => {
      const parent = findConceptByIri(parentIri);
      if (parent) {
        const nodeId = parent.iri;
        nodes.push({
          id: nodeId,
          data: { 
            label: parent.label || parent.iri.split(/[/#]/).pop(),
            sourceContext: parent.source_context
          },
          position: { x: 400 + (index - hierarchy.concept.parent_concepts.length / 2 + 0.5) * 180, y: centerY - 150 },
          style: {
            background: '#dbeafe',
            border: '1px solid #3b82f6',
            borderRadius: '6px',
            padding: '10px',
            fontSize: '12px',
            minWidth: '120px',
            textAlign: 'center'
          }
        });
        
        edges.push({
          id: `${nodeId}-${hierarchy.concept.iri}`,
          source: nodeId,
          target: hierarchy.concept.iri,
          type: 'smoothstep',
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: '#64748b'
          },
          style: { stroke: '#64748b' }
        });
      }
    });

    // Add immediate children  
    hierarchy.concept.child_concepts.forEach((childIri, index) => {
      const child = findConceptByIri(childIri);
      if (child) {
        const nodeId = child.iri;
        nodes.push({
          id: nodeId,
          data: { 
            label: child.label || child.iri.split(/[/#]/).pop(),
            sourceContext: child.source_context
          },
          position: { x: 400 + (index - hierarchy.concept.child_concepts.length / 2 + 0.5) * 180, y: centerY + 150 },
          style: {
            background: '#dcfce7',
            border: '1px solid #16a34a',
            borderRadius: '6px',
            padding: '10px',
            fontSize: '12px',
            minWidth: '120px',
            textAlign: 'center'
          }
        });
        
        edges.push({
          id: `${hierarchy.concept.iri}-${nodeId}`,
          source: hierarchy.concept.iri,
          target: nodeId,
          type: 'smoothstep',
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: '#64748b'
          },
          style: { stroke: '#64748b' }
        });
      }
    });

    // Add siblings if available
    if (hierarchy.siblings && hierarchy.siblings.length > 0) {
      hierarchy.siblings.forEach((sibling, index) => {
        const nodeId = sibling.iri;
        nodes.push({
          id: nodeId,
          data: { 
            label: sibling.label || sibling.iri.split(/[/#]/).pop(),
            sourceContext: sibling.source_context
          },
          position: { x: 600 + (index * 160), y: centerY },
          style: {
            background: '#f5f5f5',
            border: '1px solid #d1d5db',
            borderRadius: '6px',
            padding: '10px',
            fontSize: '12px',
            minWidth: '120px',
            textAlign: 'center',
            opacity: 0.6,
            color: '#9ca3af'
          }
        });
        
        // Add muted connecting line from center to sibling
        edges.push({
          id: `${hierarchy.concept.iri}-${nodeId}`,
          source: hierarchy.concept.iri,
          target: nodeId,
          type: 'smoothstep',
          style: { 
            stroke: '#d1d5db', 
            strokeWidth: 1, 
            opacity: 0.5,
            strokeDasharray: '5,5'
          },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: '#d1d5db'
          }
        });
      });
    }

    return (
      <div className="h-[500px] border rounded-lg">
        <style>
          {`
            .react-flow__handle {
              opacity: 0 !important;
              pointer-events: none !important;
              width: 1px !important;
              height: 1px !important;
            }
            .react-flow__node {
              cursor: pointer;
            }
            .react-flow__node:hover {
              transform: scale(1.05);
              transition: transform 0.2s ease;
            }
          `}
        </style>
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
          elementsSelectable={true}
          onNodeClick={(event, node) => {
            // Find and select the concept in the tree
            const allConcepts = Object.values(groupedConcepts).flat();
            const concept = allConcepts.find(c => c.iri === node.id);
            if (concept) {
              handleSelectConcept(concept);
            }
          }}
          connectionMode="strict"
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
        <div className="col-span-4 border rounded-lg flex flex-col">
          <div className="p-4 border-b">
            <div className="flex gap-2">
              <Input
                type="search"
                placeholder="Search concepts and terms..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              />
              <Button onClick={handleSearch} size="sm">
                <Search className="h-4 w-4" />
              </Button>
            </div>
          </div>
          <ScrollArea className="flex-1">
            <div className="p-4 h-full">
              <UnifiedConceptTree
                key={Object.values(groupedConcepts).flat().length}
                concepts={Object.values(groupedConcepts).flat()}
                selectedConcept={selectedConcept}
                onSelectConcept={handleSelectConcept}
                onShowKnowledgeGraph={handleShowKnowledgeGraph}
                searchQuery={searchQuery}
              />
              {Object.keys(groupedConcepts).length === 0 && !loading && (
                <div className="text-center text-muted-foreground py-8">
                  No concepts found
                </div>
              )}
            </div>
          </ScrollArea>
        </div>

        {/* Right Panel - Concept Details or Knowledge Graph */}
        <div className="col-span-8 border rounded-lg">
          {showKnowledgeGraph ? (
            <div className="h-full">
              <div className="p-6 border-b">
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h2 className="text-2xl font-semibold mb-2 flex items-center gap-2">
                      <Network className="h-6 w-6" />
                      Knowledge Graph
                    </h2>
                    <p className="text-muted-foreground">
                      Interactive visualization of all concepts and their relationships
                    </p>
                  </div>
                </div>
              </div>
              <div className="p-6">
                {renderKnowledgeGraph(Object.values(groupedConcepts).flat())}
              </div>
            </div>
          ) : selectedConcept ? (
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
                  <ConceptDetails 
                    concept={selectedConcept} 
                    concepts={Object.values(groupedConcepts).flat()}
                  />
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
                  <TaggedAssetsView concept={selectedConcept} />
                </TabsContent>
              </Tabs>
            </div>
          ) : (
            <div className="h-full flex items-center justify-center text-muted-foreground">
              <div className="text-center">
                <Network className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>Select a concept or click Knowledge Graph to view details</p>
              </div>
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