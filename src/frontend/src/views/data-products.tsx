import React, { useState, useEffect, useRef, useMemo } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Plus, Pencil, Trash2, AlertCircle, Database, ChevronDown, Upload, X, Loader2, Sparkles, Table, Workflow, KeyRound } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Column,
  ColumnDef,
} from "@tanstack/react-table"
import { useApi } from '@/hooks/use-api';
import { DataProduct, DataProductStatus, DataProductArchetype, DataProductOwner } from '@/types/data-product';
import { useToast } from "@/hooks/use-toast"
import { Toaster } from "@/components/ui/toaster"
import { RelativeDate } from '@/components/common/relative-date';
import { useNavigate } from 'react-router-dom';
import { DataTable } from "@/components/ui/data-table";
import DataProductWizardDialog from '@/components/data-products/data-product-wizard-dialog';
import { usePermissions } from '@/stores/permissions-store';
import { FeatureAccessLevel } from '@/types/settings';
import { useNotificationsStore } from '@/stores/notifications-store';
import DataProductGraphView from '@/components/data-products/data-product-graph-view';
import useBreadcrumbStore from '@/stores/breadcrumb-store';
import { useDomains } from '@/hooks/use-domains';

// --- Helper Function Type Definition --- 
type CheckApiResponseFn = <T>(
    response: { data?: T | { detail?: string }, error?: string | null | undefined },
    name: string
) => T;

// --- Helper Function Implementation (outside component) --- 
const checkApiResponse: CheckApiResponseFn = (response, name) => {
    if (response.error) {
        throw new Error(`${name} fetch failed: ${response.error}`);
    }
    // Check if data itself contains a FastAPI error detail
    if (response.data && typeof response.data === 'object' && 'detail' in response.data && typeof response.data.detail === 'string') {
        throw new Error(`${name} fetch failed: ${response.data.detail}`);
    }
    // Ensure data is not null/undefined before returning
    if (response.data === null || response.data === undefined) {
        throw new Error(`${name} fetch returned null or undefined data.`);
    }
    // Type assertion after checks - implicit from signature
    return response.data as any; // Use 'as any' temporarily if needed, but the signature defines T
};

// --- Component Code ---

