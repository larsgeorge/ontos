import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogClose,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { useApi } from '@/hooks/use-api';
import { useToast } from '@/hooks/use-toast';
import { Loader2 } from 'lucide-react';

interface ConfirmRoleRequestDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  requesterEmail: string;
  roleId: string;
  roleName: string;
  requesterMessage?: string; // Optional message from the requester
  onDecisionMade: () => void; // Callback after decision is submitted
}

const ConfirmRoleRequestDialog: React.FC<ConfirmRoleRequestDialogProps> = ({
  isOpen,
  onOpenChange,
  requesterEmail,
  roleId,
  roleName,
  requesterMessage,
  onDecisionMade,
}) => {
  const [decisionMessage, setDecisionMessage] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { post } = useApi();
  const { toast } = useToast();

  // Reset the decision message when dialog opens
  useEffect(() => {
    if (isOpen) {
      setDecisionMessage('');
    }
  }, [isOpen]);

  const handleSubmit = async (approved: boolean) => {
    setIsSubmitting(true);
    try {
        const payload = {
            requester_email: requesterEmail,
            role_id: roleId,
            approved: approved,
            message: decisionMessage,
        };

        // Send the request directly (backend expects HandleRoleRequest model)
        const response = await post('/api/settings/roles/handle-request', payload);
        if (response.error) {
             throw new Error(response.error);
        }

        toast({
            title: `Request ${approved ? 'Approved' : 'Denied'}`,
            description: `Decision for ${requesterEmail}'s request for role ${roleName} submitted.`,
        });
        onDecisionMade(); // Notify parent component
        onOpenChange(false); // Close the dialog
    } catch (err: any) {
        toast({
            title: 'Submission Failed',
            description: err.message || 'Could not submit the decision.',
            variant: 'destructive',
        });
    } finally {
        setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Handle Role Access Request</DialogTitle>
          <DialogDescription>
            Review the request from <strong>{requesterEmail}</strong> for the role <strong>{roleName}</strong>.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Display requester's message if available */}
          {requesterMessage && (
            <div className="space-y-2">
              <Label className="text-sm font-medium">Requester's Reason</Label>
              <div className="p-3 bg-muted/50 rounded-lg border text-sm">
                {requesterMessage}
              </div>
            </div>
          )}

          {/* Admin's response message */}
          <div className="space-y-2">
            <Label htmlFor="decision-message">Optional Message to Requester</Label>
            <Textarea
                id="decision-message"
                value={decisionMessage}
                onChange={(e) => setDecisionMessage(e.target.value)}
                placeholder="Provide a reason for approval or denial (optional)"
                className="resize-none"
                disabled={isSubmitting}
            />
          </div>
        </div>
        <DialogFooter className="gap-2 sm:justify-between">
            <Button
                variant="destructive"
                onClick={() => handleSubmit(false)}
                disabled={isSubmitting}
            >
                {isSubmitting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                Deny Request
            </Button>
           <div className="flex gap-2">
             <DialogClose asChild>
                <Button variant="outline" disabled={isSubmitting}>Cancel</Button>
            </DialogClose>
            <Button 
                onClick={() => handleSubmit(true)}
                disabled={isSubmitting}
            >
                {isSubmitting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                Approve Request
            </Button>
           </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default ConfirmRoleRequestDialog; 