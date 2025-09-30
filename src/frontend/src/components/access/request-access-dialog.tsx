import { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useToast } from '@/hooks/use-toast';
import { useApi } from '@/hooks/use-api';
import { useNotificationsStore } from '@/stores/notifications-store';
import { Loader2, FileText, Package, AlertCircle } from 'lucide-react';

type EntityType = 'data_product' | 'data_contract';

interface RequestAccessDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  entityType: EntityType;
  entityId: string;
  entityName?: string;
}

export default function RequestAccessDialog({
  isOpen,
  onOpenChange,
  entityType,
  entityId,
  entityName
}: RequestAccessDialogProps) {
  const { post } = useApi();
  const { toast } = useToast();
  const refreshNotifications = useNotificationsStore((state) => state.refreshNotifications);
  const [reason, setReason] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    // Validate reason
    if (!reason.trim()) {
      setError('Please provide a reason for requesting access');
      return;
    }

    if (reason.trim().length < 10) {
      setError('Please provide a more detailed reason (at least 10 characters)');
      return;
    }

    setError(null);
    setSubmitting(true);

    try {
      const response = await post('/api/access-requests', {
        entity_type: entityType,
        entity_ids: [entityId],
        message: reason.trim(),
      });

      if (response.error) {
        throw new Error(response.error);
      }

      toast({
        title: 'Request Submitted',
        description: 'Your access request has been submitted and you will be notified of the decision.'
      });

      // Refresh notifications to show any new ones
      refreshNotifications();

      // Reset form and close dialog
      setReason('');
      onOpenChange(false);

    } catch (e: any) {
      setError(e.message || 'Failed to submit access request');
      toast({
        title: 'Error',
        description: e.message || 'Failed to submit access request',
        variant: 'destructive'
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleCancel = () => {
    setReason('');
    setError(null);
    onOpenChange(false);
  };

  const getEntityIcon = () => {
    return entityType === 'data_product' ?
      <Package className="h-5 w-5 text-primary" /> :
      <FileText className="h-5 w-5 text-primary" />;
  };

  const getEntityTypeLabel = () => {
    return entityType === 'data_product' ? 'Data Product' : 'Data Contract';
  };

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {getEntityIcon()}
            Request Access
          </DialogTitle>
          <DialogDescription>
            Submit a request for access to this {getEntityTypeLabel().toLowerCase()}.
            Please provide a detailed reason for your request.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Entity Information */}
          <div className="p-3 bg-muted/50 rounded-lg border">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <span className="font-medium">{getEntityTypeLabel()}:</span>
              <span className="font-mono">{entityId}</span>
            </div>
            {entityName && (
              <div className="text-sm font-medium mt-1">{entityName}</div>
            )}
          </div>

          {/* Reason Field */}
          <div className="space-y-2">
            <Label htmlFor="access-reason" className="text-sm font-medium">
              Reason for Access Request *
            </Label>
            <Textarea
              id="access-reason"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Please explain why you need access to this resource. Include details about your intended use case, project requirements, or business justification..."
              className="min-h-[100px] resize-none"
              disabled={submitting}
            />
            <div className="text-xs text-muted-foreground">
              Minimum 10 characters required. This information will be shared with administrators.
            </div>
          </div>

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
            disabled={submitting || !reason.trim()}
          >
            {submitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {submitting ? 'Sending Request...' : 'Send Request'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}