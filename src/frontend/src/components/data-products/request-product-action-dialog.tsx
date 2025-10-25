import { useState } from 'react';
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
import { Loader2, AlertCircle, Eye, RefreshCw, Sparkles, CopyPlus, Info } from 'lucide-react';
import {
  getAllowedTransitions,
  getStatusConfig,
  getRecommendedAction,
} from '@/lib/odps-lifecycle';

type RequestType = 'access' | 'status_change' | 'genie_space' | 'new_version';

interface RequestProductActionDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  productId: string;
  productName?: string;
  productStatus?: string;
  currentVersion?: string;
  onSuccess?: () => void;
}

export default function RequestProductActionDialog({
  isOpen,
  onOpenChange,
  productId,
  productName,
  productStatus,
  currentVersion,
  onSuccess
}: RequestProductActionDialogProps) {
  const { post } = useApi();
  const { toast } = useToast();
  const refreshNotifications = useNotificationsStore((state) => state.refreshNotifications);
  
  const [requestType, setRequestType] = useState<RequestType>('access');
  const [message, setMessage] = useState('');
  const [justification, setJustification] = useState('');
  const [targetStatus, setTargetStatus] = useState('');
  const [newVersion, setNewVersion] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const getRequestTypeConfig = (type: RequestType) => {
    switch (type) {
      case 'access':
        return {
          icon: <Eye className="h-5 w-5" />,
          title: 'Request Access to Product',
          description: 'Request permission to view and use this data product.',
          enabled: true,
          endpoint: '/api/access-requests',
        };
      case 'status_change':
        const allowedTransitions = productStatus ? getAllowedTransitions(productStatus) : [];
        return {
          icon: <RefreshCw className="h-5 w-5" />,
          title: 'Request Status Change',
          description: 'Request approval to change the lifecycle status of this product.',
          enabled: allowedTransitions.length > 0,
          endpoint: `/api/data-products/${productId}/request-status-change`,
        };
      case 'genie_space':
        return {
          icon: <Sparkles className="h-5 w-5" />,
          title: 'Request Genie Space Creation',
          description: 'Request approval to create a Genie Space for this data product.',
          enabled: true,
          endpoint: '/api/data-products/genie-space',
        };
      case 'new_version':
        return {
          icon: <CopyPlus className="h-5 w-5" />,
          title: 'Request New Version',
          description: 'Request approval to create a new version of this data product.',
          enabled: true,
          endpoint: `/api/data-products/${productId}/request-version`,
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
    
    if (requestType === 'genie_space') {
      // Justification is optional but message can be provided
    }
    
    if (requestType === 'new_version') {
      if (!newVersion.trim()) {
        setError('Please provide a version number');
        return false;
      }
      if (!justification.trim()) {
        setError('Please provide a justification for the new version');
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
      setError(`Cannot request ${requestType} for a product with status '${productStatus}'`);
      return;
    }

    setError(null);
    setSubmitting(true);

    try {
      let payload: any;
      
      if (requestType === 'access') {
        // Use existing access request endpoint
        payload = {
          entity_type: 'data_product',
          entity_ids: [productId],
          message: message.trim(),
        };
      } else if (requestType === 'status_change') {
        payload = {
          target_status: targetStatus,
          justification: justification.trim(),
          current_status: productStatus,
        };
      } else if (requestType === 'genie_space') {
        payload = {
          product_ids: [productId],
          justification: justification.trim() || undefined,
        };
      } else if (requestType === 'new_version') {
        payload = {
          new_version: newVersion.trim(),
          justification: justification.trim(),
        };
      }

      const response = await post(config.endpoint, payload);

      if (response.error) {
        throw new Error(response.error);
      }

      toast({
        title: 'Request Submitted',
        description: `Your ${requestType.replace('_', ' ')} request has been submitted and you will be notified of the decision.`
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
      setTargetStatus('');
      setNewVersion('');
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
    setTargetStatus('');
    setNewVersion('');
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
            Select the type of request you want to submit for this data product.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Product Information */}
          <div className="p-3 bg-muted/50 rounded-lg border">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <span className="font-medium">Product:</span>
              <span className="font-mono">{productId}</span>
            </div>
            {productName && (
              <div className="text-sm font-medium mt-1">{productName}</div>
            )}
            {productStatus && (
              <div className="text-xs text-muted-foreground mt-1">
                Status: <span className="uppercase">{productStatus}</span>
              </div>
            )}
            {currentVersion && (
              <div className="text-xs text-muted-foreground mt-1">
                Version: <span>{currentVersion}</span>
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
                {(['access', 'status_change', 'genie_space', 'new_version'] as RequestType[]).map((type) => {
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
              {!currentConfig.enabled && requestType === 'status_change' && (
                <p className="text-destructive mt-2 text-xs">
                  No transitions available for status '{productStatus}'
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
                placeholder="Please explain why you need access to this product..."
                className="min-h-[100px] resize-none"
                disabled={submitting}
              />
              <div className="text-xs text-muted-foreground">
                Minimum 10 characters required.
              </div>
            </div>
          )}

          {requestType === 'status_change' && (
            <div className="space-y-4">
              {/* Current Status */}
              {productStatus && (
                <div className="rounded-lg border bg-muted/50 p-3">
                  <div className="flex items-center gap-2 mb-1">
                    <Label className="text-sm font-semibold">Current Status:</Label>
                    <span className="text-lg">{getStatusConfig(productStatus).icon}</span>
                    <span className="font-medium">{getStatusConfig(productStatus).label}</span>
                  </div>
                  <p className="text-xs text-muted-foreground">{getStatusConfig(productStatus).description}</p>
                </div>
              )}

              {/* Recommended Action */}
              {productStatus && getRecommendedAction(productStatus) && (
                <Alert>
                  <Info className="h-4 w-4" />
                  <AlertDescription className="text-sm">
                    <strong>Recommended:</strong> {getRecommendedAction(productStatus)}
                  </AlertDescription>
                </Alert>
              )}

              {/* Target Status Selection */}
              {productStatus && getAllowedTransitions(productStatus).length > 0 ? (
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
                      {getAllowedTransitions(productStatus).map((status) => {
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
                    <strong>Terminal State:</strong> No transitions available from {productStatus ? getStatusConfig(productStatus).label : 'current'} status.
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
                <Label className="text-xs font-semibold mb-2 block">ODPS v1.0.0 Lifecycle Flow:</Label>
                <div className="flex items-center gap-1 text-xs font-mono flex-wrap">
                  <span className={productStatus?.toLowerCase() === 'proposed' ? 'font-bold text-primary' : ''}>proposed</span>
                  <span>→</span>
                  <span className={productStatus?.toLowerCase() === 'draft' ? 'font-bold text-primary' : ''}>draft</span>
                  <span>→</span>
                  <span className={productStatus?.toLowerCase() === 'active' ? 'font-bold text-primary' : ''}>active</span>
                  <span>→</span>
                  <span className={productStatus?.toLowerCase() === 'deprecated' ? 'font-bold text-primary' : ''}>deprecated</span>
                  <span>→</span>
                  <span className={productStatus?.toLowerCase() === 'retired' ? 'font-bold text-primary' : ''}>retired</span>
                </div>
                <p className="text-xs text-muted-foreground mt-2">
                  Current status is highlighted. Emergency deprecation allowed from any status.
                </p>
              </div>
            </div>
          )}

          {requestType === 'genie_space' && (
            <div className="space-y-2">
              <Label htmlFor="genie-justification" className="text-sm font-medium">
                Justification (Optional)
              </Label>
              <Textarea
                id="genie-justification"
                value={justification}
                onChange={(e) => setJustification(e.target.value)}
                placeholder="Explain why this product needs a Genie Space..."
                className="min-h-[80px] resize-none"
                disabled={submitting}
              />
              <div className="text-xs text-muted-foreground">
                Optional but recommended for approval.
              </div>
            </div>
          )}

          {requestType === 'new_version' && (
            <div className="space-y-3">
              <div className="space-y-2">
                <Label htmlFor="new-version" className="text-sm font-medium">
                  New Version Number *
                </Label>
                <Input
                  id="new-version"
                  value={newVersion}
                  onChange={(e) => setNewVersion(e.target.value)}
                  placeholder={`e.g., ${currentVersion ? `${currentVersion.split('.')[0]}.${parseInt(currentVersion.split('.')[1] || '0') + 1}.0` : '1.1.0'}`}
                  disabled={submitting}
                />
                {currentVersion && (
                  <div className="text-xs text-muted-foreground">
                    Current version: {currentVersion}
                  </div>
                )}
              </div>
              <div className="space-y-2">
                <Label htmlFor="version-justification" className="text-sm font-medium">
                  Justification *
                </Label>
                <Textarea
                  id="version-justification"
                  value={justification}
                  onChange={(e) => setJustification(e.target.value)}
                  placeholder="Explain what changes or improvements warrant a new version..."
                  className="min-h-[100px] resize-none"
                  disabled={submitting}
                />
                <div className="text-xs text-muted-foreground">
                  Minimum 20 characters required. This will be reviewed by an admin.
                </div>
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

