import { useEffect, useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useApi } from '@/hooks/use-api';

type ConceptItem = { value: string; label: string; type: 'class' };

interface Props {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  onSelect: (iri: string) => void;
}

export default function ConceptSelectDialog({ isOpen, onOpenChange, onSelect }: Props) {
  const { get } = useApi();
  const [q, setQ] = useState('');
  const [results, setResults] = useState<ConceptItem[]>([]);

  useEffect(() => {
    const run = async () => {
      const res = await get<ConceptItem[]>(`/api/semantic-models/concepts?q=${encodeURIComponent(q)}&limit=50`);
      setResults(res.data || []);
    };
    const t = setTimeout(run, 250);
    return () => clearTimeout(t);
  }, [q]);

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl w-[90vw]">
        <DialogHeader>
          <DialogTitle>Select Business Concept</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <Input placeholder="Search business concepts..." value={q} onChange={(e) => setQ(e.target.value)} />
          <div className="space-y-2 max-h-80 overflow-auto">
            {results.map(r => (
              <div key={r.value} className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2 min-w-0 flex-1">
                  <Badge variant="secondary" className="shrink-0">class</Badge>
                  <div className="min-w-0 flex-1">
                    <div className="text-sm font-semibold truncate" title={r.label}>
                      {r.label}
                    </div>
                    <div className="text-xs text-muted-foreground font-mono break-all" title={r.value}>
                      {r.value}
                    </div>
                  </div>
                </div>
                <Button size="sm" variant="outline" className="shrink-0" onClick={() => onSelect(r.value)}>Select</Button>
              </div>
            ))}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}