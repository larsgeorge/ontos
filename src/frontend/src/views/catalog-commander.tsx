import React, { useEffect, useState } from 'react';
import { TreeView } from '@/components/ui/tree-view';
import {
  Folder,
  FolderOpen,
  Table,
  Layout,
  FolderKanban,
  Pencil,
  Trash2,
  Eye,
  ArrowRight,
  ArrowLeft,
  Info,
  Loader2,
  MessageSquare,
  PanelRightClose,
  PanelRightOpen,
  Copy,
  GitCompare
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { DataTable } from '@/components/ui/data-table';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { usePermissions } from '@/stores/permissions-store';
import { FeatureAccessLevel } from '@/types/feature-access-levels';
import useBreadcrumbStore from '@/stores/breadcrumb-store';
import { CommentTimeline } from '@/components/comments/comment-timeline';
import { cn } from '@/lib/utils';
import EntityMetadataPanel from '@/components/metadata/entity-metadata-panel';

interface CatalogItem {
  id: string;
  name: string;
  type: 'catalog' | 'schema' | 'table' | 'view';
  children: CatalogItem[];
  hasChildren: boolean;
}

interface TreeViewItem {
  id: string;
  name: string;
  icon?: React.ReactNode;
  children?: TreeViewItem[];
  onClick?: () => void;
  selected?: boolean;
  expanded?: boolean;
  onExpand?: () => void;
  hasChildren: boolean;
}

interface DatasetContent {
  schema: Array<{ name: string; type: string; nullable: boolean }>;
  data: any[];
  total_rows: number;
}

interface Estate {
  id: string;
  name: string;
  description: string;
  workspace_url: string;
  cloud_type: string;
  metastore_name: string;
  is_enabled: boolean;
}

type RightPanelMode = 'hidden' | 'dual-tree' | 'info' | 'comments';

const CatalogCommander: React.FC = () => {
  const [searchInput, setSearchInput] = useState('');
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [selectedItems, setSelectedItems] = useState<CatalogItem[]>([]);
  const [sourceItems, setSourceItems] = useState<CatalogItem[]>([]);
  const [targetItems, setTargetItems] = useState<CatalogItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [viewDialogOpen, setViewDialogOpen] = useState(false);
  const [selectedDataset, setSelectedDataset] = useState<string | null>(null);
  const [datasetContent, setDatasetContent] = useState<DatasetContent | null>(null);
  const [loadingData, setLoadingData] = useState(false);
  const [selectedObjectInfo, setSelectedObjectInfo] = useState<any>(null);
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set());
  const [loadingNodes, setLoadingNodes] = useState<Set<string>>(new Set());
  const [estates, setEstates] = useState<Estate[]>([]);
  const [selectedSourceEstate, setSelectedSourceEstate] = useState<string>('');
  const [selectedTargetEstate, setSelectedTargetEstate] = useState<string>('');
  const [rightPanelMode, setRightPanelMode] = useState<RightPanelMode>('info');

  // Draggable divider state - default to 420px, load from localStorage
  const [leftPaneWidth, setLeftPaneWidth] = useState<number>(() => {
    const stored = localStorage.getItem('catalog-commander-split');
    return stored ? parseInt(stored, 10) : 420;
  });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStartX, setDragStartX] = useState(0);
  const [dragStartWidth, setDragStartWidth] = useState(0);

  const { hasPermission } = usePermissions();
  const canPerformWriteActions = hasPermission('catalog-commander', FeatureAccessLevel.FULL);

  const setStaticSegments = useBreadcrumbStore((state) => state.setStaticSegments);
  const setDynamicTitle = useBreadcrumbStore((state) => state.setDynamicTitle);

  const handleViewDataset = async (path: string) => {
    setSelectedDataset(path);
    setLoadingData(true);
    setViewDialogOpen(true);

    try {
      const response = await fetch(`/api/catalogs/dataset/${encodeURIComponent(path)}`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setDatasetContent(data);
    } catch (err) {
      console.error('Error loading dataset:', err);
      setError(err instanceof Error ? err.message : 'Failed to load dataset');
    } finally {
      setLoadingData(false);
    }
  };

  const handleOperation = (operation: string) => {
    console.log(`${operation} operation triggered`);
  };

  const getSelectedNodeDetails = () => {
    if (!selectedObjectInfo) return null;
    const node = findNode(sourceItems, selectedObjectInfo.id) || 
                 findNode(targetItems, selectedObjectInfo.id);
    return node;
  };

  const findNode = (items: CatalogItem[], id: string): CatalogItem | null => {
    for (const item of items) {
      if (item.id === id) return item;
      if (item.children) {
        const found = findNode(item.children, id);
        if (found) return found;
      }
    }
    return null;
  };

  const updateNodeChildren = (items: CatalogItem[], nodeId: string, children: CatalogItem[]): CatalogItem[] => {
    return items.map(item => {
      if (item.id === nodeId) {
        return { ...item, children };
      }
      if (item.children) {
        return { ...item, children: updateNodeChildren(item.children, nodeId, children) };
      }
      return item;
    });
  };

  const fetchChildren = async (nodeId: string, nodeType: string): Promise<CatalogItem[]> => {
    try {
      let url = '';
      if (nodeType === 'catalog') {
        url = `/api/catalogs/${nodeId}/schemas`;
      } else if (nodeType === 'schema') {
        const [catalogName, schemaName] = nodeId.split('.');
        url = `/api/catalogs/${catalogName}/schemas/${schemaName}/tables`;
      }
      
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`Failed to fetch children: ${response.status}`);
      }
      const data = await response.json();
      return data;
    } catch (err) {
      console.error('Error fetching children:', err);
      return [];
    }
  };

  const handleNodeExpand = async (nodeId: string, nodeType: string, isSource: boolean) => {
    if (loadingNodes.has(nodeId)) return;

    setLoadingNodes(prev => new Set(prev).add(nodeId));
    try {
      const children = await fetchChildren(nodeId, nodeType);
      if (isSource) {
        setSourceItems(prev => {
          const updated = updateNodeChildren(prev, nodeId, children);
          return updated;
        });
      } else {
        setTargetItems(prev => {
          const updated = updateNodeChildren(prev, nodeId, children);
          return updated;
        });
      }
      setExpandedNodes(prev => {
        const next = new Set(prev);
        next.add(nodeId);
        return next;
      });
    } catch (err) {
      console.error('Error expanding node:', err);
      setExpandedNodes(prev => {
        const next = new Set(prev);
        next.delete(nodeId);
        return next;
      });
    } finally {
      setLoadingNodes(prev => {
        const next = new Set(prev);
        next.delete(nodeId);
        return next;
      });
    }
  };

  useEffect(() => {
    fetchCatalogs();
    fetchEstates();
    setStaticSegments([]);
    setDynamicTitle('Catalog Commander');

    return () => {
        setStaticSegments([]);
        setDynamicTitle(null);
    };
  }, [setStaticSegments, setDynamicTitle]);

  const fetchEstates = async () => {
    try {
      const response = await fetch('/api/estates');
      if (!response.ok) {
        throw new Error(`Failed to fetch estates: ${response.status}`);
      }
      const data = await response.json();
      setEstates(data || []);
    } catch (err) {
      console.error('Error fetching estates:', err);
    }
  };

  const fetchCatalogs = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const response = await fetch('/api/catalogs');
      if (!response.ok) {
        throw new Error(`Failed to fetch catalogs: ${response.status}`);
      }
      const data = await response.json();
      setSourceItems(data);
      setTargetItems(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch catalogs');
    } finally {
      setIsLoading(false);
    }
  };

  const handleItemSelect = (item: CatalogItem) => {
    setSelectedItems([item]);
    setSelectedObjectInfo({ id: item.id });
  };

  // Draggable divider handlers
  const handleMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);
    setDragStartX(e.clientX);
    setDragStartWidth(leftPaneWidth);
  };

  const handleMouseMove = React.useCallback((e: MouseEvent) => {
    if (!isDragging) return;

    const delta = e.clientX - dragStartX;
    const newWidth = Math.max(300, Math.min(800, dragStartWidth + delta));
    setLeftPaneWidth(newWidth);
  }, [isDragging, dragStartX, dragStartWidth]);

  const handleMouseUp = React.useCallback(() => {
    if (isDragging) {
      setIsDragging(false);
      localStorage.setItem('catalog-commander-split', leftPaneWidth.toString());
    }
  }, [isDragging, leftPaneWidth]);

  // Add mouse event listeners for dragging
  React.useEffect(() => {
    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      return () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [isDragging, handleMouseMove, handleMouseUp]);

  const getIcon = (type: string) => {
    switch (type) {
      case 'catalog':
        return <Folder className="h-4 w-4 text-blue-500" />;
      case 'schema':
        return <FolderOpen className="h-4 w-4 text-green-500" />;
      case 'table':
        return <Table className="h-4 w-4 text-orange-500" />;
      case 'view':
        return <Layout className="h-4 w-4 text-purple-500" />;
      default:
        return null;
    }
  };

  const renderTree = (items: CatalogItem[], isSource: boolean): TreeViewItem[] => {
    return items.map(item => {
      const hasChildren = item.hasChildren || (item.children && item.children.length > 0);
      
      const treeItem = {
        id: item.id,
        name: item.name,
        icon: getIcon(item.type),
        children: item.children ? renderTree(item.children, isSource) : [],
        onClick: () => {
          handleItemSelect(item);
        },
        selected: selectedItems.some(selected => selected.id === item.id),
        expanded: expandedNodes.has(item.id),
        onExpand: () => {
          handleNodeExpand(item.id, item.type, isSource);
        },
        loading: loadingNodes.has(item.id),
        hasChildren: hasChildren
      };
      return treeItem;
    });
  };

  if (isLoading) {
    return (
      <div className="container py-6 flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-screen">
        <div className="text-red-500 mb-4">{error}</div>
        <Button onClick={fetchCatalogs}>Retry</Button>
      </div>
    );
  }

  return (
    <div className="py-6">
      <h1 className="text-3xl font-bold mb-6 flex items-center gap-2">
        <FolderKanban className="w-8 h-8" /> Catalog Commander
      </h1>

      {/* Action Toolbar */}
      <div className="flex justify-between items-center mb-4">
        <div className="flex gap-2">
          <Button
            onClick={() => handleViewDataset(getSelectedNodeDetails()?.id || '')}
            disabled={!selectedItems.length || getSelectedNodeDetails()?.type !== 'table'}
            variant="outline"
            size="sm"
            className="h-9"
          >
            <Eye className="h-4 w-4 mr-2" />
            View Data
          </Button>
          {canPerformWriteActions && (
            <>
              <Button
                onClick={() => handleOperation('move')}
                variant="outline"
                size="sm"
                className="h-9"
              >
                <ArrowRight className="h-4 w-4 mr-2" />
                Move
              </Button>
              <Button
                onClick={() => handleOperation('delete')}
                variant="outline"
                size="sm"
                className="h-9 text-destructive hover:text-destructive hover:bg-destructive/10"
              >
                <Trash2 className="h-4 w-4 mr-2" />
                Delete
              </Button>
              <Button
                onClick={() => handleOperation('rename')}
                variant="outline"
                size="sm"
                className="h-9"
              >
                <Pencil className="h-4 w-4 mr-2" />
                Rename
              </Button>
            </>
          )}
        </div>

        {/* Right Panel Mode Toggle */}
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1 border rounded-lg p-1 bg-muted/30">
            <Button
              variant={rightPanelMode === 'info' ? 'secondary' : 'ghost'}
              size="sm"
              onClick={() => setRightPanelMode(rightPanelMode === 'info' ? 'hidden' : 'info')}
              className={cn(
                "h-8 px-3",
                rightPanelMode === 'info' && "shadow-sm"
              )}
            >
              <Info className="h-4 w-4 mr-1.5" />
              Info
            </Button>
            {canPerformWriteActions && (
              <Button
                variant={rightPanelMode === 'dual-tree' ? 'secondary' : 'ghost'}
                size="sm"
                onClick={() => setRightPanelMode(rightPanelMode === 'dual-tree' ? 'hidden' : 'dual-tree')}
                className={cn(
                  "h-8 px-3",
                  rightPanelMode === 'dual-tree' && "shadow-sm"
                )}
              >
                <GitCompare className="h-4 w-4 mr-1.5" />
                Operations
              </Button>
            )}
            <Button
              variant={rightPanelMode === 'comments' ? 'secondary' : 'ghost'}
              size="sm"
              onClick={() => setRightPanelMode(rightPanelMode === 'comments' ? 'hidden' : 'comments')}
              className={cn(
                "h-8 px-3",
                rightPanelMode === 'comments' && "shadow-sm"
              )}
            >
              <MessageSquare className="h-4 w-4 mr-1.5" />
              Comments
            </Button>
          </div>
          {rightPanelMode !== 'hidden' && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setRightPanelMode('hidden')}
              className="h-8 w-8 p-0"
            >
              <PanelRightClose className="h-4 w-4" />
            </Button>
          )}
        </div>
      </div>

      {/* Main Layout: Resizable Left Tree + Variable Right Panel */}
      <div className="flex gap-4 h-[calc(100vh-12rem)]">
        {/* Resizable Left Tree View with horizontal and vertical scrolling */}
        <Card
          className="flex-shrink-0 flex flex-col h-full shadow-sm border-border/50"
          style={{ width: `${leftPaneWidth}px` }}
        >
          <CardHeader className="flex-none pb-3 border-b">
            <CardTitle className="text-lg font-semibold">Catalog Browser</CardTitle>
          </CardHeader>
          <CardContent className="flex-1 flex flex-col h-full min-h-0 p-4 space-y-3">
            {estates.length > 1 && (
              <div className="space-y-2 flex-none">
                <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Metastore</Label>
                <Select
                  value={selectedSourceEstate}
                  onValueChange={setSelectedSourceEstate}
                >
                  <SelectTrigger className="h-9">
                    <SelectValue placeholder="Select Estate" />
                  </SelectTrigger>
                  <SelectContent>
                    {estates.map(estate => (
                      <SelectItem key={estate.id} value={estate.id}>
                        <div className="flex items-center gap-2">
                          <span>{estate.name}</span>
                          <span className="text-xs text-muted-foreground">({estate.metastore_name})</span>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}
            <Input
              placeholder="Filter catalogs..."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              className="h-9 flex-none"
            />
            <div className="flex-1 min-h-0 overflow-auto border rounded-md bg-muted/20">
              <div className="min-w-max text-xs leading-none [&_*]:!leading-none [&_button]:!py-0 [&_button]:!px-1 [&_button]:!h-4 [&_button]:!min-h-4 [&_button]:!my-0 [&_ul]:!space-y-0 [&_ul]:!gap-0 [&_li]:!my-0 [&_li]:!py-0 [&_div]:!leading-none">
                <TreeView
                  data={renderTree(sourceItems, true)}
                  className="p-1 !space-y-0 !gap-0"
                  onSelectChange={(item) => handleItemSelect(item as unknown as CatalogItem)}
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Draggable Divider - Only visible on hover */}
        {rightPanelMode !== 'hidden' && (
          <div
            className={cn(
              "w-1 bg-transparent hover:bg-border cursor-col-resize transition-colors flex-shrink-0 -mx-2",
              isDragging && "bg-primary"
            )}
            onMouseDown={handleMouseDown}
            title="Drag to resize"
          />
        )}

        {/* Variable Right Panel */}
        {rightPanelMode !== 'hidden' && (
          <>
            {/* Operations Panel: Transfer Arrows + Target Tree */}
            {rightPanelMode === 'dual-tree' && canPerformWriteActions && (
              <>
                <div className="flex flex-col justify-center gap-2">
                  <Button
                    onClick={() => handleOperation('copy')}
                    variant="outline"
                    size="icon"
                    className="h-10 w-10 hover:bg-primary hover:text-primary-foreground transition-colors"
                    title="Copy to target"
                  >
                    <Copy className="h-4 w-4" />
                  </Button>
                  <Button
                    onClick={() => handleOperation('move')}
                    variant="outline"
                    size="icon"
                    className="h-10 w-10 hover:bg-primary hover:text-primary-foreground transition-colors"
                    title="Move to target"
                  >
                    <ArrowRight className="h-4 w-4" />
                  </Button>
                  <Button
                    onClick={() => handleOperation('move')}
                    variant="outline"
                    size="icon"
                    className="h-10 w-10 hover:bg-primary hover:text-primary-foreground transition-colors"
                    title="Move from target"
                  >
                    <ArrowLeft className="h-4 w-4" />
                  </Button>
                </div>

                <Card className="flex-1 flex flex-col h-full min-w-0 shadow-sm border-border/50">
                  <CardHeader className="flex-none pb-3 border-b">
                    <CardTitle className="text-lg font-semibold">Target</CardTitle>
                  </CardHeader>
                  <CardContent className="flex-1 flex flex-col h-full min-h-0 p-4 space-y-3">
                    {estates.length > 1 && (
                      <div className="space-y-2 flex-none">
                        <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Metastore</Label>
                        <Select
                          value={selectedTargetEstate}
                          onValueChange={setSelectedTargetEstate}
                        >
                          <SelectTrigger className="h-9">
                            <SelectValue placeholder="Select Estate" />
                          </SelectTrigger>
                          <SelectContent>
                            {estates.map(estate => (
                              <SelectItem key={estate.id} value={estate.id}>
                                <div className="flex items-center gap-2">
                                  <span>{estate.name}</span>
                                  <span className="text-xs text-muted-foreground">({estate.metastore_name})</span>
                                </div>
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                    )}
                    <Input
                      placeholder="Filter catalogs..."
                      value={searchInput}
                      onChange={(e) => setSearchInput(e.target.value)}
                      className="h-9 flex-none"
                    />
                    <div className="flex-1 min-h-0 overflow-auto border rounded-md bg-muted/20">
                      <div className="min-w-max text-xs leading-none [&_*]:!leading-none [&_button]:!py-0 [&_button]:!px-1 [&_button]:!h-4 [&_button]:!min-h-4 [&_button]:!my-0 [&_ul]:!space-y-0 [&_ul]:!gap-0 [&_li]:!my-0 [&_li]:!py-0 [&_div]:!leading-none">
                        <TreeView
                          data={renderTree(targetItems, false)}
                          className="p-1 !space-y-0 !gap-0"
                          onSelectChange={(item) => handleItemSelect(item as unknown as CatalogItem)}
                        />
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </>
            )}

            {/* Info Panel */}
            {rightPanelMode === 'info' && (
              <Card className="flex-1 flex flex-col h-full min-w-0 shadow-sm border-border/50">
                <CardHeader className="flex-none pb-3 border-b">
                  <CardTitle className="text-lg font-semibold">Object Information</CardTitle>
                </CardHeader>
                <CardContent className="flex-1 overflow-auto p-4">
                  {selectedObjectInfo ? (
                    <div className="space-y-4">
                      {/* Basic Information Card */}
                      <Card>
                        <CardHeader className="pb-3">
                          <CardTitle className="text-sm font-medium flex items-center gap-2">
                            <Info className="h-4 w-4" />
                            Basic Information
                          </CardTitle>
                        </CardHeader>
                        <CardContent>
                          {(() => {
                            const node = getSelectedNodeDetails();
                            return node ? (
                              <div className="space-y-3">
                                <div className="grid grid-cols-3 gap-2 items-center">
                                  <span className="text-sm text-muted-foreground">Name:</span>
                                  <span className="text-sm font-medium col-span-2">{node.name}</span>
                                </div>
                                <Separator />
                                <div className="grid grid-cols-3 gap-2 items-center">
                                  <span className="text-sm text-muted-foreground">Type:</span>
                                  <div className="col-span-2">
                                    <Badge variant="outline" className="font-mono">{node.type}</Badge>
                                  </div>
                                </div>
                                <Separator />
                                <div className="grid grid-cols-3 gap-2">
                                  <span className="text-sm text-muted-foreground">Full Path:</span>
                                  <code className="text-xs bg-muted p-2 rounded border break-all col-span-2 font-mono">{node.id}</code>
                                </div>
                                {node.type === 'table' && (
                                  <>
                                    <Separator />
                                    <div className="flex items-center justify-between">
                                      <span className="text-sm text-muted-foreground">Actions:</span>
                                      <Button
                                        size="sm"
                                        variant="outline"
                                        onClick={() => handleViewDataset(node.id)}
                                        className="h-8"
                                      >
                                        <Eye className="h-3 w-3 mr-1" />
                                        View Data
                                      </Button>
                                    </div>
                                  </>
                                )}
                              </div>
                            ) : (
                              <p className="text-sm text-muted-foreground">Loading details...</p>
                            );
                          })()}
                        </CardContent>
                      </Card>

                      {/* Entity Metadata Panel - Notes, Links, Documents */}
                      {getSelectedNodeDetails() && (
                        <EntityMetadataPanel
                          entityId={getSelectedNodeDetails()?.id || ''}
                          entityType={'data_product' as any}
                        />
                      )}
                    </div>
                  ) : (
                    <div className="flex items-center justify-center h-full">
                      <div className="text-center">
                        <Info className="h-12 w-12 mx-auto mb-4 text-muted-foreground opacity-50" />
                        <p className="text-sm text-muted-foreground">Select an object to view its information</p>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}

            {/* Comments Panel */}
            {rightPanelMode === 'comments' && (
              <Card className="flex-1 flex flex-col h-full min-w-0 shadow-sm border-border/50">
                <CardHeader className="flex-none pb-3 border-b">
                  <CardTitle className="flex items-center gap-2 text-lg font-semibold">
                    <MessageSquare className="h-5 w-5" />
                    Comments & Activity
                  </CardTitle>
                </CardHeader>
                <CardContent className="flex-1 overflow-hidden p-4">
                  {selectedObjectInfo && getSelectedNodeDetails()?.id ? (
                    <CommentTimeline
                      entityType="catalog-object"
                      entityId={getSelectedNodeDetails()?.id || ''}
                      showHeader={false}
                      showFilters={true}
                      className="h-full"
                    />
                  ) : (
                    <div className="flex items-center justify-center h-full">
                      <div className="text-center">
                        <MessageSquare className="h-12 w-12 mx-auto mb-4 text-muted-foreground opacity-50" />
                        <p className="text-sm text-muted-foreground">Select an object to view comments</p>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}
          </>
        )}
      </div>

      <Dialog open={viewDialogOpen} onOpenChange={setViewDialogOpen}>
        <DialogContent className="max-w-[90vw] max-h-[90vh] flex flex-col">
          <DialogHeader>
            <DialogTitle>Dataset View: {selectedDataset}</DialogTitle>
          </DialogHeader>
          {loadingData ? (
            <div className="flex items-center justify-center h-32">
              <Loader2 className="animate-spin h-8 w-8 text-blue-500" />
            </div>
          ) : datasetContent ? (
            <div className="mt-4 flex-1 overflow-auto h-full">
              <DataTable
                data={datasetContent.data}
                columns={datasetContent.schema.map(col => ({
                  accessorKey: col.name,
                  header: `${col.name} (${col.type})`,
                }))}
              />
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No data available</p>
          )}
        </DialogContent>
      </Dialog>

      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Confirm Operation</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            {selectedItems.length > 0
              ? `Selected items: ${selectedItems.map(item => item.name).join(', ')}`
              : 'No items selected'}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsDialogOpen(false)}>Cancel</Button>
            <Button onClick={() => setIsDialogOpen(false)}>Confirm</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default CatalogCommander; 