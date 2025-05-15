import React, { useState, useEffect } from 'react';
import { DataContract } from '@/types/data-contract';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Card, CardContent } from '@/components/ui/card';
import { Plus, Pencil, Trash2, AlertCircle, FileText, Upload, Download, ChevronDown, Loader2 } from 'lucide-react';
import { useDropzone } from 'react-dropzone';
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
  DropdownMenuTrigger,
  DropdownMenuCheckboxItem,
} from "@/components/ui/dropdown-menu"
import { useToast } from "@/hooks/use-toast"
import useBreadcrumbStore from '@/stores/breadcrumb-store';

export default function DataContracts() {
  const { toast } = useToast();
  const [contracts, setContracts] = useState<DataContract[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [openDialog, setOpenDialog] = useState(false);
  const [selectedContract, setSelectedContract] = useState<DataContract | null>(null);
  const [openDetails, setOpenDetails] = useState(false);
  const [openUploadDialog, setOpenUploadDialog] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  // Table state
  const [sorting, setSorting] = useState<SortingState>([])
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([])
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({})
  const [rowSelection, setRowSelection] = useState({})
  const [globalFilter, setGlobalFilter] = useState("")

  // Form state
  const [name, setName] = useState('');
  const [version, setVersion] = useState('1.0');
  const [status, setStatus] = useState('draft');
  const [owner, setOwner] = useState('');
  const [description, setDescription] = useState('');
  const [contractText, setContractText] = useState('');
  const [format, setFormat] = useState('json');

  const setStaticSegments = useBreadcrumbStore((state) => state.setStaticSegments);
  const setDynamicTitle = useBreadcrumbStore((state) => state.setDynamicTitle);

  useEffect(() => {
    fetchContracts();
    // Set breadcrumbs
    setStaticSegments([]);
    setDynamicTitle('Data Contracts');

    // Cleanup breadcrumbs on unmount
    return () => {
        setStaticSegments([]);
        setDynamicTitle(null);
    };
  }, [setStaticSegments, setDynamicTitle]);

  const fetchContracts = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/data-contracts');
      if (!response.ok) throw new Error('Failed to fetch contracts');
      const data = await response.json();
      setContracts(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch contracts');
    } finally {
      setLoading(false);
    }
  };

  const fetchContract = async (id: string) => {
    try {
      const response = await fetch(`/api/data-contracts/${id}`);
      if (!response.ok) throw new Error('Failed to fetch contract');
      const data = await response.json();
      setSelectedContract(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch contract');
    }
  };

  const createContract = async (formData: any) => {
    try {
      const response = await fetch('/api/data-contracts', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });
      if (!response.ok) throw new Error('Failed to create contract');
      await fetchContracts();
      setOpenDialog(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create contract');
    }
  };

  const updateContract = async (id: string, formData: any) => {
    try {
      const response = await fetch(`/api/data-contracts/${id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });
      if (!response.ok) throw new Error('Failed to update contract');
      await fetchContracts();
      setOpenDialog(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update contract');
    }
  };

  const deleteContract = async (id: string) => {
    try {
      const response = await fetch(`/api/data-contracts/${id}`, {
        method: 'DELETE',
      });
      if (!response.ok) throw new Error('Failed to delete contract');
      await fetchContracts();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete contract');
    }
  };

  const handleCreateContract = () => {
    setSelectedContract(null);
    setName('');
    setVersion('1.0');
    setStatus('draft');
    setOwner('');
    setDescription('');
    setContractText('');
    setOpenDialog(true);
  };

  const handleEditContract = async (contract: DataContract) => {
    setSelectedContract(contract);
    setName(contract.name);
    setVersion(contract.version);
    setStatus(contract.status);
    setOwner(contract.owner);
    setDescription(contract.description || '');
    setContractText(contract.contract_text);
    setOpenDialog(true);
  };

  const handleDeleteContract = async (id: string) => {
    if (!confirm('Are you sure you want to delete this contract?')) return;
    await deleteContract(id);
  };

  const handleSaveContract = async (event: React.FormEvent) => {
    event.preventDefault();
    const formData = {
      name,
      version,
      status,
      owner,
      description,
      contract_text: contractText,
      format,
      dataProducts: [], // Initialize with empty array
      schema: {
        fields: [] // Initialize with empty array
      },
      validation_rules: [] // Initialize with empty array
    };

    if (selectedContract?.id) {
      await updateContract(selectedContract.id, formData);
    } else {
      await createContract(formData);
    }
  };

  const handleViewDetails = async (contract: DataContract) => {
    if (contract.id) {
      await fetchContract(contract.id);
      setOpenDetails(true);
    }
  };

  const handleDownloadContract = (contract: DataContract) => {
    const blob = new Blob([contract.contract_text], { 
      type: contract.format === 'json' 
        ? 'application/json' 
        : contract.format === 'yaml'
        ? 'application/x-yaml'
        : 'text/plain' 
    });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${contract.name.toLowerCase().replace(/\s+/g, '_')}.${
      contract.format === 'yaml' ? 'yaml' : 
      contract.format === 'json' ? 'json' : 'txt'
    }`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: async (acceptedFiles) => {
      if (acceptedFiles.length === 0) return;

      const file = acceptedFiles[0];
      if (!file.type.startsWith('text/') && file.type !== 'application/json' && file.type !== 'application/x-yaml') {
        setUploadError('Please upload a text file (JSON, YAML, etc)');
        return;
      }

      try {
        setUploading(true);
        setUploadError(null);

        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch('/api/data-contracts/upload', {
          method: 'POST',
          body: formData
        });

        if (!response.ok) {
          throw new Error('Failed to upload contract');
        }

        await fetchContracts();
        setOpenUploadDialog(false);
      } catch (err) {
        setUploadError(err instanceof Error ? err.message : 'Failed to upload contract');
      } finally {
        setUploading(false);
      }
    },
    accept: {
      'text/*': ['.json', '.yaml', '.yml', '.txt'],
      'application/json': ['.json'],
      'application/x-yaml': ['.yaml', '.yml']
    },
    multiple: false
  });

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'draft':
        return 'bg-yellow-100 text-yellow-800';
      case 'active':
        return 'bg-green-100 text-green-800';
      case 'deprecated':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const columns: ColumnDef<DataContract>[] = [
    {
      id: "select",
      header: ({ table }) => (
        <Checkbox
          checked={table.getIsAllPageRowsSelected()}
          onCheckedChange={(value) => table.toggleAllPageRowsSelected(!!value)}
          aria-label="Select all"
        />
      ),
      cell: ({ row }) => (
        <Checkbox
          checked={row.getIsSelected()}
          onCheckedChange={(value) => row.toggleSelected(!!value)}
          aria-label="Select row"
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
      cell: ({ row }) => <div className="font-medium">{row.getValue("name")}</div>,
    },
    {
      accessorKey: "version",
      header: ({ column }) => {
        return (
          <Button
            variant="ghost"
            onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
          >
            Version
            <ChevronDown className="ml-2 h-4 w-4" />
          </Button>
        );
      },
      cell: ({ row }) => <div>{row.getValue("version")}</div>,
    },
    {
      accessorKey: "format",
      header: ({ column }) => {
        return (
          <Button
            variant="ghost"
            onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
          >
            Format
            <ChevronDown className="ml-2 h-4 w-4" />
          </Button>
        );
      },
      cell: ({ row }) => <div>{row.getValue("format")}</div>,
    },
    {
      accessorKey: "status",
      header: ({ column }) => {
        return (
          <Button
            variant="ghost"
            onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
          >
            Status
            <ChevronDown className="ml-2 h-4 w-4" />
          </Button>
        );
      },
      cell: ({ row }) => (
        <Badge variant="outline" className={getStatusColor(row.getValue("status"))}>
          {row.getValue("status")}
        </Badge>
      ),
    },
    {
      accessorKey: "created",
      header: ({ column }) => {
        return (
          <Button
            variant="ghost"
            onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
          >
            Created
            <ChevronDown className="ml-2 h-4 w-4" />
          </Button>
        );
      },
      cell: ({ row }) => (
        <div>{new Date(row.getValue("created")).toLocaleDateString()}</div>
      ),
    },
    {
      accessorKey: "updated",
      header: ({ column }) => {
        return (
          <Button
            variant="ghost"
            onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
          >
            Updated
            <ChevronDown className="ml-2 h-4 w-4" />
          </Button>
        );
      },
      cell: ({ row }) => (
        <div>{new Date(row.getValue("updated")).toLocaleDateString()}</div>
      ),
    },
    {
      id: "actions",
      enableHiding: false,
      cell: ({ row }) => {
        const contract = row.original;
        return (
          <div className="flex space-x-2">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => handleViewDetails(contract)}
            >
              <FileText className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => handleEditContract(contract)}
            >
              <Pencil className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => handleDownloadContract(contract)}
            >
              <Download className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => contract.id && handleDeleteContract(contract.id)}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        );
      },
    },
  ];

  const table = useReactTable({
    data: contracts,
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
      globalFilter,
    },
  });

  return (
    <div className="py-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold mb-6 flex items-center gap-2">
          <FileText className="w-8 h-8" />Data Contracts
        </h1>
        <div className="flex space-x-2">
          <Button onClick={handleCreateContract} className="gap-2">
            <Plus className="h-4 w-4" />
            Create Contract
          </Button>
          <Button onClick={() => setOpenUploadDialog(true)} variant="outline" className="gap-2">
            <Upload className="h-4 w-4" />
            Upload Contract
          </Button>
        </div>
      </div>

      {error && (
        <Alert variant="destructive" className="mb-4">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {loading ? (
        <div className="flex justify-center items-center h-64">
          <Loader2 className="animate-spin h-12 w-12 text-primary" />
        </div>
      ) : (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Input
                placeholder="Filter contracts..."
                value={globalFilter ?? ""}
                onChange={(event) => setGlobalFilter(event.target.value)}
                className="max-w-sm"
              />
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" className="ml-auto">
                    Columns <ChevronDown className="ml-2 h-4 w-4" />
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
                          {column.id}
                        </DropdownMenuCheckboxItem>
                      );
                    })}
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
            {Object.keys(rowSelection).length > 0 && (
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  className="h-8"
                  onClick={() => {
                    const selectedIds = table
                      .getSelectedRowModel()
                      .rows.map((row) => row.original.id);
                    // Add bulk delete functionality here
                    console.log("Selected IDs:", selectedIds);
                  }}
                >
                  Delete Selected
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="h-8"
                  onClick={() => {
                    const selectedIds = table
                      .getSelectedRowModel()
                      .rows.map((row) => row.original.id);
                    // Add bulk status update functionality here
                    console.log("Update Status for:", selectedIds);
                  }}
                >
                  Update Status
                </Button>
              </div>
            )}
          </div>

          <Card>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  {table.getHeaderGroups().map((headerGroup) => (
                    <TableRow key={headerGroup.id}>
                      {headerGroup.headers.map((header) => {
                        return (
                          <TableHead key={header.id}>
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
                        No results.
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
                    {[10, 20, 30, 40, 50].map((pageSize) => (
                      <SelectItem key={pageSize} value={`${pageSize}`}>
                        {pageSize}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex w-[100px] items-center justify-center text-sm font-medium">
                Page {table.getState().pagination.pageIndex + 1} of{" "}
                {table.getPageCount()}
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
        </div>
      )}

      {/* Create/Edit Dialog */}
      <Dialog open={openDialog} onOpenChange={setOpenDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {selectedContract ? 'Edit Data Contract' : 'Create Data Contract'}
            </DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSaveContract} className="space-y-4">
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
              <Label htmlFor="version">Version</Label>
              <Input
                id="version"
                value={version}
                onChange={(e) => setVersion(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="format">Format</Label>
              <Select value={format} onValueChange={setFormat}>
                <SelectTrigger>
                  <SelectValue placeholder="Select format" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="json">JSON</SelectItem>
                  <SelectItem value="yaml">YAML</SelectItem>
                  <SelectItem value="text">Plain Text</SelectItem>
                </SelectContent>
              </Select>
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
                  <SelectItem value="archived">Archived</SelectItem>
                </SelectContent>
              </Select>
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
              <Label htmlFor="description">Description</Label>
              <Input
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="contractText">Contract Definition</Label>
              <textarea
                id="contractText"
                value={contractText}
                onChange={(e) => setContractText(e.target.value)}
                className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                required
                placeholder={format === 'yaml' ? 
                  `# Example contract in YAML format
name: Example Contract
version: 1.0
domain: example
datasets:
  - name: example_dataset
    type: table
    schema:
      columns:
        - name: id
          type: string
          description: Primary identifier` :
                  format === 'json' ?
                  `{
  "name": "Example Contract",
  "version": "1.0",
  "domain": "example",
  "datasets": [
    {
      "name": "example_dataset",
      "type": "table",
      "schema": {
        "columns": [
          {
            "name": "id",
            "type": "string",
            "description": "Primary identifier"
          }
        ]
      }
    }
  ]
}` : 
                  '# Enter your contract definition here'
                }
              />
            </div>
            <DialogFooter>
              <Button type="submit">
                {selectedContract ? 'Update' : 'Create'} Contract
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Details Dialog */}
      <Dialog open={openDetails} onOpenChange={setOpenDetails}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
          <DialogHeader>
            <DialogTitle>Contract Details</DialogTitle>
            <DialogDescription>
              View and manage contract details
            </DialogDescription>
          </DialogHeader>
          <div className="flex-1 overflow-y-auto pr-4">
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Name</Label>
                  <div className="text-sm">{selectedContract?.name}</div>
                </div>
                <div className="space-y-2">
                  <Label>Version</Label>
                  <div className="text-sm">{selectedContract?.version}</div>
                </div>
                <div className="space-y-2">
                  <Label>Status</Label>
                  <div className="text-sm">
                    <Badge variant={selectedContract?.status === 'active' ? 'default' : 'secondary'}>
                      {selectedContract?.status}
                    </Badge>
                  </div>
                </div>
                <div className="space-y-2">
                  <Label>Owner</Label>
                  <div className="text-sm">{selectedContract?.owner}</div>
                </div>
                <div className="space-y-2">
                  <Label>Format</Label>
                  <div className="text-sm">{selectedContract?.format}</div>
                </div>
                <div className="space-y-2">
                  <Label>Created</Label>
                  <div className="text-sm">{selectedContract?.created}</div>
                </div>
                <div className="space-y-2">
                  <Label>Updated</Label>
                  <div className="text-sm">{selectedContract?.updated}</div>
                </div>
              </div>

              <div className="space-y-2">
                <Label>Description</Label>
                <div className="text-sm whitespace-pre-wrap">{selectedContract?.description}</div>
              </div>

              <div className="space-y-2">
                <Label>Contract Text</Label>
                <div className="relative">
                  <pre className="p-4 rounded-md bg-muted text-sm overflow-x-auto">
                    {selectedContract?.contract_text}
                  </pre>
                  <Button
                    variant="outline"
                    size="sm"
                    className="absolute top-2 right-2"
                    onClick={() => {
                      navigator.clipboard.writeText(selectedContract?.contract_text || '');
                      toast({
                        title: "Copied",
                        description: "Contract text copied to clipboard",
                      });
                    }}
                  >
                    Copy
                  </Button>
                </div>
              </div>

              {selectedContract?.schema && (
                <div className="space-y-2">
                  <Label>Schema</Label>
                  <div className="rounded-md border">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Field</TableHead>
                          <TableHead>Type</TableHead>
                          <TableHead>Required</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {selectedContract.schema.fields.map((field) => (
                          <TableRow key={field.name}>
                            <TableCell>{field.name}</TableCell>
                            <TableCell>{field.type}</TableCell>
                            <TableCell>
                              <Badge variant={field.required ? 'default' : 'secondary'}>
                                {field.required ? 'Yes' : 'No'}
                              </Badge>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                </div>
              )}

              {selectedContract?.validation_rules && selectedContract.validation_rules.length > 0 && (
                <div className="space-y-2">
                  <Label>Validation Rules</Label>
                  <div className="space-y-2">
                    {selectedContract.validation_rules.map((rule, index) => (
                      <div key={index} className="p-2 rounded-md bg-muted text-sm">
                        {rule}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {selectedContract?.dataProducts && selectedContract.dataProducts.length > 0 && (
                <div className="space-y-2">
                  <Label>Data Products</Label>
                  <div className="flex flex-wrap gap-2">
                    {selectedContract.dataProducts.map((product) => (
                      <Badge key={product} variant="outline">
                        {product}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpenDetails(false)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Upload Dialog */}
      <Dialog open={openUploadDialog} onOpenChange={setOpenUploadDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Upload Data Contract</DialogTitle>
          </DialogHeader>
          {uploadError && (
            <Alert variant="destructive" className="mb-4">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{uploadError}</AlertDescription>
            </Alert>
          )}
          <div
            {...getRootProps()}
            className={`border-2 border-dashed rounded-md p-6 text-center cursor-pointer ${
              isDragActive ? 'border-primary bg-primary/5' : 'border-muted-foreground/25'
            }`}
          >
            <input {...getInputProps()} />
            {uploading ? (
              <div className="flex justify-center">
                <Loader2 className="animate-spin h-8 w-8 text-primary" />
              </div>
            ) : (
              <>
                <p className="text-sm text-muted-foreground">
                  {isDragActive
                    ? 'Drop the file here'
                    : 'Drag and drop a contract file here, or click to select'}
                </p>
                <p className="text-xs text-muted-foreground mt-2">
                  Supported formats: JSON, YAML, or plain text
                </p>
              </>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
} 