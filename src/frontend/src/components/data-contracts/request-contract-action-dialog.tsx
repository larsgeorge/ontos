import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useToast } from '@/hooks/use-toast';
import { useApi } from '@/hooks/use-api';
import { useNotificationsStore } from '@/stores/notifications-store';
import { Loader2, AlertCircle, FileText, Eye, Rocket, Database, ShieldCheck, Info, RefreshCw } from 'lucide-react';
import type { DeploymentPolicy } from '@/types/deployment-policy';
import {
  getAllowedTransitions,
  getStatusConfig,
  getRecommendedAction,
} from '@/lib/odcs-lifecycle';

type RequestType = 'access' | 'review' | 'publish' | 'deploy' | 'status_change';

interface RequestContractActionDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  contractId: string;
  contractName?: string;
  contractStatus?: string;
  onSuccess?: () => void;
}

export default function RequestContractActionDialog({
  isOpen,
  onOpenChange,
  contractId,
  contractName,
  contractStatus,
  onSuccess
}: RequestContractActionDialogProps) {
  const { post, get } = useApi();
  const { toast } = useToast();
  const refreshNotifications = useNotificationsStore((state) => state.refreshNotifications);
  
  const [requestType, setRequestType] = useState<RequestType>('deploy');
  const [message, setMessage] = useState('');
  const [justification, setJustification] = useState('');
  const [catalog, setCatalog] = useState('');
  const [schema, setSchema] = useState('');
  const [targetStatus, setTargetStatus] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Deployment policy state
  const [deploymentPolicy, setDeploymentPolicy] = useState<DeploymentPolicy | null>(null);
  const [loadingPolicy, setLoadingPolicy] = useState(false);
  const [policyError, setPolicyError] = useState<string | null>(null);

  const getRequestTypeConfig = (type: RequestType) => {
    switch (type) {
      case 'access':
        return {
          icon: <Eye className="h-5 w-5" />,
          title: 'Request Access to Contract',
          description: 'Request permission to view and use this data contract.',
          enabled: true,
          endpoint: '/api/access-requests',
        };
      case 'review':
        return {
          icon: <FileText className="h-5 w-5" />,
          title: 'Request Data Steward Review',
          description: 'Submit this contract for review by a data steward (transitions to PROPOSED status).',
          enabled: contractStatus?.toLowerCase() === 'draft',
          endpoint: `/api/data-contracts/${contractId}/request-review`,
        };
      case 'publish':
        return {
          icon: <Rocket className="h-5 w-5" />,
          title: 'Request Publish to Marketplace',
          description: 'Request to publish this approved contract to the organization-wide marketplace.',
          enabled: contractStatus?.toLowerCase() === 'approved',
          endpoint: `/api/data-contracts/${contractId}/request-publish`,
        };
      case 'deploy':
        return {
          icon: <Database className="h-5 w-5" />,
          title: 'Request Deploy to Unity Catalog',
          description: 'Request approval to deploy this contract to Unity Catalog.',
          enabled: true,
          endpoint: `/api/data-contracts/${contractId}/request-deploy`,
        };
      case 'status_change':
        const allowedTransitions = contractStatus ? getAllowedTransitions(contractStatus) : [];
        return {
          icon: <RefreshCw className="h-5 w-5" />,
          title: 'Request Status Change',
          description: 'Request approval to change the lifecycle status of this contract.',
          enabled: allowedTransitions.length > 0,
          endpoint: `/api/data-contracts/${contractId}/request-status-change`,
        };
    }
  };

  const validateForm = (): boolean => {
    setError(null);
    
    if (requestType === 'access') {
      if (!message.trim()) {
        setError('Please provide a reason for requesting access');
        return false;
      }
      if (message.trim().length < 10) {
        setError('Please provide a more detailed reason (at least 10 characters)');
        return false;
      }
    }
    
    if (requestType === 'review') {
      // Message is optional for review
    }
    
    if (requestType === 'publish') {
      // Justification is optional but recommended
    }
    
    if (requestType === 'deploy') {
      // Catalog and schema are optional
    }
    
    if (requestType === 'status_change') {
      if (!targetStatus) {
        setError('Please select a target status');
        return false;
      }
      if (!justification.trim()) {
        setError('Please provide a justification for the status change');
        return false;
      }
      if (justification.trim().length < 20) {
        setError('Please provide a more detailed justification (at least 20 characters)');
        return false;
      }
    }
    
    return true;
  };

  const handleSubmit = async () => {
    if (!validateForm()) {
      return;
    }

    const config = getRequestTypeConfig(requestType);
    if (!config.enabled) {
      setError(`Cannot request ${requestType} for a contract with status '${contractStatus}'`);
      return;
    }

    setError(null);
    setSubmitting(true);

    try {
      let payload: any;
      
      if (requestType === 'access') {
        // Use existing access request endpoint
        payload = {
          entity_type: 'data_contract',
          entity_ids: [contractId],
          message: message.trim(),
        };
      } else if (requestType === 'review') {
        payload = {
          message: message.trim() || undefined,
        };
      } else if (requestType === 'publish') {
        payload = {
          justification: justification.trim() || undefined,
        };
      } else if (requestType === 'deploy') {
        payload = {
          catalog: catalog.trim() || undefined,
          schema: schema.trim() || undefined,
          message: message.trim() || undefined,
        };
      } else if (requestType === 'status_change') {
        payload = {
          target_status: targetStatus,
          justification: justification.trim(),
          current_status: contractStatus,
        };
      }

      const response = await post(config.endpoint, payload);

      if (response.error) {
        throw new Error(response.error);
      }

      toast({
        title: 'Request Submitted',
        description: `Your ${requestType} request has been submitted and you will be notified of the decision.`
      });

      // Refresh notifications
      refreshNotifications();

      // Call success callback
      if (onSuccess) {
        onSuccess();
      }

      // Reset form and close dialog
      setMessage('');
      setJustification('');
      setCatalog('');
      setSchema('');
      setTargetStatus('');
      onOpenChange(false);

    } catch (e: any) {
      setError(e.message || 'Failed to submit request');
      toast({
        title: 'Error',
        description: e.message || 'Failed to submit request',
        variant: 'destructive'
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleCancel = () => {
    setMessage('');
    setJustification('');
    setCatalog('');
    setSchema('');
    setTargetStatus('');
    setError(null);
    onOpenChange(false);
  };

  // Fetch deployment policy when deploy option is selected
  useEffect(() => {
    const fetchDeploymentPolicy = async () => {
      if (requestType === 'deploy' && isOpen) {
        setLoadingPolicy(true);
        setPolicyError(null);
        
        try {
          const response = await get('/api/user/deployment-policy');
          
          if (response.error) {
            throw new Error(response.error);
          }
          
          const policy = response.data as DeploymentPolicy;
          setDeploymentPolicy(policy);
          
          // Pre-populate with default catalog/schema if available and fields are empty
          if (policy.default_catalog && !catalog) {
            setCatalog(policy.default_catalog);
          }
          if (policy.default_schema && !schema) {
            setSchema(policy.default_schema);
          }
        } catch (e: any) {
          setPolicyError(e.message || 'Failed to load deployment policy');
          console.error('Error fetching deployment policy:', e);
        } finally {
          setLoadingPolicy(false);
        }
      }
    };
    
    fetchDeploymentPolicy();
  }, [requestType, isOpen, get]);
  
  const currentConfig = getRequestTypeConfig(requestType);

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            Request Action
          </DialogTitle>
          <DialogDescription>
            Select the type of request you want to submit for this data contract.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Contract Information */}
          <div className="p-3 bg-muted/50 rounded-lg border">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <span className="font-medium">Contract:</span>
              <span className="font-mono">{contractId}</span>
            </div>
            {contractName && (
              <div className="text-sm font-medium mt-1">{contractName}</div>
            )}
            {contractStatus && (
              <div className="text-xs text-muted-foreground mt-1">
                Status: <span className="uppercase">{contractStatus}</span>
              </div>
            )}
          </div>

          {/* Request Type Selection */}
          <div className="space-y-3">
            <Label className="text-sm font-medium">Request Type *</Label>
            <Select value={requestType} onValueChange={(value) => setRequestType(value as RequestType)}>
              <SelectTrigger>
                <SelectValue>
                  <div className="flex items-center gap-2">
                    {currentConfig.icon}
                    <span>{currentConfig.title}</span>
                  </div>
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                {(['status_change', 'deploy', 'review', 'publish', 'access'] as RequestType[]).map((type) => {
                  const config = getRequestTypeConfig(type);
                  return (
                    <SelectItem key={type} value={type} disabled={!config.enabled}>
                      <div className="flex items-center gap-2">
                        {config.icon}
                        <span>{config.title}</span>
                      </div>
                    </SelectItem>
                  );
                })}
              </SelectContent>
            </Select>
            <div className="p-3 bg-muted/50 rounded-lg border text-sm">
              <p className="text-muted-foreground">{currentConfig.description}</p>
              {!currentConfig.enabled && (
                <p className="text-destructive mt-2 text-xs">
                  Not available for status '{contractStatus}'
                </p>
              )}
            </div>
          </div>

          {/* Dynamic Form Fields */}
          {requestType === 'access' && (
            <div className="space-y-2">
              <Label htmlFor="access-reason" className="text-sm font-medium">
                Reason for Access Request *
              </Label>
              <Textarea
                id="access-reason"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="Please explain why you need access to this contract..."
                className="min-h-[100px] resize-none"
                disabled={submitting}
              />
              <div className="text-xs text-muted-foreground">
                Minimum 10 characters required.
              </div>
            </div>
          )}

          {requestType === 'review' && (
            <div className="space-y-2">
              <Label htmlFor="review-message" className="text-sm font-medium">
                Message (Optional)
              </Label>
              <Textarea
                id="review-message"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="Add any notes for the data steward reviewing this contract..."
                className="min-h-[80px] resize-none"
                disabled={submitting}
              />
            </div>
          )}

          {requestType === 'publish' && (
            <div className="space-y-2">
              <Label htmlFor="publish-justification" className="text-sm font-medium">
                Justification (Optional)
              </Label>
              <Textarea
                id="publish-justification"
                value={justification}
                onChange={(e) => setJustification(e.target.value)}
                placeholder="Explain why this contract should be published to the marketplace..."
                className="min-h-[80px] resize-none"
                disabled={submitting}
              />
            </div>
          )}

          {requestType === 'deploy' && (
            <div className="space-y-3">
              {/* Loading Policy Indicator */}
              {loadingPolicy && (
                <Alert>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <AlertDescription>Loading deployment policy...</AlertDescription>
                </Alert>
              )}
              
              {/* Policy Error */}
              {policyError && (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>{policyError}</AlertDescription>
                </Alert>
              )}
              
              {/* Policy Info Banner */}
              {deploymentPolicy && !loadingPolicy && (
                <Alert className="bg-blue-50 border-blue-200 dark:bg-blue-950 dark:border-blue-800">
                  <ShieldCheck className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                  <AlertDescription className="text-sm text-blue-800 dark:text-blue-200">
                    <strong>Deployment Policy:</strong> You can deploy to{' '}
                    {deploymentPolicy.allowed_catalogs.length === 0 
                      ? 'no catalogs (contact admin)'
                      : deploymentPolicy.allowed_catalogs.length === 1
                      ? `${deploymentPolicy.allowed_catalogs[0]}`
                      : `${deploymentPolicy.allowed_catalogs.length} allowed catalogs`}
                    {deploymentPolicy.require_approval && ' (requires approval)'}
                  </AlertDescription>
                </Alert>
              )}
              
              <div className="grid grid-cols-2 gap-3">
                {/* Catalog Dropdown or Input */}
                <div className="space-y-2">
                  <Label htmlFor="deploy-catalog" className="text-sm font-medium">
                    Target Catalog (Optional)
                  </Label>
                  {deploymentPolicy && deploymentPolicy.allowed_catalogs.length > 0 && deploymentPolicy.allowed_catalogs.includes('*') ? (
                    // Wildcard - allow any catalog via text input
                    <Input
                      id="deploy-catalog"
                      value={catalog}
                      onChange={(e) => setCatalog(e.target.value)}
                      placeholder={deploymentPolicy.default_catalog || "Enter catalog name..."}
                      disabled={submitting || loadingPolicy}
                    />
                  ) : deploymentPolicy && deploymentPolicy.allowed_catalogs.length > 0 ? (
                    // Specific catalogs - show dropdown
                    <Select
                      value={catalog}
                      onValueChange={setCatalog}
                      disabled={submitting || loadingPolicy}
                    >
                      <SelectTrigger id="deploy-catalog">
                        <SelectValue placeholder="Select catalog..." />
                      </SelectTrigger>
                      <SelectContent>
                        {deploymentPolicy.allowed_catalogs.map((cat) => (
                          <SelectItem key={cat} value={cat}>
                            {cat}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  ) : (
                    // No catalogs available
                    <Select disabled>
                      <SelectTrigger>
                        <SelectValue placeholder="No catalogs available" />
                      </SelectTrigger>
                    </Select>
                  )}
                  {deploymentPolicy?.default_catalog && catalog === deploymentPolicy.default_catalog && (
                    <div className="text-xs text-muted-foreground flex items-center gap-1">
                      <Info className="h-3 w-3" />
                      Default catalog for your role
                    </div>
                  )}
                  {deploymentPolicy?.allowed_catalogs.includes('*') && (
                    <div className="text-xs text-muted-foreground flex items-center gap-1">
                      <Info className="h-3 w-3" />
                      You can deploy to any catalog
                    </div>
                  )}
                </div>
                
                {/* Schema Dropdown or Input */}
                <div className="space-y-2">
                  <Label htmlFor="deploy-schema" className="text-sm font-medium">
                    Target Schema (Optional)
                  </Label>
                  {deploymentPolicy && deploymentPolicy.allowed_schemas.length > 0 && deploymentPolicy.allowed_schemas.includes('*') ? (
                    // Wildcard - allow any schema via text input
                    <Input
                      id="deploy-schema"
                      value={schema}
                      onChange={(e) => setSchema(e.target.value)}
                      placeholder={deploymentPolicy.default_schema || "Enter schema name..."}
                      disabled={submitting || loadingPolicy}
                    />
                  ) : deploymentPolicy && deploymentPolicy.allowed_schemas.length > 0 ? (
                    // Specific schemas - show dropdown
                    <Select
                      value={schema}
                      onValueChange={setSchema}
                      disabled={submitting || loadingPolicy}
                    >
                      <SelectTrigger id="deploy-schema">
                        <SelectValue placeholder="Select schema..." />
                      </SelectTrigger>
                      <SelectContent>
                        {deploymentPolicy.allowed_schemas.map((sch) => (
                          <SelectItem key={sch} value={sch}>
                            {sch}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  ) : (
                    // No specific schemas - allow text input for any schema
                    <Input
                      id="deploy-schema"
                      value={schema}
                      onChange={(e) => setSchema(e.target.value)}
                      placeholder={deploymentPolicy?.default_schema || "Enter schema name..."}
                      disabled={submitting || loadingPolicy}
                    />
                  )}
                  {deploymentPolicy?.default_schema && schema === deploymentPolicy.default_schema && (
                    <div className="text-xs text-muted-foreground flex items-center gap-1">
                      <Info className="h-3 w-3" />
                      Default schema for your role
                    </div>
                  )}
                  {deploymentPolicy && (deploymentPolicy.allowed_schemas.length === 0 || deploymentPolicy.allowed_schemas.includes('*')) && (
                    <div className="text-xs text-muted-foreground flex items-center gap-1">
                      <Info className="h-3 w-3" />
                      You can deploy to any schema
                    </div>
                  )}
                </div>
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="deploy-message" className="text-sm font-medium">
                  Message (Optional)
                </Label>
                <Textarea
                  id="deploy-message"
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  placeholder="Add any deployment notes or requirements..."
                  className="min-h-[60px] resize-none"
                  disabled={submitting}
                />
              </div>
            </div>
          )}

          {requestType === 'status_change' && (
            <div className="space-y-4">
              {/* Current Status */}
              {contractStatus && (
                <div className="rounded-lg border bg-muted/50 p-3">
                  <div className="flex items-center gap-2 mb-1">
                    <Label className="text-sm font-semibold">Current Status:</Label>
                    <span className="text-lg">{getStatusConfig(contractStatus).icon}</span>
                    <span className="font-medium">{getStatusConfig(contractStatus).label}</span>
                  </div>
                  <p className="text-xs text-muted-foreground">{getStatusConfig(contractStatus).description}</p>
                </div>
              )}

              {/* Recommended Action */}
              {contractStatus && getRecommendedAction(contractStatus) && (
                <Alert>
                  <Info className="h-4 w-4" />
                  <AlertDescription className="text-sm">
                    <strong>Recommended:</strong> {getRecommendedAction(contractStatus)}
                  </AlertDescription>
                </Alert>
              )}

              {/* Target Status Selection */}
              {contractStatus && getAllowedTransitions(contractStatus).length > 0 ? (
                <div className="space-y-2">
                  <Label className="text-sm font-medium">Select Target Status *</Label>
                  <Select value={targetStatus} onValueChange={setTargetStatus}>
                    <SelectTrigger>
                      <SelectValue placeholder="Choose target status...">
                        {targetStatus && (
                          <div className="flex items-center gap-2">
                            <span className="text-lg">{getStatusConfig(targetStatus).icon}</span>
                            <span>{getStatusConfig(targetStatus).label}</span>
                          </div>
                        )}
                      </SelectValue>
                    </SelectTrigger>
                    <SelectContent>
                      {getAllowedTransitions(contractStatus).map((status) => {
                        const config = getStatusConfig(status);
                        return (
                          <SelectItem key={status} value={status}>
                            <div className="flex items-center gap-2">
                              <span className="text-lg">{config.icon}</span>
                              <span>{config.label}</span>
                            </div>
                          </SelectItem>
                        );
                      })}
                    </SelectContent>
                  </Select>
                  {targetStatus && (
                    <div className="p-3 bg-muted/50 rounded-lg border text-sm">
                      <p className="text-muted-foreground">{getStatusConfig(targetStatus).description}</p>
                    </div>
                  )}
                </div>
              ) : (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>
                    <strong>Terminal State:</strong> No transitions available from {contractStatus ? getStatusConfig(contractStatus).label : 'current'} status.
                  </AlertDescription>
                </Alert>
              )}

              {/* Justification */}
              <div className="space-y-2">
                <Label htmlFor="status-justification" className="text-sm font-medium">
                  Justification *
                </Label>
                <Textarea
                  id="status-justification"
                  value={justification}
                  onChange={(e) => setJustification(e.target.value)}
                  placeholder="Explain why this status change is needed and any relevant context..."
                  className="min-h-[100px] resize-none"
                  disabled={submitting}
                />
                <div className="text-xs text-muted-foreground">
                  Minimum 20 characters required. This will be reviewed by an admin.
                </div>
              </div>

              {/* Lifecycle Diagram */}
              <div className="rounded-lg border p-3 bg-muted/20">
                <Label className="text-xs font-semibold mb-2 block">ODCS Lifecycle Flow:</Label>
                <div className="flex items-center gap-1 text-xs font-mono flex-wrap">
                  <span className={contractStatus?.toLowerCase() === 'draft' ? 'font-bold text-primary' : ''}>draft</span>
                  <span>→</span>
                  <span className={contractStatus?.toLowerCase() === 'proposed' ? 'font-bold text-primary' : ''}>proposed</span>
                  <span>→</span>
                  <span className={contractStatus?.toLowerCase() === 'under_review' ? 'font-bold text-primary' : ''}>under_review</span>
                  <span>→</span>
                  <span className={contractStatus?.toLowerCase() === 'approved' ? 'font-bold text-primary' : ''}>approved</span>
                  <span>→</span>
                  <span className={contractStatus?.toLowerCase() === 'active' ? 'font-bold text-primary' : ''}>active</span>
                  <span>→</span>
                  <span className={contractStatus?.toLowerCase() === 'certified' ? 'font-bold text-primary' : ''}>certified</span>
                  <span>→</span>
                  <span className={contractStatus?.toLowerCase() === 'deprecated' ? 'font-bold text-primary' : ''}>deprecated</span>
                  <span>→</span>
                  <span className={contractStatus?.toLowerCase() === 'retired' ? 'font-bold text-primary' : ''}>retired</span>
                </div>
                <p className="text-xs text-muted-foreground mt-2">
                  Current status is highlighted. Emergency deprecation allowed from any status.
                </p>
              </div>
            </div>
          )}

          {/* Error Alert */}
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button
            variant="outline"
            onClick={handleCancel}
            disabled={submitting}
          >
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={submitting || !currentConfig.enabled}
          >
            {submitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {submitting ? 'Sending Request...' : 'Send Request'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

