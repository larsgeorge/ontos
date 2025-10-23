import { useEffect, useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { useToast } from '@/hooks/use-toast';
import type { OutputPort } from '@/types/data-product';

type OutputPortFormProps = {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (port: OutputPort) => Promise<void>;
  initial?: OutputPort;
};

export default function OutputPortFormDialog({ isOpen, onOpenChange, onSubmit, initial }: OutputPortFormProps) {
  const { toast } = useToast();
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [name, setName] = useState('');
  const [version, setVersion] = useState('1.0.0');
  const [description, setDescription] = useState('');
  const [type, setType] = useState('');
  const [contractId, setContractId] = useState('');
  const [assetType, setAssetType] = useState('');
  const [assetIdentifier, setAssetIdentifier] = useState('');
  const [status, setStatus] = useState('');
  const [containsPii, setContainsPii] = useState(false);
  const [autoApprove, setAutoApprove] = useState(false);

  useEffect(() => {
    if (isOpen && initial) {
      setName(initial.name || '');
      setVersion(initial.version || '1.0.0');
      setDescription(initial.description || '');
      setType(initial.type || '');
      setContractId(initial.contractId || '');
      setAssetType(initial.assetType || '');
      setAssetIdentifier(initial.assetIdentifier || '');
      setStatus(initial.status || '');
      setContainsPii(initial.containsPii || false);
      setAutoApprove(initial.autoApprove || false);
    } else if (isOpen && !initial) {
      setName('');
      setVersion('1.0.0');
      setDescription('');
      setType('');
      setContractId('');
      setAssetType('');
      setAssetIdentifier('');
      setStatus('');
      setContainsPii(false);
      setAutoApprove(false);
    }
  }, [isOpen, initial]);

  const handleSubmit = async () => {
    if (!name.trim()) {
      toast({ title: 'Validation Error', description: 'Port name is required', variant: 'destructive' });
      return;
    }

    if (!version.trim()) {
      toast({ title: 'Validation Error', description: 'Port version is required', variant: 'destructive' });
      return;
    }

    setIsSubmitting(true);
    try {
      const port: OutputPort = {
        name: name.trim(),
        version: version.trim(),
        description: description.trim() || undefined,
        type: type.trim() || undefined,
        contractId: contractId.trim() || undefined,
        assetType: assetType.trim() || undefined,
        assetIdentifier: assetIdentifier.trim() || undefined,
        status: status.trim() || undefined,
        containsPii: containsPii,
        autoApprove: autoApprove,
      };

      await onSubmit(port);
      onOpenChange(false);
      toast({
        title: 'Success',
        description: initial ? 'Output port updated' : 'Output port added',
      });
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error?.message || 'Failed to save output port',
        variant: 'destructive',
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{initial ? 'Edit Output Port' : 'Add Output Port'}</DialogTitle>
          <DialogDescription>
            Define an output data endpoint for this data product (ODPS v1.0.0).
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Required Fields */}
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">
                Port Name <span className="text-destructive">*</span>
              </Label>
              <Input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g., customer-analytics-output"
                autoFocus
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="version">
                Version <span className="text-destructive">*</span>
              </Label>
              <Input
                id="version"
                value={version}
                onChange={(e) => setVersion(e.target.value)}
                placeholder="1.0.0"
              />
              <p className="text-xs text-muted-foreground">
                Version of this output port (e.g., 1.0.0, 2.1.3)
              </p>
            </div>
          </div>

          {/* Optional ODPS Fields */}
          <div className="border-t pt-4">
            <h4 className="text-sm font-medium mb-3">Optional ODPS Fields</h4>

            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Describe what this output port provides"
                  rows={2}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="type">Port Type</Label>
                <Input
                  id="type"
                  value={type}
                  onChange={(e) => setType(e.target.value)}
                  placeholder="e.g., table, api, stream"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="contractId">Contract ID</Label>
                <Input
                  id="contractId"
                  value={contractId}
                  onChange={(e) => setContractId(e.target.value)}
                  placeholder="e.g., customer-analytics-contract-v1"
                />
                <p className="text-xs text-muted-foreground">
                  Optional link to a data contract ID
                </p>
              </div>
            </div>
          </div>

          {/* Databricks Extensions */}
          <div className="border-t pt-4">
            <h4 className="text-sm font-medium mb-3">Databricks Extensions</h4>

            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="assetType">Asset Type</Label>
                <Input
                  id="assetType"
                  value={assetType}
                  onChange={(e) => setAssetType(e.target.value)}
                  placeholder="e.g., table, view, share"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="assetIdentifier">Asset Identifier</Label>
                <Input
                  id="assetIdentifier"
                  value={assetIdentifier}
                  onChange={(e) => setAssetIdentifier(e.target.value)}
                  placeholder="e.g., catalog.schema.table"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="status">Status</Label>
                <Input
                  id="status"
                  value={status}
                  onChange={(e) => setStatus(e.target.value)}
                  placeholder="e.g., active, draft"
                />
              </div>

              <div className="flex items-center justify-between space-y-0 rounded-lg border p-4">
                <div className="space-y-0.5">
                  <Label htmlFor="containsPii" className="text-base">
                    Contains PII
                  </Label>
                  <p className="text-sm text-muted-foreground">
                    Does this output contain personally identifiable information?
                  </p>
                </div>
                <Switch
                  id="containsPii"
                  checked={containsPii}
                  onCheckedChange={setContainsPii}
                />
              </div>

              <div className="flex items-center justify-between space-y-0 rounded-lg border p-4">
                <div className="space-y-0.5">
                  <Label htmlFor="autoApprove" className="text-base">
                    Auto Approve
                  </Label>
                  <p className="text-sm text-muted-foreground">
                    Automatically approve access requests for this output?
                  </p>
                </div>
                <Switch
                  id="autoApprove"
                  checked={autoApprove}
                  onCheckedChange={setAutoApprove}
                />
              </div>
            </div>
          </div>

          {/* Info about SBOM and Input Contracts */}
          <div className="rounded-lg bg-muted/50 p-4">
            <p className="text-sm text-muted-foreground">
              <strong>Note:</strong> SBOM (Software Bill of Materials) and Input Contracts can be managed after creating the port.
              These complex nested entities require separate dialogs.
            </p>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={isSubmitting}>
            {isSubmitting ? 'Saving...' : initial ? 'Save Changes' : 'Add Port'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
