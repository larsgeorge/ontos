import { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useToast } from '@/hooks/use-toast';
import { useApi } from '@/hooks/use-api';
import { useNotificationsStore } from '@/stores/notifications-store';
import { Loader2, AlertCircle, FileText, Eye, Rocket, Database } from 'lucide-react';

type RequestType = 'access' | 'review' | 'publish' | 'deploy';

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
  const { post } = useApi();
  const { toast } = useToast();
  const refreshNotifications = useNotificationsStore((state) => state.refreshNotifications);
  
  const [requestType, setRequestType] = useState<RequestType>('deploy');
  const [message, setMessage] = useState('');
  const [justification, setJustification] = useState('');
  const [catalog, setCatalog] = useState('');
  const [schema, setSchema] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
    setError(null);
    onOpenChange(false);
  };

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
            <div className="space-y-2">
              {(['deploy', 'review', 'publish', 'access'] as RequestType[]).map((type) => {
                const config = getRequestTypeConfig(type);
                return (
                  <div key={type} className={`flex items-start space-x-3 p-3 rounded-lg border ${!config.enabled ? 'opacity-50 bg-muted/30' : 'hover:bg-muted/50 cursor-pointer'} ${requestType === type ? 'border-primary bg-primary/10' : ''}`} 
                    onClick={() => config.enabled && setRequestType(type)}>
                    <input 
                      type="radio" 
                      id={type} 
                      name="requestType" 
                      value={type} 
                      checked={requestType === type}
                      disabled={!config.enabled}
                      onChange={(e) => setRequestType(e.target.value as RequestType)}
                      className="mt-1"
                    />
                    <div className="flex-1">
                      <label htmlFor={type} className={`flex items-center gap-2 text-sm font-medium ${!config.enabled ? 'cursor-not-allowed' : 'cursor-pointer'}`}>
                        {config.icon}
                        {config.title}
                      </label>
                      <p className="text-xs text-muted-foreground mt-1">{config.description}</p>
                      {!config.enabled && (
                        <p className="text-xs text-destructive mt-1">
                          Not available for status '{contractStatus}'
                        </p>
                      )}
                    </div>
                  </div>
                );
              })}
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
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-2">
                  <Label htmlFor="deploy-catalog" className="text-sm font-medium">
                    Target Catalog (Optional)
                  </Label>
                  <Input
                    id="deploy-catalog"
                    value={catalog}
                    onChange={(e) => setCatalog(e.target.value)}
                    placeholder="catalog_name"
                    disabled={submitting}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="deploy-schema" className="text-sm font-medium">
                    Target Schema (Optional)
                  </Label>
                  <Input
                    id="deploy-schema"
                    value={schema}
                    onChange={(e) => setSchema(e.target.value)}
                    placeholder="schema_name"
                    disabled={submitting}
                  />
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

