import { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { useToast } from '@/hooks/use-toast';
import { useApi } from '@/hooks/use-api';
import { FileText } from 'lucide-react';

type Props = {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  contractId: string;
  contractName?: string;
  requesterEmail: string;
  onDecisionMade: () => void;
};

export default function HandleStewardReviewDialog({
  isOpen,
  onOpenChange,
  contractId,
  contractName,
  requesterEmail,
  onDecisionMade
}: Props) {
  const { post } = useApi();
  const { toast } = useToast();
  const [message, setMessage] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const submitDecision = async (decision: 'approve' | 'reject' | 'clarify') => {
    setSubmitting(true);
    try {
      const body = {
        decision,
        message: message || undefined,
      };
      const res = await post(`/api/data-contracts/${contractId}/handle-review`, body);
      if (res.error) throw new Error(res.error);
      
      const decisionLabels = {
        approve: 'approved',
        reject: 'rejected',
        clarify: 'clarification requested'
      };
      
      toast({
        title: 'Review Decision Submitted',
        description: `Contract review ${decisionLabels[decision]}.`
      });
      onDecisionMade();
      onOpenChange(false);
    } catch (e: any) {
      toast({
        title: 'Failed',
        description: e.message || 'Could not submit decision',
        variant: 'destructive'
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Handle Contract Review
          </DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div className="p-3 bg-muted/50 rounded-lg border space-y-2">
            <div className="text-sm text-muted-foreground">
              <span className="font-medium">Requester:</span> {requesterEmail}
            </div>
            <div className="text-sm text-muted-foreground">
              <span className="font-medium">Contract ID:</span> <span className="font-mono">{contractId}</span>
            </div>
            {contractName && (
              <div className="text-sm font-medium">{contractName}</div>
            )}
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="review-message">Feedback Message (optional)</Label>
            <Textarea
              id="review-message"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Provide feedback for the requester..."
              className="min-h-[100px]"
            />
            <p className="text-xs text-muted-foreground">
              This message will be sent to the requester along with your decision.
            </p>
          </div>
        </div>
        <DialogFooter className="gap-2">
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={submitting}>
            Cancel
          </Button>
          <Button variant="secondary" onClick={() => submitDecision('clarify')} disabled={submitting}>
            Request Clarification
          </Button>
          <Button variant="destructive" onClick={() => submitDecision('reject')} disabled={submitting}>
            Reject
          </Button>
          <Button onClick={() => submitDecision('approve')} disabled={submitting}>
            Approve
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

