import { useEffect, useMemo, useRef, useState } from 'react';
import { useApi } from '@/hooks/use-api';
import { useToast } from '@/hooks/use-toast';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { DataTable } from '@/components/ui/data-table';
import { ColumnDef, Column } from '@tanstack/react-table';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Upload, Eye, Trash2, ChevronDown, RefreshCw } from 'lucide-react';
import { SemanticModel, SemanticModelPreview } from '@/types/semantic-model';

export default function SemanticModelsSettings() {
  const { get, post, put, delete: del } = useApi();
  const { toast } = useToast();
  const [items, setItems] = useState<SemanticModel[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [preview, setPreview] = useState<SemanticModelPreview | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const fetchItems = async () => {
    setIsLoading(true);
    try {
      const res = await get<SemanticModel[]>('/api/semantic-models');
      setItems(res.data || []);
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
    const form = new FormData();
    form.append('file', file);
    const res = await post<SemanticModel>('/api/semantic-models/upload', form);
    if (res.error) {
      toast({ title: 'Upload failed', description: res.error, variant: 'destructive' });
    } else {
      toast({ title: 'Uploaded', description: `${res.data.name}` });
      fetchItems();
    }
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const toggleEnabled = async (row: SemanticModel, enabled: boolean) => {
    const res = await put<SemanticModel>(`/api/semantic-models/${row.id}`, { enabled });
    if (res.error) {
      toast({ title: 'Update failed', description: res.error, variant: 'destructive' });
    } else {
      setItems((prev) => prev.map((i) => (i.id === row.id ? { ...i, enabled } : i)));
    }
  };

  const doDelete = async (row: SemanticModel) => {
    if (!confirm(`Delete ${row.name}?`)) return;
    const res = await del(`/api/semantic-models/${row.id}`);
    if (res.error) {
      toast({ title: 'Delete failed', description: res.error, variant: 'destructive' });
    } else {
      toast({ title: 'Deleted', description: row.name });
      setItems((prev) => prev.filter((i) => i.id !== row.id));
    }
  };

  const openPreview = async (row: SemanticModel) => {
    const res = await get<SemanticModelPreview>(`/api/semantic-models/${row.id}/preview`);
    if (res.error) {
      toast({ title: 'Preview failed', description: res.error, variant: 'destructive' });
    } else {
      setPreview(res.data);
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
      accessorKey: 'format',
      header: 'Format',
      cell: ({ row }) => <Badge variant="secondary">{row.getValue('format')}</Badge>,
    },
    {
      accessorKey: 'enabled',
      header: 'Enabled',
      cell: ({ row }) => {
        const r = row.original;
        return (
          <Switch checked={r.enabled} onCheckedChange={(v) => toggleEnabled(r, v)} />
        );
      },
    },
    {
      accessorKey: 'updatedAt',
      header: 'Updated',
      cell: ({ row }) => {
        const val = row.getValue<string>('updatedAt');
        return val ? new Date(val).toLocaleString() : '-';
      },
    },
    {
      id: 'actions',
      header: '',
      cell: ({ row }) => {
        const r = row.original;
        return (
          <div className="flex gap-2 justify-end">
            <Button variant="outline" size="sm" onClick={() => openPreview(r)}>
              <Eye className="h-3.5 w-3.5" /> Preview
            </Button>
            <Button variant="destructive" size="sm" onClick={() => doDelete(r)}>
              <Trash2 className="h-3.5 w-3.5" /> Delete
            </Button>
          </div>
        );
      },
    },
  ], []);

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

      <Dialog open={!!preview} onOpenChange={(o) => !o && setPreview(null)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Preview: {preview?.name}</DialogTitle>
          </DialogHeader>
          <pre className="max-h-[60vh] overflow-auto whitespace-pre-wrap text-xs p-3 bg-muted rounded-md">
{preview?.preview}
          </pre>
        </DialogContent>
      </Dialog>
    </Card>
  );
}


