import { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useToast } from '@/hooks/use-toast';
import { useApi } from '@/hooks/use-api';
import { useNotificationsStore } from '@/stores/notifications-store';
import { Loader2, Shield, AlertCircle } from 'lucide-react';

interface RequestRoleAccessDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  roleId: string;
  roleName: string;
  roleDescription?: string;
}

export default function RequestRoleAccessDialog({
  isOpen,
  onOpenChange,
  roleId,
  roleName,
  roleDescription
}: RequestRoleAccessDialogProps) {
  const { post } = useApi();
  const { toast } = useToast();
  const refreshNotifications = useNotificationsStore((state) => state.refreshNotifications);
  const [reason, setReason] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    // Validate reason
    if (!reason.trim()) {
      setError('Please provide a reason for requesting this role');
      return;
    }

    if (reason.trim().length < 10) {
      setError('Please provide a more detailed reason (at least 10 characters)');
      return;
    }

    setError(null);
    setSubmitting(true);

    try {
      const response = await post(`/api/user/request-role/${roleId}`, {
        message: reason.trim(),
      });

      if (response.error) {
        throw new Error(response.error);
      }

      toast({
        title: 'Request Submitted',
        description: `Your request for the role "${roleName}" has been submitted and you will be notified of the decision.`
      });

      // Refresh notifications to show any new ones
      refreshNotifications();

      // Reset form and close dialog
      setReason('');
      onOpenChange(false);

    } catch (e: any) {
      setError(e.message || 'Failed to submit role access request');
      toast({
        title: 'Error',
        description: e.message || 'Failed to submit role access request',
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

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-primary" />
            Request Role Access
          </DialogTitle>
          <DialogDescription>
            Submit a request for access to this application role.
            Please provide a detailed reason for your request.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Role Information */}
          <div className="p-3 bg-muted/50 rounded-lg border">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <span className="font-medium">Role:</span>
              <span className="font-semibold text-foreground">{roleName}</span>
            </div>
            {roleDescription && (
              <div className="text-sm text-muted-foreground mt-1">{roleDescription}</div>
            )}
          </div>

          {/* Reason Field */}
          <div className="space-y-2">
            <Label htmlFor="role-access-reason" className="text-sm font-medium">
              Reason for Role Access Request *
            </Label>
            <Textarea
              id="role-access-reason"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Please explain why you need this role. Include details about your responsibilities, project requirements, or business justification..."
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
