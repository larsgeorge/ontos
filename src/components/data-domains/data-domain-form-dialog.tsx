import React from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { Loader2 } from 'lucide-react';

import { Button } from "@/components/ui/button";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger
} from "@/components/ui/dialog";
import {
  Form, FormControl, FormField, FormItem, FormLabel, FormMessage
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { DataDomain, DataDomainCreate, DataDomainUpdate } from '@/types/data-domain';
import { useApi } from '@/hooks/use-api'; // Import useApi
import { useToast } from '@/hooks/use-toast'; // Import useToast

interface DataDomainFormDialogProps {
  domain?: DataDomain | null; // Existing domain for editing
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmitSuccess: (domain: DataDomain) => void; // Callback on successful save
  trigger?: React.ReactNode; // Optional trigger element
}

const formSchema = z.object({
  name: z.string().min(2, { message: "Name must be at least 2 characters." }).max(100),
  description: z.string().max(500, { message: "Description must not exceed 500 characters." }).optional().nullable(),
});

export function DataDomainFormDialog({
  domain,
  isOpen,
  onOpenChange,
  onSubmitSuccess,
  trigger,
}: DataDomainFormDialogProps) {
  const api = useApi(); // Use the hook
  const { toast } = useToast(); // Use the hook
  const [isSubmitting, setIsSubmitting] = React.useState(false);

  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      name: domain?.name || "",
      description: domain?.description || "",
    },
  });

  // Reset form when dialog opens or domain changes
  React.useEffect(() => {
    if (isOpen) {
      form.reset({
        name: domain?.name || "",
        description: domain?.description || "",
      });
    }
  }, [isOpen, domain, form]);

  const handleFormSubmit = async (values: z.infer<typeof formSchema>) => {
    setIsSubmitting(true);
    let result;
    try {
      if (domain?.id) {
        // Update existing domain
        result = await api.put<DataDomain>(`/api/data-domains/${domain.id}`, values as DataDomainUpdate);
      } else {
        // Create new domain
        result = await api.post<DataDomain>('/api/data-domains', values as DataDomainCreate);
      }

      if (result.error) {
        throw new Error(result.error);
      }

      if (!result.data) {
         throw new Error('No data returned from API.');
      }

      toast({ title: domain ? "Domain Updated" : "Domain Created", description: `Successfully saved '${result.data.name}'.` });
      onSubmitSuccess(result.data); // Call success callback
      onOpenChange(false); // Close dialog on success

    } catch (error: any) {
      toast({ variant: "destructive", title: "Error Saving Domain", description: error.message || 'An unknown error occurred.' });
      // Keep dialog open on error
    } finally {
      setIsSubmitting(false);
    }
  };

  const dialogTitle = domain ? "Edit Data Domain" : "Create New Data Domain";
  const dialogDescription = domain
    ? "Make changes to the existing data domain."
    : "Add a new data domain to the system.";
  const submitButtonText = domain ? "Save Changes" : "Create Domain";

  const dialogContent = (
    <DialogContent className="sm:max-w-[425px]">
      <DialogHeader>
        <DialogTitle>{dialogTitle}</DialogTitle>
        <DialogDescription>{dialogDescription}</DialogDescription>
      </DialogHeader>
      <Form {...form}>
        <form onSubmit={form.handleSubmit(handleFormSubmit)} className="space-y-4 py-2">
          <FormField
            control={form.control}
            name="name"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Name *</FormLabel>
                <FormControl>
                  <Input placeholder="e.g., Sales Analytics" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="description"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Description</FormLabel>
                <FormControl>
                  <Textarea
                    placeholder="Describe the purpose of this domain..."
                    className="resize-none"
                    {...field}
                    value={field.value ?? ''} // Handle null for textarea
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={isSubmitting}>
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />} 
              {submitButtonText}
            </Button>
          </DialogFooter>
        </form>
      </Form>
    </DialogContent>
  );

  if (trigger) {
    return (
      <Dialog open={isOpen} onOpenChange={onOpenChange}>
        <DialogTrigger asChild>{trigger}</DialogTrigger>
        {dialogContent}
      </Dialog>
    );
  }

  // If no trigger, render the Dialog and Content directly (controlled externally)
  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      {dialogContent}
    </Dialog>
  );
} 