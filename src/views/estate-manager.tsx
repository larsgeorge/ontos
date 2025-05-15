import React, { useState, useEffect, useRef } from 'react';
import { useToast } from '@/hooks/use-toast';
import { useApi } from '@/hooks/use-api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { ChevronDown, MoreHorizontal, Globe, Plus, Share2, Database, Columns, Trash2, List, Network } from 'lucide-react';
import {
  ColumnDef,
  ColumnFiltersState,
  SortingState,
  VisibilityState,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table"
import { Checkbox } from "@/components/ui/checkbox"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  DropdownMenuCheckboxItem,
} from "@/components/ui/dropdown-menu"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { useNavigate } from 'react-router-dom';
import useBreadcrumbStore from '@/stores/breadcrumb-store';
import { Table as TableIcon, Workflow as WorkflowIcon } from 'lucide-react';

import ReactFlow, {
    Node, 
    Edge,
    Background,
    Controls,
    MiniMap,
    useNodesState,
    useEdgesState,
    Position,
    MarkerType,
} from 'reactflow';
import 'reactflow/dist/style.css';
import EstateNode, { EstateNodeData, DynamicHandle } from '@/components/estates/estate-node';
import EstateGraphView from '@/components/estates/estate-graph-view';

// --- TypeScript Interfaces corresponding to Pydantic Models ---
type CloudType = 'aws' | 'azure' | 'gcp';
type SyncStatus = 'pending' | 'running' | 'success' | 'failed';
type ConnectionType = 'delta_share' | 'database';
type SharingResourceType = 'data_product' | 'business_glossary';
type SharingRuleOperator = 'equals' | 'contains' | 'starts_with' | 'regex';

interface SharingRule {
  filter_type: string;
  operator: SharingRuleOperator;
  filter_value: string;
}

interface SharingPolicy {
  id?: string;
  name: string;
  description?: string;
  resource_type: SharingResourceType;
  rules: SharingRule[];
  is_enabled: boolean;
  created_at: string; // ISO datetime string
  updated_at: string; // ISO datetime string
}

interface Estate {
  id: string;
  name: string;
  description: string;
  workspace_url: string;
  cloud_type: CloudType;
  metastore_name: string;
  connection_type: ConnectionType;
  sharing_policies: SharingPolicy[];
  is_enabled: boolean;
  sync_schedule: string;
  last_sync_time?: string;
  last_sync_status?: SyncStatus;
  last_sync_error?: string;
  created_at: string;
  updated_at: string;
}
// --- End TypeScript Interfaces ---

// Define nodeTypes outside the component for memoization
const nodeTypes = { estateNode: EstateNode };

