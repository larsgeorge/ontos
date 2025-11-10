import { useEffect, useMemo, useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2 } from 'lucide-react';
import SchemaPropertyEditor from '@/components/data-contracts/schema-property-editor';
import type { ColumnProperty } from '@/types/data-contract';
import { useProjectContext } from '@/stores/project-store';

type CreateType = 'catalog' | 'schema' | 'table';

type Props = {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  initialType?: 'catalog' | 'schema' | 'table';
};

export default function SelfServiceDialog({ isOpen, onOpenChange, initialType }: Props) {
  const { currentProject } = useProjectContext();

  const [createType, setCreateType] = useState<CreateType>('table');
  const [catalog, setCatalog] = useState('');
  const [schema, setSchema] = useState('');
  const [tableName, setTableName] = useState('');
  const [columns, setColumns] = useState<ColumnProperty[]>([]);
  const [autoFix, setAutoFix] = useState(true);
  const [createContract, setCreateContract] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<any | null>(null);

  // Bootstrap defaults
  useEffect(() => {
    if (!isOpen) return;
    // Set initial type when opening
    if (initialType) {
      setCreateType(initialType);
    }
    (async () => {
      try {
        setLoading(true);
        const res = await fetch('/api/self-service/bootstrap');
        const data = await res.json();
        if (data?.defaults) {
          setCatalog(prev => prev || data.defaults.catalog || '');
          setSchema(prev => prev || data.defaults.schema || '');
        }
      } catch (e) {
        // ignore
      } finally {
        setLoading(false);
      }
    })();
  }, [isOpen]);

  // Columns are managed inline via SchemaPropertyEditor

  const canSubmit = useMemo(() => {
    if (createType === 'catalog') return !!catalog;
    if (createType === 'schema') return !!catalog && !!schema;
    return !!catalog && !!schema && !!tableName;
  }, [createType, catalog, schema, tableName]);

  const handleSubmit = async () => {
    try {
      setLoading(true);
      setError(null);
      setSuccess(null);
      const payload: any = {
        type: createType,
        catalog,
        schema,
        autoFix,
        createContract,
        defaultToUserCatalog: true,
        projectId: currentProject?.id,
      };
      if (createType === 'table') {
        payload.table = { name: tableName, columns };
      }
      const res = await fetch('/api/self-service/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const txt = await res.text();
        throw new Error(txt || `HTTP ${res.status}`);
      }
      const data = await res.json();
      setSuccess(data);
    } catch (e: any) {
      setError(e?.message || 'Failed to create');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle>Self-service data curation</DialogTitle>
        </DialogHeader>

        <div className="grid gap-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <Label>What to create</Label>
              <Select value={createType} onValueChange={(v) => setCreateType(v as CreateType)}>
                <SelectTrigger className="w-full"><SelectValue placeholder="Select type" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="catalog">Catalog</SelectItem>
                  <SelectItem value="schema">Schema</SelectItem>
                  <SelectItem value="table">Table</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Catalog</Label>
              <Input value={catalog} onChange={(e) => setCatalog(e.target.value)} placeholder="e.g. user_jdoe" />
            </div>
            <div>
              <Label>Schema</Label>
              <Input value={schema} onChange={(e) => setSchema(e.target.value)} placeholder="e.g. sandbox" />
            </div>
          </div>

          {createType === 'table' && (
            <Card>
              <CardHeader>
                <CardTitle>Table definition</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <Label>Table name</Label>
                    <Input value={tableName} onChange={(e) => setTableName(e.target.value)} placeholder="e.g. clicks" />
                  </div>
                </div>
                <div className="mt-4">
                  <SchemaPropertyEditor properties={columns} onChange={setColumns} />
                </div>
              </CardContent>
            </Card>
          )}

          <div className="flex gap-2 items-center">
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={autoFix} onChange={(e) => setAutoFix(e.target.checked)} />
              Auto-fix required tags
            </label>
            {createType === 'table' && (
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={createContract} onChange={(e) => setCreateContract(e.target.checked)} />
                Create as Data Contract
              </label>
            )}
          </div>

          {error && (
            <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>
          )}
          {success && (
            <Alert><AlertDescription>Created: {JSON.stringify(success.created)}{success.contractId ? `, contract ${success.contractId}` : ''}</AlertDescription></Alert>
          )}

          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => onOpenChange(false)}>Close</Button>
            <Button onClick={handleSubmit} disabled={!canSubmit || loading}>
              {loading ? (<span className="flex items-center gap-2"><Loader2 className="h-4 w-4 animate-spin" /> Working…</span>) : 'Create'}
            </Button>
          </div>
        </div>

        {/* Columns are edited inline via SchemaPropertyEditor */}
      </DialogContent>
    </Dialog>
  );
}


