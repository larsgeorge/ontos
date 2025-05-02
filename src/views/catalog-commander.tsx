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
  Loader2
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { DataTable } from '@/components/ui/data-table';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { usePermissions } from '@/stores/permissions-store';
import { FeatureAccessLevel } from '@/types/feature-access-levels';

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

  const { hasPermission } = usePermissions();
  const canPerformWriteActions = hasPermission('catalog-commander', FeatureAccessLevel.FULL);

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
      
      console.log('Fetching children from:', url);
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`Failed to fetch children: ${response.status}`);
      }
      const data = await response.json();
      console.log('Received children data:', data);
      return data;
    } catch (err) {
      console.error('Error fetching children:', err);
      return [];
    }
  };

  const handleNodeExpand = async (nodeId: string, nodeType: string, isSource: boolean) => {
    if (loadingNodes.has(nodeId)) return;

    console.log('Expanding node:', { nodeId, nodeType, isSource });
    setLoadingNodes(prev => new Set(prev).add(nodeId));
    try {
      const children = await fetchChildren(nodeId, nodeType);
      console.log('Updating children for node:', { nodeId, children });
      if (isSource) {
        setSourceItems(prev => {
          const updated = updateNodeChildren(prev, nodeId, children);
          console.log('Updated source items:', updated);
          return updated;
        });
      } else {
        setTargetItems(prev => {
          const updated = updateNodeChildren(prev, nodeId, children);
          console.log('Updated target items:', updated);
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
  }, []);

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
    console.log('Rendering tree items:', { items, isSource });
    return items.map(item => {
      const hasChildren = item.hasChildren || (item.children && item.children.length > 0);
      console.log('Processing item:', { item, hasChildren });
      
      const treeItem = {
        id: item.id,
        name: item.name,
        icon: getIcon(item.type),
        children: item.children ? renderTree(item.children, isSource) : [],
        onClick: () => {
          console.log('Item clicked:', item);
          handleItemSelect(item);
        },
        selected: selectedItems.some(selected => selected.id === item.id),
        expanded: expandedNodes.has(item.id),
        onExpand: () => {
          console.log('Item expanding:', { item, isSource, hasChildren });
          handleNodeExpand(item.id, item.type, isSource);
        },
        loading: loadingNodes.has(item.id),
        hasChildren: hasChildren
      };
      console.log('Created tree item:', treeItem);
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

      <div className="flex justify-between items-center mb-6">
        <div className="flex gap-2">
          <Button onClick={() => handleViewDataset(getSelectedNodeDetails()?.id || '')} 
                  disabled={!selectedItems.length || getSelectedNodeDetails()?.type !== 'table'}>
            <Eye className="h-4 w-4 mr-2" />
            View
          </Button>
          {canPerformWriteActions && (
            <>
              <Button onClick={() => handleOperation('move')}>
                <ArrowRight className="h-4 w-4 mr-2" />
                Move
              </Button>
              <Button onClick={() => handleOperation('delete')} variant="destructive">
                <Trash2 className="h-4 w-4 mr-2" />
                Delete
              </Button>
              <Button onClick={() => handleOperation('rename')}>
                <Pencil className="h-4 w-4 mr-2" />
                Rename
              </Button>
            </>
          )}
          <Button onClick={() => handleOperation('info')}>
            <Info className="h-4 w-4 mr-2" />
            Info
          </Button>
        </div>
      </div>

      <div className="flex gap-6 h-[calc(100vh-12rem)]">
        <Card className="flex-1 flex flex-col h-full min-w-0">
          <CardHeader className="flex-none">
            <CardTitle>Source</CardTitle>
          </CardHeader>
          <CardContent className="flex-1 flex flex-col h-full min-h-0">
            <div className="mb-2">
              <Select
                value={selectedSourceEstate}
                onValueChange={setSelectedSourceEstate}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select Estate" />
                </SelectTrigger>
                <SelectContent>
                  {estates.map(estate => (
                    <SelectItem key={estate.id} value={estate.id}>
                      {estate.name} <span className="text-xs text-muted-foreground ml-1">({estate.metastore_name})</span>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Input
              placeholder="Search"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              className="mb-4 flex-none"
            />
            <div className="flex-1 overflow-auto">
              <TreeView
                data={renderTree(sourceItems, true)}
                className="border rounded p-2 h-full"
                onSelectChange={(item) => handleItemSelect(item as unknown as CatalogItem)}
              />
            </div>
          </CardContent>
        </Card>

        {canPerformWriteActions && (
          <div className="flex flex-col justify-center gap-4">
            <Button onClick={() => handleOperation('copy')}>
              <ArrowRight className="h-4 w-4" />
            </Button>
            <Button onClick={() => handleOperation('move')}>
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </div>
        )}

        <Card className="flex-1 flex flex-col h-full min-w-0">
          <CardHeader className="flex-none">
            <CardTitle>Target</CardTitle>
          </CardHeader>
          <CardContent className="flex-1 flex flex-col h-full min-h-0">
            <div className="mb-2">
              <Select
                value={selectedTargetEstate}
                onValueChange={setSelectedTargetEstate}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select Estate" />
                </SelectTrigger>
                <SelectContent>
                  {estates.map(estate => (
                    <SelectItem key={estate.id} value={estate.id}>
                      {estate.name} <span className="text-xs text-muted-foreground ml-1">({estate.metastore_name})</span>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Input
              placeholder="Search"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              className="mb-4 flex-none"
            />
            <div className="flex-1 overflow-auto">
              <TreeView
                data={renderTree(targetItems, false)}
                className="border rounded p-2 h-full"
                onSelectChange={(item) => handleItemSelect(item as unknown as CatalogItem)}
              />
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle>Object Information</CardTitle>
        </CardHeader>
        <CardContent>
          {selectedObjectInfo ? (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <h3 className="text-sm font-medium mb-2">Basic Information</h3>
                {(() => {
                  const node = getSelectedNodeDetails();
                  return node ? (
                    <div className="space-y-1">
                      <p className="text-sm">Name: {node.name}</p>
                      <p className="text-sm">Type: {node.type.charAt(0).toUpperCase() + node.type.slice(1)}</p>
                      <p className="text-sm">Full Path: {node.id}</p>
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground">Loading details...</p>
                  );
                })()}
              </div>
              <div>
                <h3 className="text-sm font-medium mb-2">Properties</h3>
                {/* Add specific properties based on node type */}
              </div>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">Select an object to view its information</p>
          )}
        </CardContent>
      </Card>

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