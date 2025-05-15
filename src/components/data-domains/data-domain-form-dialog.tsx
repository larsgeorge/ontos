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
  Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { DataDomain, DataDomainCreate, DataDomainUpdate } from '@/types/data-domain';
import { useApi } from '@/hooks/use-api';
import { useToast } from '@/hooks/use-toast';

interface DataDomainFormDialogProps {
  domain?: DataDomain | null;
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmitSuccess: (domain: DataDomain) => void;
  trigger?: React.ReactNode;
  allDomains: DataDomain[];
}

const NO_PARENT_VALUE = "__NO_PARENT_SELECTED__"; // Constant for "No Parent" option

const formSchema = z.object({
  name: z.string().min(2, { message: "Name must be at least 2 characters." }).max(100),
  description: z.string().max(500, { message: "Description must not exceed 500 characters." }).optional().nullable(),
  owner: z.string().min(1, { message: "Owner(s) are required. Enter comma-separated values." }),
  tags: z.string().optional().nullable(),
  parent_id: z.string().uuid().optional().nullable().or(z.literal(NO_PARENT_VALUE)), // Allow NO_PARENT_VALUE
});

export function DataDomainFormDialog({
  domain,
  isOpen,
  onOpenChange,
  onSubmitSuccess,
  trigger,
  allDomains,
}: DataDomainFormDialogProps) {
  const api = useApi();
  const { toast } = useToast();
  const [isSubmitting, setIsSubmitting] = React.useState(false);

  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      name: domain?.name || "",
      description: domain?.description || "",
      owner: domain?.owner?.join(', ') || "",
      tags: domain?.tags?.join(', ') || "",
      parent_id: domain?.parent_id ?? NO_PARENT_VALUE, // Use NO_PARENT_VALUE for null/undefined
    },
  });

  React.useEffect(() => {
    if (isOpen) {
      form.reset({
        name: domain?.name || "",
        description: domain?.description || "",
        owner: domain?.owner?.join(', ') || "",
        tags: domain?.tags?.join(', ') || "",
        parent_id: domain?.parent_id ?? NO_PARENT_VALUE, // Use NO_PARENT_VALUE for null/undefined
      });
    }
  }, [isOpen, domain, form, allDomains]);

  const handleFormSubmit = async (values: z.infer<typeof formSchema>) => {
    setIsSubmitting(true);
    let result;

    const processedValues: DataDomainCreate | DataDomainUpdate = {
      name: values.name,
      description: values.description,
      owner: values.owner.split(',').map(s => s.trim()).filter(s => s !== ""),
      tags: values.tags ? values.tags.split(',').map(s => s.trim()).filter(s => s !== "") : null,
      parent_id: values.parent_id === NO_PARENT_VALUE ? null : values.parent_id, // Convert back to null for API
    };

    if (domain?.id) {
      result = await api.put<DataDomain>(`/api/data-domains/${domain.id}`, processedValues as DataDomainUpdate);
    } else {
      result = await api.post<DataDomain>('/api/data-domains', processedValues as DataDomainCreate);
    }

    if (result.error) {
      throw new Error(result.error);
    }
    if (!result.data) {
       throw new Error('No data returned from API.');
    }

    toast({ title: domain ? "Domain Updated" : "Domain Created", description: `Successfully saved '${result.data.name}'.` });
    onSubmitSuccess(result.data);
    onOpenChange(false);

    try {
    } catch (error: any) {
      toast({ variant: "destructive", title: "Error Saving Domain", description: error.message || 'An unknown error occurred.' });
    } finally {
      setIsSubmitting(false);
    }
  };

  const dialogTitle = domain ? "Edit Data Domain" : "Create New Data Domain";
  const dialogDescription = domain
    ? "Make changes to the existing data domain."
    : "Add a new data domain to the system.";
  const submitButtonText = domain ? "Save Changes" : "Create Domain";

  const parentDomainOptions = allDomains.filter(d => d.id !== domain?.id);

  const dialogContent = (
    <DialogContent className="sm:max-w-[525px]">
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
                    value={field.value ?? ''}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="owner"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Owners *</FormLabel>
                <FormControl>
                  <Input placeholder="user@example.com, group@example.com" {...field} />
                </FormControl>
                <FormDescription>Comma-separated list of owner emails or group names.</FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="tags"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Tags</FormLabel>
                <FormControl>
                  <Input placeholder="finance, pii, core-data" {...field} value={field.value ?? ''} />
                </FormControl>
                <FormDescription>Comma-separated list of tags.</FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="parent_id"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Parent Domain</FormLabel>
                <Select
                  onValueChange={field.onChange}
                  value={field.value ?? NO_PARENT_VALUE}
                >
                  <FormControl>
                    <SelectTrigger>
                      <SelectValue placeholder="Select a parent domain (optional)" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    <SelectItem value={NO_PARENT_VALUE}>No Parent</SelectItem>
                    {parentDomainOptions.map((d) => (
                      <SelectItem key={d.id} value={d.id}>
                        {d.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            )}
          />
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={isSubmitting}>
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting || !form.formState.isValid}>
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

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      {dialogContent}
    </Dialog>
  );
} 