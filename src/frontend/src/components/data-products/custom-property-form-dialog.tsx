import { useEffect, useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { useToast } from '@/hooks/use-toast';
import type { CustomProperty } from '@/types/data-product';

type CustomPropertyFormProps = {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (property: CustomProperty) => Promise<void>;
  initial?: CustomProperty;
};

export default function CustomPropertyFormDialog({ isOpen, onOpenChange, onSubmit, initial }: CustomPropertyFormProps) {
  const { toast } = useToast();
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [property, setProperty] = useState('');
  const [value, setValue] = useState('');
  const [description, setDescription] = useState('');

  useEffect(() => {
    if (isOpen && initial) {
      setProperty(initial.property || '');
      setValue(typeof initial.value === 'string' ? initial.value : JSON.stringify(initial.value));
      setDescription(initial.description || '');
    } else if (isOpen && !initial) {
      setProperty('');
      setValue('');
      setDescription('');
    }
  }, [isOpen, initial]);

  const handleSubmit = async () => {
    if (!property.trim()) {
      toast({ title: 'Validation Error', description: 'Property name is required', variant: 'destructive' });
      return;
    }

    if (!value.trim()) {
      toast({ title: 'Validation Error', description: 'Property value is required', variant: 'destructive' });
      return;
    }

    // Validate camelCase naming
    if (!/^[a-z][a-zA-Z0-9]*$/.test(property.trim())) {
      toast({
        title: 'Validation Error',
        description: 'Property name must be in camelCase (start with lowercase letter)',
        variant: 'destructive'
      });
      return;
    }

    setIsSubmitting(true);
    try {
      // Try to parse value as JSON, otherwise keep as string
      let parsedValue: any = value.trim();
      try {
        parsedValue = JSON.parse(value.trim());
      } catch {
        // Keep as string if not valid JSON
      }

      const customProperty: CustomProperty = {
        property: property.trim(),
        value: parsedValue,
        description: description.trim() || undefined,
      };

      await onSubmit(customProperty);
      onOpenChange(false);
      toast({
        title: 'Success',
        description: initial ? 'Custom property updated' : 'Custom property added',
      });
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error?.message || 'Failed to save custom property',
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
          <DialogTitle>{initial ? 'Edit Custom Property' : 'Add Custom Property'}</DialogTitle>
          <DialogDescription>
            Add custom metadata to extend the ODPS v1.0.0 data product schema.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="property">
              Property Name <span className="text-destructive">*</span>
            </Label>
            <Input
              id="property"
              value={property}
              onChange={(e) => setProperty(e.target.value)}
              placeholder="e.g., internalId, deploymentRegion"
              autoFocus
            />
            <p className="text-xs text-muted-foreground">
              Must be in camelCase (ODPS requirement)
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="value">
              Property Value <span className="text-destructive">*</span>
            </Label>
            <Textarea
              id="value"
              value={value}
              onChange={(e) => setValue(e.target.value)}
              placeholder='Simple text or JSON: {"key": "value"}'
              rows={3}
            />
            <p className="text-xs text-muted-foreground">
              Can be any type: string, number, boolean, object, or array. JSON values will be parsed automatically.
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Explain the purpose of this custom property"
              rows={2}
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={isSubmitting}>
            {isSubmitting ? 'Saving...' : initial ? 'Save Changes' : 'Add Property'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
