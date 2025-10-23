import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { DataProduct, DataProductStatus, InputPort, OutputPort, ManagementPort, TeamMember, Support } from '@/types/data-product';
import DataProductCreateDialog from '@/components/data-products/data-product-create-dialog';
import InputPortFormDialog from '@/components/data-products/input-port-form-dialog';
import OutputPortFormDialog from '@/components/data-products/output-port-form-dialog';
import ManagementPortFormDialog from '@/components/data-products/management-port-form-dialog';
import TeamMemberFormDialog from '@/components/data-products/team-member-form-dialog';
import SupportChannelFormDialog from '@/components/data-products/support-channel-form-dialog';
import StatusTransitionDialog from '@/components/data-products/status-transition-dialog';
import ImportExportDialog from '@/components/data-products/import-export-dialog';
import { useApi } from '@/hooks/use-api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Loader2, Pencil, Trash2, AlertCircle, Sparkles, CopyPlus, ArrowLeft, Package, KeyRound, Plus, FileText, Download } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import TagChip from '@/components/ui/tag-chip';
import { useToast } from '@/hooks/use-toast';
import { Label } from '@/components/ui/label';
import useBreadcrumbStore from '@/stores/breadcrumb-store';
import { usePermissions } from '@/stores/permissions-store';
import * as Settings from '@/types/settings';
import { useNotificationsStore } from '@/stores/notifications-store';
import CreateVersionDialog from '@/components/data-products/create-version-dialog';
import ConceptSelectDialog from '@/components/semantic/concept-select-dialog';
import LinkedConceptChips from '@/components/semantic/linked-concept-chips';
import type { EntitySemanticLink } from '@/types/semantic-link';
import EntityMetadataPanel from '@/components/metadata/entity-metadata-panel';
import { CommentSidebar } from '@/components/comments';
import { useDomains } from '@/hooks/use-domains';
import RequestAccessDialog from '@/components/access/request-access-dialog';
import EntityCostsPanel from '@/components/costs/entity-costs-panel';

/**
 * ODPS v1.0.0 Data Product Details View
 *
 * Displays product with sections for all ODPS entities.
 * Complex nested entities are edited via form dialogs (to be created).
 */

