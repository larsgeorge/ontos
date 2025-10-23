import { useEffect, useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { useToast } from '@/hooks/use-toast';
import type { AuthoritativeDefinition } from '@/types/data-product';

type AuthoritativeDefinitionFormProps = {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (definition: AuthoritativeDefinition) => Promise<void>;
  initial?: AuthoritativeDefinition;
};

const DEFINITION_TYPES = [
  'businessDefinition',
  'transformationImplementation',
  'videoTutorial',
  'tutorial',
  'implementation',
];

export default function AuthoritativeDefinitionFormDialog({
  isOpen,
  onOpenChange,
  onSubmit,
  initial,
}: AuthoritativeDefinitionFormProps) {
  const { toast } = useToast();
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [type, setType] = useState('businessDefinition');
  const [url, setUrl] = useState('');
  const [description, setDescription] = useState('');

  useEffect(() => {
    if (isOpen && initial) {
      setType(initial.type || 'businessDefinition');
      setUrl(initial.url || '');
      setDescription(initial.description || '');
    } else if (isOpen && !initial) {
      setType('businessDefinition');
      setUrl('');
      setDescription('');
    }
  }, [isOpen, initial]);

  const handleSubmit = async () => {
    if (!type.trim()) {
      toast({ title: 'Validation Error', description: 'Type is required', variant: 'destructive' });
      return;
    }

    if (!url.trim()) {
      toast({ title: 'Validation Error', description: 'URL is required', variant: 'destructive' });
      return;
    }

    // URL validation
    try {
      new URL(url.trim());
    } catch {
      toast({ title: 'Validation Error', description: 'Please enter a valid URL', variant: 'destructive' });
      return;
    }

    setIsSubmitting(true);
    try {
      const definition: AuthoritativeDefinition = {
        type: type.trim(),
        url: url.trim(),
        description: description.trim() || undefined,
      };

      await onSubmit(definition);
      onOpenChange(false);
      toast({
        title: 'Success',
        description: initial ? 'Authoritative definition updated' : 'Authoritative definition added',
      });
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error?.message || 'Failed to save authoritative definition',
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
          <DialogTitle>{initial ? 'Edit Authoritative Definition' : 'Add Authoritative Definition'}</DialogTitle>
          <DialogDescription>
            Link to authoritative sources like business definitions, implementations, or tutorials (ODPS v1.0.0).
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="type">
              Type <span className="text-destructive">*</span>
            </Label>
            <Select value={type} onValueChange={setType}>
              <SelectTrigger id="type">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {DEFINITION_TYPES.map((t) => (
                  <SelectItem key={t} value={t}>
                    {t}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              Type of authoritative source
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="url">
              URL <span className="text-destructive">*</span>
            </Label>
            <Input
              id="url"
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://docs.example.com/definitions/customer"
              autoFocus
            />
            <p className="text-xs text-muted-foreground">
              Full URL to the authoritative source
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe what information this source provides"
              rows={3}
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={isSubmitting}>
            {isSubmitting ? 'Saving...' : initial ? 'Save Changes' : 'Add Definition'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
