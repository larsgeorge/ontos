import { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { useToast } from '@/hooks/use-toast';
import { useApi } from '@/hooks/use-api';
import { Database } from 'lucide-react';

type Props = {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  contractId: string;
  contractName?: string;
  requesterEmail: string;
  catalog?: string;
  schema?: string;
  onDecisionMade: () => void;
};

export default function HandleDeployRequestDialog({
  isOpen,
  onOpenChange,
  contractId,
  contractName,
  requesterEmail,
  catalog,
  schema,
  onDecisionMade
}: Props) {
  const { post } = useApi();
  const { toast } = useToast();
  const [message, setMessage] = useState('');
  const [executeDeployment, setExecuteDeployment] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const submitDecision = async (decision: 'approve' | 'deny') => {
    setSubmitting(true);
    try {
      const body = {
        decision,
        message: message || undefined,
        execute_deployment: decision === 'approve' ? executeDeployment : false,
      };
      const res = await post(`/api/data-contracts/${contractId}/handle-deploy`, body);
      if (res.error) throw new Error(res.error);
      
      let description = `Deployment request has been ${decision === 'approve' ? 'approved' : 'denied'}.`;
      if (decision === 'approve' && executeDeployment) {
        description += ' Deployment has been initiated.';
      }
      
      toast({
        title: decision === 'approve' ? 'Deploy Approved' : 'Deploy Denied',
        description
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
            <Database className="h-5 w-5" />
            Handle Deployment Request
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
            {(catalog || schema) && (
              <div className="text-sm text-muted-foreground mt-2">
                <span className="font-medium">Target:</span>{' '}
                {catalog && schema ? `${catalog}.${schema}` : catalog || schema || 'Not specified'}
              </div>
            )}
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="deploy-message">Response Message (optional)</Label>
            <Textarea
              id="deploy-message"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Add notes about your decision..."
              className="min-h-[100px]"
            />
            <p className="text-xs text-muted-foreground">
              This message will be sent to the requester along with your decision.
            </p>
          </div>

          <div className="flex items-start space-x-3 p-3 rounded-lg border bg-blue-50 dark:bg-blue-950/20 border-blue-200 dark:border-blue-800">
            <Checkbox
              id="execute-deploy"
              checked={executeDeployment}
              onCheckedChange={(checked) => setExecuteDeployment(checked as boolean)}
              disabled={submitting}
            />
            <div className="flex-1">
              <label htmlFor="execute-deploy" className="text-sm font-medium cursor-pointer">
                Execute deployment immediately upon approval
              </label>
              <p className="text-xs text-muted-foreground mt-1">
                If checked, the deployment will be triggered automatically when you approve this request.
              </p>
            </div>
          </div>

          <div className="p-3 bg-amber-50 dark:bg-amber-950/20 rounded-lg border border-amber-200 dark:border-amber-800">
            <p className="text-sm text-amber-900 dark:text-amber-100">
              <strong>Warning:</strong> Deployment will create physical assets in Unity Catalog. Ensure you have reviewed the contract schema and configuration.
            </p>
          </div>
        </div>
        <DialogFooter className="gap-2">
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={submitting}>
            Cancel
          </Button>
          <Button variant="destructive" onClick={() => submitDecision('deny')} disabled={submitting}>
            Deny
          </Button>
          <Button onClick={() => submitDecision('approve')} disabled={submitting}>
            {executeDeployment ? 'Approve & Deploy' : 'Approve'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

