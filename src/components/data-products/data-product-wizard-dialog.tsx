import React, { useState, useEffect, useMemo, useRef } from 'react';
import { useForm, useFieldArray, Controller, FieldValues, SubmitHandler } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogDescription,
    DialogFooter,
    DialogClose,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { DataProduct, Link as DataProductLink, OutputPort as OutputPortType } from '@/types/data-product'; // Import OutputPort type
import { useApi } from '@/hooks/use-api';
import { useToast } from '@/hooks/use-toast';
import { Loader2, Plus, Trash2 } from 'lucide-react'; // Removed unused X icon
import ReactFlow, {
    Node,
    Edge,
    Background,
    Controls,
    MarkerType,
    Position,
    Handle, // Added Handle
    NodeProps, // Added NodeProps
} from 'reactflow';
import {
    Tooltip,
    TooltipContent,
    TooltipProvider,
    TooltipTrigger,
} from "@/components/ui/tooltip";
import { Card, CardContent } from '@/components/ui/card'; // Added Card for node styling

import 'reactflow/dist/style.css'; // Added ReactFlow styles

// --- Zod Schema Definition ---
// Define enums/literals for validation
const productTypes = ["source", "source-aligned", "aggregate", "consumer-aligned", "sink"] as const;
// const statuses = ["draft", "candidate", ...] as const; // Use fetched list

const linkSchema = z.object({
  url: z.string().url({ message: "Invalid URL format" }),
  description: z.string().optional(),
});

const customPropertySchema = z.object({
  key: z.string().min(1, "Key cannot be empty"),
  value: z.any(), // Allow any value for custom properties
});


const portBaseSchema = z.object({
    id: z.string().min(1, "Port ID is required"),
    name: z.string().min(1, "Port Name is required"),
    description: z.string().optional(),
    type: z.string().optional(), // Technical type like Kafka, table etc.
    assetType: z.string().optional(),
    assetIdentifier: z.string().optional(),
    location: z.string().optional(),
    // tags: z.array(z.string()).optional(), // Keep simple for now
});

const inputPortSchema = portBaseSchema.extend({
    sourceSystemId: z.string().min(1, "Source System ID is required"),
    sourceOutputPortId: z.string().optional(),
});

const outputPortSchema = portBaseSchema.extend({
    status: z.string().optional(),
    // server: serverSchema.optional(), // Add later if needed
    containsPii: z.boolean().optional().default(false),
    autoApprove: z.boolean().optional().default(false),
    dataContractId: z.string().optional(),
});

const dataProductSchema = z.object({
  // Hidden/Generated Fields (set internally)
  id: z.string().optional(), // Will be generated if creating
  dataProductSpecification: z.string().default("0.0.1"),
  created_at: z.string().optional(), // Readonly
  updated_at: z.string().optional(), // Readonly

  // Step 1
  productType: z.enum(productTypes, { required_error: "Product Type is required" }),

  // Step 2
  info: z.object({
    title: z.string().min(1, "Title is required"),
    owner: z.string().min(1, "Owner is required"),
    domain: z.string().optional(),
    description: z.string().optional(),
    status: z.string().optional(), // Make optional, can be set
    // archetype: z.string().optional(), // Maybe remove if type covers it
  }),
  version: z.string().min(1, "Version is required").default("v1.0"), // Default for creation

  // Step 3 (conditionally required)
  inputPorts: z.array(inputPortSchema).optional(),

  // Step 4
  outputPorts: z.array(outputPortSchema).optional(),

  // Step 5
  links: z.array(linkSchema).optional(), // Use array for field array
  custom: z.array(customPropertySchema).optional(), // Use array for field array
  tags: z.array(z.string()).optional(), // Simple tags for now

});


// --- Component Props ---
interface DataProductWizardDialogProps {
  isOpen: boolean;
  onOpenChange: (isOpen: boolean) => void;
  initialProduct: DataProduct | null; // For editing
  // Pass fetched dropdown data
  statuses: string[];
  // productTypes: string[]; // Using const defined above
  owners: string[];
  api: ReturnType<typeof useApi>;
  onSubmitSuccess: (product: DataProduct) => void;
}

