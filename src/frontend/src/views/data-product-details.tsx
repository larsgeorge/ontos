import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { DataProduct, InputPort, OutputPort, DataProductStatus, DataProductOwner, DataProductType } from '@/types/data-product'; // Import Port types
import DataProductWizardDialog from '@/components/data-products/data-product-wizard-dialog';
import { useApi } from '@/hooks/use-api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Loader2, Pencil, Trash2, AlertCircle, Sparkles, CopyPlus, ArrowLeft, Package, KeyRound } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import TagChip from '@/components/ui/tag-chip';
import { Toaster } from '@/components/ui/toaster';
import { useToast } from '@/hooks/use-toast';
import { Label } from '@/components/ui/label';
import useBreadcrumbStore from '@/stores/breadcrumb-store'; // Import Zustand store
import { usePermissions } from '@/stores/permissions-store'; // Import permissions hook
import * as Settings from '@/types/settings'; // Import FeatureAccessLevel enum as value
import { useNotificationsStore } from '@/stores/notifications-store'; // Import notification store
import CreateVersionDialog from '@/components/data-products/create-version-dialog';
import ConceptSelectDialog from '@/components/semantic/concept-select-dialog';
import LinkedConceptChips from '@/components/semantic/linked-concept-chips';
import type { EntitySemanticLink } from '@/types/semantic-link';
import EntityMetadataPanel from '@/components/metadata/entity-metadata-panel';
import { CommentSidebar } from '@/components/comments';
import { useDomains } from '@/hooks/use-domains';
import RequestAccessDialog from '@/components/access/request-access-dialog';
import EntityCostsPanel from '@/components/costs/entity-costs-panel';

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
  const { getDomainName, getDomainIdByName } = useDomains();

  const [product, setProduct] = useState<DataProduct | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isEditWizardOpen, setIsEditWizardOpen] = useState(false);
  const [isVersionDialogOpen, setIsVersionDialogOpen] = useState(false);
  const [iriDialogOpen, setIriDialogOpen] = useState(false);
  const [links, setLinks] = useState<EntitySemanticLink[]>([]);
  const [isCommentSidebarOpen, setIsCommentSidebarOpen] = useState(false);
  const [isRequestAccessDialogOpen, setIsRequestAccessDialogOpen] = useState(false);

  // State for dropdown values needed by the dialog
  const [statuses, setStatuses] = useState<DataProductStatus[]>([]);
  const [productTypes, setProductTypes] = useState<DataProductType[]>([]);
  const [owners, setOwners] = useState<DataProductOwner[]>([]);

  // Permissions
  const featureId = 'data-products';
  const canRead = !permissionsLoading && hasPermission(featureId, Settings.FeatureAccessLevel.READ_ONLY);
  const canWrite = !permissionsLoading && hasPermission(featureId, Settings.FeatureAccessLevel.READ_WRITE);
  const canAdmin = !permissionsLoading && hasPermission(featureId, Settings.FeatureAccessLevel.ADMIN);

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
      const [productResp, statusesResp, ownersResp, typesResp, linksResp] = await Promise.all([
        get<DataProduct>(`/api/data-products/${productId}`),
        get<DataProductStatus[]>('/api/data-products/statuses'),
        get<DataProductOwner[]>('/api/data-products/owners'),
        get<DataProductType[]>('/api/data-products/types'),
        get<EntitySemanticLink[]>(`/api/semantic-links/entity/data_product/${productId}`),
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
      setLinks(Array.isArray(linksResp.data) ? linksResp.data : []);

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

  // --- Request Access ---
  const handleRequestAccess = () => {
    if (!productId || !product) return;
    setIsRequestAccessDialogOpen(true);
  };

  const addIri = async (iri: string) => {
    if (!productId) return;
    try {
      const res = await post<EntitySemanticLink>(`/api/semantic-links/`, {
        entity_id: productId,
        entity_type: 'data_product',
        iri,
      });
      if (res.error) throw new Error(res.error);
      await fetchDetailsAndDropdowns();
      setIriDialogOpen(false);
      toast({ title: 'Linked', description: 'IRI linked to data product.' });
    } catch (e: any) {
      toast({ title: 'Error', description: e.message || 'Failed to link IRI', variant: 'destructive' });
    }
  };

  const removeLink = async (linkId: string) => {
    try {
      const res = await fetch(`/api/semantic-links/${linkId}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Failed to remove link');
      await fetchDetailsAndDropdowns();
      toast({ title: 'Removed', description: 'IRI link removed.' });
    } catch (e: any) {
      toast({ title: 'Error', description: e.message || 'Failed to remove link', variant: 'destructive' });
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
      <div className="flex items-center justify-between">
        <Button variant="outline" onClick={() => navigate('/data-products')} size="sm">
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to List
        </Button>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={handleRequestAccess} disabled={!product} size="sm" title="Request Access">
            <KeyRound className="mr-2 h-4 w-4" /> Request Access
          </Button>
          <CommentSidebar
            entityType="data_product"
            entityId={productId!}
            isOpen={isCommentSidebarOpen}
            onToggle={() => setIsCommentSidebarOpen(!isCommentSidebarOpen)}
            className="h-8"
          />
          <Button variant="outline" onClick={handleCreateGenieSpace} disabled={!product || !canWrite} title={canWrite ? "Create Genie Space" : "Create Genie Space (Permission Denied)"} size="sm">
              <Sparkles className="mr-2 h-4 w-4" /> Create Genie Space
          </Button>
          <Button variant="outline" onClick={handleCreateNewVersion} disabled={!product || !canWrite} title={canWrite ? "Create New Version" : "Create New Version (Permission Denied)"} size="sm">
              <CopyPlus className="mr-2 h-4 w-4" /> Create New Version
          </Button>
          <Button variant="outline" onClick={handleEdit} disabled={!product || !canWrite} title={canWrite ? "Edit" : "Edit (Permission Denied)"} size="sm">
            <Pencil className="mr-2 h-4 w-4" /> Edit
          </Button>
          <Button variant="destructive" onClick={handleDelete} disabled={!product || !canAdmin} title={canAdmin ? "Delete" : "Delete (Permission Denied)"} size="sm">
            <Trash2 className="mr-2 h-4 w-4" /> Delete
          </Button>
        </div>
      </div>

      {/* Info Card */} 
      <Card>
        <CardHeader>
          <CardTitle className="text-2xl font-bold flex items-center">
            <Package className="mr-3 h-7 w-7 text-primary" />{product.info.title}
          </CardTitle>
          {product.info.description && <CardDescription className="pt-1">{product.info.description}</CardDescription>}
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid md:grid-cols-4 gap-4">
            <div className="space-y-1"><Label>Owner:</Label> <span className="text-sm block">{product.info.owner_team_id || 'N/A'}</span></div>
            <div className="space-y-1">
              <Label>Domain:</Label>
              {(() => {
                const domainName = product.info.domain;
                const domainId = getDomainIdByName(domainName);
                return domainName && domainId ? (
                  <span
                    className="text-sm block cursor-pointer text-primary hover:underline"
                    onClick={() => navigate(`/data-domains/${domainId}`)}
                  >
                    {domainName}
                  </span>
                ) : (
                  <span className="text-sm block">{product.info.domain || 'N/A'}</span>
                );
              })()}
            </div>
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
                product.tags.map((tag, index) => (
                  <TagChip key={index} tag={tag} size="sm" />
                ))
              ) : (
                <span className="text-sm text-muted-foreground">No tags</span>
              )}
            </div>
          </div>
          <div className="space-y-1">
            <Label>Linked Business Concepts:</Label>
            <LinkedConceptChips
              links={links}
              onRemove={(id) => removeLink(id)}
              trailing={<Button size="sm" variant="outline" onClick={() => setIriDialogOpen(true)}>Add Concept</Button>}
            />
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
                  <div className="font-semibold text-sm">{port.name} <span className="text-xs text-muted-foreground">(ID: {port.id})</span></div>
                  {port.description && <div className="text-xs"><span className="text-muted-foreground">Description:</span> {port.description}</div>}
                   {port.status && (
                     <div className="text-xs flex items-center">
                       <span className="text-muted-foreground">Status:</span>
                       <Badge variant={getStatusColor(port.status)} className="ml-1">{port.status}</Badge>
                     </div>
                   )}
                   {port.dataContractId && <div className="text-xs"><span className="text-muted-foreground">Data Contract ID:</span> {port.dataContractId}</div>}
                   {/* TODO: Display output port server info, containsPii, autoApprove, tags, links, custom? */}
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>

      {/* Costs Panel */}
      {product.id && (
        <EntityCostsPanel entityId={product.id} entityType="data_product" />
      )}

      {/* Metadata Panel */} 
      {product.id && (
        <EntityMetadataPanel entityId={product.id} entityType="data_product" />
      )}

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

      <ConceptSelectDialog isOpen={iriDialogOpen} onOpenChange={setIriDialogOpen} onSelect={addIri} />

      {/* Request Access Dialog */}
      {product && (
        <RequestAccessDialog
          isOpen={isRequestAccessDialogOpen}
          onOpenChange={setIsRequestAccessDialogOpen}
          entityType="data_product"
          entityId={productId!}
          entityName={product.info?.title}
        />
      )}

      <Toaster />
    </div>
  );
} 