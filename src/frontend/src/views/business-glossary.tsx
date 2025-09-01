import React, { useState, useEffect } from 'react';
import type { BusinessGlossary, GlossaryTerm } from '@/types/business-glossaries';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Plus, Pencil, Trash2, AlertCircle, FileText, ChevronRight, ChevronDown, Folder, GripVertical, Book } from 'lucide-react';
import { format } from 'date-fns';
import ReactFlow, { Node, Edge, Background, MarkerType, Controls } from 'reactflow';
import { DndContext, DragEndEvent, DragOverlay, DragStartEvent, useSensor, useSensors, PointerSensor } from '@dnd-kit/core';
import { SortableContext, verticalListSortingStrategy, useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import 'reactflow/dist/style.css';
import useBreadcrumbStore from '@/stores/breadcrumb-store';

interface SortableTreeItemProps {
  item: BusinessGlossary | GlossaryTerm;
  level: number;
  selectedId: string | null;
  onSelect: (id: string) => void;
  isExpanded: boolean;
  onToggle: () => void;
  isDraggable?: boolean;
  expandedIds: Set<string>;
  toggleExpanded: (id: string) => void;
}

const SortableTreeItem: React.FC<SortableTreeItemProps> = ({ 
  item, 
  level, 
  selectedId, 
  onSelect, 
  isExpanded, 
  onToggle,
  isDraggable = false,
  expandedIds,
  toggleExpanded
}) => {
  const isGlossary = 'terms' in item;
  const terms = isGlossary ? Object.values((item as BusinessGlossary).terms) : [];
  const children = isGlossary ? (item as BusinessGlossary).children || [] : [];
  const hasChildren = isGlossary && (terms.length > 0 || children.length > 0);

  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging
  } = useSortable({
    id: item.id,
    disabled: !isDraggable
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
    paddingLeft: `${level * 16 + 8}px`
  };

  return (
    <div ref={setNodeRef} style={style} className="select-none">
      <div
        className={`
          flex items-center gap-2 px-2 py-1.5 rounded-md cursor-pointer
          hover:bg-accent hover:text-accent-foreground
          ${selectedId === item.id ? 'bg-accent text-accent-foreground' : ''}
          ${isDragging ? 'ring-2 ring-primary' : ''}
        `}
        onClick={() => onSelect(item.id)}
        {...(isDraggable ? { ...attributes, ...listeners } : {})}
      >
        {isDraggable && (
          <button className="p-1 hover:bg-accent/50 rounded-sm transition-colors cursor-grab">
            <GripVertical className="h-4 w-4 shrink-0 text-muted-foreground" />
          </button>
        )}
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
          {isGlossary ? (
            <Folder className="h-4 w-4 shrink-0 text-blue-500" />
          ) : (
            <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
          )}
          <span className="truncate text-sm">{item.name}</span>
        </div>
      </div>
      {isExpanded && hasChildren && (
        <div className="mt-1">
          {/* Render child glossaries first */}
          {children.map((child: BusinessGlossary | GlossaryTerm) => (
            <SortableTreeItem
              key={child.id}
              item={child}
              level={level + 1}
              selectedId={selectedId}
              onSelect={onSelect}
              isExpanded={expandedIds.has(child.id)}
              onToggle={() => toggleExpanded(child.id)}
              isDraggable={true}
              expandedIds={expandedIds}
              toggleExpanded={toggleExpanded}
            />
          ))}
          {/* Then render terms */}
          {terms.map((term: GlossaryTerm) => (
            <SortableTreeItem
              key={term.id}
              item={term}
              level={level + 1}
              selectedId={selectedId}
              onSelect={onSelect}
              isExpanded={false}
              onToggle={() => {}}
              isDraggable={false}
              expandedIds={expandedIds}
              toggleExpanded={toggleExpanded}
            />
          ))}
        </div>
      )}
    </div>
  );
};

interface InfoPanelProps {
  metadata: BusinessGlossary | GlossaryTerm;
  type: 'glossary' | 'term';
}

const InfoPanel: React.FC<InfoPanelProps> = ({ metadata, type }) => {
  const formatDate = (dateStr: string) => {
    return format(new Date(dateStr), 'PPP p');
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

      <DetailItem label="Owner" value={metadata.owner} />
      <DetailItem label="Status" value={<Badge variant="outline">{metadata.status}</Badge>} />
      <DetailItem label="Domain" value={metadata.domain} />

      {type === 'glossary' && (
        <>
          <DetailItem label="Scope" value={(metadata as BusinessGlossary).scope} />
          <DetailItem label="Org Unit" value={(metadata as BusinessGlossary).org_unit} />
        </>
      )}

      {(metadata as GlossaryTerm).abbreviation && (
        <DetailItem label="Abbreviation" value={(metadata as GlossaryTerm).abbreviation} />
      )}

      <div className="mb-4">
        <div className="text-sm text-muted-foreground mb-1">Tags</div>
        <div className="flex flex-wrap gap-1">
          {metadata.tags.map((tag: string) => (
            <Badge key={tag} variant="secondary" className="text-xs">
              {tag}
            </Badge>
          ))}
        </div>
      </div>

      {(metadata as GlossaryTerm).examples?.length > 0 && (
        <div className="mb-4">
          <div className="text-sm text-muted-foreground mb-1">Examples</div>
          <ul className="list-disc list-inside space-y-1">
            {(metadata as GlossaryTerm).examples.map((example: string, index: number) => (
              <li key={index} className="text-sm">
                {example}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="border-t pt-4">
        <DetailItem label="Created" value={formatDate(metadata.created_at)} />
        <DetailItem label="Last Updated" value={formatDate(metadata.updated_at)} />
      </div>
    </div>
  );
};

export default function BusinessGlossary() {
  const [glossaries, setGlossaries] = useState<BusinessGlossary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const [_, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeTab, setActiveTab] = useState('details');
  const [openDialog, setOpenDialog] = useState(false);
  const [dialogType, setDialogType] = useState<'glossary' | 'term'>('glossary');
  const [activeId, setActiveId] = useState<string | null>(null);

  // Form state
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [scope, setScope] = useState('');
  const [orgUnit, setOrgUnit] = useState('');
  const [domain, setDomain] = useState('');
  const [owner, setOwner] = useState('');
  const [tags, setTags] = useState('');
  const [status, setStatus] = useState('draft');

  // Add new state for filtered glossaries
  const [filteredGlossaries, setFilteredGlossaries] = useState<BusinessGlossary[]>([]);

  const setStaticSegments = useBreadcrumbStore((state) => state.setStaticSegments);
  const setDynamicTitle = useBreadcrumbStore((state) => state.setDynamicTitle);

  // Add sensors for drag and drop
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    })
  );

  useEffect(() => {
    fetchGlossaries();
    // Set breadcrumbs
    setStaticSegments([]);
    setDynamicTitle('Business Glossary');

    // Cleanup breadcrumbs on unmount
    return () => {
        setStaticSegments([]);
        setDynamicTitle(null);
    };
  }, [setStaticSegments, setDynamicTitle]);

  const fetchGlossaries = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/business-glossaries');
      if (!response.ok) throw new Error('Failed to fetch glossaries');
      const data = await response.json();
      setGlossaries(data.glossaries || []);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch glossaries');
    } finally {
      setLoading(false);
    }
  };

  const getSelectedItem = () => {
    if (!selectedId) return null;

    for (const glossary of glossaries) {
      if (glossary.id === selectedId) {
        return { type: 'glossary' as const, metadata: glossary };
      }
      const term = glossary.terms[selectedId];
      if (term) {
        return { type: 'term' as const, metadata: term };
      }
    }
    return null;
  };

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
    const formData = {
      name,
      description,
      domain,
      owner,
      tags: tags.split(',').map(tag => tag.trim()),
      status,
      ...(dialogType === 'glossary' ? {
        scope,
        org_unit: orgUnit,
      } : {})
    };

    try {
      const response = await fetch('/api/business-glossaries', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });
      if (!response.ok) throw new Error(`Failed to create ${dialogType}`);
      await fetchGlossaries();
      setOpenDialog(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : `Failed to create ${dialogType}`);
    }
  };

  const handleDelete = async () => {
    const selectedItem = getSelectedItem();
    if (!selectedItem) return;

    if (!confirm(`Are you sure you want to delete this ${selectedItem.type}?`)) return;

    try {
      const response = await fetch(
        selectedItem.type === 'glossary'
          ? `/api/business-glossaries/${selectedItem.metadata.id}`
          : `/api/business-glossaries/${(selectedItem.metadata as GlossaryTerm).source_glossary_id}/terms/${selectedItem.metadata.id}`,
        { method: 'DELETE' }
      );
      if (!response.ok) throw new Error(`Failed to delete ${selectedItem.type}`);
      await fetchGlossaries();
      setSelectedId(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : `Failed to delete ${selectedItem.type}`);
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

  const selectedItem = getSelectedItem();

  const renderLineage = (metadata: BusinessGlossary | GlossaryTerm) => {
    const nodes: Node[] = [];
    const edges: Edge[] = [];

    // Add current item as center node
    nodes.push({
      id: metadata.id,
      data: { label: metadata.name },
      position: { x: 250, y: 200 },
      type: 'default',
      style: { 
        background: '#fff',
        border: '2px solid #1976d2',
        borderRadius: '4px',
        padding: '8px',
        fontSize: '12px',
        width: 150,
        textAlign: 'center'
      }
    });

    // Add parent glossaries as upstream nodes
    if ('source_glossary_id' in metadata) {
      const parentGlossary = glossaries.find(g => g.id === metadata.source_glossary_id);
      if (parentGlossary) {
        nodes.push({
          id: parentGlossary.id,
          data: { 
            label: (
              <div className="text-xs">
                <div className="text-muted-foreground text-[10px]">glossary</div>
                <div className="text-sm">{parentGlossary.name}</div>
              </div>
            )
          },
          position: { x: 250, y: 50 },
          type: 'default',
          style: { 
            background: '#e3f2fd',
            borderRadius: '4px',
            padding: '6px',
            width: 150,
            textAlign: 'center'
          }
        });
        edges.push({
          id: `${parentGlossary.id}-${metadata.id}`,
          source: parentGlossary.id,
          target: metadata.id,
          type: 'smoothstep'
        });
      }
    } else {
      // For glossaries, show parent glossaries
      const glossary = metadata as BusinessGlossary;
      glossary.parent_glossary_ids.forEach((parentId: string, index: number) => {
        const parent = glossaries.find(g => g.id === parentId);
        if (parent) {
          nodes.push({
            id: parent.id,
            data: { 
              label: (
                <div className="text-xs">
                  <div className="text-muted-foreground text-[10px]">glossary</div>
                  <div className="text-sm">{parent.name}</div>
                </div>
              )
            },
            position: { x: 150 + (index * 200), y: 50 },
            type: 'default',
            style: { 
              background: '#e3f2fd',
              borderRadius: '8px',
              padding: '10px'
            }
          });
          edges.push({
            id: `${parent.id}-${metadata.id}`,
            source: parent.id,
            target: metadata.id,
            type: 'smoothstep'
          });
        }
      });
    }

    // Add tagged assets as downstream nodes
    const taggedAssets = metadata.taggedAssets || [];
    taggedAssets.forEach((asset: { id: string; name: string; type?: string }, index: number) => {
      nodes.push({
        id: asset.id,
        type: asset.type || 'asset',
        data: { 
          label: (
            <div className="text-xs">
              <div className="text-muted-foreground text-[10px]">{asset.type}</div>
              <div className="text-sm">{asset.name}</div>
            </div>
          )
        },
        position: { x: 100 + (index * 175), y: 350 },
        style: { 
          background: '#f5f5f5',
          borderRadius: '4px',
          padding: '6px',
          width: 150,
          textAlign: 'center'
        }
      });
      edges.push({
        id: `${metadata.id}-${asset.id}`,
        source: metadata.id,
        target: asset.id,
        type: 'smoothstep'
      });
    });

    return (
      <div className="h-[500px] border rounded-lg">
        <ReactFlow 
          nodes={nodes} 
          edges={edges}
          fitView
          defaultViewport={{ x: 0, y: 0, zoom: 1 }}
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

  const handleSearch = (query: string) => {
    setSearchQuery(query);
    // Filter glossaries and terms based on the search query
    const filteredGlossaries = glossaries.map(glossary => ({
      ...glossary,
      terms: Object.fromEntries(
        Object.entries(glossary.terms).filter(([_, term]) => 
          term.name.toLowerCase().includes(query.toLowerCase()) ||
          term.definition?.toLowerCase().includes(query.toLowerCase())
        )
      )
    })).filter(glossary => 
      glossary.name.toLowerCase().includes(query.toLowerCase()) ||
      glossary.description.toLowerCase().includes(query.toLowerCase()) ||
      Object.keys(glossary.terms).length > 0
    );

    // Update the tree view with filtered results
    setFilteredGlossaries(filteredGlossaries);
  };

  // Update filtered glossaries when glossaries change
  useEffect(() => {
    setFilteredGlossaries(glossaries);
  }, [glossaries]);

  // Function to build the glossary tree
  const buildGlossaryTree = (glossaries: BusinessGlossary[]) => {
    const glossaryMap = new Map<string, BusinessGlossary>();
    const rootGlossaries: BusinessGlossary[] = [];

    // First pass: create a map of all glossaries
    glossaries.forEach(glossary => {
      glossaryMap.set(glossary.id, { ...glossary, children: [] });
    });

    // Second pass: build the tree structure
    glossaries.forEach(glossary => {
      const currentGlossary = glossaryMap.get(glossary.id)!;
      if (!glossary.parent_glossary_ids || glossary.parent_glossary_ids.length === 0) {
        rootGlossaries.push(currentGlossary);
      } else {
        // Add to all parent's children
        glossary.parent_glossary_ids.forEach((parentId: string) => {
          const parent = glossaryMap.get(parentId);
          if (parent) {
            if (!parent.children) {
              parent.children = [];
            }
            // Only add if not already in the children array
            if (!parent.children.some((child: BusinessGlossary | GlossaryTerm) => child.id === currentGlossary.id)) {
              parent.children.push(currentGlossary);
            }
          }
        });
      }
    });

    return rootGlossaries;
  };

  // Function to flatten the tree for drag and drop
  const flattenGlossaryTree = (glossaries: BusinessGlossary[]): BusinessGlossary[] => {
    return glossaries.reduce((acc: BusinessGlossary[], glossary) => {
      acc.push(glossary);
      if (glossary.children) {
        acc.push(...flattenGlossaryTree(glossary.children));
      }
      return acc;
    }, []);
  };

  const handleDragStart = (event: DragStartEvent) => {
    setActiveId(event.active.id as string);
  };

  const handleDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) {
      setActiveId(null);
      return;
    }

    try {
      const response = await fetch(`/api/business-glossaries/${active.id}/move`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          target_id: over.id,
          position: 'after'
        }),
      });

      if (!response.ok) throw new Error('Failed to move glossary');
      await fetchGlossaries();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to move glossary');
    } finally {
      setActiveId(null);
    }
  };

  // Update the tree view rendering
  const renderTreeView = () => {
    const treeGlossaries = buildGlossaryTree(filteredGlossaries);
    const flatGlossaries = flattenGlossaryTree(treeGlossaries);

    return (
      <DndContext
        sensors={sensors}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
      >
        <SortableContext
          items={flatGlossaries.map(g => g.id)}
          strategy={verticalListSortingStrategy}
        >
          <div className="p-2">
            {treeGlossaries.map((glossary) => (
              <SortableTreeItem
                key={glossary.id}
                item={glossary}
                level={0}
                selectedId={selectedId}
                onSelect={setSelectedId}
                isExpanded={expandedIds.has(glossary.id)}
                onToggle={() => toggleExpanded(glossary.id)}
                isDraggable={true}
                expandedIds={expandedIds}
                toggleExpanded={toggleExpanded}
              />
            ))}
          </div>
        </SortableContext>
        <DragOverlay>
          {activeId ? (
            <div className="opacity-50">
              <SortableTreeItem
                item={flatGlossaries.find(g => g.id === activeId)!}
                level={0}
                selectedId={selectedId}
                onSelect={() => {}}
                isExpanded={false}
                onToggle={() => {}}
                isDraggable={true}
                expandedIds={expandedIds}
                toggleExpanded={toggleExpanded}
              />
            </div>
          ) : null}
        </DragOverlay>
      </DndContext>
    );
  };

  return (
    <div className="py-6">

      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold mb-6 flex items-center gap-2">
          <Book className="w-8 h-8" /> Business Glossary
        </h1>
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

      {error && (
        <Alert variant="destructive" className="mb-6">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="grid grid-cols-12 gap-6">
        {/* Left Panel - Tree View */}
        <div className="col-span-3 border rounded-lg">
          <div className="p-4 border-b">
            <Input
              type="search"
              placeholder="Search glossaries and terms..."
              value={searchQuery}
              onChange={(e) => handleSearch(e.target.value)}
            />
          </div>
          <ScrollArea className="h-[calc(100vh-300px)]">
            {renderTreeView()}
          </ScrollArea>
        </div>

        {/* Right Panel - Details */}
        <div className="col-span-9 border rounded-lg">
          {selectedItem ? (
            <div className="h-full">
              <div className="p-6 border-b">
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h2 className="text-2xl font-semibold mb-2">{selectedItem.metadata.name}</h2>
                    <p className="text-muted-foreground">
                      {selectedItem.type === 'glossary'
                        ? (selectedItem.metadata as BusinessGlossary).description
                        : (selectedItem.metadata as GlossaryTerm).definition}
                    </p>
                  </div>
                  <div className="flex space-x-2">
                    <Button variant="ghost" size="sm" onClick={handleDelete}>
                      <Trash2 className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="sm">
                      <Pencil className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </div>

              <Tabs value={activeTab} onValueChange={setActiveTab} className="p-6">
                <TabsList>
                  <TabsTrigger value="details">Details</TabsTrigger>
                  <TabsTrigger value="tagged">Tagged Items</TabsTrigger>
                  {selectedItem.type === 'term' && (
                    <TabsTrigger value="lineage">Lineage</TabsTrigger>
                  )}
                </TabsList>
                <TabsContent value="details">
                  <InfoPanel metadata={selectedItem.metadata} type={selectedItem.type} />
                </TabsContent>
                <TabsContent value="tagged">
                  {selectedItem.metadata.taggedAssets?.length ? (
                    <div className="space-y-4">
                      {selectedItem.metadata.taggedAssets.map((asset: { id: string; name: string; type?: string; path?: string }) => (
                        <div key={asset.id} className="p-4 border rounded-lg">
                          <div className="font-medium">{asset.name}</div>
                          {asset.type && <div className="text-sm text-muted-foreground">{asset.type}</div>}
                          {asset.path && <div className="text-sm text-muted-foreground">{asset.path}</div>}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-muted-foreground">No tagged items found</div>
                  )}
                </TabsContent>
                {selectedItem.type === 'term' && (
                  <TabsContent value="lineage">
                    {renderLineage(selectedItem.metadata)}
                  </TabsContent>
                )}
              </Tabs>
            </div>
          ) : (
            <div className="h-full flex items-center justify-center text-muted-foreground">
              Select a glossary or term to view details
            </div>
          )}
        </div>
      </div>

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