// --- Product Type Details for ReactFlow ---
const productTypeDetails = [
  { id: 'source', label: 'Source', description: 'Raw data directly from origin systems. Represents the entry point of data into your ecosystem.' },
  { id: 'source-aligned', label: 'Source-Aligned', description: 'Cleaned, standardized, and validated source data. Ready for initial consumption or further processing.' },
  { id: 'aggregate', label: 'Aggregate', description: 'Derived or transformed data, often combining multiple sources. Provides new insights or summarized views.' },
  { id: 'consumer-aligned', label: 'Consumer-Aligned', description: 'Data specifically tailored for a particular business use case or consumer group. Often highly processed.' },
  { id: 'sink', label: 'Sink', description: 'An endpoint for data, typically feeding into external systems or applications. Marks an exit point from this data product ecosystem.' },
] as const;

// --- Custom Node for Product Type Selection ---
interface ProductTypeNodeData {
  label: string;
  // description: string; // Description is no longer needed in node data if displayed externally
  isSelected: boolean;
  onClick: () => void;
}

// --- Define nodeTypes outside the component for memoization ---
const ProductTypeNode: React.FC<NodeProps<ProductTypeNodeData>> = ({ data }) => {
  return (
    <>
      <Handle type="target" position={Position.Left} id="in" style={{ background: 'transparent', width: '1px', height: '1px', border: 'none' }} />
      {/* Tooltip components are fully removed */}
      <Card
        onClick={data.onClick}
        className={`w-36 h-20 flex items-center justify-center text-center cursor-pointer shadow-md hover:shadow-lg transition-shadow rounded-md
                        ${data.isSelected ? 'border-2 border-primary bg-primary/10' : 'bg-card border'}`}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            data.onClick();
          }
        }}
      >
        <CardContent className="p-1">
          <p className="text-xs font-semibold">{data.label}</p>
        </CardContent>
      </Card>
      <Handle type="source" position={Position.Right} id="out" style={{ background: 'transparent', width: '1px', height: '1px', border: 'none' }} />
    </>
  );
};

// Define nodeTypes outside the component for memoization
const nodeTypes = { productType: ProductTypeNode };

