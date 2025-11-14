import { useEffect, useMemo, useRef, useState } from 'react';
import { useApi } from '@/hooks/use-api';
import { useToast } from '@/hooks/use-toast';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { DataTable } from '@/components/ui/data-table';
import { ColumnDef, Column } from '@tanstack/react-table';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Upload, ChevronDown, RefreshCw, Trash2 } from 'lucide-react';
import type { SemanticModel } from '@/types/ontology';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';

export default function SemanticModelsSettings() {
  const { get, post, delete: deleteApi } = useApi();
  const { toast } = useToast();
  const [items, setItems] = useState<SemanticModel[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [uploadingId, setUploadingId] = useState<string | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [modelToDelete, setModelToDelete] = useState<SemanticModel | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const fetchItems = async () => {
    setIsLoading(true);
    try {
      const res = await get<{ semantic_models: SemanticModel[] } | SemanticModel[]>('/api/semantic-models');
      const data = (res.data as any);
      const models: SemanticModel[] = Array.isArray(data) ? data : (data?.semantic_models || []);
      console.log('Semantic models loaded:', models.map(m => ({ name: m.name, created_by: m.created_by })));
      setItems(models || []);
    } catch (e: any) {
      toast({ title: 'Error', description: e.message || 'Failed to load models', variant: 'destructive' });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => { fetchItems(); }, []);

  const onUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await post<{ model: SemanticModel; message: string }>('/api/semantic-models/upload', formData);
      
      if (res.error) {
        toast({ 
          title: 'Upload Failed', 
          description: res.error, 
          variant: 'destructive' 
        });
      } else {
        toast({ 
          title: 'Success', 
          description: res.data.message || 'Semantic model uploaded successfully' 
        });
        await fetchItems();
      }
    } catch (e: any) {
      toast({ 
        title: 'Upload Error', 
        description: e.message || 'Failed to upload file', 
        variant: 'destructive' 
      });
    } finally {
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const onToggleEnabled = async (modelId: string, currentEnabled: boolean) => {
    setUploadingId(modelId);
    try {
      const response = await fetch(`/api/semantic-models/${modelId}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ enabled: !currentEnabled }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to update model');
      }

      toast({ 
        title: 'Success', 
        description: `Model ${!currentEnabled ? 'enabled' : 'disabled'} successfully` 
      });
      
      await fetchItems();
    } catch (e: any) {
      toast({ 
        title: 'Error', 
        description: e.message || 'Failed to update model', 
        variant: 'destructive' 
      });
    } finally {
      setUploadingId(null);
    }
  };

  const onDeleteClick = (model: SemanticModel) => {
    setModelToDelete(model);
    setDeleteDialogOpen(true);
  };

  const onDeleteConfirm = async () => {
    if (!modelToDelete) return;

    try {
      const res = await deleteApi(`/api/semantic-models/${modelToDelete.id}`);
      
      if (res.error) {
        toast({ 
          title: 'Delete Failed', 
          description: res.error, 
          variant: 'destructive' 
        });
      } else {
        toast({ 
          title: 'Success', 
          description: 'Semantic model deleted successfully' 
        });
        await fetchItems();
      }
    } catch (e: any) {
      toast({ 
        title: 'Delete Error', 
        description: e.message || 'Failed to delete model', 
        variant: 'destructive' 
      });
    } finally {
      setDeleteDialogOpen(false);
      setModelToDelete(null);
    }
  };

  const columns = useMemo<ColumnDef<SemanticModel>[]>(() => [
    {
      accessorKey: 'name',
      header: ({ column }: { column: Column<SemanticModel, unknown> }) => (
        <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}>
          Name <ChevronDown className="ml-2 h-4 w-4" />
        </Button>
      ),
      cell: ({ row }) => <div className="font-medium">{row.getValue('name')}</div>,
    },
    { 
      id: 'source',
      header: 'Source', 
      cell: ({ row }) => {
        const model = row.original;
        const createdBy = model.created_by || '';
        
        // Determine source based on created_by
        let label = 'Unknown';
        let variant: 'default' | 'secondary' | 'outline' = 'secondary';
        
        if (createdBy === 'system@startup') {
          label = 'System';
          variant = 'outline';
        } else if (createdBy === 'system@file') {
          label = 'File';
          variant = 'secondary';
        } else if (createdBy === 'system@schema') {
          label = 'Schema';
          variant = 'secondary';
        } else if (createdBy.startsWith('system@')) {
          label = 'System';
          variant = 'outline';
        } else if (createdBy && createdBy !== '') {
          label = 'Upload';
          variant = 'default';
        }
        
        return <Badge variant={variant}>{label}</Badge>;
      }
    },
    { 
      accessorKey: 'format', 
      header: 'Format', 
      cell: ({ row }) => <Badge variant="secondary">{row.getValue('format')?.toUpperCase()}</Badge> 
    },
    { 
      accessorKey: 'size_bytes', 
      header: 'Size', 
      cell: ({ row }) => {
        const bytes = row.getValue('size_bytes') as number | undefined;
        if (!bytes) return <span>-</span>;
        const kb = (bytes / 1024).toFixed(1);
        return <span>{kb} KB</span>;
      }
    },
    {
      accessorKey: 'enabled',
      header: 'Enabled',
      cell: ({ row }) => {
        const model = row.original;
        const isToggling = uploadingId === model.id;
        const isFileBased = model.id?.startsWith('file-');
        const createdBy = model.created_by || '';
        const isSystemManaged = createdBy.startsWith('system@') && createdBy !== 'system@startup';
        
        // File-based and schema models can't be toggled (always enabled)
        if (isFileBased || isSystemManaged) {
          return (
            <div data-action-cell="true">
              <Badge variant="outline" className="text-xs">Always On</Badge>
            </div>
          );
        }
        
        return (
          <div data-action-cell="true">
            <Switch
              checked={row.getValue('enabled')}
              onCheckedChange={() => onToggleEnabled(model.id, row.getValue('enabled'))}
              disabled={isToggling}
            />
          </div>
        );
      },
    },
    {
      id: 'actions',
      header: 'Actions',
      cell: ({ row }) => {
        const model = row.original;
        const isFileBased = model.id?.startsWith('file-');
        const createdBy = model.created_by || '';
        const isSystemManaged = createdBy.startsWith('system@') && createdBy !== 'system@startup';
        
        // File-based and schema models can't be deleted (read-only from filesystem)
        if (isFileBased || isSystemManaged) {
          return (
            <div data-action-cell="true">
              <span className="text-xs text-muted-foreground">Read-only</span>
            </div>
          );
        }
        
        return (
          <div data-action-cell="true">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => onDeleteClick(model)}
              title="Delete model"
            >
              <Trash2 className="h-4 w-4 text-destructive" />
            </Button>
          </div>
        );
      },
    },
  ], [uploadingId]);

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle>Semantic Models (RDFS/SKOS)</CardTitle>
          <CardDescription>Upload and manage taxonomy files for tagging.</CardDescription>
        </div>
        <div className="flex items-center gap-2">
          <Input ref={fileInputRef} type="file" accept=".ttl,.rdf,.xml,.skos,.rdfs,.owl,.nt,.n3,.trig,.trix,.jsonld,.json" className="hidden" onChange={onUpload} />
          <Button variant="outline" onClick={() => fileInputRef.current?.click()}>
            <Upload className="h-4 w-4 mr-2" /> Upload
          </Button>
          <Button variant="ghost" onClick={fetchItems}>
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <DataTable columns={columns} data={items} searchColumn="name" isLoading={isLoading} />
      </CardContent>

      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Semantic Model</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete <strong>{modelToDelete?.name}</strong>? 
              This action cannot be undone and will remove the model from the semantic graph.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={onDeleteConfirm} className="bg-destructive text-destructive-foreground hover:bg-destructive/90">
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Card>
  );
}


