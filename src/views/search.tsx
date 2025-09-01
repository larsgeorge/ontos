import { useEffect, useMemo, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import { useApi } from '@/hooks/use-api';
import { Search as SearchIcon } from 'lucide-react';
import { HoverCard, HoverCardContent, HoverCardTrigger } from '@/components/ui/hover-card';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import useBreadcrumbStore from '@/stores/breadcrumb-store';

type KGItem = { value: string; type: 'resource' | 'property' };
type Neighbor = {
  direction: 'outgoing' | 'incoming' | 'predicate';
  predicate: string;
  display: string;
  displayType: 'resource' | 'property' | 'literal';
  stepIri?: string | null;
  stepIsResource?: boolean;
};

type AppSearchResult = {
  id: string;
  type: 'data-product' | 'data-contract' | 'glossary-term' | 'persona';
  title: string;
  description: string;
  link: string;
};

export default function SearchView() {
  const { get, post } = useApi();
  const [mode, setMode] = useState<'app' | 'kg' | 'llm'>('app');
  const location = useLocation();
  const setStaticSegments = useBreadcrumbStore((state) => state.setStaticSegments);
  const setDynamicTitle = useBreadcrumbStore((state) => state.setDynamicTitle);

  useEffect(() => {
    setStaticSegments([]);
    setDynamicTitle('Search');
    return () => {
      setStaticSegments([]);
      setDynamicTitle(null);
    };
  }, [setStaticSegments, setDynamicTitle]);

  // --- App Search (inline results) ---
  const [appQuery, setAppQuery] = useState('');
  const [appResults, setAppResults] = useState<AppSearchResult[]>([]);
  const [appLoading, setAppLoading] = useState(false);
  useEffect(() => {
    const run = async () => {
      const q = appQuery.trim();
      if (!q) { setAppResults([]); return; }
      setAppLoading(true);
      try {
        const resp = await fetch(`/api/search?search_term=${encodeURIComponent(q)}`);
        const data = resp.ok ? await resp.json() : [];
        setAppResults(Array.isArray(data) ? data : []);
      } catch {
        setAppResults([]);
      } finally {
        setAppLoading(false);
      }
    };
    const t = setTimeout(run, 300);
    return () => clearTimeout(t);
  }, [appQuery]);

  // --- KG Search ---
  const [prefix, setPrefix] = useState('');
  const [prefixResults, setPrefixResults] = useState<KGItem[]>([]);
  const [path, setPath] = useState<string[]>([]); // breadcrumb of selected IRIs
  const [neighbors, setNeighbors] = useState<Neighbor[]>([]);
  const [sparql, setSparql] = useState('SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10');
  const [sparqlRows, setSparqlRows] = useState<any[]>([]);

  useEffect(() => {
    const run = async () => {
      if (!prefix.trim()) { setPrefixResults([]); return; }
      const res = await get<KGItem[]>(`/api/semantic-models/prefix?q=${encodeURIComponent(prefix)}&limit=25`);
      setPrefixResults(res.data || []);
    };
    const t = setTimeout(run, 250);
    return () => clearTimeout(t);
  }, [prefix]);

  const selectStart = async (iri: string) => {
    setPath([iri]);
    const res = await get<Neighbor[]>(`/api/semantic-models/neighbors?iri=${encodeURIComponent(iri)}&limit=200`);
    setNeighbors(res.data || []);
  };

  const stepTo = async (iri: string) => {
    const newPath = [...path, iri];
    setPath(newPath);
    const res = await get<Neighbor[]>(`/api/semantic-models/neighbors?iri=${encodeURIComponent(iri)}&limit=200`);
    setNeighbors(res.data || []);
  };

  const jumpTo = async (index: number) => {
    const newPath = path.slice(0, index + 1);
    setPath(newPath);
    const iri = newPath[newPath.length - 1];
    const res = await get<Neighbor[]>(`/api/semantic-models/neighbors?iri=${encodeURIComponent(iri)}&limit=200`);
    setNeighbors(res.data || []);
  };

  const runSparql = async () => {
    const res = await post<any[]>(`/api/semantic-models/query`, { sparql });
    setSparqlRows(res.data || []);
  };

  // Start on a specific IRI via query param
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const iri = params.get('startIri');
    if (iri) {
      setMode('kg');
      selectStart(iri);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.search]);

  // Helper: detect ucapp entities
  const parseAppEntity = (iri: string): { entityType: 'data_product' | 'data_domain' | 'data_contract'; entityId: string } | null => {
    const m = iri.match(/^urn:ucapp:(data_product|data_domain|data_contract):(.+)$/);
    if (!m) return null;
    return { entityType: m[1] as any, entityId: m[2] };
  };

  const AppEntityHover: React.FC<{ iri: string; children: React.ReactNode }> = ({ iri, children }) => {
    const info = parseAppEntity(iri);
    const [details, setDetails] = useState<any>(null);
    const [open, setOpen] = useState(false);
    useEffect(() => {
      if (!open || !info) return;
      const load = async () => {
        try {
          const url = info.entityType === 'data_product'
            ? `/api/data-products/${info.entityId}`
            : info.entityType === 'data_domain'
            ? `/api/data-domains/${info.entityId}`
            : `/api/data-contracts/${info.entityId}`;
          const resp = await fetch(url);
          if (resp.ok) setDetails(await resp.json());
        } catch { /* ignore */ }
      };
      load();
    }, [open, iri]);
    if (!info) return <>{children}</>;
    return (
      <HoverCard openDelay={200} onOpenChange={setOpen}>
        <HoverCardTrigger asChild>{children as any}</HoverCardTrigger>
        <HoverCardContent className="w-96 text-xs">
          {!details ? (
            <div className="text-muted-foreground">Loading...</div>
          ) : (
            <div className="space-y-1">
              <div className="font-medium text-sm">{details.info?.title || details.name || info.entityId}</div>
              <div className="text-muted-foreground">Type: {info.entityType.replace('_', ' ')}</div>
              <div className="text-muted-foreground">
                <div className="truncate">ID: {info.entityId}</div>
                {details.info?.owner && <div className="truncate">Owner: {details.info.owner}</div>}
                {details.info?.status && <div className="truncate">Status: {details.info.status}</div>}
              </div>
              {details.info?.description && (
                <div className="text-muted-foreground break-words max-h-24 overflow-auto">{details.info.description}</div>
              )}
              <Button size="sm" variant="outline" className="h-7 px-2 mt-1"
                onClick={() => {
                  const path = info.entityType === 'data_product'
                    ? `/data-products/${info.entityId}`
                    : info.entityType === 'data_domain'
                    ? `/data-domains/${info.entityId}`
                    : `/data-contracts/${info.entityId}`;
                  window.location.href = path;
                }}>Open</Button>
            </div>
          )}
        </HoverCardContent>
      </HoverCard>
    );
  };

  return (
    <div className="py-4 space-y-4">
      <h1 className="text-3xl font-bold mb-4 flex items-center gap-2">
        <SearchIcon className="w-8 h-8" />
        Search
      </h1>
      <Tabs value={mode} onValueChange={(v) => setMode(v as any)}>
        <TabsList>
          <TabsTrigger value="app">App Search</TabsTrigger>
          <TabsTrigger value="kg">Knowledge Graph</TabsTrigger>
          <TabsTrigger value="llm">LLM (coming soon)</TabsTrigger>
        </TabsList>

        <TabsContent value="app">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Application Search</CardTitle>
              <CardDescription className="text-xs">Type to search. Results appear below.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="relative">
                <Input value={appQuery} onChange={(e) => setAppQuery(e.target.value)} placeholder="Search for data products, terms, contracts..." className="h-9 text-sm" />
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
        </TabsContent>

        <TabsContent value="kg">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Prefix Search</CardTitle>
                <CardDescription className="text-xs">Find resources or properties by IRI substring.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <Input value={prefix} placeholder="e.g., example.org/banking" onChange={(e) => setPrefix(e.target.value)} />
                <div className="space-y-2">
                  {prefixResults.map((r) => (
                    <div key={r.value} className="flex items-center justify-between">
                      <div className="truncate mr-2">
                        <Badge variant="secondary">{r.type}</Badge>{' '}
                        <AppEntityHover iri={r.value}>
                          <span className="hover:underline cursor-pointer" title={r.value}>{r.value}</span>
                        </AppEntityHover>
                      </div>
                      <Button size="sm" variant="outline" onClick={() => selectStart(r.value)}>Start path</Button>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Path Explorer</CardTitle>
                <CardDescription className="text-xs">Click objects to extend the path horizontally.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex flex-wrap gap-2 text-sm">
                  {path.map((iri, idx) => (
                    <Button key={idx} variant="outline" size="sm" onClick={() => jumpTo(idx)} title={iri}>
                      {iri}
                    </Button>
                  ))}
                </div>
                <Separator />
                <div className="space-y-2 text-sm">
                  {neighbors.length === 0 ? (
                    <div className="text-sm text-muted-foreground">No outgoing links for current selection.</div>
                  ) : neighbors.map((n, i) => (
                    <div key={i} className="flex items-center justify-between">
                      <div className="truncate mr-2">
                        <div className="text-[10px] text-muted-foreground uppercase">{n.direction}</div>
                        <div className="text-xs text-muted-foreground">{n.predicate}</div>
                        <div className="truncate">
                          {parseAppEntity(n.display) ? (
                            <AppEntityHover iri={n.display}>
                              <span className="hover:underline cursor-pointer">{n.display}</span>
                            </AppEntityHover>
                          ) : (
                            <span title={n.display}>{n.display}</span>
                          )}
                          <span className="ml-2 text-[10px] px-1 py-0.5 rounded bg-muted text-muted-foreground uppercase">
                            {n.displayType}
                          </span>
                        </div>
                      </div>
                      {n.stepIsResource && n.stepIri ? (
                        <Button variant="ghost" size="sm" onClick={() => stepTo(n.stepIri)}>Step</Button>
                      ) : null}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>

          <Card className="mt-4">
            <CardHeader>
              <div className="flex items-center justify-between gap-2">
                <div>
                  <CardTitle>SPARQL</CardTitle>
                  <CardDescription>Run advanced queries over the loaded graph.</CardDescription>
                </div>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="outline" size="sm">Examples</Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-[420px] max-w-[80vw]">
                    <DropdownMenuItem onClick={() => setSparql('SELECT ?resource WHERE { ?resource ?p ?o . FILTER(REGEX(STR(?resource), "^urn:ucapp")) }')}>Resources in app namespace</DropdownMenuItem>
                    <DropdownMenuItem onClick={() => setSparql('SELECT ?s ?label WHERE { ?s <http://www.w3.org/2000/01/rdf-schema#label> ?label } LIMIT 50')}>Resources with rdfs:label</DropdownMenuItem>
                    <DropdownMenuItem onClick={() => setSparql('SELECT ?s ?type WHERE { ?s a ?type } LIMIT 100')}>Subjects and their types</DropdownMenuItem>
                    <DropdownMenuItem onClick={() => setSparql('SELECT ?p (COUNT(*) AS ?count) WHERE { ?s ?p ?o } GROUP BY ?p ORDER BY DESC(?count) LIMIT 25')}>Top predicates by frequency</DropdownMenuItem>
                    <DropdownMenuItem onClick={() => setSparql('SELECT ?o (COUNT(*) AS ?count) WHERE { ?s <http://www.w3.org/2000/01/rdf-schema#seeAlso> ?o } GROUP BY ?o ORDER BY DESC(?count) LIMIT 25')}>Most linked via rdfs:seeAlso</DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              <Input value={sparql} onChange={(e) => setSparql(e.target.value)} />
              <Button onClick={runSparql}>Run SPARQL</Button>
              <div className="space-y-1 text-sm">
                {sparqlRows.map((row, idx) => (
                  <pre key={idx} className="bg-muted p-2 rounded-md overflow-auto whitespace-pre-wrap">{JSON.stringify(row, null, 2)}</pre>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="llm">
          <Card>
            <CardHeader>
              <CardTitle>LLM-Assisted Search (Coming Soon)</CardTitle>
              <CardDescription>Ask questions in natural language to explore the graph.</CardDescription>
            </CardHeader>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}