// --- Wizard Component ---
export default function DataProductWizardDialog({
  isOpen,
  onOpenChange,
  initialProduct,
  statuses,
  owners,
  api,
  onSubmitSuccess,
}: DataProductWizardDialogProps) {
  const [step, setStep] = useState(1);
  const [isLoading, setIsLoading] = useState(false);
  const { toast } = useToast();
  const { post, put } = api;

  const isEditing = !!initialProduct;
  const totalSteps = 5;

  const reactFlowWrapperRef = useRef<HTMLDivElement>(null); // Ref for ReactFlow container

  // Transform links/custom from Record<string, T> to Array<{key: string, value: T}> for form
  const transformInitialData = (product: DataProduct | null): z.infer<typeof dataProductSchema> => {
      const base: z.infer<typeof dataProductSchema> = {
        dataProductSpecification: "0.0.1", // Explicit default
        info: {
          title: '',
          owner: '',
          domain: '',
          description: '',
          status: statuses?.[0] || '',
        },
        version: "v1.0", // Explicit default
        productType: productTypes[0],
        inputPorts: [],
        outputPorts: [],
        links: [],
        custom: [],
        tags: [],
        // id, created_at, updated_at are optional and can be undefined initially
        id: undefined,
        created_at: undefined,
        updated_at: undefined,
      };

      if (!product) return base;

      // Helper to safely transform tags
      const transformTags = (tags: any): string[] | undefined => {
         if (Array.isArray(tags)) {
            return tags.filter(tag => typeof tag === 'string');
         }
         return undefined; // Or return [] if you prefer empty array over undefined
      };

      return {
          ...base,
          ...product,
          dataProductSpecification: product.dataProductSpecification || base.dataProductSpecification,
          version: product.version || base.version,
          links: product.links 
            ? Object.entries(product.links).map(([_, linkValue]) => ({ 
                url: linkValue.url || '', 
                description: linkValue.description || '' 
              })) 
            : base.links,
          custom: product.custom 
            ? Object.entries(product.custom).map(([key, value]) => ({ 
                key: key || '', 
                value: value ?? '' // Default value to empty string if null/undefined
              })) 
            : base.custom,
          tags: transformTags(product.tags) || base.tags,
          inputPorts: product.inputPorts ? product.inputPorts.map(port => {
            // Explicitly map fields to match inputPortSchema (Zod)
            // port is of type InputPort from @/types/data-product
            return {
              id: port.id || '',
              name: port.name || '',
              description: port.description || '',
              type: port.type || '',
              assetType: '', // Not in InputPort type, default for form
              assetIdentifier: '', // Not in InputPort type, default for form
              location: port.location || '',
              sourceSystemId: port.sourceSystemId || '',
              sourceOutputPortId: port.sourceOutputPortId || '',
              // links and custom are handled by field array state, not directly part of this default mapping if complex
            };
          }) : base.inputPorts,
          outputPorts: product.outputPorts ? product.outputPorts.map(port => {
            // Explicitly map fields to match outputPortSchema (Zod)
            // port is of type OutputPort from @/types/data-product
            return {
              id: port.id || '',
              name: port.name || '',
              description: port.description || '',
              type: port.type || '',
              assetType: '', // Not in OutputPort type, default for form
              assetIdentifier: '', // Not in OutputPort type, default for form
              location: port.location || '',
              status: port.status || '',
              containsPii: port.containsPii ?? false,
              autoApprove: port.autoApprove ?? false,
              dataContractId: port.dataContractId || '',
              // server, links and custom might need more specific handling or default empty objects if complex
            };
          }) : base.outputPorts,
          info: {
            title: product.info?.title || base.info.title,
            owner: product.info?.owner || base.info.owner,
            domain: product.info?.domain ?? base.info.domain,
            description: product.info?.description ?? base.info.description,
            status: product.info?.status ?? base.info.status,
          },
          productType: (product.productType && productTypes.includes(product.productType as any)) ? product.productType as z.infer<typeof dataProductSchema>['productType'] : base.productType,
          id: product.id || undefined,
      };
  };


  const form = useForm<z.infer<typeof dataProductSchema>>({
    resolver: zodResolver(dataProductSchema),
    defaultValues: transformInitialData(initialProduct), // transformInitialData now always returns a valid default
  });

   const { fields: inputPortFields, append: appendInputPort, remove: removeInputPort } = useFieldArray({
      control: form.control,
      name: "inputPorts",
    });

    const { fields: outputPortFields, append: appendOutputPort, remove: removeOutputPort } = useFieldArray({
        control: form.control,
        name: "outputPorts",
    });

    const { fields: linkFields, append: appendLink, remove: removeLink } = useFieldArray({
        control: form.control,
        name: "links",
    });

    const { fields: customFields, append: appendCustom, remove: removeCustom } = useFieldArray({
        control: form.control,
        name: "custom",
    });

  // Reset form when initialProduct changes (e.g., opening dialog for edit)
  useEffect(() => {
    const defaultValues = transformInitialData(initialProduct);
    form.reset(defaultValues);
    setStep(1); // Always start at step 1
  }, [initialProduct, form.reset]);


  const watchedProductType = form.watch('productType');
  const showInputPortsStep = watchedProductType !== 'source';

  const handleNext = async () => {
    let fieldsToValidate: (keyof z.infer<typeof dataProductSchema>)[] = [];
     switch (step) {
        case 1: fieldsToValidate = ['productType']; break;
        case 2: fieldsToValidate = ['info', 'version', 'tags']; break; // Add tags validation here
        case 3: if (showInputPortsStep) fieldsToValidate = ['inputPorts']; break;
        case 4: fieldsToValidate = ['outputPorts']; break;
        case 5: fieldsToValidate = ['links', 'custom']; break; // Add links/custom validation
     }

    const isValid = await form.trigger(fieldsToValidate);
    if (isValid) {
        // Skip step 3 if not applicable
        if (step === 2 && !showInputPortsStep) {
            setStep(4);
        } else if (step < totalSteps) {
            setStep(step + 1);
        }
    } else {
        console.log("Validation Errors:", form.formState.errors);
        toast({ title: "Validation Error", description: "Please fix the errors before proceeding.", variant: "destructive" });
    }
  };

  const handlePrevious = () => {
    // Skip step 3 if not applicable
    if (step === 4 && !showInputPortsStep) {
        setStep(2);
    } else if (step > 1) {
        setStep(step - 1);
    }
  };

  const onSubmit: SubmitHandler<z.infer<typeof dataProductSchema>> = async (data) => {
    setIsLoading(true);
    setError(null);

    // Generate ID if creating, ensure it's a valid UUID string
    const generatedId = window.crypto.randomUUID();
    const productId = isEditing ? initialProduct?.id : generatedId;

    if (!productId) {
         setError("Could not determine Product ID.");
         setIsLoading(false);
         toast({ title: 'Error', description: "Product ID is missing.", variant: 'destructive' });
         return;
    }

    // Transform data before sending
    const finalData: any = { // Use 'any' temporarily for flexibility during transformation
        ...data,
        id: productId,
        // Transform links/custom back to Record format for API
        links: data.links?.reduce((acc, link) => {
            // Use description as key if present and non-empty, otherwise use URL
            const key = link.description?.trim() || link.url;
            if (key) { // Ensure we have a valid key
                 acc[key] = { url: link.url, description: link.description || '' };
            }
            return acc;
        }, {} as Record<string, DataProductLink>) || {},
        custom: data.custom?.reduce((acc, prop) => {
            if (prop.key?.trim()) { // Ensure key is valid
                 acc[prop.key.trim()] = prop.value;
            }
            return acc;
        }, {} as Record<string, any>) || {},
        // Ensure ports are arrays even if undefined/null
        inputPorts: data.inputPorts || [],
        outputPorts: data.outputPorts || [],
        // Ensure tags is a simple array of strings
        tags: Array.isArray(data.tags) ? data.tags.filter(t => typeof t === 'string') : [],
        info: {
           ...data.info,
           status: data.info.status || statuses?.[0] || 'draft', // Default status
        },
        // Ensure productType is the string value
        productType: data.productType, // Should be the string enum value from the form
    };


    try {
      let response;
      if (isEditing) {
        console.log("Submitting PUT request with data:", JSON.stringify(finalData, null, 2));
        response = await put<DataProduct>(`/api/data-products/${productId}`, finalData);
      } else {
         console.log("Submitting POST request with data:", JSON.stringify(finalData, null, 2));
        response = await post<DataProduct>('/api/data-products', finalData);
      }

      // Enhanced Error Handling
      if (response.error) {
         // Try to parse backend error detail if it exists
         let backendError = response.error;
         try {
            const errorObj = JSON.parse(response.error);
            if (errorObj.detail) {
               backendError = typeof errorObj.detail === 'string' ? errorObj.detail : JSON.stringify(errorObj.detail);
            }
         } catch (e) { /* Ignore parsing errors, use original error string */ }
         throw new Error(backendError);
      }
      if (response.data && typeof response.data === 'object' && 'detail' in response.data) {
         // Handle FastAPI validation errors or other detailed errors
         const detail = response.data.detail;
         const errorMsg = typeof detail === 'string' ? detail : JSON.stringify(detail);
         throw new Error(errorMsg);
      }
      if (!response.data) {
          throw new Error("API response did not contain product data.");
      }

      toast({ title: 'Success', description: `Data product ${isEditing ? 'updated' : 'created'}.` });
      onSubmitSuccess(response.data); // Pass the saved product back
      onOpenChange(false); // Close dialog

    } catch (err: any) {
      const errorMsg = err.message || 'An unexpected error occurred.';
      console.error(`API Error (${isEditing ? 'PUT' : 'POST'} /api/data-products/${isEditing ? productId : ''}):`, errorMsg);
      setError(errorMsg); // Display error in the dialog if needed
      toast({ title: 'Error', description: errorMsg, variant: 'destructive' });
    } finally {
      setIsLoading(false);
    }
  };

  const [error, setError] = useState<string | null>(null);

  // --- ReactFlow Nodes and Edges ---
  const { nodes: flowNodes, edges: flowEdges } = useMemo(() => {
    const nodesList: Node<ProductTypeNodeData>[] = productTypeDetails.map((pt, index) => ({
      id: pt.id,
      type: 'productType',
      position: { x: index * 170 + 20, y: 40 },
      data: {
        label: pt.label,
        isSelected: watchedProductType === pt.id,
        onClick: () => {
          form.setValue('productType', pt.id as z.infer<typeof dataProductSchema>['productType'], { shouldValidate: true, shouldDirty: true, shouldTouch: true });
        },
      },
      draggable: false,
      selectable: false,
      connectable: false, // Nodes themselves are not connectable
      focusable: true, // Let's make them focusable to see if it helps with keyboard nav for click
    }));

    const edgesList: Edge[] = productTypeDetails.slice(0, -1).map((pt, index) => ({
      id: `e-${pt.id}-to-${productTypeDetails[index + 1].id}`,
      source: pt.id,
      target: productTypeDetails[index + 1].id,
      sourceHandle: 'out',
      targetHandle: 'in',
      type: 'smoothstep',
      markerEnd: { type: MarkerType.ArrowClosed, color: '#6b7280', width: 15, height: 15 },
      style: { stroke: '#6b7280', strokeWidth: 1.5 },
      animated: false, // Keep it static unless active
      selectable: false,
    }));
    return { nodes: nodesList, edges: edgesList };
  }, [watchedProductType, form.setValue, form.getValues]); // Add dependencies for useMemo

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent 
        className="sm:max-w-[600px] md:max-w-[800px] lg:max-w-[1000px] max-h-[90vh] flex flex-col"
      >
        <DialogHeader>
          <DialogTitle>{isEditing ? 'Edit Data Product' : 'Create New Data Product'} (Step {step} of {totalSteps})</DialogTitle>
          <DialogDescription>
            {step === 1 && "Select the type that best describes this data product's role in the data flow."}
            {step === 2 && "Provide basic information about the data product."}
            {step === 3 && "Define the input ports (data sources consumed by this product)."}
            {step === 4 && "Define the output ports (data produced by this product)."}
            {step === 5 && "Add relevant links and custom metadata properties."}
          </DialogDescription>
        </DialogHeader>

        {/* Form Content - Overflow handled here */}
        <div className="flex-grow overflow-y-auto pr-6 pl-1 space-y-4 py-4">
          {/* Wrap content in form, but submit button is external */}
          {/* Step 1: Product Type */}
            <div className={`${step === 1 ? 'block' : 'hidden'} space-y-6`}>
                {/* ReactFlow Diagram */}
                <style>{`
                  .reactflow-custom-cursor .react-flow__pane {
                    cursor: default !important;
                  }
                  /* Dashed edges can be removed if arrows are showing */
                  /* .reactflow-custom-cursor .react-flow__edge path {
                    stroke-dasharray: 5, 5; 
                  } */
                `}</style>
                <div 
                  ref={reactFlowWrapperRef} // Attach ref here
                  className="h-40 w-full border rounded-lg relative bg-muted/30 reactflow-custom-cursor" 
                  style={{ minHeight: '160px' }} 
                >
                  <ReactFlow
                    nodes={flowNodes}
                    edges={flowEdges}
                    nodeTypes={nodeTypes}
                    fitView
                    attributionPosition="top-right"
                    nodesDraggable={false}
                    nodesConnectable={false}
                    elementsSelectable={false}
                    zoomOnScroll={false}
                    panOnScroll={false}
                    preventScrolling={false}
                    panOnDrag={false}
                    zoomOnPinch={false}
                    zoomOnDoubleClick={false}
                    nodesFocusable={true}
                    fitViewOptions={{ padding: 0.05 }}
                    onNodeClick={(_, node) => { // Cleaned up onNodeClick
                        if (node.data && typeof node.data.onClick === 'function') {
                            node.data.onClick();
                        }
                    }}
                  >
                    <Background gap={16} />
                    <Controls showInteractive={false} showFitView={false} showZoom={false} />
                  </ReactFlow>
                </div>

                {/* Display selected product type description */}
                {watchedProductType && (
                  <div className="mt-4 p-3 border rounded-md bg-muted/50 min-h-[60px]">
                    <p className="text-sm font-semibold mb-1">
                      {productTypeDetails.find(pt => pt.id === watchedProductType)?.label} Description:
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {productTypeDetails.find(pt => pt.id === watchedProductType)?.description}
                    </p>
                  </div>
                )}

                {/* Existing Select Dropdown */}
                <div>
                  <Label htmlFor="productType" className="text-base font-medium mb-2 block">Or select Product Type from list *</Label>
                  <Controller
                    control={form.control}
                    name="productType"
                    render={({ field }) => (
                        <Select onValueChange={field.onChange} value={field.value || ''}>
                            <SelectTrigger id="productType">
                                <SelectValue placeholder="Select product type" />
                            </SelectTrigger>
                            <SelectContent>
                                {productTypes.map((type) => (
                                    <SelectItem key={type} value={type}>
                                        <span className="capitalize">{type.replace('-', ' ')}</span>
                                        <span className="text-xs text-muted-foreground ml-2">
                                            {type === 'source' && 'Raw data from origin systems.'}
                                            {type === 'source-aligned' && 'Cleaned/standardized source data.'}
                                            {type === 'aggregate' && 'Derived/transformed data.'}
                                            {type === 'consumer-aligned' && 'Data tailored for specific use cases.'}
                                            {type === 'sink' && 'Data endpoint for external systems.'}
                                        </span>
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    )}
                />
                {form.formState.errors.productType && <p className="text-sm text-destructive mt-1">{form.formState.errors.productType.message}</p>}
                </div>
            </div>

            {/* Step 2: Info */}
            <div className={`${step === 2 ? 'block' : 'hidden'} space-y-4`}>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                    <Label htmlFor="info.title">Title *</Label>
                    <Input id="info.title" {...form.register('info.title')} />
                    {form.formState.errors.info?.title && <p className="text-sm text-destructive mt-1">{form.formState.errors.info.title.message}</p>}
                </div>
                <div>
                    <Label htmlFor="info.owner">Owner *</Label>
                    <Controller
                        control={form.control}
                        name="info.owner"
                        render={({ field }) => (
                            <Select onValueChange={field.onChange} value={field.value || ''}>
                            <SelectTrigger>
                                <SelectValue placeholder="Select owner" />
                            </SelectTrigger>
                            <SelectContent>
                                {owners.map(owner => <SelectItem key={owner} value={owner}>{owner}</SelectItem>)}
                            </SelectContent>
                            </Select>
                        )}
                        />
                    {form.formState.errors.info?.owner && <p className="text-sm text-destructive mt-1">{form.formState.errors.info.owner.message}</p>}
                </div>
                <div>
                    <Label htmlFor="version">Version *</Label>
                    <Input id="version" {...form.register('version')} />
                    {form.formState.errors.version && <p className="text-sm text-destructive mt-1">{form.formState.errors.version.message}</p>}
                </div>
                <div>
                    <Label htmlFor="info.status">Status</Label>
                    <Controller
                        control={form.control}
                        name="info.status"
                        render={({ field }) => (
                            <Select onValueChange={field.onChange} value={field.value || ''}>
                            <SelectTrigger>
                                <SelectValue placeholder="Select status" />
                            </SelectTrigger>
                            <SelectContent>
                                {statuses.map(status => <SelectItem key={status} value={status}>{status}</SelectItem>)}
                            </SelectContent>
                            </Select>
                        )}
                        />
                    {form.formState.errors.info?.status && <p className="text-sm text-destructive mt-1">{form.formState.errors.info.status.message}</p>}
                </div>
                <div>
                    <Label htmlFor="info.domain">Domain</Label>
                    <Input id="info.domain" {...form.register('info.domain')} />
                    {form.formState.errors.info?.domain && <p className="text-sm text-destructive mt-1">{form.formState.errors.info.domain.message}</p>}
                </div>
                </div>
                <div>
                <Label htmlFor="info.description">Description</Label>
                <Textarea id="info.description" {...form.register('info.description')} />
                {form.formState.errors.info?.description && <p className="text-sm text-destructive mt-1">{form.formState.errors.info.description.message}</p>}
                </div>
                <div>
                    <Label htmlFor="tags">Tags (comma-separated)</Label>
                    {/* Update tag handling */}
                    <Controller
                        name="tags"
                        control={form.control}
                        render={({ field }) => (
                            <Input
                            id="tags"
                            value={Array.isArray(field.value) ? field.value.join(', ') : ''}
                            onChange={(e) => {
                                const tags = e.target.value.split(',').map(t => t.trim()).filter(Boolean);
                                field.onChange(tags);
                            }}
                            />
                        )}
                    />
                    {form.formState.errors.tags && <p className="text-sm text-destructive mt-1">{form.formState.errors.tags.message}</p>}
                </div>
            </div>

            {/* Step 3: Input Ports */}
            <div className={`${step === 3 && showInputPortsStep ? 'block' : 'hidden'} space-y-4`}>
                <h3 className="text-lg font-medium">Input Ports</h3>
                {inputPortFields.map((field, index) => (
                    <div key={field.id} className="border p-4 rounded space-y-3 relative">
                        <Button variant="ghost" size="icon" className="absolute top-1 right-1 text-destructive hover:bg-destructive/10 h-6 w-6" onClick={() => removeInputPort(index)}>
                        <Trash2 className="h-4 w-4" />
                        </Button>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <Label htmlFor={`inputPorts.${index}.id`}>Port ID *</Label>
                                <Input {...form.register(`inputPorts.${index}.id`)} />
                                {form.formState.errors.inputPorts?.[index]?.id && <p className="text-sm text-destructive mt-1">{form.formState.errors.inputPorts[index]?.id?.message}</p>}
                            </div>
                            <div>
                                <Label htmlFor={`inputPorts.${index}.name`}>Port Name *</Label>
                                <Input {...form.register(`inputPorts.${index}.name`)} />
                                {form.formState.errors.inputPorts?.[index]?.name && <p className="text-sm text-destructive mt-1">{form.formState.errors.inputPorts[index]?.name?.message}</p>}
                            </div>
                            <div>
                                <Label htmlFor={`inputPorts.${index}.sourceSystemId`}>Source System ID *</Label>
                                <Input placeholder="e.g., data-product:other-id, system:kafka" {...form.register(`inputPorts.${index}.sourceSystemId`)} />
                                {form.formState.errors.inputPorts?.[index]?.sourceSystemId && <p className="text-sm text-destructive mt-1">{form.formState.errors.inputPorts[index]?.sourceSystemId?.message}</p>}
                            </div>
                            <div>
                                <Label htmlFor={`inputPorts.${index}.sourceOutputPortId`}>Source Output Port ID</Label>
                                <Input {...form.register(`inputPorts.${index}.sourceOutputPortId`)} />
                                {form.formState.errors.inputPorts?.[index]?.sourceOutputPortId && <p className="text-sm text-destructive mt-1">{form.formState.errors.inputPorts[index]?.sourceOutputPortId?.message}</p>}
                            </div>
                            <div>
                                <Label htmlFor={`inputPorts.${index}.description`}>Description</Label>
                                <Input {...form.register(`inputPorts.${index}.description`)} />
                            </div>
                            {/* Add other input port fields if needed */}
                        </div>
                    </div>
                ))}
                <Button type="button" variant="outline" size="sm" onClick={() => appendInputPort({ id: '', name: '', sourceSystemId: '' })}>
                <Plus className="h-4 w-4 mr-2"/> Add Input Port
                </Button>
                {form.formState.errors.inputPorts?.root && <p className="text-sm text-destructive mt-1">{form.formState.errors.inputPorts.root.message}</p>}
            </div>
            <div className={`${step === 3 && !showInputPortsStep ? 'block' : 'hidden'} space-y-4`}>
                <p className="text-muted-foreground">Input ports are not applicable for 'Source' data products.</p>
            </div>


            {/* Step 4: Output Ports */}
            <div className={`${step === 4 ? 'block' : 'hidden'} space-y-4`}>
            <h3 className="text-lg font-medium">Output Ports</h3>
                {outputPortFields.map((field, index) => (
                    <div key={field.id} className="border p-4 rounded space-y-3 relative">
                        <Button variant="ghost" size="icon" className="absolute top-1 right-1 text-destructive hover:bg-destructive/10 h-6 w-6" onClick={() => removeOutputPort(index)}>
                            <Trash2 className="h-4 w-4" />
                        </Button>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                            <Label htmlFor={`outputPorts.${index}.id`}>Port ID *</Label>
                            <Input {...form.register(`outputPorts.${index}.id`)} />
                            {form.formState.errors.outputPorts?.[index]?.id && <p className="text-sm text-destructive mt-1">{form.formState.errors.outputPorts[index]?.id?.message}</p>}
                        </div>
                        <div>
                            <Label htmlFor={`outputPorts.${index}.name`}>Port Name *</Label>
                            <Input {...form.register(`outputPorts.${index}.name`)} />
                            {form.formState.errors.outputPorts?.[index]?.name && <p className="text-sm text-destructive mt-1">{form.formState.errors.outputPorts[index]?.name?.message}</p>}
                        </div>
                        <div>
                            <Label htmlFor={`outputPorts.${index}.description`}>Description</Label>
                            <Input {...form.register(`outputPorts.${index}.description`)} />
                        </div>
                        {/* Add other output port fields: status, server, containsPii, etc. */}
                        </div>
                    </div>
                ))}
                <Button type="button" variant="outline" size="sm" onClick={() => appendOutputPort({ id: '', name: '', containsPii: false, autoApprove: false })}>
                    <Plus className="h-4 w-4 mr-2"/>Add Output Port
                </Button>
            </div>

            {/* Step 5: Links & Custom */}
            <div className={`${step === 5 ? 'block' : 'hidden'} space-y-6`}>
                {/* Links */}
                <div>
                <h3 className="text-lg font-medium mb-2">Links</h3>
                    {linkFields.map((field, index) => (
                        <div key={field.id} className="flex items-end gap-2 mb-2 p-3 border rounded">
                        <div className="flex-1">
                            <Label htmlFor={`links.${index}.url`}>URL *</Label>
                            <Input {...form.register(`links.${index}.url`)} />
                            {form.formState.errors.links?.[index]?.url && <p className="text-sm text-destructive mt-1">{form.formState.errors.links[index]?.url?.message}</p>}
                        </div>
                            <div className="flex-1">
                            <Label htmlFor={`links.${index}.description`}>Description (used as link key)</Label>
                            <Input {...form.register(`links.${index}.description`)} />
                             {form.formState.errors.links?.[index]?.description && <p className="text-sm text-destructive mt-1">{form.formState.errors.links[index]?.description?.message}</p>}
                        </div>
                            <Button variant="ghost" size="icon" className="text-destructive hover:bg-destructive/10 mb-1 h-8 w-8" onClick={() => removeLink(index)}>
                            <Trash2 className="h-4 w-4" />
                        </Button>
                        </div>
                    ))}
                    <Button type="button" variant="outline" size="sm" onClick={() => appendLink({ url: '', description: '' })}>
                        <Plus className="h-4 w-4 mr-2"/>Add Link
                    </Button>
                </div>

                {/* Custom Properties */}
                <div>
                    <h3 className="text-lg font-medium mb-2">Custom Properties</h3>
                    {customFields.map((field, index) => (
                        <div key={field.id} className="flex items-end gap-2 mb-2 p-3 border rounded">
                            <div className="flex-1">
                            <Label htmlFor={`custom.${index}.key`}>Key *</Label>
                            <Input {...form.register(`custom.${index}.key`)} />
                            {form.formState.errors.custom?.[index]?.key && <p className="text-sm text-destructive mt-1">{form.formState.errors.custom[index]?.key?.message}</p>}
                            </div>
                            <div className="flex-1">
                            <Label htmlFor={`custom.${index}.value`}>Value</Label>
                            {/* Consider type dropdown or flexible input later */}
                            <Input {...form.register(`custom.${index}.value`)} />
                              {form.formState.errors.custom?.[index]?.value?.message && typeof form.formState.errors.custom?.[index]?.value?.message === 'string' &&
                               <p className="text-sm text-destructive mt-1">{form.formState.errors.custom[index]?.value?.message as string}</p>}
                            </div>
                            <Button variant="ghost" size="icon" className="text-destructive hover:bg-destructive/10 mb-1 h-8 w-8" onClick={() => removeCustom(index)}>
                                <Trash2 className="h-4 w-4" />
                        </Button>
                        </div>
                    ))}
                    <Button type="button" variant="outline" size="sm" onClick={() => appendCustom({ key: '', value: '' })}>
                         <Plus className="h-4 w-4 mr-2"/>Add Custom Property
                    </Button>
                </div>
            </div>
          {error && (
              <p className="text-sm text-destructive mt-2">{error}</p>
          )}
        </div>

        {/* Dialog Footer */}
        <DialogFooter className="mt-auto pt-4 border-t">
          <div className="flex justify-between w-full">
            <Button type="button" variant="outline" onClick={handlePrevious} disabled={step === 1 || isLoading}>
              Previous
            </Button>
             {step < totalSteps ? (
              <Button type="button" onClick={handleNext} disabled={isLoading}>
                Next
              </Button>
            ) : (
              // Use form.handleSubmit to trigger final validation and onSubmit
              <Button type="button" onClick={form.handleSubmit(onSubmit)} disabled={isLoading}>
                {isLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                {isEditing ? 'Save Changes' : 'Create Product'}
              </Button>
            )}
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
} 