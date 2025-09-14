import React, { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { useToast } from '@/hooks/use-toast';
import { useApi } from '@/hooks/use-api';

type Props = {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  requesterEmail: string;
  entityType: 'data_product' | 'data_contract';
  entityId: string;
  onDecisionMade: () => void;
};

export default function ConfirmAccessRequestDialog({ isOpen, onOpenChange, requesterEmail, entityType, entityId, onDecisionMade }: Props) {
  const { post } = useApi();
  const { toast } = useToast();
  const [message, setMessage] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const submitDecision = async (decision: 'approve' | 'deny' | 'clarify') => {
    setSubmitting(true);
    try {
      const body = {
        entity_type: entityType,
        entity_id: entityId,
        requester_email: requesterEmail,
        decision,
        message: message || undefined,
      };
      const res = await post('/api/access-requests/handle', body);
      if (res.error) throw new Error(res.error);
      toast({ title: 'Submitted', description: `Decision "${decision}" sent.` });
      onDecisionMade();
      onOpenChange(false);
    } catch (e: any) {
      toast({ title: 'Failed', description: e.message || 'Could not submit decision', variant: 'destructive' });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Handle Access Request</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <div className="text-sm text-muted-foreground">
            Requester: <span className="font-medium">{requesterEmail}</span>
          </div>
          <div className="text-sm text-muted-foreground">
            Entity: <span className="font-mono">{entityType} / {entityId}</span>
          </div>
          <div className="space-y-2">
            <Label htmlFor="decision-message">Message (optional)</Label>
            <Textarea id="decision-message" value={message} onChange={(e) => setMessage(e.target.value)} placeholder="Add notes for the requester..." />
          </div>
        </div>
        <DialogFooter className="gap-2">
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={submitting}>Close</Button>
          <Button variant="secondary" onClick={() => submitDecision('clarify')} disabled={submitting}>Ask Clarification</Button>
          <Button variant="destructive" onClick={() => submitDecision('deny')} disabled={submitting}>Deny</Button>
          <Button onClick={() => submitDecision('approve')} disabled={submitting}>Approve</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}


