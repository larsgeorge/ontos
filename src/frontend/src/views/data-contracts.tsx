import React, { useState, useEffect } from 'react';
import type { DataContractListItem, DataContractDraft } from '@/types/data-contract';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Card, CardContent } from '@/components/ui/card';
import { Plus, Pencil, Trash2, AlertCircle, Upload, ChevronDown, Loader2, KeyRound } from 'lucide-react';
// Removed Ajv and draft store imports with modal removal
import DataContractWizardDialog from '@/components/data-contracts/data-contract-wizard-dialog'
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
  const [contracts, setContracts] = useState<DataContractListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [openWizard, setOpenWizard] = useState(false);
  const [openUploadDialog, setOpenUploadDialog] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  // Table state
  const [sorting, setSorting] = useState<SortingState>([])
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([])
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({})
  const [rowSelection, setRowSelection] = useState({})
  const [globalFilter, setGlobalFilter] = useState("")

  // Removed inline editor form and validation state
  const [odcsPaste, setOdcsPaste] = useState<string>('')

  const setStaticSegments = useBreadcrumbStore((state) => state.setStaticSegments);
  const setDynamicTitle = useBreadcrumbStore((state) => state.setDynamicTitle);
  const navigate = useNavigate();

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

  // Removed ODCS schema load for inline JSON validation
  // Removed inline JSON validation

  // Persist draft to store on form changes
  // Removed draft persistence for inline editor

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

  // Removed per-row fetch for modal; navigation handles details

  const createContract = async (formData: DataContractDraft) => {
    try {
      const response = await fetch('/api/data-contracts', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Failed to create contract: ${errorText}`);
      }
      await fetchContracts();
      toast({ 
        title: 'Success', 
        description: 'Data contract created successfully' 
      });
      setOpenWizard(false); // Close the wizard on success
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to create contract';
      setError(message);
      toast({ 
        title: 'Error', 
        description: message, 
        variant: 'destructive' 
      });
      throw err; // Re-throw so wizard can handle it
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

  const handleBulkDelete = async (selectedIds: string[]) => {
    if (selectedIds.length === 0) return;
    if (!confirm(`Are you sure you want to delete ${selectedIds.length} selected contract(s)?`)) return;
    try {
      const results = await Promise.allSettled(selectedIds.map(async (id) => {
        const res = await fetch(`/api/data-contracts/${id}`, { method: 'DELETE' });
        if (!res.ok) throw new Error(`ID ${id}: delete failed`);
        return id;
      }));
      const successes = results.filter(r => r.status === 'fulfilled').length;
      const failures = results.filter(r => r.status === 'rejected').length;
      if (successes > 0) {
        toast({ title: 'Bulk Delete Success', description: `${successes} contract(s) deleted.` });
      }
      if (failures > 0) {
        const firstError = (results.find(r => r.status === 'rejected') as PromiseRejectedResult)?.reason?.message || 'Unknown error';
        toast({ title: 'Bulk Delete Error', description: `${failures} contract(s) could not be deleted. First error: ${firstError}`, variant: 'destructive' });
      }
      await fetchContracts();
    } catch (e) {
      toast({ title: 'Error', description: e instanceof Error ? e.message : 'Failed to bulk delete', variant: 'destructive' });
    }
  };

  const handleBulkRequestAccess = async (selectedIds: string[]) => {
    if (selectedIds.length === 0) return;
    try {
      const res = await fetch('/api/access-requests', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ entity_type: 'data_contract', entity_ids: selectedIds })
      });
      if (!res.ok) throw new Error('Failed to submit access requests');
      toast({ title: 'Request Sent', description: 'Access request submitted. You will be notified.' });
    } catch (e) {
      toast({ title: 'Error', description: e instanceof Error ? e.message : 'Failed to submit', variant: 'destructive' });
    }
  };

  const handleDeleteContract = async (id: string) => {
    if (!confirm('Are you sure you want to delete this contract?')) return;
    await deleteContract(id);
  };

  const handleExportOdcs = async (id: string, nameHint?: string) => {
    try {
      const response = await fetch(`/api/data-contracts/${id}/odcs/export`)
      if (!response.ok) throw new Error('Failed to export ODCS')
      const data = await response.json()
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${(nameHint || 'contract').toLowerCase().replace(/\s+/g, '_')}-odcs.json`
      a.click()
      window.URL.revokeObjectURL(url)
    } catch (e) {
      toast({ title: 'Export failed', description: e instanceof Error ? e.message : 'Unable to export ODCS', variant: 'destructive' })
    }
  }

  const handleDownloadContract = async (id: string, nameHint?: string, fmtHint?: string) => {
    try {
      const res = await fetch(`/api/data-contracts/${id}/export`)
      if (!res.ok) throw new Error('Failed to export contract')
      const text = await res.text()
      const blob = new Blob([text], { type: 'text/plain' })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${(nameHint || 'contract').toLowerCase().replace(/\s+/g, '_')}.${fmtHint || 'txt'}`
      a.click()
      window.URL.revokeObjectURL(url)
    } catch (e) {
      toast({ title: 'Export failed', description: e instanceof Error ? e.message : 'Unable to export contract', variant: 'destructive' })
    }
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

  const columns: ColumnDef<DataContractListItem>[] = [
    {
      id: "select",
      header: ({ table }) => (
        <Checkbox
          checked={table.getIsAllPageRowsSelected()}
          onCheckedChange={(value) => table.toggleAllPageRowsSelected(!!value)}
          onClick={(e) => e.stopPropagation()}
          aria-label="Select all"
        />
      ),
      cell: ({ row }) => (
        <Checkbox
          checked={row.getIsSelected()}
          onCheckedChange={(value) => row.toggleSelected(!!value)}
          onClick={(e) => e.stopPropagation()}
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
          <div className="flex space-x-1 justify-end">
            <Button
              variant="ghost"
              size="icon"
              onClick={(e) => { e.stopPropagation(); contract.id && navigate(`/data-contracts/${contract.id}`) }}
              title="Edit"
            >
              <Pencil className="h-4 w-4" />
            </Button>
            {contract.id && (
              <Button
                variant="ghost"
                size="icon"
                className="text-destructive hover:text-destructive"
                onClick={(e) => { e.stopPropagation(); handleDeleteContract(contract.id as string) }}
                title="Delete"
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            )}
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
      <h1 className="text-3xl font-bold mb-6 flex items-center gap-2">
        Data Contracts
      </h1>

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
          {/* Toolbar aligned like products view via shared DataTable */}
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
                    .map((column) => (
                      <DropdownMenuCheckboxItem
                        key={column.id}
                        className="capitalize"
                        checked={column.getIsVisible()}
                        onCheckedChange={(value) => column.toggleVisibility(!!value)}
                      >
                        {column.id}
                      </DropdownMenuCheckboxItem>
                    ))}
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
            <div className="flex items-center gap-2">
              <Button onClick={() => setOpenWizard(true)} className="gap-2 h-9" title="Create Data Contract">
                <Plus className="h-4 w-4" />
                New Contract
              </Button>
              <Button onClick={() => setOpenUploadDialog(true)} variant="outline" className="gap-2 h-9" title="Upload Contract">
                <Upload className="h-4 w-4" />
                Upload File
              </Button>
            </div>
          </div>

          {Object.keys(rowSelection).length > 0 && (() => {
            const selectedIds = Object.keys(rowSelection).map((k) => contracts[Number(k)].id!).filter(Boolean);
            const count = selectedIds.length;
            return (
              <div className="flex items-center justify-end py-2">
                <div className="text-sm text-muted-foreground mr-3">{count} selected</div>
                <div className="mx-2 h-6 w-px bg-muted-foreground/25" />
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-9 gap-1"
                    onClick={() => handleBulkRequestAccess(selectedIds)}
                    title="Request access for selected"
                  >
                    <KeyRound className="w-4 h-4 mr-1" />
                    Request Access ({count})
                  </Button>
                  <Button
                    variant="destructive"
                    size="sm"
                    className="h-9 gap-1"
                    onClick={() => handleBulkDelete(selectedIds)}
                    title="Delete selected"
                  >
                    <Trash2 className="w-4 h-4 mr-1" />
                    Delete Selected ({count})
                  </Button>
                </div>
              </div>
            );
          })()}

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
                        className="cursor-pointer"
                        onClick={() => {
                          const id = row.original.id
                          if (id) navigate(`/data-contracts/${id}`)
                        }}
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
          <div className="mt-4">
            <Label htmlFor="odcsPaste">Or paste ODCS JSON</Label>
            <textarea
              id="odcsPaste"
              placeholder="Paste ODCS JSON"
              className="flex min-h-[120px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
              value={odcsPaste}
              onChange={(e) => setOdcsPaste(e.target.value)}
              onBlur={async () => {
                const value = odcsPaste.trim()
                if (!value) return
                try {
                  const body = JSON.parse(value)
                  const res = await fetch('/api/data-contracts/odcs/import', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(body)
                  })
                  if (!res.ok) throw new Error('Failed to import ODCS JSON')
                  await fetchContracts()
                  setOpenUploadDialog(false)
                  setOdcsPaste('')
                  toast({ title: 'Imported', description: 'ODCS JSON imported successfully' })
                } catch (err) {
                  setUploadError(err instanceof Error ? err.message : 'Failed to import ODCS JSON')
                }
              }}
            />
          </div>
        </DialogContent>
      </Dialog>

      {/* Wizard Dialog */}
      <DataContractWizardDialog
        isOpen={openWizard}
        onOpenChange={setOpenWizard}
        initial={null}
        onSubmit={async (payload) => {
          const odcsContract = {
            kind: 'DataContract',
            apiVersion: 'v3.0.2',
            name: payload.name,
            version: payload.version,
            status: payload.status,
            owner: payload.owner,
            domainId: payload.domainId,
            tenant: payload.tenant,
            dataProduct: payload.dataProduct,
            description: payload.description,
            schema: payload.schema || [],
          }
          
          await createContract({
            name: payload.name,
            version: payload.version,
            status: payload.status,
            owner: payload.owner,
            domainId: payload.domainId,
            tenant: payload.tenant,
            dataProduct: payload.dataProduct,
            description: payload.description,
            schema: payload.schema,
            format: 'json',
            contract_text: JSON.stringify(odcsContract, null, 2),
          })
        }}
      />
    </div>
  );
} 