export default function EstateManager() {
  const { toast } = useToast();
  const { get, post, put, delete: deleteEstateApi } = useApi();
  const navigate = useNavigate();
  const setStaticSegments = useBreadcrumbStore((state) => state.setStaticSegments);
  const setDynamicTitle = useBreadcrumbStore((state) => state.setDynamicTitle);
  const [estates, setEstates] = useState<Estate[]>([]);
  const [selectedEstate, setSelectedEstate] = useState<Estate | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [sorting, setSorting] = useState<SortingState>([]);
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({});
  const [rowSelection, setRowSelection] = useState({});
  const [formData, setFormData] = useState<Partial<Estate>>({
    name: '',
    description: '',
    workspace_url: '',
    cloud_type: 'aws',
    metastore_name: '',
    connection_type: 'delta_share',
    sharing_policies: [],
    is_enabled: true,
    sync_schedule: '0 0 * * *',
  });
  const [viewMode, setViewMode] = useState<'table' | 'graph'>('table');

  useEffect(() => {
    fetchEstates();
    // Set breadcrumbs for this top-level view
    setStaticSegments([]); // No static parents other than Home
    setDynamicTitle('Estate Manager');

    return () => {
        // Clear breadcrumbs when component unmounts
        setStaticSegments([]);
        setDynamicTitle(null);
    };
  }, [setStaticSegments, setDynamicTitle]);

  const fetchEstates = async () => {
    try {
      const response = await get<Estate[]>('/api/estates');
      setEstates(response.data || []);
    } catch (error) {
      toast({
        title: 'Error Fetching Estates',
        description: error instanceof Error ? error.message : 'Could not load estates.',
        variant: 'destructive',
      });
      setEstates([]);
    }
  };

  const handleSubmit = async () => {
    if (!formData.name || !formData.description || !formData.workspace_url || !formData.metastore_name || !formData.cloud_type || !formData.connection_type) {
        toast({
            title: "Validation Error",
            description: "Please fill in all required fields: Name, Description, Workspace URL, Metastore Name, Cloud Type, and Connection Type.",
            variant: "destructive",
        });
        return;
    }
    
    try {
      let response;
      const payload: Estate = {
        id: selectedEstate?.id || '',
        name: formData.name!,
        description: formData.description!,
        workspace_url: formData.workspace_url!,
        cloud_type: formData.cloud_type!,
        metastore_name: formData.metastore_name!,
        connection_type: formData.connection_type!,
        sharing_policies: formData.sharing_policies || [],
        is_enabled: formData.is_enabled === undefined ? true : formData.is_enabled,
        sync_schedule: formData.sync_schedule || '0 0 * * *',
        created_at: selectedEstate?.created_at || new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };

      if (selectedEstate && selectedEstate.id) {
        response = await put<Estate>(`/api/estates/${selectedEstate.id}`, payload);
      } else {
        const createPayload = { ...payload };
        delete (createPayload as any).id; 
        delete (createPayload as any).created_at;
        delete (createPayload as any).updated_at;
        response = await post<Estate>('/api/estates', createPayload);
      }
      
      if (response.error) throw new Error(response.error);
      if (response.data && typeof response.data === 'object' && 'detail' in response.data && typeof response.data.detail === 'string') {
        throw new Error(response.data.detail);
      }
      
      toast({
        title: 'Success',
        description: `Estate ${selectedEstate ? 'updated' : 'created'} successfully`,
      });
      
      setIsDialogOpen(false);
      fetchEstates();
    } catch (error) {
      toast({
        title: 'Error Saving Estate',
        description: error instanceof Error ? error.message : 'Failed to save estate',
        variant: 'destructive',
      });
    }
  };

  const handleDelete = async (estateId: string) => {
    if (!confirm('Are you sure you want to delete this estate?')) return;
    try {
      const response = await deleteEstateApi(`/api/estates/${estateId}`);
      if (response.error) throw new Error(response.error);
      toast({
        title: 'Success',
        description: 'Estate deleted successfully',
      });
      fetchEstates();
    } catch (error) {
      toast({
        title: 'Error Deleting Estate',
        description: error instanceof Error ? error.message : 'Failed to delete estate',
        variant: 'destructive',
      });
    }
  };
  
  const handleDeleteSelected = async () => {
    const selectedRows = table.getSelectedRowModel().rows;
    if (selectedRows.length === 0) {
        toast({ title: "No Rows Selected", description: "Please select estates to delete.", variant: "destructive" });
        return;
    }
    if (!confirm(`Are you sure you want to delete ${selectedRows.length} selected estate(s)?`)) return;

    const deletePromises = selectedRows.map(row => deleteEstateApi(`/api/estates/${row.original.id}`));
    try {
        const results = await Promise.allSettled(deletePromises);
        const failedDeletes = results.filter(result => result.status === 'rejected' || (result.status === 'fulfilled' && result.value.error));
        
        if (failedDeletes.length > 0) {
            toast({
                title: "Partial Deletion Error",
                description: `${failedDeletes.length} estate(s) could not be deleted. Check console for details.`,
                variant: "destructive",
            });
            failedDeletes.forEach(fail => console.error("Deletion error:", (fail as any).reason || (fail as any).value?.error));
        } else {
            toast({ title: "Success", description: `${selectedRows.length} estate(s) deleted successfully.` });
        }
    } catch (err) {
        toast({ title: "Bulk Delete Error", description: "An unexpected error occurred during bulk deletion.", variant: "destructive" });
        console.error("Bulk delete error:", err);
    } finally {
        fetchEstates();
        table.resetRowSelection();
    }
  };

  const handleSync = async (id: string) => {
    toast({ title: 'Triggering Sync', description: 'Requesting sync for the estate...' });
    try {
      const response = await post(`/api/estates/${id}/sync`, {});
      if (response.error) throw new Error(response.error);
      if (response.data && typeof response.data === 'object' && 'detail' in response.data && typeof response.data.detail === 'string') {
        throw new Error(response.data.detail);
      }
      toast({
        title: 'Success',
        description: 'Sync triggered successfully. Refreshing data...',
      });
      setTimeout(fetchEstates, 1000);
    } catch (error) {
      toast({
        title: 'Error Triggering Sync',
        description: error instanceof Error ? error.message : 'Failed to trigger sync',
        variant: 'destructive',
      });
    }
  };

  const openDialog = (estate?: Estate) => {
    if (estate) {
      setSelectedEstate(estate);
      setFormData({
        ...estate,
        connection_type: estate.connection_type || 'delta_share',
        sharing_policies: estate.sharing_policies || [],
      });
    } else {
      setSelectedEstate(null);
      setFormData({
        name: '',
        description: '',
        workspace_url: '',
        cloud_type: 'aws',
        metastore_name: '',
        connection_type: 'delta_share',
        sharing_policies: [],
        is_enabled: true,
        sync_schedule: '0 0 * * *',
      });
    }
    setIsDialogOpen(true);
  };
  
  const handleNodeClick = (estateId: string) => {
    navigate(`/estates/${estateId}`);
  };

  const columns: ColumnDef<Estate>[] = [
    {
      id: "select",
      header: ({ table }) => (
        <Checkbox
          checked={table.getIsAllPageRowsSelected() ? true : (table.getIsSomePageRowsSelected() ? "indeterminate" : false)}
          onCheckedChange={(value) => table.toggleAllPageRowsSelected(!!value)}
          aria-label="Select all"
        />
      ),
      cell: ({ row }) => (
        <Checkbox
          checked={row.getIsSelected()}
          onCheckedChange={(value) => row.toggleSelected(!!value)}
          aria-label="Select row"
          onClick={(e) => e.stopPropagation()}
        />
      ),
      enableSorting: false,
      enableHiding: false,
    },
    {
      accessorKey: "name",
      header: ({ column }) => {
        return (
          <Button
            variant="ghost"
            onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
          >
            Name
            <ChevronDown className="ml-2 h-4 w-4" />
          </Button>
        );
      },
      cell: ({ row }) => (
        <div 
            className="font-medium cursor-pointer hover:underline"
            onClick={() => handleNodeClick(row.original.id)}
        >
            {row.getValue("name")}
        </div>
      ),
    },
    {
      accessorKey: "workspace_url",
      header: "Workspace URL",
      cell: ({ row }) => <div>{row.getValue("workspace_url")}</div>,
    },
    {
      accessorKey: "cloud_type",
      header: "Cloud",
      cell: ({ row }) => <div className="capitalize">{row.getValue("cloud_type")}</div>,
    },
    {
      accessorKey: "connection_type",
      header: "Connection",
      cell: ({ row }) => {
        const connectionType = row.getValue("connection_type") as ConnectionType;
        return (
          <div className="flex items-center gap-1 capitalize">
            {connectionType === 'delta_share' ? 
              <Share2 className="h-4 w-4 text-blue-500" /> : 
              <Database className="h-4 w-4 text-green-500" />}
            {connectionType.replace('_', ' ')}
          </div>
        );
      },
    },
    {
      accessorKey: "metastore_name",
      header: "Metastore",
      cell: ({ row }) => <div>{row.getValue("metastore_name")}</div>,
    },
    {
      accessorKey: "is_enabled",
      header: "Sync Status",
      cell: ({ row }) => (
        <Badge variant={row.getValue("is_enabled") ? "default" : "secondary"}>
          {row.getValue("is_enabled") ? "Enabled" : "Disabled"}
        </Badge>
      ),
    },
    {
      accessorKey: "last_sync_status",
      header: "Last Sync",
      cell: ({ row }) => {
        const lastSyncTime = row.original.last_sync_time;
        const status = row.original.last_sync_status;
        const error = row.original.last_sync_error;

        if (!status) return <Badge variant="outline">Never Synced</Badge>;

        let badgeVariant: "default" | "destructive" | "secondary" | "outline" = 'outline';
        if (status === 'success') badgeVariant = 'default';
        else if (status === 'failed') badgeVariant = 'destructive';
        else if (status === 'running' || status === 'pending') badgeVariant = 'secondary';
        
        const statusText = status.charAt(0).toUpperCase() + status.slice(1);

        return (
          <TooltipProvider delayDuration={100}>
            <Tooltip>
              <TooltipTrigger asChild>
                <span>
                  <Badge variant={badgeVariant} className="cursor-default">
                    {statusText}
                  </Badge>
                </span>
              </TooltipTrigger>
              <TooltipContent side="top">
                <p>Status: {statusText}</p>
                {lastSyncTime && <p>Time: {new Date(lastSyncTime).toLocaleString()}</p>}
                {status === 'failed' && error && <p className="text-red-400">Error: {error}</p>}
                {(status === 'running' || status === 'pending') && <p>Sync in progress or queued...</p>}
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        );
      },
    },
    {
      id: "actions",
      enableHiding: false,
      cell: ({ row }) => {
        const estate = row.original;
        return (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="h-8 w-8 p-0" onClick={(e) => e.stopPropagation()}>
                <span className="sr-only">Open menu</span>
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuLabel>Actions</DropdownMenuLabel>
              <DropdownMenuItem onClick={(e) => { e.stopPropagation(); handleNodeClick(estate.id); }}>View Details</DropdownMenuItem>
              <DropdownMenuItem onClick={(e) => { e.stopPropagation(); handleSync(estate.id); }}>
                Trigger Sync
              </DropdownMenuItem>
              <DropdownMenuItem onClick={(e) => { e.stopPropagation(); openDialog(estate); }}>
                Edit
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                className="text-red-600 focus:text-red-50 focus:bg-red-600"
                onClick={(e) => { e.stopPropagation(); handleDelete(estate.id); }}
              >
                Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        );
      },
    },
  ];

  const table = useReactTable({
    data: estates,
    columns,
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    getCoreRowModel: getCoreRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    onColumnVisibilityChange: setColumnVisibility,
    onRowSelectionChange: setRowSelection,
    state: {
      sorting,
      columnFilters,
      columnVisibility,
      rowSelection,
    },
  });

  return (
    <div className="py-6">
      <h1 className="text-3xl font-bold mb-6 flex items-center gap-2">
        <Globe className="w-8 h-8" /> Estate Manager
      </h1>

      <div className="space-y-4">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 flex-grow">
            {viewMode === 'table' && (
              <Input
                placeholder="Filter estates (name, URL, metastore...)"
                value={(table.getState().globalFilter as string) ?? ''}
                onChange={(event) => table.setGlobalFilter(event.target.value)}
                className="max-w-sm h-9"
              />
            )}
          </div>
          
          <div className="flex items-center gap-2">
            {viewMode === 'table' && Object.keys(rowSelection).length > 0 && (
                <Button
                    variant="outline"
                    size="sm"
                    className="h-9 text-red-600 hover:bg-red-600 hover:text-white border-red-600"
                    onClick={handleDeleteSelected} 
                >
                    <Trash2 className="mr-2 h-4 w-4" /> Delete ({Object.keys(rowSelection).length})
                </Button>
            )}
            {viewMode === 'table' && (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" className="h-9">
                    <Columns className="mr-2 h-4 w-4" /> Columns 
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  {table
                    .getAllColumns()
                    .filter((column) => column.getCanHide())
                    .map((column) => {
                      return (
                        <DropdownMenuCheckboxItem
                          key={column.id}
                          className="capitalize"
                          checked={column.getIsVisible()}
                          onCheckedChange={(value) =>
                            column.toggleVisibility(!!value)
                          }
                        >
                          {column.id.replace(/_/g, ' ')}
                        </DropdownMenuCheckboxItem>
                      );
                    })}
                </DropdownMenuContent>
              </DropdownMenu>
            )}
            <div className="flex items-center gap-1 border rounded-md p-0.5 ml-auto">
                <Button
                    variant={viewMode === 'table' ? 'secondary' : 'ghost'}
                    size="sm"
                    onClick={() => setViewMode('table')}
                    className="h-8 px-2"
                    title="Table View"
                >
                    <TableIcon className="h-4 w-4" />
                </Button>
                <Button
                    variant={viewMode === 'graph' ? 'secondary' : 'ghost'}
                    size="sm"
                    onClick={() => setViewMode('graph')}
                    className="h-8 px-2"
                    title="Graph View"
                >
                    <WorkflowIcon className="h-4 w-4" />
                </Button>
            </div>
            <Button onClick={() => openDialog()} className="h-9">
              <Plus className="h-4 w-4 mr-2" />
              Add Estate
            </Button>
          </div>
        </div>

        {viewMode === 'table' ? (
          <>
            <Card>
              <CardContent className="p-0">
                <Table>
                  <TableHeader>
                    {table.getHeaderGroups().map((headerGroup) => (
                      <TableRow key={headerGroup.id}>
                        {headerGroup.headers.map((header) => {
                          return (
                            <TableHead key={header.id} style={{ whiteSpace: 'nowrap' }}>
                              {header.isPlaceholder
                                ? null
                                : flexRender(
                                    header.column.columnDef.header,
                                    header.getContext()
                                  )}
                            </TableHead>
                          );
                        })}
                      </TableRow>
                    ))}
                  </TableHeader>
                  <TableBody>
                    {table.getRowModel().rows?.length ? (
                      table.getRowModel().rows.map((row) => (
                        <TableRow
                          key={row.id}
                          data-state={row.getIsSelected() && "selected"}
                        >
                          {row.getVisibleCells().map((cell) => (
                            <TableCell key={cell.id}>
                              {flexRender(
                                cell.column.columnDef.cell,
                                cell.getContext()
                              )}
                            </TableCell>
                          ))}
                        </TableRow>
                      ))
                    ) : (
                      <TableRow>
                        <TableCell
                          colSpan={columns.length}
                          className="h-24 text-center"
                        >
                          No results. {estates.length > 0 ? "Try adjusting your filters." : "Create an estate to get started."}
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>

            <div className="flex items-center justify-between space-x-2 py-4">
              <div className="flex-1 text-sm text-muted-foreground">
                {table.getFilteredSelectedRowModel().rows.length} of{" "}
                {table.getFilteredRowModel().rows.length} row(s) selected.
              </div>
              <div className="flex items-center space-x-2">
                <div className="flex items-center space-x-2">
                  <p className="text-sm font-medium">Rows per page</p>
                  <Select
                    value={`${table.getState().pagination.pageSize}`}
                    onValueChange={(value) => {
                      table.setPageSize(Number(value));
                    }}
                  >
                    <SelectTrigger className="h-8 w-[70px]">
                      <SelectValue placeholder={table.getState().pagination.pageSize} />
                    </SelectTrigger>
                    <SelectContent side="top">
                      {[10, 20, 30, 40, 50, 100].map((pageSize) => (
                        <SelectItem key={pageSize} value={`${pageSize}`}>
                          {pageSize}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex w-[100px] items-center justify-center text-sm font-medium">
                  Page {table.getState().pagination.pageIndex + 1} of{" "}
                  {table.getPageCount() > 0 ? table.getPageCount() : 1}
                </div>
                <div className="flex items-center space-x-2">
                  <Button
                    variant="outline"
                    className="hidden h-8 w-8 p-0 lg:flex"
                    onClick={() => table.setPageIndex(0)}
                    disabled={!table.getCanPreviousPage()}
                  >
                    <span className="sr-only">Go to first page</span>
                    <ChevronDown className="h-4 w-4 rotate-90" />
                  </Button>
                  <Button
                    variant="outline"
                    className="h-8 w-8 p-0"
                    onClick={() => table.previousPage()}
                    disabled={!table.getCanPreviousPage()}
                  >
                    <span className="sr-only">Go to previous page</span>
                    <ChevronDown className="h-4 w-4 rotate-90" />
                  </Button>
                  <Button
                    variant="outline"
                    className="h-8 w-8 p-0"
                    onClick={() => table.nextPage()}
                    disabled={!table.getCanNextPage()}
                  >
                    <span className="sr-only">Go to next page</span>
                    <ChevronDown className="h-4 w-4 -rotate-90" />
                  </Button>
                  <Button
                    variant="outline"
                    className="hidden h-8 w-8 p-0 lg:flex"
                    onClick={() => table.setPageIndex(table.getPageCount() - 1)}
                    disabled={!table.getCanNextPage()}
                  >
                    <span className="sr-only">Go to last page</span>
                    <ChevronDown className="h-4 w-4 -rotate-90" />
                  </Button>
                </div>
              </div>
            </div>
          </>
        ) : (
          <div className="h-[calc(100vh-280px)] w-full border rounded-lg">
            <EstateGraphView estates={estates} onNodeClick={handleNodeClick} />
          </div>
        )}
      </div>

      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="sm:max-w-[600px]">
          <DialogHeader>
            <DialogTitle>{selectedEstate ? 'Edit Estate' : 'Add New Estate'}</DialogTitle>
            <DialogDescription>
              Configure the Databricks estate connection and basic settings. Sharing policies are managed on the detail page.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="name" className="text-right">Name</Label>
              <Input
                id="name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="col-span-3"
                placeholder="e.g., US Production Workspace"
              />
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="description" className="text-right">Description</Label>
              <Input
                id="description"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className="col-span-3"
                placeholder="e.g., Primary production environment for US region"
              />
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="workspace_url" className="text-right">Workspace URL</Label>
              <Input
                id="workspace_url"
                value={formData.workspace_url}
                onChange={(e) => setFormData({ ...formData, workspace_url: e.target.value })}
                className="col-span-3"
                placeholder="e.g., https://myworkspace.cloud.databricks.com"
              />
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="cloud_type" className="text-right">Cloud</Label>
              <Select
                value={formData.cloud_type}
                onValueChange={(value) => setFormData({ ...formData, cloud_type: value as CloudType })}
              >
                <SelectTrigger className="col-span-3">
                  <SelectValue placeholder="Select cloud provider" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="aws">AWS</SelectItem>
                  <SelectItem value="azure">Azure</SelectItem>
                  <SelectItem value="gcp">GCP</SelectItem>
                </SelectContent>
              </Select>
            </div>
             <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="connection_type" className="text-right">Connection Type</Label>
              <Select
                value={formData.connection_type}
                onValueChange={(value) => setFormData({ ...formData, connection_type: value as ConnectionType })}
              >
                <SelectTrigger className="col-span-3">
                  <SelectValue placeholder="Select connection type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="delta_share">Delta Share</SelectItem>
                  <SelectItem value="database">Database (Future Use)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="metastore_name" className="text-right">Metastore Name</Label>
              <Input
                id="metastore_name"
                value={formData.metastore_name}
                onChange={(e) => setFormData({ ...formData, metastore_name: e.target.value })}
                className="col-span-3"
                placeholder="e.g., primary_prod_metastore"
              />
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="sync_schedule" className="text-right">Sync Schedule</Label>
              <Input
                id="sync_schedule"
                value={formData.sync_schedule}
                onChange={(e) => setFormData({ ...formData, sync_schedule: e.target.value })}
                className="col-span-3"
                placeholder="Cron expression, e.g., 0 0 * * *"
              />
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
                <Label htmlFor="is_enabled" className="text-right">Enable Sync</Label>
                <div className="col-span-3 flex items-center">
                    <Switch
                        id="is_enabled"
                        checked={formData.is_enabled}
                        onCheckedChange={(checked) => setFormData({ ...formData, is_enabled: checked })}
                    />
                </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSubmit}>
              {selectedEstate ? 'Save Changes' : 'Create Estate'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
} 