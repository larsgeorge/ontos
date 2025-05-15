import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { DataProduct, InputPort, OutputPort, DataProductStatus, DataProductArchetype, DataProductOwner, DataProductType } from '@/types/data-product'; // Import Port types
import DataProductWizardDialog from '@/components/data-products/data-product-wizard-dialog';
import { useApi } from '@/hooks/use-api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Loader2, Pencil, Trash2, AlertCircle, Sparkles, CopyPlus } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Toaster } from '@/components/ui/toaster';
import { useToast } from '@/hooks/use-toast';
import { Label } from '@/components/ui/label';
import useBreadcrumbStore from '@/stores/breadcrumb-store'; // Import Zustand store
import { usePermissions } from '@/stores/permissions-store'; // Import permissions hook
import { FeatureAccessLevel } from '@/types/settings'; // Import FeatureAccessLevel
import { useNotificationsStore } from '@/stores/notifications-store'; // Import notification store
import CreateVersionDialog from '@/components/data-products/create-version-dialog';

// Helper Function Type Definition (copied from DataProducts view for checking API responses)
type CheckApiResponseFn = <T>(
    response: { data?: T | { detail?: string }, error?: string | null | undefined },
    name: string
) => T;

// Helper Function Implementation
const checkApiResponse: CheckApiResponseFn = (response, name) => {
    if (response.error) {
        throw new Error(`${name} fetch failed: ${response.error}`);
    }
    if (response.data && typeof response.data === 'object' && 'detail' in response.data && typeof response.data.detail === 'string') {
        throw new Error(`${name} fetch failed: ${response.data.detail}`);
    }
    if (response.data === null || response.data === undefined) {
        throw new Error(`${name} fetch returned null or undefined data.`);
    }
    return response.data as any;
};

