import { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { useApi } from '@/hooks/use-api';
import { HoverCard, HoverCardContent, HoverCardTrigger } from '@/components/ui/hover-card';

type KGItem = { value: string; type: 'resource' | 'property' };
type Neighbor = {
  direction: 'outgoing' | 'incoming' | 'predicate';
  predicate: string;
  display: string;
  displayType: 'resource' | 'property' | 'literal';
  stepIri?: string | null;
  stepIsResource?: boolean;
};

type DirectionFilter = 'all' | 'incoming' | 'outgoing';

interface KGSearchProps {
  initialPrefix?: string;
  initialPath?: string[];
  initialSparql?: string;
  initialDirectionFilter?: DirectionFilter;
  initialShowConceptsOnly?: boolean;
}

// Helper component for app entity hover
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

// Helper function to parse app entities
const parseAppEntity = (iri: string): { entityType: 'data_product' | 'data_domain' | 'data_contract'; entityId: string } | null => {
  const m = iri.match(/^urn:ontos:(data_product|data_domain|data_contract):(.+)$/);
  if (!m) return null;
  return { entityType: m[1] as any, entityId: m[2] };
};

export default function KGSearch({
  initialPrefix = '',
  initialPath = [],
  initialSparql = 'SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10',
  initialDirectionFilter = 'all',
  initialShowConceptsOnly = false
}: KGSearchProps) {
  const { get, post } = useApi();
  const navigate = useNavigate();
  const location = useLocation();

  const [prefix, setPrefix] = useState(initialPrefix);
  const [prefixResults, setPrefixResults] = useState<KGItem[]>([]);
  const [path, setPath] = useState<string[]>(initialPath);
  const [neighbors, setNeighbors] = useState<Neighbor[]>([]);
  const [sparql, setSparql] = useState(initialSparql);
  const [sparqlRows, setSparqlRows] = useState<any[]>([]);

  // New filter states
  const [directionFilter, setDirectionFilter] = useState<DirectionFilter>(initialDirectionFilter);
  const [showConceptsOnly, setShowConceptsOnly] = useState(initialShowConceptsOnly);

  // Update URL when state changes
  const updateUrl = (updates: Partial<{
    prefix: string;
    path: string[];
    sparql: string;
    directionFilter: DirectionFilter;
    showConceptsOnly: boolean;
  }>) => {
    const params = new URLSearchParams(location.search);

    if (updates.prefix !== undefined) {
      if (updates.prefix) {
        params.set('kg_prefix', updates.prefix);
      } else {
        params.delete('kg_prefix');
      }
    }

    if (updates.path !== undefined) {
      if (updates.path.length > 0) {
        params.set('kg_path', updates.path.join('|'));
      } else {
        params.delete('kg_path');
      }
    }

    if (updates.sparql !== undefined && updates.sparql !== 'SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10') {
      params.set('kg_sparql', updates.sparql);
    } else if (updates.sparql !== undefined) {
      params.delete('kg_sparql');
    }

    if (updates.directionFilter !== undefined && updates.directionFilter !== 'all') {
      params.set('kg_direction', updates.directionFilter);
    } else if (updates.directionFilter !== undefined) {
      params.delete('kg_direction');
    }

    if (updates.showConceptsOnly !== undefined && updates.showConceptsOnly) {
      params.set('kg_concepts_only', 'true');
    } else if (updates.showConceptsOnly !== undefined) {
      params.delete('kg_concepts_only');
    }

    const newUrl = `${location.pathname}?${params.toString()}`;
    navigate(newUrl, { replace: true });
  };

  // Load initial state from URL
  useEffect(() => {
    const params = new URLSearchParams(location.search);

    const urlPrefix = params.get('kg_prefix');
    const urlPath = params.get('kg_path');
    const urlSparql = params.get('kg_sparql');
    const urlDirection = params.get('kg_direction') as DirectionFilter;
    const urlConceptsOnly = params.get('kg_concepts_only') === 'true';

    if (urlPrefix && urlPrefix !== initialPrefix) setPrefix(urlPrefix);
    if (urlPath) {
      const pathArray = urlPath.split('|').filter(Boolean);
      if (pathArray.length > 0 && JSON.stringify(pathArray) !== JSON.stringify(initialPath)) {
        setPath(pathArray);
      }
    }
    if (urlSparql && urlSparql !== initialSparql) setSparql(urlSparql);
    if (urlDirection && urlDirection !== initialDirectionFilter) setDirectionFilter(urlDirection);
    if (urlConceptsOnly !== initialShowConceptsOnly) setShowConceptsOnly(urlConceptsOnly);
  }, [location.search]);

  // Load neighbors when path changes
  useEffect(() => {
    const loadNeighbors = async () => {
      if (path.length > 0) {
        const currentIri = path[path.length - 1];
        try {
          const res = await get<Neighbor[]>(`/api/semantic-models/neighbors?iri=${encodeURIComponent(currentIri)}&limit=200`);
          setNeighbors(res.data || []);
        } catch (e) {
          console.error('Failed to load neighbors:', e);
          setNeighbors([]);
        }
      } else {
        setNeighbors([]);
      }
    };
    loadNeighbors();
  }, [path]);

  // Prefix search
  useEffect(() => {
    const run = async () => {
      if (!prefix.trim()) {
        setPrefixResults([]);
        updateUrl({ prefix: '' });
        return;
      }
      const res = await get<KGItem[]>(`/api/semantic-models/prefix?q=${encodeURIComponent(prefix)}&limit=25`);
      setPrefixResults(res.data || []);
      updateUrl({ prefix });
    };
    const t = setTimeout(run, 250);
    return () => clearTimeout(t);
  }, [prefix]);

  const selectStart = async (iri: string) => {
    const newPath = [iri];
    setPath(newPath);
    updateUrl({ path: newPath });
  };

  const stepTo = async (iri: string) => {
    const newPath = [...path, iri];
    setPath(newPath);
    updateUrl({ path: newPath });
  };

  const jumpTo = async (index: number) => {
    const newPath = path.slice(0, index + 1);
    setPath(newPath);
    updateUrl({ path: newPath });
  };

  const runSparql = async () => {
    const res = await post<any[]>(`/api/semantic-models/query`, { sparql });
    setSparqlRows(res.data || []);
    updateUrl({ sparql });
  };

  // Filter neighbors based on current filters
  const filteredNeighbors = neighbors.filter(neighbor => {
    // Direction filter
    if (directionFilter === 'incoming' && neighbor.direction !== 'incoming') return false;
    if (directionFilter === 'outgoing' && neighbor.direction !== 'outgoing') return false;

    // Concepts/Classes only filter
    if (showConceptsOnly) {
      // Show only resources that are likely concepts/classes
      const isConceptOrClass = neighbor.displayType === 'resource' &&
        (neighbor.predicate.includes('type') ||
         neighbor.predicate.includes('subClassOf') ||
         neighbor.predicate.includes('Class') ||
         neighbor.display.includes('Class') ||
         neighbor.display.includes('concept'));
      if (!isConceptOrClass) return false;
    }

    return true;
  });

  const handleDirectionFilterChange = (value: DirectionFilter) => {
    setDirectionFilter(value);
    updateUrl({ directionFilter: value });
  };

  const handleConceptsOnlyToggle = (checked: boolean) => {
    setShowConceptsOnly(checked);
    updateUrl({ showConceptsOnly: checked });
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Prefix Search</CardTitle>
          <CardDescription className="text-xs">Find resources or properties by IRI substring.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <Input
            value={prefix}
            placeholder="e.g., example.org/banking"
            onChange={(e) => setPrefix(e.target.value)}
          />
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

          {/* Filter Controls */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-4 bg-muted/30 rounded-lg border">
            <div className="flex flex-col space-y-2">
              <Label htmlFor="direction-filter" className="text-sm font-medium">Direction Filter</Label>
              <Select value={directionFilter} onValueChange={handleDirectionFilterChange}>
                <SelectTrigger className="w-full h-9">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Everything</SelectItem>
                  <SelectItem value="incoming">Incoming Only</SelectItem>
                  <SelectItem value="outgoing">Outgoing Only</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex flex-col space-y-2">
              <Label className="text-sm font-medium">Content Filter</Label>
              <div className="flex items-center space-x-3 h-9">
                <Switch
                  id="concepts-only"
                  checked={showConceptsOnly}
                  onCheckedChange={handleConceptsOnlyToggle}
                />
                <Label htmlFor="concepts-only" className="text-sm cursor-pointer">
                  Show concepts/classes only
                </Label>
              </div>
            </div>
          </div>

          <Separator />

          <div className="space-y-2 text-sm">
            {filteredNeighbors.length === 0 ? (
              <div className="text-sm text-muted-foreground">
                {neighbors.length === 0
                  ? "No outgoing links for current selection."
                  : "No links match the current filters."}
              </div>
            ) : filteredNeighbors.map((n, i) => (
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

      {/* SPARQL Query Section - Full Width */}
      <Card className="lg:col-span-2">
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
                <DropdownMenuItem onClick={() => setSparql('SELECT ?resource WHERE { ?resource ?p ?o . FILTER(REGEX(STR(?resource), "^urn:ontos")) }')}>Resources in app namespace</DropdownMenuItem>
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
    </div>
  );
}