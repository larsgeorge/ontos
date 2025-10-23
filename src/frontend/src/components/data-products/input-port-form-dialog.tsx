import { useEffect, useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useToast } from '@/hooks/use-toast';
import type { InputPort } from '@/types/data-product';

type InputPortFormProps = {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (port: InputPort) => Promise<void>;
  initial?: InputPort;
};

export default function InputPortFormDialog({ isOpen, onOpenChange, onSubmit, initial }: InputPortFormProps) {
  const { toast } = useToast();
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [name, setName] = useState('');
  const [version, setVersion] = useState('1.0.0');
  const [contractId, setContractId] = useState('');
  const [assetType, setAssetType] = useState('');
  const [assetIdentifier, setAssetIdentifier] = useState('');

  useEffect(() => {
    if (isOpen && initial) {
      setName(initial.name || '');
      setVersion(initial.version || '1.0.0');
      setContractId(initial.contractId || '');
      setAssetType(initial.assetType || '');
      setAssetIdentifier(initial.assetIdentifier || '');
    } else if (isOpen && !initial) {
      setName('');
      setVersion('1.0.0');
      setContractId('');
      setAssetType('');
      setAssetIdentifier('');
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

    if (!contractId.trim()) {
      toast({
        title: 'Validation Error',
        description: 'Contract ID is required (ODPS v1.0.0 requirement)',
        variant: 'destructive'
      });
      return;
    }

    setIsSubmitting(true);
    try {
      const port: InputPort = {
        name: name.trim(),
        version: version.trim(),
        contractId: contractId.trim(),
        assetType: assetType.trim() || undefined,
        assetIdentifier: assetIdentifier.trim() || undefined,
      };

      await onSubmit(port);
      onOpenChange(false);
      toast({
        title: 'Success',
        description: initial ? 'Input port updated' : 'Input port added',
      });
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error?.message || 'Failed to save input port',
        variant: 'destructive',
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{initial ? 'Edit Input Port' : 'Add Input Port'}</DialogTitle>
          <DialogDescription>
            Define an input data dependency for this data product (ODPS v1.0.0).
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="name">
              Port Name <span className="text-destructive">*</span>
            </Label>
            <Input
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., customer-data-input"
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
              Version of this input port (e.g., 1.0.0, 2.1.3)
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="contractId">
              Contract ID <span className="text-destructive">*</span>
            </Label>
            <Input
              id="contractId"
              value={contractId}
              onChange={(e) => setContractId(e.target.value)}
              placeholder="e.g., customer-data-contract-v1"
            />
            <p className="text-xs text-muted-foreground">
              Reference to the data contract ID (REQUIRED in ODPS v1.0.0)
            </p>
          </div>

          <div className="border-t pt-4">
            <h4 className="text-sm font-medium mb-3">Databricks Extensions (Optional)</h4>

            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="assetType">Asset Type</Label>
                <Input
                  id="assetType"
                  value={assetType}
                  onChange={(e) => setAssetType(e.target.value)}
                  placeholder="e.g., table, notebook, job"
                />
                <p className="text-xs text-muted-foreground">
                  Type of Databricks asset
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="assetIdentifier">Asset Identifier</Label>
                <Input
                  id="assetIdentifier"
                  value={assetIdentifier}
                  onChange={(e) => setAssetIdentifier(e.target.value)}
                  placeholder="e.g., catalog.schema.table, /path/to/notebook"
                />
                <p className="text-xs text-muted-foreground">
                  Unique identifier for the Databricks asset
                </p>
              </div>
            </div>
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
