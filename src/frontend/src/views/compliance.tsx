import React, { useState, useEffect, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { useToast } from '@/hooks/use-toast';
import { Plus, Scale, MoreHorizontal, ChevronDown } from 'lucide-react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  DropdownMenuCheckboxItem,
} from "@/components/ui/dropdown-menu";
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
} from "@tanstack/react-table";
import { Checkbox } from "@/components/ui/checkbox";
import { useApi } from '@/hooks/use-api';
import useBreadcrumbStore from '@/stores/breadcrumb-store';

interface CompliancePolicy {
  id: string;
  name: string;
  description: string;
  rule: string;
  compliance: number;
  history: number[];
  created_at: string;
  updated_at: string;
  is_active: boolean;
  severity: 'low' | 'medium' | 'high' | 'critical';
  category: string;
}

interface ComplianceStats {
  overall_compliance: number;
  active_policies: number;
  critical_issues: number;
}

interface ComplianceApiResponse {
  policies: CompliancePolicy[];
  stats: ComplianceStats;
}

export default function Compliance() {
  const { toast } = useToast();
  const { get: apiGet, post: apiPost, put: apiPut, delete: apiDeleteApi, loading: apiIsLoading } = useApi();
  const setStaticSegments = useBreadcrumbStore((state) => state.setStaticSegments);
  const setDynamicTitle = useBreadcrumbStore((state) => state.setDynamicTitle);
  const [policies, setPolicies] = useState<CompliancePolicy[]>([]);
  const [stats, setStats] = useState<ComplianceStats>({
    overall_compliance: 0,
    active_policies: 0,
    critical_issues: 0
  });
  const [selectedPolicy, setSelectedPolicy] = useState<CompliancePolicy | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [sorting, setSorting] = useState<SortingState>([]);
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({});
  const [rowSelection, setRowSelection] = useState({});
  const [globalFilter, setGlobalFilter] = useState("");
  const [componentError, setComponentError] = useState<string | null>(null);

  const loadPolicies = useCallback(async () => {
    setComponentError(null);
    try {
      const response = await apiGet<ComplianceApiResponse>('/api/compliance/policies');
      if (response.error) {
        throw new Error(response.error);
      }
      if (response.data) {
        setPolicies(response.data.policies || []);
        setStats(response.data.stats || {
          overall_compliance: 0,
          active_policies: 0,
          critical_issues: 0
        });
      } else {
        setPolicies([]);
        setStats({ overall_compliance: 0, active_policies: 0, critical_issues: 0 });
        throw new Error("No data received from compliance policies endpoint.");
      }
    } catch (error) {
      console.error('Error loading policies:', error);
      const errorMessage = error instanceof Error ? error.message : "Failed to load compliance policies";
      setComponentError(errorMessage);
      toast({
        title: "Error Loading Policies",
        description: errorMessage,
        variant: "destructive"
      });
      setPolicies([]);
      setStats({ overall_compliance: 0, active_policies: 0, critical_issues: 0 });
    }
  }, [apiGet, toast]);

  useEffect(() => {
    loadPolicies();
    setStaticSegments([]);
    setDynamicTitle('Compliance');

    return () => {
        setStaticSegments([]);
        setDynamicTitle(null);
    };
  }, [loadPolicies, setStaticSegments, setDynamicTitle]);

  const handleSave = async (event: React.FormEvent) => {
    event.preventDefault();
    setComponentError(null);
    try {
      const form = event.target as HTMLFormElement;
      const policyData: Omit<CompliancePolicy, 'id' | 'created_at' | 'updated_at' | 'compliance' | 'history'> & Partial<Pick<CompliancePolicy, 'id' | 'compliance' | 'history' | 'created_at' | 'updated_at'>> = {
        name: (form.querySelector('#name') as HTMLInputElement).value,
        description: (form.querySelector('#description') as HTMLTextAreaElement).value,
        category: (form.querySelector('select[name="category"]') as HTMLSelectElement)?.value || 'General',
        severity: (form.querySelector('select[name="severity"]') as HTMLSelectElement)?.value as CompliancePolicy['severity'] || 'medium',
        rule: (form.querySelector('#rule') as HTMLTextAreaElement).value,
        is_active: selectedPolicy?.is_active ?? true,
      };

      let response;
      if (selectedPolicy?.id) {
        const updatePayload: CompliancePolicy = {
          ...selectedPolicy,
          ...policyData,
          updated_at: new Date().toISOString(),
        };
        response = await apiPut<CompliancePolicy>(`/api/compliance/policies/${selectedPolicy.id}`, updatePayload);
      } else {
        const createPayload: Omit<CompliancePolicy, 'id'> = {
          ...policyData,
          compliance: 0,
          history: [],
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        } as Omit<CompliancePolicy, 'id'>;
        response = await apiPost<CompliancePolicy>('/api/compliance/policies', createPayload);
      }
      
      if (response.error || !response.data) {
        throw new Error(response.error || 'Failed to save policy: No data returned');
      }
      
      toast({
        title: "Success",
        description: `Policy '${response.data.name}' saved successfully`
      });
      
      setIsDialogOpen(false);
      loadPolicies();
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to save policy";
      setComponentError(errorMessage);
      toast({
        variant: "destructive",
        title: "Error Saving Policy",
        description: errorMessage
      });
    }
  };

  const handleDelete = async (id: string) => {
    setComponentError(null);
    try {
      const response = await apiDeleteApi(`/api/compliance/policies/${id}`);
      
      if (response.error) {
        throw new Error(response.error || 'Failed to delete policy');
      }
      
      toast({
        title: "Success",
        description: "Policy deleted successfully"
      });
      
      loadPolicies();
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to delete policy";
      setComponentError(errorMessage);
      toast({
        variant: "destructive",
        title: "Error Deleting Policy",
        description: errorMessage
      });
    }
  };

  const overallCompliance = stats.overall_compliance;
  const activePolicies = stats.active_policies;
  const criticalIssues = stats.critical_issues;

  const handleCreateRule = () => {
    setSelectedPolicy(null);
    setIsDialogOpen(true);
  };

  const handleEditRule = (policy: CompliancePolicy) => {
    setSelectedPolicy(policy);
    setIsDialogOpen(true);
  };

  const getComplianceColor = (score: number) => {
    if (score >= 90) return 'text-green-600';
    if (score >= 70) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getSeverityBadge = (severity: string) => {
    const variants = {
      low: 'bg-blue-100 text-blue-800',
      medium: 'bg-yellow-100 text-yellow-800',
      high: 'bg-orange-100 text-orange-800',
      critical: 'bg-red-100 text-red-800'
    };
    return variants[severity as keyof typeof variants] || 'bg-gray-100 text-gray-800';
  };

  const columns: ColumnDef<CompliancePolicy>[] = [
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
      accessorKey: "category",
      header: "Category",
      cell: ({ row }) => (
        <Badge variant="outline">{row.getValue("category")}</Badge>
      ),
    },
    {
      accessorKey: "severity",
      header: ({ column }) => {
        return (
          <Button
            variant="ghost"
            onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
          >
            Severity
            <ChevronDown className="ml-2 h-4 w-4" />
          </Button>
        );
      },
      cell: ({ row }) => (
        <Badge className={getSeverityBadge(row.getValue("severity"))}>
          {row.getValue("severity")}
        </Badge>
      ),
    },
    {
      accessorKey: "compliance",
      header: ({ column }) => {
        return (
          <Button
            variant="ghost"
            onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
          >
            Compliance
            <ChevronDown className="ml-2 h-4 w-4" />
          </Button>
        );
      },
      cell: ({ row }) => (
        <div className={`font-semibold ${getComplianceColor(row.getValue("compliance"))}`}>
          {row.getValue("compliance")}%
        </div>
      ),
    },
    {
      accessorKey: "is_active",
      header: "Status",
      cell: ({ row }) => (
        <Badge variant={row.getValue("is_active") ? "default" : "secondary"}>
          {row.getValue("is_active") ? "Active" : "Inactive"}
        </Badge>
      ),
    },
    {
      id: "actions",
      enableHiding: false,
      cell: ({ row }) => {
        const policy = row.original;
        return (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="h-8 w-8 p-0">
                <span className="sr-only">Open menu</span>
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuLabel>Actions</DropdownMenuLabel>
              <DropdownMenuItem onClick={() => handleEditRule(policy)}>
                Edit
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                className="text-red-600"
                onClick={() => handleDelete(policy.id)}
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
    data: policies,
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
          <Scale className="w-8 h-8" />
          Compliance
        </h1>
        <Button onClick={handleCreateRule} className="gap-2" disabled={apiIsLoading}>
          <Plus className="h-4 w-4" />
          Create Rule
        </Button>
      </div>

      {apiIsLoading && !isDialogOpen && (
        <div className="flex justify-center items-center h-64">
          <p>Loading compliance data...</p>
        </div>
      )}

      {componentError && (
         <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative mb-4" role="alert">
           <strong className="font-bold">Error: </strong>
           <span className="block sm:inline">{componentError}</span>
         </div>
      )}

      {!apiIsLoading && !componentError && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Overall Compliance</CardTitle>
              </CardHeader>
              <CardContent>
                <div className={`text-3xl font-bold ${getComplianceColor(overallCompliance)}`}>
                  {overallCompliance.toFixed(0)}%
                </div>
                <p className="text-sm text-muted-foreground mt-2">Across all rules</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Active Rules</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold">{activePolicies}</div>
                <p className="text-sm text-muted-foreground mt-2">Currently enforced</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Critical Issues</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold text-red-600">{criticalIssues}</div>
                <p className="text-sm text-muted-foreground mt-2">Require attention</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Last Updated</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold">Today</div>
                <p className="text-sm text-muted-foreground mt-2">12:30 PM</p>
              </CardContent>
            </Card>
          </div>

          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Input
                  placeholder="Filter rules..."
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
                      console.log("Toggle Status for:", selectedIds);
                    }}
                  >
                    Toggle Status
                  </Button>
                </div>
              )}
            </div>

            <div className="rounded-md border">
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
            </div>

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

          <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>
                  {selectedPolicy ? 'Edit Compliance Rule' : 'Create New Compliance Rule'}
                </DialogTitle>
              </DialogHeader>
              <form onSubmit={handleSave} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="name">Name</Label>
                  <Input
                    id="name"
                    defaultValue={selectedPolicy?.name}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="description">Description</Label>
                  <Textarea
                    id="description"
                    defaultValue={selectedPolicy?.description}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="category">Category</Label>
                  <Select defaultValue={selectedPolicy?.category}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select category" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Security">Security</SelectItem>
                      <SelectItem value="Data Quality">Data Quality</SelectItem>
                      <SelectItem value="Privacy">Privacy</SelectItem>
                      <SelectItem value="Governance">Governance</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="severity">Severity</Label>
                  <Select defaultValue={selectedPolicy?.severity}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select severity" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="low">Low</SelectItem>
                      <SelectItem value="medium">Medium</SelectItem>
                      <SelectItem value="high">High</SelectItem>
                      <SelectItem value="critical">Critical</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="rule">Rule Code</Label>
                  <Textarea
                    id="rule"
                    defaultValue={selectedPolicy?.rule}
                    className="font-mono text-sm"
                    rows={8}
                    required
                    placeholder="Enter the compliance rule in Compliance DSL format"
                  />
                </div>
                <DialogFooter>
                  <Button type="button" variant="outline" onClick={() => setIsDialogOpen(false)} disabled={apiIsLoading}>
                    Cancel
                  </Button>
                  <Button type="submit" disabled={apiIsLoading}>
                    {apiIsLoading ? 'Saving...' : 'Save'}
                  </Button>
                </DialogFooter>
              </form>
            </DialogContent>
          </Dialog>
        </>
      )}
    </div>
  );
} 