import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { DataProduct, InputPort, OutputPort, ManagementPort, TeamMember, Support } from '@/types/data-product';
import DataProductCreateDialog from '@/components/data-products/data-product-create-dialog';
import InputPortFormDialog from '@/components/data-products/input-port-form-dialog';
import OutputPortFormDialog from '@/components/data-products/output-port-form-dialog';
import ManagementPortFormDialog from '@/components/data-products/management-port-form-dialog';
import TeamMemberFormDialog from '@/components/data-products/team-member-form-dialog';
import SupportChannelFormDialog from '@/components/data-products/support-channel-form-dialog';
import ImportExportDialog from '@/components/data-products/import-export-dialog';
import ImportTeamMembersDialog from '@/components/data-contracts/import-team-members-dialog';
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
import RequestProductActionDialog from '@/components/data-products/request-product-action-dialog';
import EntityCostsPanel from '@/components/costs/entity-costs-panel';
import LinkContractToPortDialog from '@/components/data-products/link-contract-to-port-dialog';
import { Link2, Unlink } from 'lucide-react';

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
  const [isRequestDialogOpen, setIsRequestDialogOpen] = useState(false);

  // Dialog states for nested entities
  const [isInputPortDialogOpen, setIsInputPortDialogOpen] = useState(false);
  const [isOutputPortDialogOpen, setIsOutputPortDialogOpen] = useState(false);
  const [isManagementPortDialogOpen, setIsManagementPortDialogOpen] = useState(false);
  const [isTeamMemberDialogOpen, setIsTeamMemberDialogOpen] = useState(false);
  const [isSupportChannelDialogOpen, setIsSupportChannelDialogOpen] = useState(false);
  const [isImportExportDialogOpen, setIsImportExportDialogOpen] = useState(false);
  const [isImportTeamMembersOpen, setIsImportTeamMembersOpen] = useState(false);

  // Team member editing state
  const [editingTeamMemberIndex, setEditingTeamMemberIndex] = useState<number | null>(null);

  // Contract linking states
  const [isLinkContractDialogOpen, setIsLinkContractDialogOpen] = useState(false);
  const [selectedPortForLinking, setSelectedPortForLinking] = useState<number | null>(null);
  const [contractNames, setContractNames] = useState<Record<string, string>>({});

  // Owner team state
  const [ownerTeamName, setOwnerTeamName] = useState<string>('');

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

  const fetchOwnerTeamName = async (teamId: string) => {
    if (!teamId) return
    try {
      const response = await fetch(`/api/teams/${teamId}`)
      if (response.ok) {
        const data = await response.json()
        setOwnerTeamName(data.name || '')
      }
    } catch (e) {
      console.warn('Failed to fetch owner team:', e)
    }
  };

  const fetchContractNames = async (outputPorts: OutputPort[]) => {
    const names: Record<string, string> = {};
    for (const port of outputPorts) {
      if (port.contractId && !names[port.contractId]) {
        try {
          const response = await fetch(`/api/data-contracts/${port.contractId}`);
          if (response.ok) {
            const contract = await response.json();
            names[port.contractId] = contract.name || port.contractId;
          }
        } catch (e) {
          console.warn(`Failed to fetch contract ${port.contractId}:`, e);
        }
      }
    }
    setContractNames(names);
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

      // Fetch owner team name if owner_team_id is set
      if (productData.owner_team_id) {
        await fetchOwnerTeamName(productData.owner_team_id);
      } else {
        setOwnerTeamName('');
      }

      // Fetch contract names for output ports
      if (productData.outputPorts && productData.outputPorts.length > 0) {
        await fetchContractNames(productData.outputPorts);
      }

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
      toast({
        title: 'Team Member Added',
        description: 'Team member added successfully.',
      });
    } catch (e: any) {
      toast({
        title: 'Error',
        description: e?.message || 'Failed to add team member',
        variant: 'destructive',
      });
      throw new Error(e?.message || 'Failed to add team member');
    }
  };

  const handleUpdateTeamMember = async (member: TeamMember) => {
    if (!productId || !product || editingTeamMemberIndex === null) return;
    try {
      const updatedMembers = [...(product.team?.members || [])];
      updatedMembers[editingTeamMemberIndex] = member;
      const updatedTeam = { ...product.team, members: updatedMembers };
      const res = await fetch(`/api/data-products/${productId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...product, team: updatedTeam }),
      });
      if (!res.ok) throw new Error(`Failed to update team member (${res.status})`);
      await fetchProductDetails();
      setEditingTeamMemberIndex(null);
      toast({
        title: 'Team Member Updated',
        description: 'Team member updated successfully.',
      });
    } catch (e: any) {
      toast({
        title: 'Error',
        description: e?.message || 'Failed to update team member',
        variant: 'destructive',
      });
      throw new Error(e?.message || 'Failed to update team member');
    }
  };

  const handleDeleteTeamMember = async (index: number) => {
    if (!productId || !product) return;
    if (!confirm('Remove this team member?')) return;
    try {
      const updatedMembers = (product.team?.members || []).filter((_, i) => i !== index);
      const updatedTeam = { ...product.team, members: updatedMembers };
      const res = await fetch(`/api/data-products/${productId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...product, team: updatedTeam }),
      });
      if (!res.ok) throw new Error(`Failed to delete team member (${res.status})`);
      await fetchProductDetails();
      toast({
        title: 'Team Member Removed',
        description: 'Team member removed successfully.',
      });
    } catch (e: any) {
      toast({
        title: 'Error',
        description: e?.message || 'Failed to delete team member',
        variant: 'destructive',
      });
    }
  };

  const handleImportTeamMembers = async (members: TeamMember[]) => {
    if (!productId || !product) return;
    
    try {
      // Append imported members to existing team members
      const existingMembers = product.team?.members || [];
      const updatedMembers = [...existingMembers, ...members];
      const updatedTeam = { ...product.team, members: updatedMembers };
      
      // Convert tags from objects to strings (tag FQNs) if needed
      const tags = Array.isArray(product.tags) 
        ? product.tags.map((tag: any) => typeof tag === 'string' ? tag : (tag.tag_fqn || tag.tagFQN))
        : [];
      
      // Store team assignment metadata in customProperties
      const teamMetadata = {
        property: 'assigned_team',
        value: JSON.stringify({
          team_id: product.owner_team_id,
          team_name: ownerTeamName,
          assigned_at: new Date().toISOString(),
          member_count: members.length
        }),
        description: 'App team assignment metadata'
      };
      
      const existingCustomProps = product.customProperties || [];
      const updatedCustomProps = [
        ...existingCustomProps.filter((p: any) => p.property !== 'assigned_team'),
        teamMetadata
      ];
      
      const res = await fetch(`/api/data-products/${productId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          ...product, 
          team: updatedTeam, 
          customProperties: updatedCustomProps,
          tags // Use converted tags
        }),
      });
      
      if (!res.ok) {
        const errorText = await res.text().catch(() => '');
        throw new Error(`Failed to import team members (${res.status}): ${errorText}`);
      }
      
      await fetchProductDetails();
      setIsImportTeamMembersOpen(false);
      
      toast({
        title: 'Team Members Imported',
        description: `Successfully imported ${members.length} team member(s) from ${ownerTeamName}`,
      });
    } catch (error) {
      console.error('Failed to import team members:', error);
      toast({
        title: 'Import Failed',
        description: error instanceof Error ? error.message : 'Failed to import team members',
        variant: 'destructive',
      });
      throw error;
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

  const handleLinkContract = (portIndex: number) => {
    setSelectedPortForLinking(portIndex);
    setIsLinkContractDialogOpen(true);
  };

  const handleUnlinkContract = async (portIndex: number) => {
    if (!productId || !product) return;
    if (!confirm('Unlink contract from this output port?')) return;
    
    try {
      const updatedPorts = [...(product.outputPorts || [])];
      updatedPorts[portIndex] = { ...updatedPorts[portIndex], contractId: undefined };
      
      // Normalize tags to string array (backend expects strings, not tag objects)
      const normalizedTags = product.tags?.map((tag: any) => 
        typeof tag === 'string' ? tag : tag.tag_id || tag.name || tag
      );
      
      const res = await fetch(`/api/data-products/${productId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          ...product, 
          tags: normalizedTags,
          outputPorts: updatedPorts 
        }),
      });
      
      if (!res.ok) throw new Error(`Failed to unlink contract (${res.status})`);
      
      await fetchProductDetails();
      toast({
        title: 'Contract Unlinked',
        description: 'Contract successfully unlinked from output port',
      });
    } catch (e: any) {
      toast({
        title: 'Error',
        description: e?.message || 'Failed to unlink contract',
        variant: 'destructive',
      });
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

  const domainLabel = product.domain ? (getDomainName(product.domain) || product.domain) : 'N/A';

  return (
    <div className="py-6 space-y-6">
      <div className="flex items-center justify-between">
        <Button variant="outline" onClick={() => navigate('/data-products')} size="sm">
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to List
        </Button>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => setIsRequestDialogOpen(true)} size="sm">
            <KeyRound className="mr-2 h-4 w-4" /> Request...
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
              {product.owner_team_id && ownerTeamName ? (
                <span
                  className="text-sm block cursor-pointer text-primary hover:underline"
                  onClick={() => navigate(`/teams/${product.owner_team_id}`)}
                  title={`Team ID: ${product.owner_team_id}`}
                >
                  {ownerTeamName}
                </span>
              ) : (
                <span className="text-sm block">{product.owner_team_id || 'N/A'}</span>
              )}
            </div>
            <div className="space-y-1">
              <Label>API Version:</Label>
              {product.apiVersion ? (
                <Badge variant="outline" className="ml-1">{product.apiVersion}</Badge>
              ) : (
                <span className="text-sm block">N/A</span>
              )}
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
                (product.tags || []).map((tag, index) => (
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
              {canWrite && <Button size="sm" variant="outline" onClick={handleEdit}><Pencil className="h-4 w-4" /></Button>}
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
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="font-medium">{port.name} (v{port.version})</div>
                      {port.description && <div className="text-sm text-muted-foreground mt-1">{port.description}</div>}
                      {port.contractId && (
                        <div className="mt-2 flex items-center gap-2">
                          <Badge 
                            variant="secondary" 
                            className="cursor-pointer hover:bg-secondary/80"
                            onClick={() => navigate(`/data-contracts/${port.contractId}`)}
                          >
                            Contract: {contractNames[port.contractId] || port.contractId}
                          </Badge>
                        </div>
                      )}
                    </div>
                    {canWrite && (
                      <div className="flex gap-2 ml-3">
                        {port.contractId ? (
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => handleUnlinkContract(idx)}
                            title="Unlink contract"
                          >
                            <Unlink className="h-4 w-4" />
                          </Button>
                        ) : (
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => handleLinkContract(idx)}
                            title="Link contract"
                          >
                            <Link2 className="h-4 w-4" />
                          </Button>
                        )}
                      </div>
                    )}
                  </div>
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
            <div className="flex gap-2">
              {canWrite && product.owner_team_id && (
                <Button 
                  size="sm" 
                  variant="outline"
                  onClick={() => setIsImportTeamMembersOpen(true)}
                >
                  <Download className="mr-2 h-4 w-4" />
                  Import from Team
                </Button>
              )}
              {canWrite && (
                <Button size="sm" onClick={() => setIsTeamMemberDialogOpen(true)}>
                  <Plus className="mr-2 h-4 w-4" />
                  Add Member
                </Button>
              )}
            </div>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {product.team?.members && product.team.members.length > 0 ? (
            <div className="space-y-2">
              {product.team.members.map((member, idx) => (
                <div key={idx} className="flex items-center justify-between p-3 border rounded-lg">
                  <div className="flex items-center gap-3">
                    <Badge variant="outline">{member.role || 'Member'}</Badge>
                    <span className="text-sm">{member.name || member.username}</span>
                  </div>
                  {canWrite && (
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => {
                          setEditingTeamMemberIndex(idx);
                          setIsTeamMemberDialogOpen(true);
                        }}
                      >
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleDeleteTeamMember(idx)}
                        className="text-destructive hover:text-destructive"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  )}
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
        product={product || undefined}
        mode="edit"
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

      <RequestProductActionDialog
        isOpen={isRequestDialogOpen}
        onOpenChange={setIsRequestDialogOpen}
        productId={productId!}
        productName={product.name}
        productStatus={product.status}
        currentVersion={product.version}
        onSuccess={() => fetchProductDetails()}
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
        product={product || undefined}
      />

      <ManagementPortFormDialog
        isOpen={isManagementPortDialogOpen}
        onOpenChange={setIsManagementPortDialogOpen}
        onSubmit={handleAddManagementPort}
      />

      <TeamMemberFormDialog
        isOpen={isTeamMemberDialogOpen}
        onOpenChange={(open) => {
          setIsTeamMemberDialogOpen(open);
          if (!open) setEditingTeamMemberIndex(null);
        }}
        onSubmit={editingTeamMemberIndex !== null ? handleUpdateTeamMember : handleAddTeamMember}
        initial={editingTeamMemberIndex !== null ? product?.team?.members?.[editingTeamMemberIndex] : undefined}
      />

      <SupportChannelFormDialog
        isOpen={isSupportChannelDialogOpen}
        onOpenChange={setIsSupportChannelDialogOpen}
        onSubmit={handleAddSupportChannel}
      />

      {/* ODPS v1.0.0 Import/Export */}
      <ImportExportDialog
        isOpen={isImportExportDialogOpen}
        onOpenChange={setIsImportExportDialogOpen}
        currentProduct={product}
      />

      {/* Import Team Members Dialog */}
      {product.owner_team_id && (
        <ImportTeamMembersDialog
          isOpen={isImportTeamMembersOpen}
          onOpenChange={setIsImportTeamMembersOpen}
          entityId={productId!}
          entityType="product"
          teamId={product.owner_team_id}
          teamName={ownerTeamName || product.owner_team_id}
          onImport={handleImportTeamMembers}
        />
      )}

      {/* Link Contract to Port Dialog */}
      <LinkContractToPortDialog
        isOpen={isLinkContractDialogOpen}
        onOpenChange={setIsLinkContractDialogOpen}
        productId={productId!}
        portIndex={selectedPortForLinking!}
        currentPort={selectedPortForLinking !== null ? product?.outputPorts?.[selectedPortForLinking] : undefined}
        onSuccess={() => {
          fetchProductDetails();
          setIsLinkContractDialogOpen(false);
          setSelectedPortForLinking(null);
        }}
      />
    </div>
  );
}
