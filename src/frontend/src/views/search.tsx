import { useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useApi } from '@/hooks/use-api';
import { useToast } from '@/hooks/use-toast';
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

type ConceptItem = { value: string; label: string; type: 'class' };

type SemanticLink = {
  id: string;
  entity_id: string;
  entity_type: string;
  iri: string;
};

type EnrichedSemanticLink = SemanticLink & {
  entity_name?: string;
};

export default function SearchView() {
  const { get, post } = useApi();
  const { toast } = useToast();
  const navigate = useNavigate();
  const [mode, setMode] = useState<'app' | 'kg' | 'concepts' | 'llm'>('app');
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

  // --- Concepts Tab State ---
  const [conceptSearchQuery, setConceptSearchQuery] = useState('');
  const [conceptSearchResults, setConceptSearchResults] = useState<ConceptItem[]>([]);
  const [isConceptDropdownOpen, setIsConceptDropdownOpen] = useState(false);
  const [selectedConcept, setSelectedConcept] = useState<ConceptItem | null>(null);
  const [conceptIri, setConceptIri] = useState('');
  const [conceptLabel, setConceptLabel] = useState('');
  const [conceptNeighbors, setConceptNeighbors] = useState<Neighbor[]>([]);
  const [semanticLinks, setSemanticLinks] = useState<EnrichedSemanticLink[]>([]);
  
  // Assign to Object dialog for concepts
  const [assignDialogOpen, setAssignDialogOpen] = useState(false);
  const [selectedEntityType, setSelectedEntityType] = useState<string>('');
  const [selectedEntityId, setSelectedEntityId] = useState<string>('');
  const [availableEntities, setAvailableEntities] = useState<any[]>([]);

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

  // --- Concepts Tab Functions ---
  
  // Search concepts as user types
  useEffect(() => {
    const searchConcepts = async () => {
      if (!conceptSearchQuery.trim()) {
        setConceptSearchResults([]);
        setIsConceptDropdownOpen(false);
        return;
      }
      
      try {
        const res = await get<ConceptItem[]>(`/api/semantic-models/concepts?q=${encodeURIComponent(conceptSearchQuery)}&limit=50`);
        setConceptSearchResults(res.data || []);
        setIsConceptDropdownOpen((res.data || []).length > 0);
      } catch (error) {
        console.error('Error searching concepts:', error);
        setConceptSearchResults([]);
        setIsConceptDropdownOpen(false);
      }
    };

    const timer = setTimeout(searchConcepts, 250);
    return () => clearTimeout(timer);
  }, [conceptSearchQuery, get]);

  // Select a concept and load its details
  const selectConcept = async (concept: ConceptItem) => {
    setSelectedConcept(concept);
    setConceptIri(concept.value);
    
    // Use label if available, otherwise extract last part of IRI
    let displayLabel = concept.label;
    if (!displayLabel || displayLabel.trim() === concept.value) {
      // Extract the last segment after # or /
      if (concept.value.includes('#')) {
        displayLabel = concept.value.split('#').pop() || concept.value;
      } else if (concept.value.includes('/')) {
        displayLabel = concept.value.split('/').pop() || concept.value;
      } else {
        displayLabel = concept.value;
      }
    }
    
    setConceptLabel(displayLabel);
    setConceptSearchQuery(`${displayLabel} - ${concept.value}`);
    setIsConceptDropdownOpen(false);

    // Load neighbors for this concept
    try {
      const res = await get<Neighbor[]>(`/api/semantic-models/neighbors?iri=${encodeURIComponent(concept.value)}&limit=200`);
      setConceptNeighbors(res.data || []);
    } catch (error) {
      console.error('Error loading neighbors:', error);
      setConceptNeighbors([]);
    }

    // Load semantic links (catalog objects linked to this concept)
    try {
      const res = await get<SemanticLink[]>(`/api/semantic-links/iri/${encodeURIComponent(concept.value)}`);
      const links = res.data || [];
      
      // Enrich semantic links with entity names
      const enrichedLinks = await enrichSemanticLinksWithNames(links);
      setSemanticLinks(enrichedLinks);
    } catch (error) {
      console.error('Error loading semantic links:', error);
      setSemanticLinks([]);
    }
  };

  // Navigate to a related concept (parent/subclass)
  const navigateToConcept = async (iri: string) => {
    // Find concept details from neighbors or search
    const label = conceptNeighbors.find(n => n.stepIri === iri)?.display || iri.split('/').pop() || iri.split('#').pop() || iri;
    const conceptItem: ConceptItem = {
      value: iri,
      label: label,
      type: 'class'
    };
    await selectConcept(conceptItem);
  };

  // Get parent classes from neighbors
  const getParentClasses = () => {
    return conceptNeighbors.filter(n => 
      n.direction === 'outgoing' && 
      (n.predicate.includes('subClassOf') || n.predicate.includes('rdfs:subClassOf')) &&
      n.stepIsResource
    );
  };

  // Get subclasses from neighbors
  const getSubclasses = () => {
    return conceptNeighbors.filter(n => 
      n.direction === 'incoming' && 
      (n.predicate.includes('subClassOf') || n.predicate.includes('rdfs:subClassOf')) &&
      n.stepIsResource
    );
  };

  // Get related properties
  const getRelatedProperties = () => {
    return conceptNeighbors.filter(n => 
      n.displayType === 'property' || 
      n.predicate.includes('domain') || 
      n.predicate.includes('range')
    );
  };

  // Get linked catalog objects from semantic links
  const getCatalogObjects = () => {
    return semanticLinks;
  };

  // Enrich semantic links with readable entity names
  const enrichSemanticLinksWithNames = async (links: SemanticLink[]): Promise<EnrichedSemanticLink[]> => {
    const enrichedLinks: EnrichedSemanticLink[] = [];
    
    for (const link of links) {
      try {
        let entityName = link.entity_id; // fallback to ID
        let endpoint = '';
        
        // Determine the correct endpoint based on entity type
        switch (link.entity_type) {
          case 'data_product':
            endpoint = `/api/data-products/${link.entity_id}`;
            break;
          case 'data_contract':
            endpoint = `/api/data-contracts/${link.entity_id}`;
            break;
          case 'data_domain':
            endpoint = `/api/data-domains/${link.entity_id}`;
            break;
          default:
            enrichedLinks.push({ ...link, entity_name: link.entity_id });
            continue;
        }
        
        // Fetch entity details to get the name
        const entityRes = await get<any>(endpoint);
        if (entityRes.data && !entityRes.error) {
          // Different entities store names in different fields
          entityName = entityRes.data.name || entityRes.data.info?.title || entityRes.data.title || link.entity_id;
        }
        
        enrichedLinks.push({ ...link, entity_name: entityName });
      } catch (error) {
        console.error(`Error fetching details for ${link.entity_type}:${link.entity_id}`, error);
        enrichedLinks.push({ ...link, entity_name: link.entity_id });
      }
    }
    
    return enrichedLinks;
  };

  // Load entities for assignment
  const loadEntitiesForType = async (entityType: string) => {
    try {
      let endpoint = '';
      switch (entityType) {
        case 'data_product':
          endpoint = '/api/data-products';
          break;
        case 'data_contract':
          endpoint = '/api/data-contracts';
          break;
        case 'data_domain':
          endpoint = '/api/data-domains';
          break;
        default:
          return;
      }
      
      const res = await get<any[]>(endpoint);
      setAvailableEntities(res.data || []);
    } catch (error) {
      console.error('Error loading entities:', error);
      setAvailableEntities([]);
    }
  };

  // Handle entity type selection
  const handleEntityTypeChange = (entityType: string) => {
    setSelectedEntityType(entityType);
    setSelectedEntityId('');
    loadEntitiesForType(entityType);
  };

  // Navigate to entity detail page
  const navigateToEntity = (link: SemanticLink) => {
    let path = '';
    switch (link.entity_type) {
      case 'data_product':
        path = `/data-products/${link.entity_id}`;
        break;
      case 'data_contract':
        path = `/data-contracts/${link.entity_id}`;
        break;
      case 'data_domain':
        path = `/data-domains/${link.entity_id}`;
        break;
      default:
        toast({
          title: 'Navigation Error',
          description: `Cannot navigate to ${link.entity_type}`,
          variant: 'destructive'
        });
        return;
    }
    navigate(path);
  };

  // Create semantic link
  const handleAssignToObject = async () => {
    if (!selectedConcept || !selectedEntityType || !selectedEntityId) {
      toast({
        title: 'Error',
        description: 'Please select both an entity type and specific entity.',
        variant: 'destructive'
      });
      return;
    }

    try {
      const res = await post('/api/semantic-links/', {
        entity_id: selectedEntityId,
        entity_type: selectedEntityType,
        iri: selectedConcept.value,
      });

      if (res.error) {
        throw new Error(res.error);
      }

      toast({
        title: 'Linked Successfully',
        description: `Concept "${selectedConcept.label}" linked to ${selectedEntityType.replace('_', ' ')} "${selectedEntityId}".`,
      });

      setAssignDialogOpen(false);
      setSelectedEntityType('');
      setSelectedEntityId('');
      
      // Reload semantic links
      await selectConcept(selectedConcept);
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Failed to assign concept to object.',
        variant: 'destructive'
      });
    }
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
          <TabsTrigger value="concepts">Concepts</TabsTrigger>
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

        <TabsContent value="concepts">
          <div className="space-y-6">
            {/* Search Section */}
            <div className="space-y-2">
              <p className="text-sm text-muted-foreground">Search and select a concept:</p>
              <div className="relative">
                <Input
                  value={conceptSearchQuery}
                  onChange={(e) => setConceptSearchQuery(e.target.value)}
                  onFocus={() => setIsConceptDropdownOpen(conceptSearchResults.length > 0)}
                  placeholder="Type to search by name, label, or IRI..."
                  className="w-full"
                />
                
                {/* Search Results Dropdown */}
                {isConceptDropdownOpen && conceptSearchResults.length > 0 && (
                  <div className="absolute z-50 w-full mt-1 bg-popover border rounded-md shadow-md max-h-80 overflow-y-auto">
                    {conceptSearchResults.map((result) => (
                      <div
                        key={result.value}
                        className="px-3 py-2 text-popover-foreground hover:bg-accent hover:text-accent-foreground cursor-pointer border-b border-border last:border-b-0 transition-colors"
                        onClick={() => selectConcept(result)}
                      >
                        <div className="text-sm">{result.label} - {result.value}</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Selected Concept Details */}
            {selectedConcept && (
              <div className="space-y-4">
                {/* Concept Info - Show ALL assigned properties */}
                <Card>
                  <CardContent className="pt-4">
                    <div className="space-y-2">
                      <div>
                        <span className="text-sm font-medium text-muted-foreground">IRI: </span>
                        <span className="text-sm font-mono text-foreground">{conceptIri}</span>
                      </div>
                      {/* Show all properties assigned to this concept */}
                      {conceptNeighbors.filter(n => 
                        n.direction === 'outgoing' && 
                        n.displayType === 'literal' &&
                        !n.predicate.includes('subClassOf') &&
                        !n.predicate.includes('type')
                      ).map((prop, idx) => (
                        <div key={idx}>
                          <span className="text-sm font-medium text-muted-foreground">
                            {prop.predicate.split('/').pop()?.split('#').pop() || prop.predicate}: 
                          </span>
                          <span className="text-sm text-foreground ml-1">{prop.display}</span>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                {/* Three Column Layout */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                  {/* Concept Hierarchy */}
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg">Concept Hierarchy</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div>
                        <h3 className="text-sm font-medium text-muted-foreground mb-2">Parent Classes:</h3>
                        <div className="space-y-2">
                          {getParentClasses().length === 0 ? (
                            <p className="text-sm text-muted-foreground">No parent classes found</p>
                          ) : (
                            getParentClasses().map((parent, idx) => (
                              <Badge 
                                key={idx} 
                                variant="outline" 
                                className="cursor-pointer hover:bg-accent"
                                onClick={() => parent.stepIri && navigateToConcept(parent.stepIri)}
                              >
                                {parent.display.split('/').pop() || parent.display.split('#').pop() || parent.display}
                              </Badge>
                            ))
                          )}
                        </div>
                      </div>

                      <div>
                        <h3 className="text-sm font-medium text-muted-foreground mb-2">Subclasses:</h3>
                        <div className="flex flex-wrap gap-2">
                          {getSubclasses().length === 0 ? (
                            <p className="text-sm text-muted-foreground">No subclasses found</p>
                          ) : (
                            getSubclasses().map((sub, idx) => (
                              <Badge 
                                key={idx} 
                                variant="outline" 
                                className="cursor-pointer hover:bg-accent"
                                onClick={() => sub.stepIri && navigateToConcept(sub.stepIri)}
                              >
                                {sub.display.split('/').pop() || sub.display.split('#').pop() || sub.display}
                              </Badge>
                            ))
                          )}
                        </div>
                      </div>
                    </CardContent>
                  </Card>

                  {/* Related Properties */}
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg">Related Properties</CardTitle>
                    </CardHeader>
                    <CardContent>
                      {getRelatedProperties().length === 0 ? (
                        <p className="text-sm text-center text-muted-foreground">No related properties found.</p>
                      ) : (
                        <div className="flex flex-wrap gap-2">
                          {getRelatedProperties().map((prop, idx) => (
                            <Badge key={idx} variant="secondary" className="text-xs">
                              {prop.display.split('/').pop() || prop.display.split('#').pop() || prop.display}
                            </Badge>
                          ))}
                        </div>
                      )}
                    </CardContent>
                  </Card>

                  {/* Linked Catalog Objects */}
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg">Linked Catalog Objects</CardTitle>
                    </CardHeader>
                    <CardContent>
                      {getCatalogObjects().length === 0 ? (
                        <p className="text-sm text-center text-muted-foreground">No catalog objects assigned.</p>
                      ) : (
                        <div className="flex flex-wrap gap-2">
                          {getCatalogObjects().map((link) => (
                            <Badge 
                              key={link.id} 
                              variant="outline" 
                              className="text-xs cursor-pointer hover:bg-accent transition-colors"
                              onClick={() => navigateToEntity(link)}
                              title={`Click to view ${link.entity_type.replace('_', ' ')} details`}
                            >
                              {link.entity_type.replace('_', ' ')}: {link.entity_name || link.entity_id}
                            </Badge>
                          ))}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </div>

                {/* Assign to Object Button */}
                <div className="pt-4">
                  <Button 
                    variant="outline"
                    onClick={() => setAssignDialogOpen(true)}
                    disabled={!selectedConcept}
                  >
                    Assign to Object
                  </Button>
                </div>
              </div>
            )}
          </div>
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

      {/* Assign to Object Dialog for Concepts */}
      <Dialog open={assignDialogOpen} onOpenChange={setAssignDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Assign Concept to Object</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            {selectedConcept && (
              <div className="text-sm">
                <p className="font-medium">{selectedConcept.label}</p>
                <p className="text-muted-foreground font-mono text-xs">{selectedConcept.value}</p>
              </div>
            )}
            
            <div className="space-y-2">
              <label className="text-sm font-medium">Entity Type</label>
              <Select value={selectedEntityType} onValueChange={handleEntityTypeChange}>
                <SelectTrigger>
                  <SelectValue placeholder="Select entity type..." />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="data_product">Data Product</SelectItem>
                  <SelectItem value="data_contract">Data Contract</SelectItem>
                  <SelectItem value="data_domain">Data Domain</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {selectedEntityType && (
              <div className="space-y-2">
                <label className="text-sm font-medium">
                  {selectedEntityType.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                </label>
                <Select value={selectedEntityId} onValueChange={setSelectedEntityId}>
                  <SelectTrigger>
                    <SelectValue placeholder={`Select ${selectedEntityType.replace('_', ' ')}...`} />
                  </SelectTrigger>
                  <SelectContent>
                    {availableEntities.map((entity) => (
                      <SelectItem key={entity.id} value={entity.id}>
                        {entity.name || entity.info?.title || entity.id}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            <div className="flex justify-end space-x-2 pt-4">
              <Button variant="outline" onClick={() => setAssignDialogOpen(false)}>
                Cancel
              </Button>
              <Button 
                onClick={handleAssignToObject}
                disabled={!selectedEntityType || !selectedEntityId}
              >
                Assign
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}