export default function DataProductDetails() {
  const { productId } = useParams<{ productId: string }>();
  const navigate = useNavigate();
  const api = useApi();
  const { get, post, delete: deleteApi } = api; // Destructure methods
  const { toast } = useToast();
  const setDynamicTitle = useBreadcrumbStore((state) => state.setDynamicTitle);
  const setStaticSegments = useBreadcrumbStore((state) => state.setStaticSegments); // For potential parent path
  const { hasPermission, isLoading: permissionsLoading } = usePermissions(); // Use permissions hook
  const refreshNotifications = useNotificationsStore((state) => state.refreshNotifications); // Get refresh action

  const [product, setProduct] = useState<DataProduct | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isEditWizardOpen, setIsEditWizardOpen] = useState(false);
  const [isVersionDialogOpen, setIsVersionDialogOpen] = useState(false);

  // State for dropdown values needed by the dialog
  const [statuses, setStatuses] = useState<DataProductStatus[]>([]);
  const [productTypes, setProductTypes] = useState<DataProductType[]>([]);
  const [owners, setOwners] = useState<DataProductOwner[]>([]);

  // Permissions
  const featureId = 'data-products';
  const canRead = !permissionsLoading && hasPermission(featureId, FeatureAccessLevel.READ_ONLY);
  const canWrite = !permissionsLoading && hasPermission(featureId, FeatureAccessLevel.READ_WRITE);
  const canAdmin = !permissionsLoading && hasPermission(featureId, FeatureAccessLevel.ADMIN);

  // Helper to format dates safely
  const formatDate = (dateString: string | undefined): string => {
    if (!dateString) return 'N/A';
    try {
      return new Date(dateString).toLocaleString();
    } catch (e) {
      return 'Invalid Date';
    }
  };

  // Helper to get status badge variant
  const getStatusColor = (status: string | undefined): 'default' | 'secondary' | 'destructive' | 'outline' => {
    const lowerStatus = status?.toLowerCase() || '';
    if (lowerStatus.includes('active')) return 'default';
    if (lowerStatus.includes('development')) return 'secondary';
    if (lowerStatus.includes('retired') || lowerStatus.includes('deprecated')) return 'outline';
    if (lowerStatus.includes('deleted') || lowerStatus.includes('archived')) return 'destructive';
    return 'default';
  };

  // Function to fetch product details and dropdown data
  const fetchDetailsAndDropdowns = async () => {
    if (!productId) {
      setError('Product ID not found in URL.');
      setDynamicTitle(null); // Clear title if ID is missing
      setLoading(false);
      return;
    }
    if (!canRead && !permissionsLoading) {
        setError('Permission Denied: Cannot view data product details.');
        setDynamicTitle('Permission Denied');
        setLoading(false);
        return;
    }
    setLoading(true);
    setError(null);
    setStaticSegments([{ label: 'Data Products', path: '/data-products'}]); // Set parent breadcrumb
    setDynamicTitle('Loading...'); // Set loading state for the dynamic part
    try {
      // Fetch product details and dropdown values concurrently
      const [productResp, statusesResp, ownersResp, typesResp] = await Promise.all([
        get<DataProduct>(`/api/data-products/${productId}`),
        get<DataProductStatus[]>('/api/data-products/statuses'),
        get<DataProductOwner[]>('/api/data-products/owners'),
        get<DataProductType[]>('/api/data-products/types'),
      ]);

      // Check responses using the helper
      const productData = checkApiResponse(productResp, 'Product Details');
      const statusesData = checkApiResponse(statusesResp, 'Statuses');
      const ownersData = checkApiResponse(ownersResp, 'Owners');
      const typesData = checkApiResponse(typesResp, 'Product Types');

      // Set state
      setProduct(productData);
      setStatuses(Array.isArray(statusesData) ? statusesData : []);
      setProductTypes(Array.isArray(typesData) ? typesData : []);
      setOwners(Array.isArray(ownersData) ? ownersData : []);

      // Update breadcrumb store with the actual title
      setDynamicTitle(productData.info.title);

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch data';
      setError(errorMessage);
      setProduct(null); // Clear product on error
      // Clear dropdowns on error too?
      setStatuses([]);
      setProductTypes([]);
      setOwners([]);
      setDynamicTitle('Error'); // Set error state or null
      toast({ title: 'Error', description: `Failed to load data: ${errorMessage}`, variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  };

  // Initial fetch and cleanup
  useEffect(() => {
    fetchDetailsAndDropdowns();
    
    // Cleanup function: Clear the title when the component unmounts
    return () => {
        console.log("DataProductDetails unmounting, clearing breadcrumb title.");
        setStaticSegments([]); // Clear static segments as well
        setDynamicTitle(null);
    };
    // Depend on permissions and canRead status as well
  }, [productId, get, toast, setDynamicTitle, setStaticSegments, canRead, permissionsLoading]);

  const handleEdit = () => {
    if (!canWrite) {
        toast({ title: 'Permission Denied', description: 'You do not have permission to edit this product.', variant: 'destructive' });
        return;
    }
    if (!product) {
        toast({ title: 'Error', description: 'Product data not loaded yet.', variant: 'destructive' });
        return;
    }
    setIsEditWizardOpen(true);
  };

  // Handler for successful wizard submission (shared logic with list view)
  const handleWizardSubmitSuccess = (savedProduct: DataProduct) => {
    console.log('Edit wizard submitted successfully, refreshing details...', savedProduct);
    setIsEditWizardOpen(false); // Close the wizard
    fetchDetailsAndDropdowns(); // Refetch details to show updates
  };

  const handleDelete = async () => {
    if (!canAdmin) {
        toast({ title: 'Permission Denied', description: 'You do not have permission to delete this product.', variant: 'destructive' });
        return;
    }
    if (!productId || !product) return;
    // Use info.title for confirmation
    if (!confirm(`Are you sure you want to delete data product "${product.info.title}"?`)) return;

    try {
      await deleteApi(`/api/data-products/${productId}`);
      toast({ title: 'Success', description: 'Data product deleted successfully.' });
      navigate('/data-products'); // Navigate back to the list view
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to delete product';
      toast({ title: 'Error', description: `Failed to delete: ${errorMessage}`, variant: 'destructive' });
    }
  };

  // --- Genie Space Handler --- 
  const handleCreateGenieSpace = async () => {
      if (!canWrite) { // Check for WRITE permission
          toast({ title: "Permission Denied", description: "You do not have permission to create Genie Spaces.", variant: "destructive" });
          return;
      }
      if (!productId || !product) {
          toast({ title: "Error", description: "Product data not available.", variant: "destructive" });
          return;
      }

      if (!confirm(`Create a Genie Space for the data product "${product.info.title}"?`)) {
          return;
      }

      toast({ title: 'Initiating Genie Space', description: `Requesting Genie Space creation for ${product.info.title}...` });

      try {
          const response = await post('/api/data-products/genie-space', { product_ids: [productId] }); // Send single ID in list
          
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
          setError(errorMsg); // Can also show error in main area if desired
      }
  };

  // --- Open Create New Version Dialog Handler --- 
  const handleCreateNewVersion = async () => {
      if (!canWrite || !productId || !product) { // Check permissions and data
          toast({ title: "Permission Denied or Data Missing", description: "Cannot create new version.", variant: "destructive" });
          return;
      }
      setIsVersionDialogOpen(true); // Open the dialog
  };

  // --- Submit New Version Handler (called by dialog) --- 
  const submitNewVersion = async (newVersionString: string) => {
      if (!productId) return; // Should not happen if button is enabled
      
      toast({ title: 'Creating New Version', description: `Creating version ${newVersionString}...` });

      try {
          // Use the trimmed version string from the dialog callback
          const response = await post<DataProduct>(`/api/data-products/${productId}/versions`, { new_version: newVersionString.trim() });

          // checkApiResponse will throw if response.error or response.data.detail exists
          const newProduct = response.data;
          if (!newProduct || !newProduct.id) {
             throw new Error('Invalid response when creating version.');
          }

          toast({ title: 'Success', description: `Version ${newVersionString} created successfully!` });
          // Navigate to the new product's detail page
          navigate(`/data-products/${newProduct.id}`);

      } catch (err: any) {
          console.error('Error creating new version:', err);
          const errorMsg = err.message || 'Failed to create new version.';
          toast({ title: 'Error', description: errorMsg, variant: 'destructive' });
          setError(errorMsg); // Optionally show error in main area
      }
  };

  // Loading state
  if (loading || permissionsLoading) { // Check permissionsLoading too
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="h-12 w-12 animate-spin text-primary" />
      </div>
    );
  }

  // Error state (includes permission denied)
  if (error) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    );
  }

  // Not found state (after loading and checking permissions)
  if (!product) {
    return (
      <Alert>
        <AlertDescription>Data product not found.</AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="py-6 space-y-6">
      <div className="flex justify-between items-start">
        <h1 className="text-3xl font-bold mb-2">{product.info.title}</h1>
        <div className="flex space-x-2">
          <Button variant="outline" onClick={handleCreateGenieSpace} disabled={!product || !canWrite} title={canWrite ? "Create Genie Space" : "Create Genie Space (Permission Denied)"}>
              <Sparkles className="mr-2 h-4 w-4" /> Create Genie Space
          </Button>
          <Button variant="outline" onClick={handleCreateNewVersion} disabled={!product || !canWrite} title={canWrite ? "Create New Version" : "Create New Version (Permission Denied)"}>
              <CopyPlus className="mr-2 h-4 w-4" /> Create New Version
          </Button>
          <Button variant="outline" onClick={handleEdit} disabled={!product || !canWrite} title={canWrite ? "Edit" : "Edit (Permission Denied)"}>
            <Pencil className="mr-2 h-4 w-4" /> Edit
          </Button>
          <Button variant="destructive" onClick={handleDelete} disabled={!product || !canAdmin} title={canAdmin ? "Delete" : "Delete (Permission Denied)"}>
            <Trash2 className="mr-2 h-4 w-4" /> Delete
          </Button>
        </div>
      </div>

      {/* Info Card */} 
      <Card>
        <CardHeader>
          <CardTitle>Info</CardTitle>
          <CardDescription>Core metadata about the data product.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid md:grid-cols-4 gap-4">
            <div className="space-y-1"><Label>Owner:</Label> <span className="text-sm block">{product.info.owner}</span></div>
            <div className="space-y-1"><Label>Domain:</Label> <span className="text-sm block">{product.info.domain || 'N/A'}</span></div>
            <div className="space-y-1">
              <Label>Status:</Label>
              <Badge variant={getStatusColor(product.info.status)} className="ml-1">{product.info.status || 'N/A'}</Badge>
            </div>
            <div className="space-y-1">
              <Label>Version:</Label>
              <Badge variant="secondary" className="ml-1">{product.version}</Badge>
            </div>
            <div className="space-y-1">
              <Label>Type:</Label>
              <Badge variant="outline" className="ml-1">{product.productType || 'N/A'}</Badge>
            </div>
            <div className="space-y-1"><Label>Archetype:</Label> <span className="text-sm block">{product.info.archetype || 'N/A'}</span></div>
            <div className="space-y-1"><Label>Created:</Label> <span className="text-sm block">{formatDate(product.created_at)}</span></div>
            <div className="space-y-1"><Label>Updated:</Label> <span className="text-sm block">{formatDate(product.updated_at)}</span></div>
            <div className="space-y-1"><Label>Spec Version:</Label> <span className="text-sm block">{product.dataProductSpecification}</span></div>
          </div>
          <div className="space-y-1"><Label>Description:</Label> <p className="text-sm mt-1">{product.info.description || 'N/A'}</p></div>
          <div className="space-y-1">
            <Label>Tags:</Label>
            <div className="flex flex-wrap gap-1 mt-1">
              {(product.tags || []).length > 0 ? (
                product.tags.map((tag: string) => (
                  <Badge key={tag} variant="secondary">{tag}</Badge>
                ))
              ) : (
                <span className="text-sm text-muted-foreground">No tags</span>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Ports Card */} 
      <Card>
        <CardHeader>
          <CardTitle>Ports</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <h4 className="font-medium mb-2 text-base">Input Ports</h4>
            {(product.inputPorts?.length ?? 0) === 0 ? (
              <p className="text-sm text-muted-foreground">No input ports defined.</p>
            ) : (
              product.inputPorts.map((port: InputPort, index: number) => (
                <div key={`input-${index}-${port.id}`} className="border p-3 rounded mb-2 space-y-1">
                  <p className="font-semibold text-sm">{port.name} <span className="text-xs text-muted-foreground">(ID: {port.id})</span></p>
                  <p className="text-xs"><span className="text-muted-foreground">Source System ID:</span> {port.sourceSystemId}</p>
                  {port.description && <p className="text-xs"><span className="text-muted-foreground">Description:</span> {port.description}</p>}
                  {/* TODO: Display port tags, links, custom props? */}
                </div>
              ))
            )}
          </div>
          <div>
            <h4 className="font-medium mb-2 text-base">Output Ports</h4>
             {(product.outputPorts?.length ?? 0) === 0 ? (
              <p className="text-sm text-muted-foreground">No output ports defined.</p>
            ) : (
              product.outputPorts.map((port: OutputPort, index: number) => (
                 <div key={`output-${index}-${port.id}`} className="border p-3 rounded mb-2 space-y-1">
                  <p className="font-semibold text-sm">{port.name} <span className="text-xs text-muted-foreground">(ID: {port.id})</span></p>
                  {port.description && <p className="text-xs"><span className="text-muted-foreground">Description:</span> {port.description}</p>}
                   {port.status && <p className="text-xs"><span className="text-muted-foreground">Status:</span> <Badge variant={getStatusColor(port.status)} className="ml-1">{port.status}</Badge></p>}
                   {port.dataContractId && <p className="text-xs"><span className="text-muted-foreground">Data Contract ID:</span> {port.dataContractId}</p>}
                   {/* TODO: Display output port server info, containsPii, autoApprove, tags, links, custom? */}
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>

      {/* TODO: Add Cards for Links, Custom Properties, etc. */}

      {/* Render the reusable Edit Wizard component */}
      {isEditWizardOpen && product && (
        <DataProductWizardDialog
            isOpen={isEditWizardOpen}
            onOpenChange={setIsEditWizardOpen} // Let dialog control closing
            initialProduct={product} // Pass the current product data for editing
            // Pass dropdown data needed by the wizard
            statuses={statuses}
            // productTypes={productTypes} // Remove - wizard uses internal const
            owners={owners}
            api={api} // Pass the full api object
            onSubmitSuccess={handleWizardSubmitSuccess} // Pass the success handler
        />
      )}

      {/* Render the new version dialog */} 
      {product && (
          <CreateVersionDialog
              isOpen={isVersionDialogOpen}
              onOpenChange={setIsVersionDialogOpen}
              currentVersion={product.version}
              productTitle={product.info.title}
              onSubmit={submitNewVersion} // Pass the submit handler
          />
      )}

      <Toaster />
    </div>
  );
} 