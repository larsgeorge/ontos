import { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { Card, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Search as SearchIcon } from 'lucide-react';
import useBreadcrumbStore from '@/stores/breadcrumb-store';
import AppSearch from '@/components/search/app-search';
import KGSearch from '@/components/search/kg-search';
import ConceptsSearch from '@/components/search/concepts-search';


export default function SearchView() {
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

  // Load initial state from URL parameters
  useEffect(() => {
    const params = new URLSearchParams(location.search);

    // Check for startIri param (legacy KG mode)
    const startIri = params.get('startIri');
    if (startIri) {
      setMode('kg');
    }

    // Check for concepts_iri or concepts_query param (concepts mode)
    const conceptsIri = params.get('concepts_iri');
    const conceptsQuery = params.get('concepts_query');
    if (conceptsIri || conceptsQuery) {
      setMode('concepts');
    }

    // Check for tab parameter to set initial mode (takes precedence)
    const tabParam = params.get('tab');
    if (tabParam && ['app', 'kg', 'concepts', 'llm'].includes(tabParam)) {
      setMode(tabParam as 'app' | 'kg' | 'concepts' | 'llm');
    }
  }, [location.search]);

  // Update URL when mode changes
  const handleModeChange = (newMode: 'app' | 'kg' | 'concepts' | 'llm') => {
    setMode(newMode);
    const params = new URLSearchParams(location.search);
    params.set('tab', newMode);
    const newUrl = `${location.pathname}?${params.toString()}`;
    window.history.replaceState(null, '', newUrl);
  };

  // Extract URL parameters for component initialization
  const params = new URLSearchParams(location.search);
  const appQuery = params.get('app_query') || '';
  const kgPrefix = params.get('kg_prefix') || '';
  const kgPath = params.get('kg_path')?.split('|').filter(Boolean) || [];
  const kgSparql = params.get('kg_sparql') || 'SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10';
  const kgDirection = params.get('kg_direction') as 'all' | 'incoming' | 'outgoing' || 'all';
  const kgConceptsOnly = params.get('kg_concepts_only') === 'true';
  const conceptsQuery = params.get('concepts_query') || '';
  const conceptsIri = params.get('concepts_iri');

  // Handle legacy startIri parameter - if present, add it to the KG path
  const startIri = params.get('startIri');
  const finalKgPath = startIri && kgPath.length === 0 ? [startIri] : kgPath;

  // Create initial concept for concepts search
  const initialConcept = conceptsIri ? {
    value: conceptsIri,
    label: conceptsIri.split('/').pop() || conceptsIri.split('#').pop() || conceptsIri,
    type: 'class' as const
  } : null;

  return (
    <div className="py-4 space-y-4">
      <h1 className="text-3xl font-bold mb-4 flex items-center gap-2">
        <SearchIcon className="w-8 h-8" />
        Search
      </h1>
      <Tabs value={mode} onValueChange={(v) => handleModeChange(v as 'app' | 'kg' | 'concepts' | 'llm')}>
        <TabsList>
          <TabsTrigger value="app">App Search</TabsTrigger>
          <TabsTrigger value="kg">Knowledge Graph</TabsTrigger>
          <TabsTrigger value="concepts">Concepts</TabsTrigger>
          <TabsTrigger value="llm">LLM (coming soon)</TabsTrigger>
        </TabsList>

        <TabsContent value="app">
          <AppSearch initialQuery={appQuery} />
        </TabsContent>

        <TabsContent value="kg">
          <KGSearch
            initialPrefix={kgPrefix}
            initialPath={finalKgPath}
            initialSparql={kgSparql}
            initialDirectionFilter={kgDirection}
            initialShowConceptsOnly={kgConceptsOnly}
          />
        </TabsContent>

        <TabsContent value="concepts">
          <ConceptsSearch
            initialQuery={conceptsQuery}
            initialSelectedConcept={initialConcept}
          />
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