export default function DataProducts() {
  const [products, setProducts] = useState<DataProduct[]>([]);
  const [isWizardOpen, setIsWizardOpen] = useState(false);
  const [productToEdit, setProductToEdit] = useState<DataProduct | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Use the imported types for state
  const [statuses, setStatuses] = useState<DataProductStatus[]>([]);
  const [owners, setOwners] = useState<DataProductOwner[]>([]);

  // Add state for product types
  const [productTypes, setProductTypes] = useState<string[]>([]);

  const [viewMode, setViewMode] = useState<'table' | 'graph'>('table');

  const api = useApi();
  const { get, post, delete: deleteApi } = api;
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { toast } = useToast();
  const navigate = useNavigate();
  const { getDomainName, getDomainIdByName } = useDomains();
  const refreshNotifications = useNotificationsStore((state) => state.refreshNotifications);
  const setStaticSegments = useBreadcrumbStore((state) => state.setStaticSegments);
  const setDynamicTitle = useBreadcrumbStore((state) => state.setDynamicTitle);

  // Get permissions
  const { hasPermission, isLoading: permissionsLoading } = usePermissions();
  const featureId = 'data-products'; // ID for this feature

  // Determine if user has specific access levels
  const canRead = !permissionsLoading && hasPermission(featureId, FeatureAccessLevel.READ_ONLY);
  const canWrite = !permissionsLoading && hasPermission(featureId, FeatureAccessLevel.READ_WRITE);
  const canAdmin = !permissionsLoading && hasPermission(featureId, FeatureAccessLevel.ADMIN);

  // Fetch initial data for the table and dropdowns
  useEffect(() => {
    // Set breadcrumbs for this top-level view
    setStaticSegments([]); // No static parents other than Home
    setDynamicTitle('Data Products');

    const loadInitialData = async () => {
      setLoading(true);
      setError(null);
      try {
        // Fetch products and dropdown values concurrently
        const [productsResp, statusesResp, ownersResp, typesResp] = await Promise.all([
          get<DataProduct[]>('/api/data-products'),
          get<DataProductStatus[]>('/api/data-products/statuses'),
          get<DataProductOwner[]>('/api/data-products/owners'),
          get<string[]>('/api/data-products/types'), // Fetch product types
        ]);

        // Check responses using the helper
        const productsData = checkApiResponse(productsResp, 'Products');
        const statusesData = checkApiResponse(statusesResp, 'Statuses');
        const ownersData = checkApiResponse(ownersResp, 'Owners');
        const typesData = checkApiResponse(typesResp, 'Product Types');

        setProducts(Array.isArray(productsData) ? productsData : []);
        setStatuses(Array.isArray(statusesData) ? statusesData : []);
        setOwners(Array.isArray(ownersData) ? ownersData : []);
        setProductTypes(Array.isArray(typesData) ? typesData : []); // Set product types

      } catch (err: any) {
        console.error('Error fetching initial data:', err);
        setError(err.message || 'Failed to load initial data');
        // Reset state on error
        setProducts([]);
        setStatuses([]);
        setProductTypes([]); // Reset types on error
        setOwners([]);
      } finally {
        setLoading(false);
      }
    };
    // Only load initial data if the user has permission and permissions are loaded
    if (!permissionsLoading && canRead) {
        loadInitialData();
    } else if (!permissionsLoading && !canRead) {
        // Ensure loading is stopped if permissions are loaded but access denied.
        // The permission denied message is handled by the render logic.
        setLoading(false);
        // Clear breadcrumbs if no permission
        setStaticSegments([]);
        setDynamicTitle(null);
    }

    // Cleanup breadcrumbs on unmount
    return () => {
        setStaticSegments([]);
        setDynamicTitle(null);
    };
  }, [get, canRead, permissionsLoading, setStaticSegments, setDynamicTitle]);

  // Function to refetch products list
  const fetchProducts = async () => {
    if (!canRead) return;
    try {
      const response = await get<DataProduct[]>('/api/data-products');
      const productsData = checkApiResponse(response, 'Products Refetch');
      setProducts(Array.isArray(productsData) ? productsData : []);
    } catch (err: any) {
      console.error('Error refetching products:', err);
      setError(err.message || 'Failed to refresh products list');
      toast({ title: 'Error', description: `Failed to refresh products: ${err.message}`, variant: 'destructive' });
    } 
  };

  // --- Wizard Open Handler ---
  const handleOpenWizard = (product?: DataProduct) => {
      if (!canWrite && !product) { // Need write permission to create
          toast({ title: "Permission Denied", description: "You do not have permission to create data products.", variant: "destructive" });
          return;
      }
       if (!canWrite && product) { // Need write permission to edit
          toast({ title: "Permission Denied", description: "You do not have permission to edit data products.", variant: "destructive" });
          return;
      }
      setProductToEdit(product || null);
      setIsWizardOpen(true); // Use the new state variable
  };

  // --- Wizard Submit Success Handler ---
  const handleWizardSubmitSuccess = (savedProduct: DataProduct) => {
    fetchProducts();
  };

  // --- CRUD Handlers (Keep Delete and Upload here) ---
  const handleDeleteProduct = async (id: string, skipConfirm = false) => {
      if (!canAdmin) {
          toast({ title: "Permission Denied", description: "You do not have permission to delete data products.", variant: "destructive" });
          return;
      }
      if (!skipConfirm && !confirm('Are you sure you want to delete this data product?')) {
          return;
      }
      try {
          await deleteApi(`/api/data-products/${id}`);
          toast({ title: 'Success', description: 'Data product deleted.' });
          fetchProducts();
      } catch (err: any) {
          const errorMsg = err.message || 'Failed to delete data product.';
          toast({ title: 'Error', description: errorMsg, variant: 'destructive' });
          setError(errorMsg);
          if (skipConfirm) throw err;
      }
  };

  // Bulk Delete Handler
  const handleBulkDelete = async (selectedRows: DataProduct[]) => {
      if (!canAdmin) {
          toast({ title: "Permission Denied", description: "You do not have permission to bulk delete.", variant: "destructive" });
          return;
      }
      const selectedIds = selectedRows.map(r => r.id).filter((id): id is string => !!id);
      if (selectedIds.length === 0) return;
      if (!confirm(`Are you sure you want to delete ${selectedIds.length} selected product(s)?`)) return;

      // Track individual delete statuses
      const results = await Promise.allSettled(selectedIds.map(async (id) => {
          try {
              await deleteApi(`/api/data-products/${id}`);
              // If deleteApi throws on error, we won't reach here on failure
              // If it returns an object like { error: string } on failure, 
              // we need to check that, but the current structure assumes throw.
              return id; // Return ID on success
          } catch (err: any) {
              // Re-throw the error with the ID for better context in the main handler
              throw new Error(`ID ${id}: ${err.message || 'Unknown delete error'}`);
          }
      }));

      const successes = results.filter(r => r.status === 'fulfilled').length;
      const failures = results.filter(r => r.status === 'rejected').length;

      if (successes > 0) {
          toast({ title: 'Bulk Delete Success', description: `${successes} product(s) deleted.` });
      }
      if (failures > 0) {
          const firstError = (results.find(r => r.status === 'rejected') as PromiseRejectedResult)?.reason?.message || 'Unknown error';
          toast({ 
              title: 'Bulk Delete Error', 
              description: `${failures} product(s) could not be deleted. First error: ${firstError}`, 
              variant: 'destructive' 
          });
      }
      fetchProducts();
  };

  // Bulk Request Access
  const handleBulkRequestAccess = async (selectedRows: DataProduct[]) => {
      const selectedIds = selectedRows.map(r => r.id).filter((id): id is string => !!id);
      if (selectedIds.length === 0) return;
      try {
          toast({ title: 'Submitting', description: `Requesting access for ${selectedIds.length} item(s)...` });
          const res = await fetch('/api/access-requests', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ entity_type: 'data_product', entity_ids: selectedIds })
          });
          if (!res.ok) throw new Error('Failed to submit access requests');
          toast({ title: 'Request Sent', description: 'Access request submitted. You will be notified.' });
          refreshNotifications();
      } catch (e: any) {
          toast({ title: 'Error', description: e.message || 'Failed to submit access requests', variant: 'destructive' });
      }
  };

  // Keep File Upload Handlers
  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    if (!canWrite) {
      toast({ title: "Permission Denied", description: "You do not have permission to upload data products.", variant: "destructive" });
      if (fileInputRef.current) fileInputRef.current.value = "";
      return;
    }
    const file = event.target.files?.[0];
    if (!file) return;
    setIsUploading(true);
    setError(null);
    const formData = new FormData();
    formData.append('file', file);
    try {
      const response = await post<{ count: number }>('/api/data-products/upload', formData);

      if (response.error) {
         throw new Error(response.error || 'Unknown upload error');
      }

      const count = response.data?.count ?? 0;
      toast({
        title: "Upload Successful",
        description: `Successfully processed ${file.name}. ${count} product(s) processed.`,
      });
      await fetchProducts();

    } catch (err: any) {
      console.error('Error uploading file:', err);
      const errorMsg = err.message || 'An unexpected error occurred during upload.';
      toast({
          title: "Upload Failed",
          description: errorMsg,
          variant: "destructive"
      });
      setError(errorMsg);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const triggerFileUpload = () => {
    fileInputRef.current?.click();
  };

  // --- Genie Space Handler ---
  const handleCreateGenieSpace = async (selectedRows: DataProduct[]) => {
      if (!canWrite) {
          toast({ title: "Permission Denied", description: "You do not have permission to create Genie Spaces.", variant: "destructive" });
          return;
      }
      const selectedIds = selectedRows.map(r => r.id).filter((id): id is string => !!id);
      if (selectedIds.length === 0) {
          toast({ title: "No Selection", description: "Please select at least one data product.", variant: "default" });
          return;
      }

      if (!confirm(`Create a Genie Space for ${selectedIds.length} selected product(s)?`)) {
          return;
      }

      toast({ title: 'Initiating Genie Space', description: `Requesting Genie Space creation for ${selectedIds.length} product(s)...` });

      try {
          const response = await post('/api/data-products/genie-space', { product_ids: selectedIds });
          
          if (response.error) {
              throw new Error(response.error);
          }
          if (response.data && typeof response.data === 'object' && 'detail' in response.data) {
              throw new Error(response.data.detail as string);
          }

          toast({ title: 'Request Submitted', description: `Genie Space creation initiated. You'll be notified.` });
          refreshNotifications();

      } catch (err: any) {
          console.error('Error initiating Genie Space creation:', err);
          const errorMsg = err.message || 'Failed to start Genie Space creation.';
          toast({ title: 'Error', description: errorMsg, variant: 'destructive' });
          setError(errorMsg);
      }
  };

  // --- Define these outside the columns definition --- 
  const handleEditClick = (product: DataProduct) => {
      handleOpenWizard(product);
  };

  const handleDeleteClick = (product: DataProduct) => {
       if (product.id) {
          handleDeleteProduct(product.id, false);
       }
  };

  // Keep Status Color Helper (used by table column)
  const getStatusColor = (status: string | undefined): "default" | "secondary" | "destructive" | "outline" => {
    const lowerStatus = status?.toLowerCase() || '';
    if (lowerStatus.includes('active')) return 'default';
    if (lowerStatus.includes('development')) return 'secondary';
    if (lowerStatus.includes('retired') || lowerStatus.includes('deprecated')) return 'outline';
    if (lowerStatus.includes('deleted') || lowerStatus.includes('archived')) return 'destructive';
    return 'default';
  };

  // --- Column Definitions (Keep as they are for the DataTable) ---
  const columns = useMemo<ColumnDef<DataProduct>[]>(() => [
    {
      accessorKey: "info.title",
      header: ({ column }: { column: Column<DataProduct, unknown> }) => (
        <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Title <ChevronDown className="ml-2 h-4 w-4" />
        </Button>
      ),
      cell: ({ row }) => {
        const product = row.original;
        const domainName = product.info.domain;
        const domainId = getDomainIdByName(domainName);
        return (
          <div>
            <div className="font-medium">{product.info.title}</div>
            {domainName && domainId && (
              <div
                className="text-xs text-muted-foreground cursor-pointer hover:underline"
                onClick={(e) => {
                  e.stopPropagation();
                  navigate(`/data-domains/${domainId}`);
                }}
              >
                ↳ Domain: {domainName}
              </div>
            )}
          </div>
        );
      },
    },
    {
      accessorKey: "info.owner",
      header: ({ column }: { column: Column<DataProduct, unknown> }) => (
        <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Owner <ChevronDown className="ml-2 h-4 w-4" />
        </Button>
      ),
      cell: ({ row }) => <div>{row.original.info.owner}</div>,
    },
    {
      accessorKey: "version",
      header: ({ column }: { column: Column<DataProduct, unknown> }) => (
        <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Version <ChevronDown className="ml-2 h-4 w-4" />
        </Button>
      ),
      cell: ({ row }) => <Badge variant="secondary">{row.original.version}</Badge>,
    },
    {
      accessorKey: "productType",
      header: ({ column }: { column: Column<DataProduct, unknown> }) => (
        <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Type <ChevronDown className="ml-2 h-4 w-4" />
        </Button>
      ),
      cell: ({ row }) => (
        row.original.productType ? 
        <Badge variant="outline">{row.original.productType}</Badge> : 'N/A'
      ),
    },
    {
      accessorKey: "info.status",
      header: ({ column }: { column: Column<DataProduct, unknown> }) => (
        <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Status <ChevronDown className="ml-2 h-4 w-4" />
        </Button>
      ),
      cell: ({ row }) => (
        row.original.info.status ?
        <Badge variant={getStatusColor(row.original.info.status)}>{row.original.info.status}</Badge> : 'N/A'
      ),
    },
    {
      accessorKey: "tags",
      header: "Tags",
      cell: ({ row }) => {
        const tags = row.original.tags || [];
        return (
          <div className="flex flex-wrap gap-1">
            {tags.map((tag: string) => (
              <Badge key={tag} variant="secondary">{tag}</Badge>
            ))}
          </div>
        );
      },
      enableSorting: false,
    },
    {
      accessorKey: "created_at",
      header: ({ column }: { column: Column<DataProduct, unknown> }) => (
        <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Created <ChevronDown className="ml-2 h-4 w-4" />
        </Button>
      ),
      cell: ({ row }) => row.original.created_at ? <RelativeDate date={row.original.created_at} /> : 'N/A',
    },
    {
      accessorKey: "updated_at",
      header: ({ column }: { column: Column<DataProduct, unknown> }) => (
        <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Updated <ChevronDown className="ml-2 h-4 w-4" />
        </Button>
      ),
      cell: ({ row }) => <RelativeDate date={row.original.updated_at} />,
    },
    {
      id: "actions",
      enableHiding: false,
      cell: ({ row }) => {
        const product = row.original;
        return (
          <div className="flex space-x-1 justify-end">
            <Button
                variant="ghost"
                size="icon"
                onClick={() => handleEditClick(product)}
                disabled={!canWrite || permissionsLoading}
                title={canWrite ? "Edit" : "Edit (Permission Denied)"}
            >
              <Pencil className="h-4 w-4" />
            </Button>
            {product.id && (
              <Button
                variant="ghost"
                size="icon"
                className="text-destructive hover:text-destructive"
                onClick={(e) => {
                    e.stopPropagation();
                    handleDeleteClick(product);
                }}
                disabled={!canAdmin || permissionsLoading}
                title={canAdmin ? "Delete" : "Delete (Permission Denied)"}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            )}
          </div>
        );
      },
    },
  ], [handleOpenWizard, handleDeleteProduct, getStatusColor, canWrite, canAdmin, permissionsLoading, navigate]);

  // --- Button Variant Logic (Moved outside) ---
  const tableButtonVariant = viewMode === 'table' ? 'secondary' : 'ghost';
  const graphButtonVariant = viewMode === 'graph' ? 'secondary' : 'ghost';

  // --- Render Logic ---
  return (
    <div className="py-6">
      <h1 className="text-3xl font-bold mb-6 flex items-center gap-2">
        <Database className="w-8 h-8" />
        Data Products
      </h1>

      {/* 1. Check Permissions Loading */}
      {permissionsLoading ? (
        <div className="flex justify-center items-center h-64">
          <Loader2 className="h-12 w-12 animate-spin text-primary" />
        </div>
      ) : !canRead ? (
        // 2. Check Read Permission (if permissions loaded)
        <Alert variant="destructive" className="mb-4">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>You do not have permission to view data products.</AlertDescription>
        </Alert>
      ) : loading ? (
        // 3. Check Data Loading (if permissions OK)
        <div className="flex justify-center items-center h-64">
          <Loader2 className="h-12 w-12 animate-spin text-primary" />
        </div>
      ) : error ? (
         // 4. Check Data Loading Error (if permissions OK and data loading finished)
        <Alert variant="destructive" className="mb-4">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription> {/* Display the actual data loading error */}
        </Alert>
      ) : (
        // 5. Render Content (if permissions OK and data loaded without error)
        viewMode === 'table' ? (
          <DataTable
            columns={columns}
            data={products}
            searchColumn="info.title"
            toolbarActions={
              <>
                {/* Create Button - Conditionally enabled */}
                <Button
                    onClick={() => handleOpenWizard()}
                    className="gap-2 h-9"
                    disabled={!canWrite || permissionsLoading}
                    title={canWrite ? "Create Data Product" : "Create (Permission Denied)"}
                >
                  <Plus className="h-4 w-4" />
                  Create Product
                </Button>
                {/* Upload Button - Conditionally enabled */}
                <Button
                    onClick={triggerFileUpload}
                    className="gap-2 h-9"
                    variant="outline"
                    disabled={isUploading || !canWrite || permissionsLoading}
                    title={canWrite ? "Upload Data Product File" : "Upload (Permission Denied)"}
                >
                  <Upload className="h-4 w-4" />
                  {isUploading ? (<><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Uploading...</>) : 'Upload File'}
                </Button>
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileChange}
                  accept=".json,.yaml,.yml"
                  style={{ display: 'none' }}
                />
                {/* View Toggle Buttons - Moved Here */}
                <div className="flex items-center gap-1 border rounded-md p-0.5 ml-auto">
                    <Button
                        variant={tableButtonVariant}
                        size="sm"
                        onClick={() => setViewMode('table')}
                        className="h-8 px-2"
                        title="Table View"
                    >
                        <Table className="h-4 w-4" />
                    </Button>
                    <Button
                        variant={graphButtonVariant}
                        size="sm"
                        onClick={() => setViewMode('graph')}
                        className="h-8 px-2"
                        title="Graph View"
                    >
                        <Workflow className="h-4 w-4" />
                    </Button>
                </div>
              </>
            }
            bulkActions={(selectedRows) => {
              // Remove view toggle logic from here
              return (
                <>
                  <Button
                      variant="outline"
                      size="sm"
                      className="h-9 gap-1"
                      onClick={() => handleBulkRequestAccess(selectedRows)}
                      disabled={selectedRows.length === 0}
                      title="Request access for selected"
                  >
                      <KeyRound className="w-4 h-4 mr-1" />
                      Request Access ({selectedRows.length})
                  </Button>
                  <Button
                      variant="outline"
                      size="sm"
                      className="h-9 gap-1"
                      onClick={() => handleCreateGenieSpace(selectedRows)}
                      disabled={selectedRows.length === 0 || !canWrite}
                      title={canWrite ? "Create Genie Space from selected" : "Create Genie Space (Permission Denied)"}
                  >
                      <Sparkles className="w-4 h-4 mr-1" />
                      Create Genie Space ({selectedRows.length})
                  </Button>
                  <Button
                      variant="destructive"
                      size="sm"
                      className="h-9 gap-1"
                      onClick={() => handleBulkDelete(selectedRows)}
                      disabled={selectedRows.length === 0 || !canAdmin}
                      title={canAdmin ? "Delete selected" : "Delete (Permission Denied)"}
                  >
                      <Trash2 className="w-4 h-4 mr-1" />
                      Delete Selected ({selectedRows.length})
                  </Button>
                </>
              );
            }}
            onRowClick={(row) => {
              const productId = row.original.id;
              if (productId) {
                navigate(`/data-products/${productId}`);
              } else {
                console.warn("Cannot navigate: Product ID is missing.", row.original);
                toast({ title: 'Navigation Error', description: 'Could not navigate to details, product ID is missing.', variant: "default" });
              }
            }}
          />
        ) : (
          <DataProductGraphView 
              products={products} 
              viewMode={viewMode}
              setViewMode={setViewMode}
              navigate={navigate}
          />
        )
      )}

      {/* Render the new Wizard Dialog Component */}
      {isWizardOpen && (
          <DataProductWizardDialog
            isOpen={isWizardOpen}
            onOpenChange={setIsWizardOpen}
            initialProduct={productToEdit}
            statuses={statuses}
            owners={owners}
            api={api}
            onSubmitSuccess={handleWizardSubmitSuccess}
          />
       )}

      {/* Render Toaster component (ideally place in root layout like App.tsx) */}
      <Toaster />
    </div>
  );
} 