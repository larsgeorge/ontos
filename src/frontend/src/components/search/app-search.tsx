import { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Input } from '@/components/ui/input';

type AppSearchResult = {
  id: string;
  type: 'data-product' | 'data-contract' | 'glossary-term' | 'persona';
  title: string;
  description: string;
  link: string;
};

interface AppSearchProps {
  initialQuery?: string;
}

export default function AppSearch({ initialQuery = '' }: AppSearchProps) {
  const navigate = useNavigate();
  const location = useLocation();

  const [appQuery, setAppQuery] = useState(initialQuery);
  const [appResults, setAppResults] = useState<AppSearchResult[]>([]);
  const [appLoading, setAppLoading] = useState(false);

  // Update URL when state changes
  const updateUrl = (query: string) => {
    const params = new URLSearchParams(location.search);
    if (query) {
      params.set('app_query', query);
    } else {
      params.delete('app_query');
    }
    const newUrl = `${location.pathname}?${params.toString()}`;
    navigate(newUrl, { replace: true });
  };

  // Load initial state from URL
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const urlQuery = params.get('app_query');
    if (urlQuery && urlQuery !== initialQuery) {
      setAppQuery(urlQuery);
    }
  }, [location.search]);

  // Perform search
  useEffect(() => {
    const run = async () => {
      const q = appQuery.trim();
      if (!q) {
        setAppResults([]);
        updateUrl('');
        return;
      }
      setAppLoading(true);
      try {
        const resp = await fetch(`/api/search?search_term=${encodeURIComponent(q)}`);
        const data = resp.ok ? await resp.json() : [];
        setAppResults(Array.isArray(data) ? data : []);
        updateUrl(q);
      } catch {
        setAppResults([]);
      } finally {
        setAppLoading(false);
      }
    };
    const t = setTimeout(run, 300);
    return () => clearTimeout(t);
  }, [appQuery]);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Application Search</CardTitle>
        <CardDescription className="text-xs">Type to search. Results appear below.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="relative">
          <Input
            value={appQuery}
            onChange={(e) => setAppQuery(e.target.value)}
            placeholder="Search for data products, terms, contracts..."
            className="h-9 text-sm"
          />
        </div>
        <div className="space-y-2 text-sm">
          {appLoading ? (
            <div className="text-xs text-muted-foreground">Loading...</div>
          ) : appResults.length === 0 ? (
            <div className="text-xs text-muted-foreground">No results</div>
          ) : (
            appResults.map(r => (
              <a key={r.id} href={r.link} className="block p-2 rounded hover:bg-accent">
                <div className="text-sm font-medium">{r.title}</div>
                <div className="text-xs text-muted-foreground">{r.description}</div>
              </a>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  );
}