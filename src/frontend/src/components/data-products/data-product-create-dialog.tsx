import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useToast } from '@/hooks/use-toast';
import { Loader2 } from 'lucide-react';
import { DataProduct, DataProductStatus } from '@/types/data-product';
import { useDomains } from '@/hooks/use-domains';
import { useTeams } from '@/hooks/use-teams';

/**
 * ODPS v1.0.0 Data Product Creation Dialog
 *
 * Lightweight dialog for creating the essential product information.
 * Complex nested entities (ports, team, support) are edited in the details view.
 */

const productTypes = ['source', 'source-aligned', 'aggregate', 'consumer-aligned', 'sink'] as const;

const dataProductCreateSchema = z.object({
  name: z.string().min(1, 'Product name is required'),
  version: z.string().min(1, 'Version is required').default('0.0.1'),
  status: z.string().min(1, 'Status is required'),
  productType: z.enum(productTypes).optional(),
  ownerTeamId: z.string().optional(),
  domain: z.string().optional(),
  tenant: z.string().optional(),
  purpose: z.string().optional(),
  limitations: z.string().optional(),
  usage: z.string().optional(),
});

type FormData = z.infer<typeof dataProductCreateSchema>;

interface DataProductCreateDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: (product: DataProduct) => void;
}

export default function DataProductCreateDialog({
  open,
  onOpenChange,
  onSuccess,
}: DataProductCreateDialogProps) {
  const { toast } = useToast();
  const { domains, loading: domainsLoading } = useDomains();
  const { teams, loading: teamsLoading } = useTeams();
  const [isSubmitting, setIsSubmitting] = useState(false);

  const form = useForm<FormData>({
    resolver: zodResolver(dataProductCreateSchema),
    defaultValues: {
      name: '',
      version: '0.0.1',
      status: DataProductStatus.DRAFT,
      productType: undefined,
      ownerTeamId: '',
      domain: '',
      tenant: '',
      purpose: '',
      limitations: '',
      usage: '',
    },
  });

  // Reset form when dialog opens
  useEffect(() => {
    if (open) {
      form.reset({
        name: '',
        version: '0.0.1',
        status: DataProductStatus.DRAFT,
        productType: undefined,
        ownerTeamId: '',
        domain: '',
        tenant: '',
        purpose: '',
        limitations: '',
        usage: '',
      });
    }
  }, [open, form]);

  const onSubmit = async (data: FormData) => {
    setIsSubmitting(true);

    try {
      // Get selected team name
      const selectedTeam = teams.find(t => t.id === data.ownerTeamId);

      // Construct ODPS v1.0.0 product
      const productData: Partial<DataProduct> = {
        apiVersion: 'v1.0.0',
        kind: 'DataProduct',
        name: data.name,
        version: data.version,
        status: data.status,
        domain: data.domain || undefined,
        tenant: data.tenant || undefined,
        owner_team_id: data.ownerTeamId || undefined,
        description: {
          purpose: data.purpose || undefined,
          limitations: data.limitations || undefined,
          usage: data.usage || undefined,
        },
        // Set team from selected team
        team: selectedTeam ? {
          name: selectedTeam.name,
          description: selectedTeam.description,
          members: [],
        } : undefined,
        // Initialize empty arrays for complex entities
        inputPorts: [],
        outputPorts: [],
        managementPorts: [],
        support: [],
        authoritativeDefinitions: [],
        customProperties: data.productType ? [{
          property: 'productType',
          value: data.productType,
          description: 'Type of data product in the value chain',
        }] : [],
      };

      const response = await fetch('/api/data-products', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(productData),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to create data product');
      }

      const createdProduct: DataProduct = await response.json();

      toast({
        title: 'Success',
        description: 'Data product created successfully. Add ports and team in the details view.',
      });

      onSuccess(createdProduct);
      onOpenChange(false);
    } catch (error: any) {
      console.error('Error creating data product:', error);
      toast({
        title: 'Error',
        description: error.message || 'Failed to create data product',
        variant: 'destructive',
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Create Data Product (ODPS v1.0.0)</DialogTitle>
          <DialogDescription>
            Create a new data product with essential information.
            You can add ports, team members, and support channels in the details view.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
          {/* Required Fields */}
          <div className="space-y-2">
            <Label htmlFor="name">
              Product Name <span className="text-red-500">*</span>
            </Label>
            <Input
              id="name"
              {...form.register('name')}
              placeholder="e.g., Customer Analytics Data"
            />
            {form.formState.errors.name && (
              <p className="text-sm text-red-500">{form.formState.errors.name.message}</p>
            )}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="version">
                Version <span className="text-red-500">*</span>
              </Label>
              <Input
                id="version"
                {...form.register('version')}
                placeholder="0.0.1"
              />
              {form.formState.errors.version && (
                <p className="text-sm text-red-500">{form.formState.errors.version.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="status">
                Status <span className="text-red-500">*</span>
              </Label>
              <Select
                value={form.watch('status')}
                onValueChange={(value) => form.setValue('status', value)}
              >
                <SelectTrigger id="status">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.values(DataProductStatus).map((status) => (
                    <SelectItem key={status} value={status}>
                      {status.charAt(0).toUpperCase() + status.slice(1)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {form.formState.errors.status && (
                <p className="text-sm text-red-500">{form.formState.errors.status.message}</p>
              )}
            </div>
          </div>

          {/* Product Type & Owner Team */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="productType">Product Type</Label>
              <Select
                value={form.watch('productType') || ''}
                onValueChange={(value) => form.setValue('productType', value as any)}
              >
                <SelectTrigger id="productType">
                  <SelectValue placeholder="Select product type..." />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">None</SelectItem>
                  {productTypes.map((type) => (
                    <SelectItem key={type} value={type}>
                      {type.split('-').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                Position in the data value chain
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="ownerTeamId">Owner Team</Label>
              <Select
                value={form.watch('ownerTeamId') || ''}
                onValueChange={(value) => form.setValue('ownerTeamId', value)}
                disabled={teamsLoading}
              >
                <SelectTrigger id="ownerTeamId">
                  <SelectValue placeholder="Select team..." />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">None</SelectItem>
                  {teamsLoading ? (
                    <SelectItem value="" disabled>
                      Loading teams...
                    </SelectItem>
                  ) : (
                    teams.map((team) => (
                      <SelectItem key={team.id} value={team.id}>
                        {team.name}
                      </SelectItem>
                    ))
                  )}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                Team responsible for this product
              </p>
            </div>
          </div>

          {/* Optional Fields */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="domain">Domain</Label>
              <Select
                value={form.watch('domain') || ''}
                onValueChange={(value) => form.setValue('domain', value)}
              >
                <SelectTrigger id="domain">
                  <SelectValue placeholder="Select domain..." />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">None</SelectItem>
                  {domainsLoading ? (
                    <SelectItem value="" disabled>
                      Loading...
                    </SelectItem>
                  ) : (
                    domains.map((domain) => (
                      <SelectItem key={domain.id} value={domain.id}>
                        {domain.name}
                      </SelectItem>
                    ))
                  )}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="tenant">Tenant/Organization</Label>
              <Input
                id="tenant"
                {...form.register('tenant')}
                placeholder="e.g., acme-corp"
              />
            </div>
          </div>

          {/* Structured Description */}
          <div className="space-y-4 border-t pt-4">
            <h3 className="font-medium">Description (ODPS Structured)</h3>

            <div className="space-y-2">
              <Label htmlFor="purpose">Purpose</Label>
              <Textarea
                id="purpose"
                {...form.register('purpose')}
                placeholder="What is the intended purpose of this data?"
                rows={2}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="limitations">Limitations</Label>
              <Textarea
                id="limitations"
                {...form.register('limitations')}
                placeholder="Technical, compliance, and legal limitations"
                rows={2}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="usage">Usage</Label>
              <Textarea
                id="usage"
                {...form.register('usage')}
                placeholder="Recommended usage of this data"
                rows={2}
              />
            </div>
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Create Product
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
