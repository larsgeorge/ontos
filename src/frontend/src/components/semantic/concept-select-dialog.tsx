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
  parentConceptIri?: string;
}

export default function ConceptSelectDialog({ isOpen, onOpenChange, onSelect, parentConceptIri }: Props) {
  const { get } = useApi();
  const [q, setQ] = useState('');
  const [suggested, setSuggested] = useState<ConceptItem[]>([]);
  const [other, setOther] = useState<ConceptItem[]>([]);

  useEffect(() => {
    const run = async () => {
      const params = new URLSearchParams({
        q: q,
        limit: '50'
      });
      
      if (parentConceptIri) {
        params.set('parent_iri', parentConceptIri);
        const res = await get<{suggested: ConceptItem[], other: ConceptItem[]}>(`/api/semantic-models/concepts/suggestions?${params}`);
        setSuggested(res.data?.suggested || []);
        setOther(res.data?.other || []);
      } else {
        const res = await get<ConceptItem[]>(`/api/semantic-models/concepts?${params}`);
        setSuggested([]);
        setOther(res.data || []);
      }
    };
    const t = setTimeout(run, 250);
    return () => clearTimeout(t);
  }, [q, parentConceptIri]);

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl w-[90vw]">
        <DialogHeader>
          <DialogTitle>Select Business Concept</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <Input placeholder="Search business concepts..." value={q} onChange={(e) => setQ(e.target.value)} />
          <div className="space-y-4 max-h-80 overflow-auto">
            {suggested.length > 0 && (
              <div className="space-y-2">
                <div className="text-sm font-medium text-muted-foreground border-b pb-1">
                  Suggested (child concepts)
                </div>
                {suggested.map(r => (
                  <div key={r.value} className="flex items-center justify-between gap-3 bg-blue-50 p-2 rounded-lg">
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
                    <Button size="sm" variant="default" className="shrink-0" onClick={() => onSelect(r.value)}>Select</Button>
                  </div>
                ))}
              </div>
            )}
            {other.length > 0 && (
              <div className="space-y-2">
                {suggested.length > 0 && (
                  <div className="text-sm font-medium text-muted-foreground border-b pb-1">
                    Other concepts
                  </div>
                )}
                {other.map(r => (
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
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}