import { useEffect, useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useApi } from '@/hooks/use-api';

type KGItem = { value: string; type: 'resource' | 'property' };

interface Props {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  onPick: (iri: string) => void;
}

export default function IriPickerDialog({ isOpen, onOpenChange, onPick }: Props) {
  const { get } = useApi();
  const [q, setQ] = useState('');
  const [results, setResults] = useState<KGItem[]>([]);

  useEffect(() => {
    const run = async () => {
      if (!q.trim()) { setResults([]); return; }
      const res = await get<KGItem[]>(`/api/semantic-models/prefix?q=${encodeURIComponent(q)}&limit=25`);
      setResults(res.data || []);
    };
    const t = setTimeout(run, 250);
    return () => clearTimeout(t);
  }, [q]);

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Pick an RDF IRI</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <Input placeholder="Search IRI..." value={q} onChange={(e) => setQ(e.target.value)} />
          <div className="space-y-2 max-h-80 overflow-auto">
            {results.map(r => (
              <div key={r.value} className="flex items-center justify-between">
                <div className="truncate mr-2"><Badge variant="secondary">{r.type}</Badge> <span title={r.value}>{r.value}</span></div>
                <Button size="sm" variant="outline" onClick={() => onPick(r.value)}>Select</Button>
              </div>
            ))}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}