type CheckApiResponseFn = <T>(
  response: { data?: T | { detail?: string }, error?: string | null | undefined },
  name: string
) => T;

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
  const { get, post, delete: deleteApi } = api;
  const { toast } = useToast();
  const setDynamicTitle = useBreadcrumbStore((state) => state.setDynamicTitle);
  const setStaticSegments = useBreadcrumbStore((state) => state.setStaticSegments);
  const { hasPermission, isLoading: permissionsLoading } = usePermissions();
  const refreshNotifications = useNotificationsStore((state) => state.refreshNotifications);
  const { getDomainName, getDomainIdByName } = useDomains();

  const [product, setProduct] = useState<DataProduct | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [isVersionDialogOpen, setIsVersionDialogOpen] = useState(false);
  const [iriDialogOpen, setIriDialogOpen] = useState(false);
  const [links, setLinks] = useState<EntitySemanticLink[]>([]);
  const [isCommentSidebarOpen, setIsCommentSidebarOpen] = useState(false);
  const [isRequestAccessDialogOpen, setIsRequestAccessDialogOpen] = useState(false);
  const [isTransitioning, setIsTransitioning] = useState(false);

  // Dialog states for nested entities
  const [isInputPortDialogOpen, setIsInputPortDialogOpen] = useState(false);
  const [isOutputPortDialogOpen, setIsOutputPortDialogOpen] = useState(false);
  const [isManagementPortDialogOpen, setIsManagementPortDialogOpen] = useState(false);
  const [isTeamMemberDialogOpen, setIsTeamMemberDialogOpen] = useState(false);
  const [isSupportChannelDialogOpen, setIsSupportChannelDialogOpen] = useState(false);
  const [isStatusTransitionDialogOpen, setIsStatusTransitionDialogOpen] = useState(false);
  const [isImportExportDialogOpen, setIsImportExportDialogOpen] = useState(false);

  // Permissions
  const featureId = 'data-products';
  const canRead = !permissionsLoading && hasPermission(featureId, Settings.FeatureAccessLevel.READ_ONLY);
  const canWrite = !permissionsLoading && hasPermission(featureId, Settings.FeatureAccessLevel.READ_WRITE);
  const canAdmin = !permissionsLoading && hasPermission(featureId, Settings.FeatureAccessLevel.ADMIN);

  const formatDate = (dateString: string | undefined): string => {
    if (!dateString) return 'N/A';
    try {
      return new Date(dateString).toLocaleString();
    } catch (e) {
      return 'Invalid Date';
    }
  };

  const getStatusColor = (status: string | undefined): 'default' | 'secondary' | 'destructive' | 'outline' => {
    const lowerStatus = status?.toLowerCase() || '';
    if (lowerStatus === 'active') return 'default';
    if (lowerStatus === 'draft' || lowerStatus === 'proposed') return 'secondary';
    if (lowerStatus === 'retired' || lowerStatus === 'deprecated') return 'outline';
    return 'default';
  };

  const fetchProductDetails = async () => {
    if (!productId) {
      setError('Product ID not found in URL.');
      setDynamicTitle(null);
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
    setStaticSegments([{ label: 'Data Products', path: '/data-products' }]);
    setDynamicTitle('Loading...');

    try {
      const [productResp, linksResp] = await Promise.all([
        get<DataProduct>(`/api/data-products/${productId}`),
        get<EntitySemanticLink[]>(`/api/semantic-links/entity/data_product/${productId}`),
      ]);

      const productData = checkApiResponse(productResp, 'Product Details');
      setProduct(productData);
      setLinks(Array.isArray(linksResp.data) ? linksResp.data : []);

      // ODPS v1.0.0: name is at root level
      setDynamicTitle(productData.name || 'Unnamed Product');
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch data';
      setError(errorMessage);
      setProduct(null);
      setDynamicTitle('Error');
      toast({ title: 'Error', description: `Failed to load data: ${errorMessage}`, variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  };

  // ODPS v1.0.0 Lifecycle state machine handler
  const handleStatusTransition = async (targetStatus: string, notes?: string) => {
    if (!productId || !product || !canWrite) return;

    setIsTransitioning(true);
    try {
      const res = await fetch(`/api/data-products/${productId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...product, status: targetStatus }),
      });
      if (!res.ok) throw new Error(`Status transition failed (${res.status})`);

      await fetchProductDetails();

      toast({
        title: 'Status Updated',
        description: `Product status changed to ${targetStatus.toUpperCase()}`,
      });

      // Log transition notes if provided
      if (notes) {
        console.log(`Status transition notes: ${notes}`);
        // Could POST to an audit log endpoint here if implemented
      }
    } catch (e: any) {
      throw new Error(e?.message || 'Status transition failed');
    } finally {
      setIsTransitioning(false);
    }
  };

  useEffect(() => {
    fetchProductDetails();
    return () => {
      setStaticSegments([]);
      setDynamicTitle(null);
    };
  }, [productId, canRead, permissionsLoading]);

  const handleEdit = () => {
    if (!canWrite) {
      toast({ title: 'Permission Denied', description: 'You do not have permission to edit.', variant: 'destructive' });
      return;
    }
    setIsEditDialogOpen(true);
  };

  const handleDelete = async () => {
    if (!canAdmin || !productId || !product) return;
    if (!confirm(`Delete data product "${product.name}"?`)) return;

    try {
      await deleteApi(`/api/data-products/${productId}`);
      toast({ title: 'Success', description: 'Data product deleted successfully.' });
      navigate('/data-products');
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to delete product';
      toast({ title: 'Error', description: `Failed to delete: ${errorMessage}`, variant: 'destructive' });
    }
  };

  const handleRequestAccess = () => {
    if (!productId || !product) return;
    setIsRequestAccessDialogOpen(true);
  };

  // Nested entity handlers
  const handleAddInputPort = async (port: InputPort) => {
    if (!productId || !product) return;
    try {
      const updatedPorts = [...(product.inputPorts || []), port];
      const res = await fetch(`/api/data-products/${productId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...product, inputPorts: updatedPorts }),
      });
      if (!res.ok) throw new Error(`Failed to add input port (${res.status})`);
      await fetchProductDetails();
    } catch (e: any) {
      throw new Error(e?.message || 'Failed to add input port');
    }
  };

  const handleAddOutputPort = async (port: OutputPort) => {
    if (!productId || !product) return;
    try {
      const updatedPorts = [...(product.outputPorts || []), port];
      const res = await fetch(`/api/data-products/${productId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...product, outputPorts: updatedPorts }),
      });
      if (!res.ok) throw new Error(`Failed to add output port (${res.status})`);
      await fetchProductDetails();
    } catch (e: any) {
      throw new Error(e?.message || 'Failed to add output port');
    }
  };

  const handleAddManagementPort = async (port: ManagementPort) => {
    if (!productId || !product) return;
    try {
      const updatedPorts = [...(product.managementPorts || []), port];
      const res = await fetch(`/api/data-products/${productId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...product, managementPorts: updatedPorts }),
      });
      if (!res.ok) throw new Error(`Failed to add management port (${res.status})`);
      await fetchProductDetails();
    } catch (e: any) {
      throw new Error(e?.message || 'Failed to add management port');
    }
  };

  const handleAddTeamMember = async (member: TeamMember) => {
    if (!productId || !product) return;
    try {
      const updatedMembers = [...(product.team?.members || []), member];
      const updatedTeam = { ...product.team, members: updatedMembers };
      const res = await fetch(`/api/data-products/${productId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...product, team: updatedTeam }),
      });
      if (!res.ok) throw new Error(`Failed to add team member (${res.status})`);
      await fetchProductDetails();
    } catch (e: any) {
      throw new Error(e?.message || 'Failed to add team member');
    }
  };

  const handleAddSupportChannel = async (channel: Support) => {
    if (!productId || !product) return;
    try {
      const updatedChannels = [...(product.support || []), channel];
      const res = await fetch(`/api/data-products/${productId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...product, support: updatedChannels }),
      });
      if (!res.ok) throw new Error(`Failed to add support channel (${res.status})`);
      await fetchProductDetails();
    } catch (e: any) {
      throw new Error(e?.message || 'Failed to add support channel');
    }
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
      await fetchProductDetails();
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
      await fetchProductDetails();
      toast({ title: 'Removed', description: 'IRI link removed.' });
    } catch (e: any) {
      toast({ title: 'Error', description: e.message || 'Failed to remove link', variant: 'destructive' });
    }
  };

  const handleCreateGenieSpace = async () => {
    if (!canWrite || !productId || !product) return;
    if (!confirm(`Create a Genie Space for "${product.name}"?`)) return;

    toast({ title: 'Initiating Genie Space', description: `Requesting Genie Space creation...` });

    try {
      const response = await post('/api/data-products/genie-space', { product_ids: [productId] });
      if (response.error) throw new Error(response.error);
      toast({ title: 'Request Submitted', description: `Genie Space creation initiated.` });
      refreshNotifications();
    } catch (err: any) {
      toast({ title: 'Error', description: err.message || 'Failed to start Genie Space creation.', variant: 'destructive' });
    }
  };

  const handleCreateNewVersion = () => {
    if (!canWrite || !productId || !product) return;
    setIsVersionDialogOpen(true);
  };

  const submitNewVersion = async (newVersionString: string) => {
    if (!productId) return;
    toast({ title: 'Creating New Version', description: `Creating version ${newVersionString}...` });

    try {
      const response = await post<DataProduct>(`/api/data-products/${productId}/versions`, { new_version: newVersionString.trim() });
      const newProduct = response.data;
      if (!newProduct || !newProduct.id) throw new Error('Invalid response when creating version.');

      toast({ title: 'Success', description: `Version ${newVersionString} created!` });
      navigate(`/data-products/${newProduct.id}`);
    } catch (err: any) {
      toast({ title: 'Error', description: err.message || 'Failed to create version.', variant: 'destructive' });
    }
  };

  if (loading || permissionsLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="h-12 w-12 animate-spin text-primary" />
      </div>
    );
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    );
  }

  if (!product) {
    return (
      <Alert>
        <AlertDescription>Data product not found.</AlertDescription>
      </Alert>
    );
  }

  // ODPS v1.0.0: Get owner from team
  const owner = product.team?.members?.[0]?.username || product.team?.name || 'N/A';
  const domainLabel = product.domain ? (getDomainName(product.domain) || product.domain) : 'N/A';

  return (
    <div className="py-6 space-y-6">
      <div className="flex items-center justify-between">
        <Button variant="outline" onClick={() => navigate('/data-products')} size="sm">
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to List
        </Button>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={handleRequestAccess} size="sm">
            <KeyRound className="mr-2 h-4 w-4" /> Request Access
          </Button>
          <CommentSidebar
            entityType="data_product"
            entityId={productId!}
            isOpen={isCommentSidebarOpen}
            onToggle={() => setIsCommentSidebarOpen(!isCommentSidebarOpen)}
            className="h-8"
          />
          <Button variant="outline" onClick={handleCreateGenieSpace} disabled={!canWrite} size="sm">
            <Sparkles className="mr-2 h-4 w-4" /> Create Genie Space
          </Button>
          <Button variant="outline" onClick={handleCreateNewVersion} disabled={!canWrite} size="sm">
            <CopyPlus className="mr-2 h-4 w-4" /> New Version
          </Button>
          <Button variant="outline" onClick={() => setIsImportExportDialogOpen(true)} size="sm">
            <Download className="mr-2 h-4 w-4" /> Export ODPS
          </Button>
          <Button variant="outline" onClick={handleEdit} disabled={!canWrite} size="sm">
            <Pencil className="mr-2 h-4 w-4" /> Edit
          </Button>
          <Button variant="destructive" onClick={handleDelete} disabled={!canAdmin} size="sm">
            <Trash2 className="mr-2 h-4 w-4" /> Delete
          </Button>
        </div>
      </div>

      {/* Basic Info Card */}
      <Card>
        <CardHeader>
          <CardTitle className="text-2xl font-bold flex items-center">
            <Package className="mr-3 h-7 w-7 text-primary" />
            {product.name || 'Unnamed Product'}
          </CardTitle>
          <CardDescription className="pt-1">
            {product.description?.purpose || 'No description provided'}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* ODPS v1.0.0 Lifecycle actions */}
          <div className="flex items-center gap-2">
            {canWrite && product.status?.toLowerCase() !== 'retired' && (
              <Button
                size="sm"
                variant="outline"
                onClick={() => setIsStatusTransitionDialogOpen(true)}
                disabled={isTransitioning}
              >
                Change Status
              </Button>
            )}
            {product.status?.toLowerCase() === 'retired' && (
              <Badge variant="destructive">Terminal State - No transitions available</Badge>
            )}
          </div>

          <div className="grid md:grid-cols-4 gap-4">
            <div className="space-y-1">
              <Label>Status:</Label>
              <Badge variant={getStatusColor(product.status)} className="ml-1">
                {product.status || 'N/A'}
              </Badge>
            </div>
            <div className="space-y-1">
              <Label>Version:</Label>
              <Badge variant="secondary" className="ml-1">{product.version || 'N/A'}</Badge>
            </div>
            <div className="space-y-1">
              <Label>Domain:</Label>
              {product.domain && getDomainIdByName(domainLabel) ? (
                <span
                  className="text-sm block cursor-pointer text-primary hover:underline"
                  onClick={() => navigate(`/data-domains/${getDomainIdByName(domainLabel)}`)}
                >
                  {domainLabel}
                </span>
              ) : (
                <span className="text-sm block">{domainLabel}</span>
              )}
            </div>
            <div className="space-y-1">
              <Label>Tenant:</Label>
              <span className="text-sm block">{product.tenant || 'N/A'}</span>
            </div>
            <div className="space-y-1">
              <Label>Owner:</Label>
              <span className="text-sm block">{owner}</span>
            </div>
            <div className="space-y-1">
              <Label>API Version:</Label>
              <Badge variant="outline" className="ml-1">{product.apiVersion}</Badge>
            </div>
            <div className="space-y-1">
              <Label>Created:</Label>
              <span className="text-sm block">{formatDate(product.created_at)}</span>
            </div>
            <div className="space-y-1">
              <Label>Updated:</Label>
              <span className="text-sm block">{formatDate(product.updated_at)}</span>
            </div>
          </div>

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
              onRemove={canWrite ? removeLink : undefined}
              onAdd={canWrite ? () => setIriDialogOpen(true) : undefined}
            />
          </div>
        </CardContent>
      </Card>

      {/* ODPS Structured Description */}
      {product.description && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span className="flex items-center">
                <FileText className="mr-2 h-5 w-5" />
                Structured Description (ODPS)
              </span>
              {canWrite && <Button size="sm" variant="outline"><Pencil className="h-4 w-4" /></Button>}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {product.description.purpose && (
              <div>
                <Label>Purpose:</Label>
                <p className="text-sm mt-1">{product.description.purpose}</p>
              </div>
            )}
            {product.description.limitations && (
              <div>
                <Label>Limitations:</Label>
                <p className="text-sm mt-1">{product.description.limitations}</p>
              </div>
            )}
            {product.description.usage && (
              <div>
                <Label>Usage:</Label>
                <p className="text-sm mt-1">{product.description.usage}</p>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Input Ports Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>Input Ports ({product.inputPorts?.length || 0})</span>
            {canWrite && <Button size="sm" onClick={() => setIsInputPortDialogOpen(true)}><Plus className="mr-2 h-4 w-4" />Add Input Port</Button>}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {product.inputPorts && product.inputPorts.length > 0 ? (
            <div className="space-y-2">
              {product.inputPorts.map((port, idx) => (
                <div key={idx} className="border rounded p-3">
                  <div className="font-medium">{port.name} (v{port.version})</div>
                  <div className="text-sm text-muted-foreground">Contract: {port.contractId}</div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No input ports defined</p>
          )}
        </CardContent>
      </Card>

      {/* Output Ports Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>Output Ports ({product.outputPorts?.length || 0})</span>
            {canWrite && <Button size="sm" onClick={() => setIsOutputPortDialogOpen(true)}><Plus className="mr-2 h-4 w-4" />Add Output Port</Button>}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {product.outputPorts && product.outputPorts.length > 0 ? (
            <div className="space-y-2">
              {product.outputPorts.map((port, idx) => (
                <div key={idx} className="border rounded p-3">
                  <div className="font-medium">{port.name} (v{port.version})</div>
                  {port.description && <div className="text-sm">{port.description}</div>}
                  {port.contractId && <div className="text-sm text-muted-foreground">Contract: {port.contractId}</div>}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No output ports defined</p>
          )}
        </CardContent>
      </Card>

      {/* Management Ports Section (NEW in ODPS v1.0.0) */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>Management Ports ({product.managementPorts?.length || 0})</span>
            {canWrite && <Button size="sm" onClick={() => setIsManagementPortDialogOpen(true)}><Plus className="mr-2 h-4 w-4" />Add Management Port</Button>}
          </CardTitle>
          <CardDescription>Observability, control, and discoverability endpoints</CardDescription>
        </CardHeader>
        <CardContent>
          {product.managementPorts && product.managementPorts.length > 0 ? (
            <div className="space-y-2">
              {product.managementPorts.map((port, idx) => (
                <div key={idx} className="border rounded p-3">
                  <div className="font-medium">{port.name}</div>
                  <div className="text-sm">Content: {port.content}</div>
                  {port.url && <div className="text-sm text-muted-foreground">URL: {port.url}</div>}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No management ports defined</p>
          )}
        </CardContent>
      </Card>

      {/* Team Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>Team ({product.team?.members?.length || 0} members)</span>
            {canWrite && <Button size="sm" onClick={() => setIsTeamMemberDialogOpen(true)}><Plus className="mr-2 h-4 w-4" />Add Member</Button>}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {product.team?.members && product.team.members.length > 0 ? (
            <div className="space-y-2">
              {product.team.members.map((member, idx) => (
                <div key={idx} className="border rounded p-3">
                  <div className="font-medium">{member.name || member.username}</div>
                  <div className="text-sm text-muted-foreground">
                    {member.role && `Role: ${member.role}`} | {member.username}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No team members defined</p>
          )}
        </CardContent>
      </Card>

      {/* Support Channels */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>Support Channels ({product.support?.length || 0})</span>
            {canWrite && <Button size="sm" onClick={() => setIsSupportChannelDialogOpen(true)}><Plus className="mr-2 h-4 w-4" />Add Channel</Button>}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {product.support && product.support.length > 0 ? (
            <div className="space-y-2">
              {product.support.map((channel, idx) => (
                <div key={idx} className="border rounded p-3">
                  <div className="font-medium">{channel.channel}</div>
                  <div className="text-sm">URL: <a href={channel.url} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">{channel.url}</a></div>
                  {channel.tool && <div className="text-sm text-muted-foreground">Tool: {channel.tool}</div>}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No support channels defined</p>
          )}
        </CardContent>
      </Card>

      {/* Metadata Panel */}
      <EntityMetadataPanel entityId={productId!} entityType="data_product" />

      {/* Costs Panel */}
      <EntityCostsPanel entityId={productId!} entityType="data_product" />

      {/* Dialogs */}
      <DataProductCreateDialog
        open={isEditDialogOpen}
        onOpenChange={setIsEditDialogOpen}
        onSuccess={() => {
          setIsEditDialogOpen(false);
          fetchProductDetails();
        }}
      />

      <CreateVersionDialog
        open={isVersionDialogOpen}
        onClose={() => setIsVersionDialogOpen(false)}
        onSubmit={submitNewVersion}
        currentVersion={product.version || '1.0.0'}
      />

      <ConceptSelectDialog
        open={iriDialogOpen}
        onOpenChange={setIriDialogOpen}
        onSelect={addIri}
      />

      <RequestAccessDialog
        open={isRequestAccessDialogOpen}
        onOpenChange={setIsRequestAccessDialogOpen}
        entityId={productId!}
        entityType="data_product"
        entityName={product.name || 'Unnamed Product'}
      />

      {/* Nested Entity Form Dialogs */}
      <InputPortFormDialog
        isOpen={isInputPortDialogOpen}
        onOpenChange={setIsInputPortDialogOpen}
        onSubmit={handleAddInputPort}
      />

      <OutputPortFormDialog
        isOpen={isOutputPortDialogOpen}
        onOpenChange={setIsOutputPortDialogOpen}
        onSubmit={handleAddOutputPort}
      />

      <ManagementPortFormDialog
        isOpen={isManagementPortDialogOpen}
        onOpenChange={setIsManagementPortDialogOpen}
        onSubmit={handleAddManagementPort}
      />

      <TeamMemberFormDialog
        isOpen={isTeamMemberDialogOpen}
        onOpenChange={setIsTeamMemberDialogOpen}
        onSubmit={handleAddTeamMember}
      />

      <SupportChannelFormDialog
        isOpen={isSupportChannelDialogOpen}
        onOpenChange={setIsSupportChannelDialogOpen}
        onSubmit={handleAddSupportChannel}
      />

      {/* ODPS v1.0.0 Lifecycle State Machine */}
      <StatusTransitionDialog
        isOpen={isStatusTransitionDialogOpen}
        onOpenChange={setIsStatusTransitionDialogOpen}
        currentStatus={product.status || DataProductStatus.DRAFT}
        onTransition={handleStatusTransition}
        productName={product.name}
      />

      {/* ODPS v1.0.0 Import/Export */}
      <ImportExportDialog
        isOpen={isImportExportDialogOpen}
        onOpenChange={setIsImportExportDialogOpen}
        currentProduct={product}
      />
    </div>
  );
}
