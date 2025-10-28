import { useEffect, useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useToast } from '@/hooks/use-toast';
import { Badge } from '@/components/ui/badge';
import { Loader2, Plus } from 'lucide-react';
import type { OutputPort, DataProduct } from '@/types/data-product';
import type { DataContractListItem } from '@/types/data-contract';
import CreateContractInlineDialog from '@/components/data-contracts/create-contract-inline-dialog';

type LinkContractToPortDialogProps = {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  productId: string;
  portIndex: number;
  currentPort?: OutputPort;
  onSuccess: () => void;
};

export default function LinkContractToPortDialog({
  isOpen,
  onOpenChange,
  productId,
  portIndex,
  currentPort,
  onSuccess
}: LinkContractToPortDialogProps) {
  const { toast } = useToast();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoadingContracts, setIsLoadingContracts] = useState(false);
  const [contracts, setContracts] = useState<DataContractListItem[]>([]);
  const [selectedContractId, setSelectedContractId] = useState('');
  const [isCreateContractOpen, setIsCreateContractOpen] = useState(false);
  const [product, setProduct] = useState<DataProduct | null>(null);

  const activeStatuses = ['active', 'approved', 'certified'];

  useEffect(() => {
    if (isOpen) {
      fetchContracts();
      fetchProduct();
      setSelectedContractId('');
    }
  }, [isOpen]);

  const fetchProduct = async () => {
    try {
      const response = await fetch(`/api/data-products/${productId}`);
      if (response.ok) {
        const data = await response.json();
        setProduct(data);
      }
    } catch (e) {
      console.warn('Failed to fetch product:', e);
    }
  };

  const fetchContracts = async () => {
    setIsLoadingContracts(true);
    try {
      const response = await fetch('/api/data-contracts');
      if (!response.ok) throw new Error('Failed to fetch contracts');
      
      const data: DataContractListItem[] = await response.json();
      
      // Filter to only show contracts with appropriate status
      const filteredContracts = data.filter(c => 
        activeStatuses.includes(c.status?.toLowerCase() || '')
      );
      
      setContracts(filteredContracts);
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error?.message || 'Failed to load contracts',
        variant: 'destructive'
      });
    } finally {
      setIsLoadingContracts(false);
    }
  };

  const handleSubmit = async () => {
    if (!selectedContractId) {
      toast({
        title: 'Validation Error',
        description: 'Please select a contract',
        variant: 'destructive'
      });
      return;
    }

    setIsSubmitting(true);
    try {
      // Fetch current product details
      const productResponse = await fetch(`/api/data-products/${productId}`);
      if (!productResponse.ok) throw new Error('Failed to fetch product');
      const productData: DataProduct = await productResponse.json();

      // Update the specific output port
      const updatedPorts = [...(productData.outputPorts || [])];
      if (updatedPorts[portIndex]) {
        updatedPorts[portIndex] = {
          ...updatedPorts[portIndex],
          contractId: selectedContractId
        };
      }

      // Normalize tags to string array (backend expects strings, not tag objects)
      const normalizedTags = productData.tags?.map((tag: any) => 
        typeof tag === 'string' ? tag : tag.tag_id || tag.name || tag
      );

      // Update product
      const updateResponse = await fetch(`/api/data-products/${productId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...productData,
          tags: normalizedTags,
          outputPorts: updatedPorts
        })
      });

      if (!updateResponse.ok) throw new Error('Failed to link contract');

      toast({
        title: 'Contract Linked',
        description: 'Contract successfully linked to output port'
      });

      onSuccess();
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error?.message || 'Failed to link contract',
        variant: 'destructive'
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleContractCreated = (contractId: string) => {
    setSelectedContractId(contractId);
    setIsCreateContractOpen(false);
    fetchContracts(); // Refresh contract list
  };

  return (
    <>
      <Dialog open={isOpen} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Link Contract to Output Port</DialogTitle>
            <DialogDescription>
              Select an existing contract or create a new one to link to <strong>{currentPort?.name || 'this output port'}</strong>
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {currentPort && (
              <div className="rounded-lg bg-muted p-4 space-y-2">
                <Label className="text-sm font-medium">Output Port</Label>
                <div className="flex items-center gap-2">
                  <span className="font-medium">{currentPort.name}</span>
                  <Badge variant="outline">v{currentPort.version}</Badge>
                </div>
                {currentPort.description && (
                  <p className="text-sm text-muted-foreground">{currentPort.description}</p>
                )}
              </div>
            )}

            <div className="space-y-2">
              <Label htmlFor="contract">
                Select Contract <span className="text-destructive">*</span>
              </Label>
              {isLoadingContracts ? (
                <div className="flex items-center justify-center p-4">
                  <Loader2 className="h-6 w-6 animate-spin" />
                </div>
              ) : (
                <Select value={selectedContractId} onValueChange={setSelectedContractId}>
                  <SelectTrigger id="contract">
                    <SelectValue placeholder="Choose a contract..." />
                  </SelectTrigger>
                  <SelectContent>
                    {contracts.length === 0 ? (
                      <div className="p-2 text-sm text-muted-foreground text-center">
                        No active/approved contracts available
                      </div>
                    ) : (
                      contracts.map((contract) => (
                        <SelectItem key={contract.id} value={contract.id}>
                          <div className="flex items-center gap-2">
                            <span>{contract.name}</span>
                            <Badge variant="secondary" className="text-xs">v{contract.version}</Badge>
                            <Badge variant="outline" className="text-xs">{contract.status}</Badge>
                          </div>
                        </SelectItem>
                      ))
                    )}
                  </SelectContent>
                </Select>
              )}
              <p className="text-xs text-muted-foreground">
                Only showing contracts with 'active', 'approved', or 'certified' status
              </p>
            </div>

            <div className="flex items-center gap-2">
              <div className="flex-1 border-t" />
              <span className="text-sm text-muted-foreground">OR</span>
              <div className="flex-1 border-t" />
            </div>

            <Button
              type="button"
              variant="outline"
              className="w-full"
              onClick={() => setIsCreateContractOpen(true)}
            >
              <Plus className="mr-2 h-4 w-4" />
              Create New Contract
            </Button>
          </div>

          <DialogFooter>
            <Button 
              variant="outline" 
              onClick={() => onOpenChange(false)} 
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button 
              onClick={handleSubmit} 
              disabled={isSubmitting || !selectedContractId}
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Linking...
                </>
              ) : (
                'Link Contract'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <CreateContractInlineDialog
        isOpen={isCreateContractOpen}
        onOpenChange={setIsCreateContractOpen}
        onSuccess={handleContractCreated}
        prefillData={{
          domain: product?.domain,
          domainId: product?.domain,
          tenant: product?.tenant,
          owner_team_id: product?.owner_team_id
        }}
      />
    </>
  );
}

