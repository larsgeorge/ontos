import { useEffect, useMemo, useRef, useState } from 'react';
import { useApi } from '@/hooks/use-api';
import { useToast } from '@/hooks/use-toast';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { DataTable } from '@/components/ui/data-table';
import { ColumnDef, Column } from '@tanstack/react-table';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Upload, ChevronDown, RefreshCw } from 'lucide-react';
import type { SemanticModel } from '@/types/ontology';

export default function SemanticModelsSettings() {
  const { get } = useApi();
  const { toast } = useToast();
  const [items, setItems] = useState<SemanticModel[]>([]);
  const [isLoading, setIsLoading] = useState(true); // retained for potential spinner usage
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const fetchItems = async () => {
    setIsLoading(true);
    try {
      const res = await get<{ semantic_models: SemanticModel[] } | SemanticModel[]>('/api/semantic-models');
      const data = (res.data as any);
      const models: SemanticModel[] = Array.isArray(data) ? data : (data?.semantic_models || []);
      setItems(models || []);
    } catch (e: any) {
      toast({ title: 'Error', description: e.message || 'Failed to load models', variant: 'destructive' });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => { fetchItems(); }, []);

  const onUpload = async (_e: React.ChangeEvent<HTMLInputElement>) => {
    toast({ title: 'Not supported', description: 'Upload is disabled for file-based models.', variant: 'destructive' });
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  // Read-only page: toggle, delete, preview are not available.

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
    { accessorKey: 'source_type', header: 'Source', cell: ({ row }) => <Badge variant="secondary">{row.getValue('source_type')}</Badge> },
    { accessorKey: 'format', header: 'Format', cell: ({ row }) => <Badge variant="secondary">{row.getValue('format') || '-'}</Badge> },
    { accessorKey: 'concepts_count', header: 'Concepts', cell: ({ row }) => <span>{row.getValue('concepts_count')}</span> },
    { accessorKey: 'properties_count', header: 'Properties', cell: ({ row }) => <span>{row.getValue('properties_count')}</span> },
    // Enabled column removed in read-only mode
    // Read-only: omit updated/actions columns for now
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
        <DataTable columns={columns} data={items} searchColumn="name" />
      </CardContent>

      {/* Preview dialog removed in read-only mode */}
    </Card>
  );
}


