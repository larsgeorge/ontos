import React, { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
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
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { ScrollArea } from '@/components/ui/scroll-area';
import { DataTable } from '@/components/ui/data-table';
import { ColumnDef } from '@tanstack/react-table';
import {
  AlertCircle,
  ChevronRight,
  ChevronDown,
  Layers,
  Zap,
  Search,
  Network,
  Loader2,
} from 'lucide-react';
import ReactFlow, { Node, Edge, Background, MarkerType, Controls, ConnectionMode, MiniMap, Position } from 'reactflow';
import ForceGraph2D from 'react-force-graph-2d';
import dagre from 'dagre';
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
        return <Layers className="h-4 w-4 shrink-0 text-green-500" />;
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
  // Helper function to find the path from root to a specific concept
  const findPathToConcept = useCallback((targetIri: string, conceptMap: Map<string, OntologyConcept>, hierarchy: Map<string, string[]>): string[] => {
    const visited = new Set<string>();
    
    const findPath = (currentIri: string, path: string[]): string[] | null => {
      if (visited.has(currentIri)) return null;
      visited.add(currentIri);
      
      if (currentIri === targetIri) {
        return [...path, currentIri];
      }
      
      // Check children
      const children = hierarchy.get(currentIri) || [];
      for (const childIri of children) {
        const result = findPath(childIri, [...path, currentIri]);
        if (result) return result;
      }
      
      return null;
    };
    
    // Start from root
    const result = findPath('root', []);
    return result || [];
  }, []);

  // Build hierarchical data structure for Headless Tree
  const treeData = useMemo(() => {
    const conceptMap = new Map<string, OntologyConcept>();
    const hierarchy = new Map<string, string[]>();
    
    // Filter out ConceptSchemes and individuals, but keep classes and concepts
    const baseConcepts = concepts.filter(concept => {
      const conceptType = (concept as any).concept_type as string;
      return conceptType !== 'individual' && conceptType !== 'concept_scheme';
    });
    
    // Build concept map and hierarchy
    baseConcepts.forEach(concept => {
      conceptMap.set(concept.iri, concept);
      

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
          // Provide a minimal object satisfying OntologyConcept shape
          return {
            iri: 'root',
            label: 'Root',
            concept_type: 'root' as any,
            parent_concepts: [],
            child_concepts: [],
            properties: {},
            tagged_assets: [],
            source_context: 'root'
          } as unknown as OntologyConcept;
        }
        const found = treeData.conceptMap.get(itemId);
        if (!found) {
          // Fallback to a minimal placeholder to satisfy return type
          return {
            iri: itemId,
            label: itemId.split(/[/#]/).pop() || itemId,
            concept_type: 'concept' as any,
            parent_concepts: [],
            child_concepts: [],
            properties: {},
            tagged_assets: [],
            source_context: 'unknown'
          } as unknown as OntologyConcept;
        }
        return found;
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

  // Effect to expand tree path when selected concept changes
  useEffect(() => {
    if (selectedConcept && treeData.conceptMap.has(selectedConcept.iri)) {
      // Use a timeout to ensure tree is fully loaded
      const expandPath = () => {
        // Expand all ancestor concepts of the selected concept
        // Build a set of all ancestors by walking parent_concepts recursively
        const ancestorsToExpand = new Set<string>();
        const stack: string[] = [...selectedConcept.parent_concepts];
        while (stack.length > 0) {
          const current = stack.pop() as string;
          if (!treeData.conceptMap.has(current)) continue;
          if (ancestorsToExpand.has(current)) continue;
          ancestorsToExpand.add(current);
          const parentConcept = treeData.conceptMap.get(current)!;
          parentConcept.parent_concepts.forEach((p) => stack.push(p));
        }

        // Expand any ancestor items that already exist in the tree; repeated calls
        // will progressively expand deeper ancestors as they are created
        const items = tree.getItems();
        items.forEach((item) => {
          const id = item.getId();
          if (ancestorsToExpand.has(id) && !item.isExpanded()) {
            item.expand();
          }
        });
      };
      
      // Execute immediately and also with a small delay to handle async tree loading
      expandPath();
      setTimeout(expandPath, 100);
      setTimeout(expandPath, 500);
    }
  }, [selectedConcept, treeData, tree]);

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
// Deprecated: TaxonomyGroupProps unused after removing TaxonomyGroup

// Deprecated: TaxonomyGroup is currently unused and removed to avoid lints

interface ConceptDetailsProps {
  concept: OntologyConcept;
  concepts: OntologyConcept[];
  onSelectConcept: (concept: OntologyConcept) => void;
}

const ConceptDetails: React.FC<ConceptDetailsProps> = ({ concept, concepts, onSelectConcept }) => {
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
              {concept.parent_concepts.map(parentIri => {
                const parentConcept = concepts.find(c => c.iri === parentIri);
                return (
                  <Badge 
                    key={parentIri} 
                    variant="secondary" 
                    className="text-xs cursor-pointer hover:bg-secondary/80 transition-colors"
                    onClick={() => {
                      if (parentConcept) {
                        onSelectConcept(parentConcept);
                      }
                    }}
                  >
                    {getConceptLabel(parentIri)}
                  </Badge>
                );
              })}
            </div>
          } 
        />
      )}
      
      {concept.child_concepts.length > 0 && (
        <DetailItem 
          label="Child Concepts" 
          value={
            <div className="flex flex-wrap gap-2">
              {concept.child_concepts.map(childIri => {
                const childConcept = concepts.find(c => c.iri === childIri);
                return (
                  <Badge 
                    key={childIri} 
                    variant="outline" 
                    className="text-xs cursor-pointer hover:bg-accent/80 transition-colors"
                    onClick={() => {
                      if (childConcept) {
                        onSelectConcept(childConcept);
                      }
                    }}
                  >
                    {getConceptLabel(childIri)}
                  </Badge>
                );
              })}
            </div>
          } 
        />
      )}
    </div>
  );
};

// Deprecated: ConceptHierarchyView is unused and removed to avoid lints

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
  const [searchParams, setSearchParams] = useSearchParams();
  const [taxonomies, setTaxonomies] = useState<OntologyTaxonomy[]>([]);
  const [groupedConcepts, setGroupedConcepts] = useState<GroupedConcepts>({});
  const [selectedConcept, setSelectedConcept] = useState<OntologyConcept | null>(null);
  const [selectedHierarchy, setSelectedHierarchy] = useState<ConceptHierarchy | null>(null);
  // Removed unused treeExpandedIds state

  // Override ForceGraph2D tooltip shadows
  useEffect(() => {
    const styleId = 'force-graph-tooltip-override';
    if (!document.getElementById(styleId)) {
      const style = document.createElement('style');
      style.id = styleId;
      style.textContent = `
        /* Override all possible tooltip shadow sources in ForceGraph2D */
        .graph-tooltip,
        .graph-info-tooltip,
        [data-tip],
        .d3-tip,
        .tooltip,
        .node-tooltip,
        .force-graph-tooltip {
          box-shadow: none !important;
          -webkit-box-shadow: none !important;
          -moz-box-shadow: none !important;
          filter: none !important;
          -webkit-filter: none !important;
          text-shadow: none !important;
          border: none !important;
        }
        
        /* Target any div with tooltip-like styling */
        div[style*="position: absolute"][style*="pointer-events: none"] {
          box-shadow: none !important;
          -webkit-box-shadow: none !important;
          -moz-box-shadow: none !important;
          filter: none !important;
          -webkit-filter: none !important;
        }
      `;
      document.head.appendChild(style);
    }
  }, []);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const searchTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  // Tabs removed; show sections in a single view
  const [stats, setStats] = useState<TaxonomyStats | null>(null);
  const [showKnowledgeGraph, setShowKnowledgeGraph] = useState(false);
  const [graphExpanded, setGraphExpanded] = useState<Set<string>>(new Set());

  // Legacy form state removed - Phase 0 (read-only ontologies)

  const setStaticSegments = useBreadcrumbStore((state) => state.setStaticSegments);
  const setDynamicTitle = useBreadcrumbStore((state) => state.setDynamicTitle);

  useEffect(() => {
    fetchData();
    
    // Set breadcrumbs
    setStaticSegments([]);
    setDynamicTitle('Semantic Models');

    // Cleanup breadcrumbs and search timeout on unmount
    return () => {
      setStaticSegments([]);
      setDynamicTitle(null);
      if (searchTimeoutRef.current) {
        clearTimeout(searchTimeoutRef.current);
      }
    };
  }, []); // Empty dependency array to run only once on mount

  // Handle URL parameters to select concept on load or URL change
  useEffect(() => {
    const conceptParam = searchParams.get('concept');
    if (conceptParam && Object.keys(groupedConcepts).length > 0) {
      const decodedIri = decodeURIComponent(conceptParam);
      const allConcepts = Object.values(groupedConcepts).flat();
      const conceptToSelect = allConcepts.find(c => c.iri === decodedIri);
      
      if (conceptToSelect && conceptToSelect.iri !== selectedConcept?.iri) {
        // Use a timeout to avoid updating state during render
        setTimeout(() => {
          handleSelectConcept(conceptToSelect);
        }, 0);
      }
    } else if (!conceptParam && selectedConcept) {
      // Clear selection if no concept in URL
      setSelectedConcept(null);
      setSelectedHierarchy(null);
      setShowKnowledgeGraph(false);
    }
  }, [searchParams, groupedConcepts]); // React to changes in URL params and loaded concepts

  const fetchData = async () => {
    try {
      setLoading(true);
      
      // Fetch taxonomies
      const taxonomiesResponse = await fetch('/api/semantic-models');
      if (!taxonomiesResponse.ok) throw new Error('Failed to fetch taxonomies');
      const taxonomiesData = await taxonomiesResponse.json();
      setTaxonomies(taxonomiesData.taxonomies || []);
      
      // Fetch grouped concepts
      const conceptsResponse = await fetch('/api/semantic-models/concepts-grouped');
      if (!conceptsResponse.ok) throw new Error('Failed to fetch concepts');
      const conceptsData = await conceptsResponse.json();
      setGroupedConcepts(conceptsData.grouped_concepts || {});
      
      // Fetch stats
      const statsResponse = await fetch('/api/semantic-models/stats');
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
    
    // Update URL with the selected concept IRI
    const newParams = new URLSearchParams(searchParams);
    newParams.set('concept', encodeURIComponent(concept.iri));
    setSearchParams(newParams);
    
    // Fetch hierarchy information
    try {
      const response = await fetch(`/api/semantic-models/concepts/${encodeURIComponent(concept.iri)}/hierarchy`);
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
            name: link.label || link.entity_id, // Backend should now provide meaningful labels
            type: link.entity_type,
            path: link.entity_id, // Show full ID in path column for reference
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
    
    // Clear concept from URL
    const newParams = new URLSearchParams(searchParams);
    newParams.delete('concept');
    setSearchParams(newParams);
  };

  const handleSearch = async (query?: string) => {
    const searchTerm = query !== undefined ? query : searchQuery;
    if (!searchTerm.trim()) {
      fetchData();
      return;
    }

    try {
      setLoading(true);
      const response = await fetch(
        `/api/semantic-models/search?q=${encodeURIComponent(searchTerm)}`
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

  // Removed unused toggleTreeExpanded

  const renderKnowledgeGraph = (concepts: OntologyConcept[]) => {
    // Only include classes and concepts, to match the tree
    const visibleConcepts = concepts.filter(
      (c) => c.concept_type === 'class' || c.concept_type === 'concept'
    );

    // Transform concepts to graph data
    const graphNodes = visibleConcepts.map(concept => ({
      id: concept.iri,
      label: concept.label || concept.iri.split(/[/#]/).pop() || 'Unknown',
      sourceContext: concept.source_context,
      concept: concept,
      childCount: concept.child_concepts?.length || 0,
      parentCount: concept.parent_concepts?.length || 0
    }));

    const graphLinks: any[] = [];
    visibleConcepts.forEach(concept => {
      concept.child_concepts.forEach(childIri => {
        const childExists = visibleConcepts.some(c => c.iri === childIri);
        if (childExists) {
          graphLinks.push({
            source: concept.iri,
            target: childIri
          });
        }
      });
    });

    const sourceColors = {
      'corporate-global': '#3b82f6',
      'manufacturing-lob': '#10b981', 
      'retail-banking-dept': '#f59e0b',
      'quality-assurance-dept': '#8b5cf6',
      'financial-services-lob': '#ef4444',
      'sporting_goods_skos.ttl': '#06b6d4',
      'banking_skos.ttl': '#84cc16',
      'health_science_rdfs.rdf': '#ec4899',
      'banking_rdfs.rdf': '#f97316'
    };

    return (
      <div className="h-full border rounded-lg bg-white overflow-hidden">
        <ForceGraph2D
              width={800}
              height={800}
              graphData={{
                nodes: graphNodes,
                links: graphLinks
              }}
              nodeAutoColorBy="sourceContext"
              nodeCanvasObject={(node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
                const label = node.label;
                const fontSize = Math.max(8, Math.min(14, 12 / globalScale));
                const nodeRadius = Math.max(4, Math.min(12, 8 / globalScale));
                
                // Get color based on source context
                const color = sourceColors[node.sourceContext as keyof typeof sourceColors] || '#64748b';
                
                // Draw node circle
                ctx.beginPath();
                ctx.arc(node.x, node.y, nodeRadius, 0, 2 * Math.PI);
                ctx.fillStyle = color;
                ctx.fill();
                
                // Add white border
                ctx.strokeStyle = '#ffffff';
                ctx.lineWidth = 2 / globalScale;
                ctx.stroke();
                
                // Only show label on actual hover (not zoom)
                if (node.__isHovered) {
                  ctx.font = `${fontSize}px Inter, system-ui, sans-serif`;
                  ctx.textAlign = 'center';
                  ctx.textBaseline = 'middle';
                  ctx.fillStyle = '#1f2937';
                  
                  // Add text background for better readability
                  const textWidth = ctx.measureText(label).width;
                  const textHeight = fontSize;
                  const padding = 4;
                  
                  ctx.fillStyle = 'rgba(255, 255, 255, 0.95)';
                  ctx.fillRect(
                    node.x - textWidth / 2 - padding,
                    node.y + nodeRadius + 4,
                    textWidth + padding * 2,
                    textHeight + padding
                  );
                  
                  // Add subtle border to text background
                  ctx.strokeStyle = 'rgba(0, 0, 0, 0.2)';
                  ctx.lineWidth = 1 / globalScale;
                  ctx.strokeRect(
                    node.x - textWidth / 2 - padding,
                    node.y + nodeRadius + 4,
                    textWidth + padding * 2,
                    textHeight + padding
                  );
                  
                  // Draw text
                  ctx.fillStyle = '#1f2937';
                  ctx.fillText(label, node.x, node.y + nodeRadius + textHeight / 2 + 6);
                }
              }}
              linkDirectionalArrowLength={6}
              linkDirectionalArrowRelPos={1}
              linkColor={() => '#64748b'}
              linkWidth={2}
              linkDirectionalParticles={0}
              onNodeHover={(node: any) => {
                // Clear all previous hover states
                graphNodes.forEach(n => {
                  delete (n as any).__isHovered;
                });
                
                // Set hover state for current node
                if (node) {
                  node.__isHovered = true;
                }
              }}
              onNodeClick={(node: any) => {
                if (node && node.concept) {
                  handleSelectConcept(node.concept);
                }
              }}
              nodeLabel={(node: any) => {
                const concept = node.concept as OntologyConcept;
                const color = sourceColors[node.sourceContext as keyof typeof sourceColors] || '#64748b';
                return `<div style="
                  background: ${color} !important; 
                  color: white !important; 
                  padding: 10px 14px !important; 
                  border-radius: 8px !important; 
                  max-width: 250px !important;
                  font-family: Inter, system-ui, sans-serif !important;
                  border: none !important;
                  box-shadow: none !important;
                  outline: none !important;
                  filter: none !important;
                  -webkit-filter: none !important;
                  -webkit-box-shadow: none !important;
                  -moz-box-shadow: none !important;
                ">
                  <div style="font-weight: 600; margin-bottom: 6px; font-size: 14px;">${node.label}</div>
                  ${concept.comment ? `<div style="font-size: 12px; margin-bottom: 6px; opacity: 0.95; line-height: 1.4;">${concept.comment}</div>` : ''}
                  <div style="font-size: 11px; opacity: 0.85; line-height: 1.3;">
                    <div style="margin-bottom: 2px;"><strong>Source:</strong> ${concept.source_context}</div>
                    <div><strong>Connections:</strong> ${node.childCount} children, ${node.parentCount} parents</div>
                  </div>
                </div>`;
              }}
              d3AlphaDecay={0.05}
              d3VelocityDecay={0.3}
              d3ReheatDecay={0.1}
              warmupTicks={100}
              cooldownTicks={200}
              d3ForceConfig={{
                charge: { strength: -120, distanceMax: 400 },
                link: { distance: 50, iterations: 2 },
                center: { x: 0.5, y: 0.5 }
              }}
              enablePointerInteraction={true}
              enableNodeDrag={true}
              enableZoomInteraction={true}
              enablePanInteraction={true}
              minZoom={0.1}
              maxZoom={8}
            />
      </div>
    );
  };

  const renderLineage = (hierarchy: ConceptHierarchy, selectedConcept: OntologyConcept | null = null) => {
    const nodes: Node[] = [];
    const edges: Edge[] = [];
    const allConcepts = Object.values(groupedConcepts).flat();
    
    // Helper function to find concept by IRI or create a minimal concept object
    const findConceptByIri = (iri: string): OntologyConcept | null => {
      // First, check if it's the current concept
      if (hierarchy.concept.iri === iri) {
        return hierarchy.concept;
      }
      
      // Try to find in grouped concepts first
      const foundInGrouped = allConcepts.find(c => c.iri === iri);
      if (foundInGrouped) {
        return foundInGrouped;
      }
      
      // If not found, create a minimal concept object with the IRI
      // Extract label from IRI (last part after # or /)
      const label = iri.split(/[/#]/).pop() || iri;
      
      return {
        iri,
        label,
        concept_type: 'class', // Default to class
        parent_concepts: [],
        child_concepts: [],
        source_context: '', // Will be empty for missing concepts
        description: '',
        comment: '',
        status: 'published',
        owner: '',
        created_at: '',
        updated_at: ''
      } as OntologyConcept;
    };

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

    // Add ALL parent concepts (not just immediate ones)
    const allParentIris = [...new Set([...hierarchy.concept.parent_concepts, ...(hierarchy.parents || [])])]; 
    allParentIris.forEach((parentIri, index) => {
      const parent = findConceptByIri(parentIri);
      if (parent && parent.iri !== hierarchy.concept.iri) {
        const nodeId = parent.iri;
        nodes.push({
          id: nodeId,
          data: { 
            label: parent.label || parent.iri.split(/[/#]/).pop(),
            sourceContext: parent.source_context
          },
          position: { x: 400 + (index - allParentIris.length / 2 + 0.5) * 160, y: centerY - 150 },
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

    // Add ALL child concepts - use selectedConcept if available, fallback to hierarchy.concept
    const conceptForChildren = selectedConcept?.iri === hierarchy.concept.iri ? selectedConcept : hierarchy.concept;
    const allChildIris = [...new Set([...conceptForChildren.child_concepts, ...(hierarchy.children || [])])]; 
    
    allChildIris.forEach((childIri, index) => {
      const child = findConceptByIri(childIri);
      if (child && child.iri !== hierarchy.concept.iri) {
        const nodeId = child.iri;
        nodes.push({
          id: nodeId,
          data: { 
            label: child.label || child.iri.split(/[/#]/).pop(),
            sourceContext: child.source_context
          },
          position: { x: 400 + (index - allChildIris.length / 2 + 0.5) * 160, y: centerY + 150 },
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

    // Add siblings if available (dashed lines FROM selected concept TO siblings)
    if (hierarchy.siblings && hierarchy.siblings.length > 0) {
      hierarchy.siblings.forEach((sibling, index) => {
        // Don't add the selected concept as its own sibling
        if (sibling.iri === hierarchy.concept.iri) return;
        
        const nodeId = sibling.iri;
        nodes.push({
          id: nodeId,
          data: { 
            label: sibling.label || sibling.iri.split(/[/#]/).pop(),
            sourceContext: sibling.source_context
          },
          position: { x: 700 + (index * 180), y: centerY },
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
        
        // Find shared parent for sibling relationships
        const sharedParent = allParentIris.find(parentIri => 
          sibling.parent_concepts && sibling.parent_concepts.includes(parentIri)
        ) || allParentIris[0]; // Fallback to first parent if no shared parent found
        
        if (sharedParent) {
          // Add muted connecting line FROM shared parent TO sibling
          edges.push({
            id: `${sharedParent}-sibling-${nodeId}`,
            source: sharedParent,
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
        }
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
          onInit={(reactFlowInstance) => {
            // Enhanced fit view on initialization
            setTimeout(() => {
              reactFlowInstance.fitView({ 
                padding: 0.15,
                includeHiddenNodes: false,
                minZoom: 0.5,
                maxZoom: 1.2
              });
            }, 100);
          }}
          minZoom={0.5}
          maxZoom={1.5}
          style={{ background: '#ffffff' }}
          defaultEdgeOptions={{
            style: { strokeWidth: 1.5 },
            markerEnd: { type: MarkerType.ArrowClosed }
          }}
          nodesDraggable={false}
          nodesConnectable={false}
          elementsSelectable={true}
          onNodeClick={(_, node) => {
            // Find and select the concept in the tree
            const allConcepts = Object.values(groupedConcepts).flat();
            const concept = allConcepts.find(c => c.iri === node.id);
            if (concept) {
              handleSelectConcept(concept);
            }
          }}
          connectionMode={ConnectionMode.Strict}
        >
          <Controls />
          <Background />
        </ReactFlow>
      </div>
    );
  };

  // Legacy create handlers removed - Phase 0 (read-only ontologies)

  // Removed early return to keep header visible while loading

  return (
    <div className="py-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold mb-6 flex items-center gap-2">
          <Network className="w-8 h-8" /> Semantic Models
        </h1>
        <div className="flex items-center gap-4">
          {stats && (
            <div className="text-sm text-muted-foreground">
              {stats.taxonomies.length} models / {stats.total_concepts + stats.total_properties} terms
            </div>
          )}
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center items-center h-64">
          <Loader2 className="h-12 w-12 animate-spin text-primary" />
        </div>
      ) : error ? (
        <Alert variant="destructive" className="mb-6">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : (
      <div className="grid grid-cols-12 gap-6">
        {/* Left Panel - Taxonomy Tree */}
        <div className="col-span-4 border rounded-lg flex flex-col">
          <div className="p-4 border-b">
            <div className="flex gap-2">
              <div className="relative flex-1">
                <Input
                  type="search"
                  placeholder="Search concepts and terms..."
                  value={searchQuery}
                  onChange={(e) => {
                    const value = e.target.value;
                    setSearchQuery(value);
                    // Debounced search as user types
                    if (searchTimeoutRef.current) {
                      clearTimeout(searchTimeoutRef.current);
                    }
                    searchTimeoutRef.current = setTimeout(() => {
                      handleSearch(value);
                    }, 300);
                  }}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      if (searchTimeoutRef.current) {
                        clearTimeout(searchTimeoutRef.current);
                      }
                      handleSearch();
                    } else if (e.key === 'Escape') {
                      setSearchQuery('');
                      if (searchTimeoutRef.current) {
                        clearTimeout(searchTimeoutRef.current);
                      }
                      handleSearch('');
                    }
                  }}
                />
                {searchQuery && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="absolute right-1 top-1/2 -translate-y-1/2 h-6 w-6 p-0"
                    onClick={() => {
                      setSearchQuery('');
                      if (searchTimeoutRef.current) {
                        clearTimeout(searchTimeoutRef.current);
                      }
                      handleSearch('');
                    }}
                  >
                    ×
                  </Button>
                )}
              </div>
              <Button onClick={() => handleSearch()} size="sm">
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
            <div className="h-full flex flex-col">
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
                  <div className="text-sm text-muted-foreground">
                    {Object.values(groupedConcepts).flat().length} concepts
                  </div>
                </div>
                <div className="flex flex-wrap gap-3 text-xs">
                  <div className="flex items-center gap-1">
                    <div className="w-3 h-3 rounded-full bg-blue-500"></div>
                    <span>Corporate Global</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <div className="w-3 h-3 rounded-full bg-green-500"></div>
                    <span>Manufacturing LOB</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <div className="w-3 h-3 rounded-full bg-red-500"></div>
                    <span>Financial Services LOB</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <div className="w-3 h-3 rounded-full bg-orange-500"></div>
                    <span>Retail Banking Dept</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <div className="w-3 h-3 rounded-full bg-purple-500"></div>
                    <span>Quality Assurance Dept</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <div className="w-3 h-3 rounded-full bg-gray-400"></div>
                    <span>Other Taxonomies</span>
                  </div>
                </div>
              </div>
              <div className="flex-1">
                {renderKnowledgeGraph(Object.values(groupedConcepts).flat())}
              </div>
            </div>
          ) : selectedConcept ? (
            <div className="h-full">
              <div className="p-6 border-b">
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h2 className="text-2xl font-semibold mb-2 flex items-center gap-2">
                      {(() => {
                        switch (selectedConcept.concept_type) {
                          case 'class':
                            return <Layers className="h-6 w-6 shrink-0 text-blue-500" />;
                          case 'concept':
                            return <Layers className="h-6 w-6 shrink-0 text-green-500" />;
                          default:
                            return <Zap className="h-6 w-6 shrink-0 text-yellow-500" />;
                        }
                      })()}
                      {selectedConcept.label || selectedConcept.iri.split(/[/#]/).pop()}
                    </h2>
                    <p className="text-muted-foreground">
                      {selectedConcept.comment || 'No description available'}
                    </p>
                  </div>
                </div>
              </div>

              <div className="p-6 space-y-6">
                {/* Details Section */}
                <div className="border rounded-lg p-4">
                  <ConceptDetails 
                    concept={selectedConcept} 
                    concepts={Object.values(groupedConcepts).flat()}
                    onSelectConcept={handleSelectConcept}
                  />
                </div>

                {/* Hierarchy Section */}
                <div className="border rounded-lg p-4">
                  {selectedHierarchy ? (
                    <div className="space-y-4">
                      <h3 className="text-lg font-semibold">Concept Hierarchy</h3>
                      {renderLineage(selectedHierarchy, selectedConcept)}
                    </div>
                  ) : (
                    <div className="text-muted-foreground">Loading hierarchy...</div>
                  )}
                </div>

                {/* Tagged Assets Section */}
                <div className="border rounded-lg p-4">
                  <TaggedAssetsView concept={selectedConcept} />
                </div>
              </div>
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
      )}
    </div>
  );
}