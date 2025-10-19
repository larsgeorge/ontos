import { useEffect, useMemo, useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Loader2, Database, BoxSelect, Star, AlertCircle, Info } from 'lucide-react';
import { Link } from 'react-router-dom';
import EntityInfoDialog from '@/components/metadata/entity-info-dialog';
import { useDomains } from '@/hooks/use-domains';
import { type DataProduct } from '@/types/data-product';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { DataDomain } from '@/types/data-domain';
import { DataDomainMiniGraph } from '@/components/data-domains/data-domain-mini-graph';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';

interface DiscoverySectionProps {
  maxItems?: number;
}

export default function DiscoverySection({ maxItems = 12 }: DiscoverySectionProps) {
  const { t } = useTranslation('home');
  const { domains, loading: domainsLoading, getDomainName } = useDomains();
  const [selectedDomainId, setSelectedDomainId] = useState<string | null>(null);
  const [selectedDomainDetails, setSelectedDomainDetails] = useState<DataDomain | null>(null);
  const [domainLoading, setDomainLoading] = useState<boolean>(false);
  const [domainError, setDomainError] = useState<string | null>(null);
  const [exactMatchesOnly, setExactMatchesOnly] = useState<boolean>(false);
  const [matchesLoading, setMatchesLoading] = useState<boolean>(false);
  const [matchSets, setMatchSets] = useState<{ ids: Set<string>; namesLower: Set<string> } | null>(null);
  const [graphFadeIn, setGraphFadeIn] = useState<boolean>(false);
  const [allProducts, setAllProducts] = useState<DataProduct[]>([]);
  const [productsLoading, setProductsLoading] = useState<boolean>(false);
  const [productsError, setProductsError] = useState<string | null>(null);
  const [infoProductId, setInfoProductId] = useState<string | null>(null);
  const [infoProductTitle, setInfoProductTitle] = useState<string | undefined>(undefined);

  useEffect(() => {
    const loadProducts = async () => {
      try {
        setProductsLoading(true);
        // Fetch only published (ACTIVE) products for marketplace discovery
        const resp = await fetch('/api/data-products/published');
        if (!resp.ok) throw new Error(`HTTP error! status: ${resp.status}`);
        const data = await resp.json();
        setAllProducts(Array.isArray(data) ? data : []);
        setProductsError(null);
      } catch (e: any) {
        setProductsError(e.message || t('discoverySection.error'));
        setAllProducts([]);
      } finally {
        setProductsLoading(false);
      }
    };
    loadProducts();
  }, []);

  // Choose a sensible default domain (prefer a domain named "Core")
  useEffect(() => {
    if (!domainsLoading && domains && domains.length > 0 && !selectedDomainId) {
      const core = domains.find(d => d.name.toLowerCase() === 'core');
      if (core) {
        setSelectedDomainId(core.id);
      }
    }
  }, [domainsLoading, domains, selectedDomainId]);

  const loadDomainDetails = useCallback(async (domainId: string) => {
    try {
      setDomainLoading(true);
      setDomainError(null);
      const resp = await fetch(`/api/data-domains/${domainId}`);
      if (!resp.ok) throw new Error(`HTTP error! status: ${resp.status}`);
      const data: DataDomain = await resp.json();
      setSelectedDomainDetails(data);
    } catch (e: any) {
      setDomainError(e.message || t('discoverySection.error'));
      setSelectedDomainDetails(null);
    } finally {
      setDomainLoading(false);
    }
  }, [t]);

  // Load selected domain details whenever selection changes
  useEffect(() => {
    if (selectedDomainId) {
      loadDomainDetails(selectedDomainId);
    } else {
      setSelectedDomainDetails(null);
    }
  }, [selectedDomainId, loadDomainDetails]);

  // Subtle fade-in of the graph when switching domains
  useEffect(() => {
    // Trigger fade on domain change
    setGraphFadeIn(false);
    const raf = requestAnimationFrame(() => setGraphFadeIn(true));
    return () => cancelAnimationFrame(raf);
  }, [selectedDomainDetails?.id]);

  // Build match sets depending on exact/children selection
  useEffect(() => {
    const buildSets = async () => {
      if (!selectedDomainId) { setMatchSets(null); return; }
      const selected = domains.find(d => d.id === selectedDomainId);
      if (exactMatchesOnly) {
        const ids = new Set<string>([String(selectedDomainId)]);
        const namesLower = new Set<string>();
        if (selected?.name) namesLower.add(selected.name.toLowerCase());
        setMatchSets({ ids, namesLower });
        return;
      }
      setMatchesLoading(true);
      try {
        const ids = new Set<string>();
        const namesLower = new Set<string>();
        const enqueue = (id?: string | null, name?: string | null) => {
          if (id) ids.add(String(id));
          if (name) namesLower.add(String(name).toLowerCase());
        };

        // Start from the selected domain and walk all descendants via API
        try {
          const rootResp = await fetch(`/api/data-domains/${selectedDomainId}`);
          if (rootResp.ok) {
            const root: DataDomain = await rootResp.json();
            enqueue(root.id, root.name);
            const queue: { id: string; name?: string | null }[] = [...(root.children_info || []).map(c => ({ id: c.id, name: c.name }))];
            while (queue.length > 0) {
              const { id, name } = queue.shift()!;
              enqueue(id, name);
              try {
                const resp = await fetch(`/api/data-domains/${id}`);
                if (resp.ok) {
                  const data: DataDomain = await resp.json();
                  (data.children_info || []).forEach(ch => queue.push({ id: ch.id, name: ch.name }));
                }
              } catch { /* ignore child fetch errors */ }
            }
          }
        } catch { /* ignore root fetch errors; fallback to just selected id */
          enqueue(String(selectedDomainId), selected?.name || null);
        }

        setMatchSets({ ids, namesLower });
      } finally {
        setMatchesLoading(false);
      }
    };
    buildSets();
  }, [selectedDomainId, exactMatchesOnly, domains]);

  const filteredProducts = useMemo(() => {
    if (!selectedDomainId) return allProducts;
    if (!matchSets) return [];
    return allProducts.filter(p => {
      const productDomainRaw = p?.info?.domain;
      const productDomainIdLike = productDomainRaw != null ? String(productDomainRaw) : '';
      const productDomainLower = productDomainIdLike.toLowerCase();
      if (!productDomainLower) return false;
      if (matchSets.ids.has(productDomainIdLike)) return true; // match by id
      if (matchSets.namesLower.has(productDomainLower)) return true;
      return false;
    });
  }, [allProducts, selectedDomainId, matchSets]);

  return (
    <section className="mb-16">
      <h2 className="text-2xl font-semibold mb-4">{t('discoverySection.title')}</h2>

      <div className="mb-6">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2"><BoxSelect className="h-5 w-5" /><span className="font-medium">{t('discoverySection.dataDomains')}</span></div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">{t('discoverySection.exactMatchOnly')}</span>
              <Switch checked={exactMatchesOnly} onCheckedChange={(v) => setExactMatchesOnly(!!v)} />
            </div>
            {selectedDomainId && (
              <Button variant="outline" size="sm" onClick={() => setSelectedDomainId(null)} title={t('discoverySection.clearFilter')}>
                {t('discoverySection.allDomains')}
              </Button>
            )}
          </div>
        </div>

        {domainsLoading || domainLoading ? (
          <div style={{ height: 220, margin: 'auto' }} className="border rounded-lg overflow-hidden bg-muted/20 w-full flex items-center justify-center">
            <Loader2 className="h-6 w-6 animate-spin" />
          </div>
        ) : domainError ? (
          <div style={{ height: 220, margin: 'auto' }} className="border rounded-lg overflow-hidden bg-muted/20 w-full flex items-center justify-center">
            <Alert variant="destructive" className="m-0 border-0 bg-transparent">
              <AlertDescription>{domainError}</AlertDescription>
            </Alert>
          </div>
        ) : selectedDomainDetails ? (
          <div className={`transition-opacity duration-300 ${graphFadeIn ? 'opacity-100' : 'opacity-0'}`}>
            <DataDomainMiniGraph
              currentDomain={selectedDomainDetails}
              onNodeClick={(id) => setSelectedDomainId(id)}
            />
          </div>
        ) : (
          <div style={{ height: 220, margin: 'auto' }} className="border rounded-lg overflow-hidden bg-muted/20 w-full flex items-center justify-center text-muted-foreground">
            {t('discoverySection.selectDomain')}
          </div>
        )}
      </div>

      <div>
        <div className="flex items-center gap-2 mb-3"><Star className="h-5 w-5 text-primary" /><span className="font-medium">{t('discoverySection.popularProducts')}</span></div>
        {productsLoading || matchesLoading ? (
          <div className="flex items-center justify-center h-32"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>
        ) : productsError ? (
          <Alert variant="destructive" className="mb-4"><AlertCircle className="h-4 w-4" /><AlertDescription>{productsError}</AlertDescription></Alert>
        ) : filteredProducts.length === 0 ? (
          <p className="text-center text-muted-foreground">{t('discoverySection.noProducts')}</p>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {filteredProducts
              .slice()
              .sort((a, b) => new Date(b.updated_at || '').getTime() - new Date(a.updated_at || '').getTime())
              .slice(0, maxItems)
              .map(p => {
                const rawDomain = (p?.info?.domain as any);
                const domainStr = rawDomain != null ? String(rawDomain) : '';
                const resolvedById = getDomainName(domainStr);
                const resolvedByName = !resolvedById && domainStr
                  ? (domains.find(d => d.name.toLowerCase() === domainStr.toLowerCase())?.name || null)
                  : null;
                const domainLabel = resolvedById || resolvedByName || (domainStr || null);
                return (
                  <div key={p.id || p.info.title} className="group">
                    <Card className="transition-shadow group-hover:shadow-md h-full">
                      <CardHeader>
                        <div className="flex items-center gap-2">
                          <Database className="h-5 w-5 text-primary" />
                          <CardTitle className="truncate flex-1">
                            <Link to={p.id ? `/data-products/${p.id}` : '/data-products'} className="hover:underline">
                              {p.info?.title || t('discoverySection.untitled')}
                            </Link>
                          </CardTitle>
                          <button
                            className="inline-flex items-center justify-center text-foreground/80 hover:text-foreground transition-colors"
                            title={t('discoverySection.info')}
                            aria-label={t('discoverySection.info')}
                            onClick={() => { if (p.id) { setInfoProductId(p.id); setInfoProductTitle(p.info?.title); } }}
                          >
                            <Info className="h-4 w-4" />
                          </button>
                        </div>
                        {p.info?.description ? (
                          <CardDescription className="line-clamp-2">{p.info.description}</CardDescription>
                        ) : null}
                      </CardHeader>
                      <CardContent>
                        <div className="text-xs text-muted-foreground mb-1 truncate" title={domainLabel || undefined}>
                          {t('discoverySection.domain')}: {domainLabel || t('discoverySection.unknown')}
                        </div>
                        <div className="flex justify-between text-xs text-muted-foreground">
                          <span className="truncate max-w-[60%]">{t('discoverySection.owner')}: {p.info?.owner || t('discoverySection.unknown')}</span>
                          <span>{p.info?.status || t('discoverySection.status')}</span>
                        </div>
                      </CardContent>
                    </Card>
                  </div>
                );
              })}
          </div>
        )}
      </div>
      <EntityInfoDialog
        entityType={'data_product'}
        entityId={infoProductId}
        title={infoProductTitle}
        open={!!infoProductId}
        onOpenChange={(open) => { if (!open) { setInfoProductId(null); setInfoProductTitle(undefined); } }}
      />
    </section>
  );
}


