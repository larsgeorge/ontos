import React, { useState, useEffect, useRef, useMemo } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Plus, Pencil, Trash2, AlertCircle, Database, ChevronDown, Upload, X, Loader2, Sparkles } from 'lucide-react';
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
import DataProductFormDialog from '@/components/data-products/data-product-form-dialog';
import { usePermissions } from '@/stores/permissions-store';
import { FeatureAccessLevel } from '@/types/settings';
import { useNotificationsStore } from '@/stores/notifications-store';

// --- Helper Function Type Definition --- 
type CheckApiResponseFn = <T>(
    response: { data?: T | { detail?: string }, error?: string },
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
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [productToEdit, setProductToEdit] = useState<DataProduct | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Use the imported types for state
  const [statuses, setStatuses] = useState<DataProductStatus[]>([]);
  const [archetypes, setArchetypes] = useState<DataProductArchetype[]>([]);
  const [owners, setOwners] = useState<DataProductOwner[]>([]);

  const api = useApi();
  const { get, post, delete: deleteApi } = api;
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { toast } = useToast();
  const navigate = useNavigate();
  const refreshNotifications = useNotificationsStore((state) => state.refreshNotifications);

  // Get permissions
  const { hasPermission, isLoading: permissionsLoading } = usePermissions();
  const featureId = 'data-products'; // ID for this feature

  // Determine if user has specific access levels
  const canRead = !permissionsLoading && hasPermission(featureId, FeatureAccessLevel.READ_ONLY);
  const canWrite = !permissionsLoading && hasPermission(featureId, FeatureAccessLevel.READ_WRITE);
  const canAdmin = !permissionsLoading && hasPermission(featureId, FeatureAccessLevel.ADMIN);

  // Fetch initial data for the table and dropdowns
  useEffect(() => {
    const loadInitialData = async () => {
      setLoading(true);
      setError(null);
      try {
        // Fetch products and dropdown values concurrently
        const [productsResp, statusesResp, archetypesResp, ownersResp] = await Promise.all([
          get<DataProduct[]>('/api/data-products'),
          get<DataProductStatus[]>('/api/data-products/statuses'),
          get<DataProductArchetype[]>('/api/data-products/archetypes'),
          get<DataProductOwner[]>('/api/data-products/owners'),
        ]);

        // Check responses using the helper
        const productsData = checkApiResponse(productsResp, 'Products');
        const statusesData = checkApiResponse(statusesResp, 'Statuses');
        const archetypesData = checkApiResponse(archetypesResp, 'Archetypes');
        const ownersData = checkApiResponse(ownersResp, 'Owners');

        setProducts(Array.isArray(productsData) ? productsData : []);
        setStatuses(Array.isArray(statusesData) ? statusesData : []);
        setArchetypes(Array.isArray(archetypesData) ? archetypesData : []);
        setOwners(Array.isArray(ownersData) ? ownersData : []);

      } catch (err: any) {
        console.error('Error fetching initial data:', err);
        setError(err.message || 'Failed to load initial data');
        // Reset state on error
        setProducts([]);
        setStatuses([]);
        setArchetypes([]);
        setOwners([]);
      } finally {
        setLoading(false);
      }
    };
    if (canRead) {
        loadInitialData();
    } else if (!permissionsLoading) {
        setLoading(false);
        setError("Permission Denied: Cannot view data products.");
    }
  }, [get, canRead, permissionsLoading]);

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

  // --- Dialog Open Handler ---
  const handleOpenDialog = (product?: DataProduct) => {
      if (!canWrite) {
          toast({ title: "Permission Denied", description: "You do not have permission to edit data products.", variant: "destructive" });
          return;
      }
      setProductToEdit(product || null);
      setIsDialogOpen(true);
  };

  // --- Dialog Submit Success Handler ---
  const handleDialogSubmitSuccess = (savedProduct: DataProduct) => {
    console.log('Dialog submitted successfully, refreshing list...', savedProduct);
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
      console.log(`Successfully uploaded ${count} products from file:`, file.name);
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
      handleOpenDialog(product);
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
      cell: ({ row }) => <div className="font-medium">{row.original.info.title}</div>,
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
      accessorKey: "info.archetype",
      header: ({ column }: { column: Column<DataProduct, unknown> }) => (
        <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
          Archetype <ChevronDown className="ml-2 h-4 w-4" />
        </Button>
      ),
      cell: ({ row }) => (
        row.original.info.archetype ?
        <Badge variant="outline">{row.original.info.archetype}</Badge> : 'N/A'
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
  ], [handleOpenDialog, handleDeleteProduct, getStatusColor, canWrite, canAdmin, permissionsLoading]);

  // --- Render Logic ---
  return (
    <div className="py-6">
      <h1 className="text-3xl font-bold mb-6 flex items-center gap-2">
        <Database className="w-8 h-8" />
        Data Products
      </h1>

      {error && (
        <Alert variant="destructive" className="mb-4">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {loading || permissionsLoading ? (
        <div className="flex justify-center items-center h-64">
          <Loader2 className="h-12 w-12 animate-spin text-primary" />
        </div>
      ) : !canRead ? (
         <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>You do not have permission to view data products.</AlertDescription>
          </Alert>
      ) : (
        <DataTable
          columns={columns}
          data={products}
          searchColumn="info.title"
          toolbarActions={
            <>
              {/* Create Button - Conditionally enabled */}
              <Button
                  onClick={() => handleOpenDialog()}
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
            </>
          }
          bulkActions={(selectedRows) => (
            <>
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
          )}
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
      )}

      {/* Render the new Dialog Component */}
      {isDialogOpen && (
          <DataProductFormDialog
            isOpen={isDialogOpen}
            onOpenChange={setIsDialogOpen}
            initialProduct={productToEdit}
            statuses={statuses}
            archetypes={archetypes}
            owners={owners}
            api={api}
            onSubmitSuccess={handleDialogSubmitSuccess}
          />
       )}

      {/* Render Toaster component (ideally place in root layout like App.tsx) */}
      <Toaster />
    </div>
  );
} 