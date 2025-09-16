import { useEffect, useMemo, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Loader2, Database, BoxSelect, Star, AlertCircle, Info } from 'lucide-react';
import { Link } from 'react-router-dom';
import EntityInfoDialog from '@/components/metadata/entity-info-dialog';
import { useDomains } from '@/hooks/use-domains';
import { type DataProduct } from '@/types/data-product';
import { Alert, AlertDescription } from '@/components/ui/alert';

interface DiscoverySectionProps {
  maxItems?: number;
}

export default function DiscoverySection({ maxItems = 12 }: DiscoverySectionProps) {
  const { domains, loading: domainsLoading } = useDomains();
  const [selectedDomainId, setSelectedDomainId] = useState<string | null>(null);
  const [allProducts, setAllProducts] = useState<DataProduct[]>([]);
  const [productsLoading, setProductsLoading] = useState<boolean>(false);
  const [productsError, setProductsError] = useState<string | null>(null);
  const [infoProductId, setInfoProductId] = useState<string | null>(null);
  const [infoProductTitle, setInfoProductTitle] = useState<string | undefined>(undefined);

  useEffect(() => {
    const loadProducts = async () => {
      try {
        setProductsLoading(true);
        const resp = await fetch('/api/data-products');
        if (!resp.ok) throw new Error(`HTTP error! status: ${resp.status}`);
        const data = await resp.json();
        setAllProducts(Array.isArray(data) ? data : []);
        setProductsError(null);
      } catch (e: any) {
        setProductsError(e.message || 'Failed to load data products');
        setAllProducts([]);
      } finally {
        setProductsLoading(false);
      }
    };
    loadProducts();
  }, []);

  const filteredProducts = useMemo(() => {
    if (!selectedDomainId) return allProducts;
    const selected = domains.find(d => d.id === selectedDomainId);
    const selectedName = selected?.name?.toLowerCase();
    const selectedId = selected?.id;
    return allProducts.filter(p => {
      const pd = (p?.info?.domain || '').toString().toLowerCase();
      if (!pd) return false;
      // Match by stored domain id OR by domain name (case-insensitive)
      if (selectedId && p?.info?.domain === selectedId) return true;
      if (selectedName && pd === selectedName) return true;
      return false;
    });
  }, [allProducts, selectedDomainId, domains]);

  return (
    <section className="mb-16">
      <h2 className="text-2xl font-semibold mb-4">Discovery</h2>

      <div className="mb-6">
        <div className="flex items-center gap-2 mb-3"><BoxSelect className="h-5 w-5" /><span className="font-medium">Data Domains</span></div>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <button
            className={`text-left px-3 py-2 border rounded-md hover:bg-accent/50 ${!selectedDomainId ? 'border-primary' : 'border-muted'}`}
            onClick={() => setSelectedDomainId(null)}
          >All Domains</button>
          {domainsLoading ? (
            <div className="col-span-full flex items-center justify-center py-6"><Loader2 className="h-5 w-5 animate-spin" /></div>
          ) : domains.map(d => (
            <button
              key={d.id}
              className={`text-left px-3 py-2 border rounded-md hover:bg-accent/50 truncate ${selectedDomainId === d.id ? 'border-primary' : 'border-muted'}`}
              onClick={() => setSelectedDomainId(selectedDomainId === d.id ? null : d.id)}
              title={d.name}
            >{d.name}</button>
          ))}
        </div>
      </div>

      <div>
        <div className="flex items-center gap-2 mb-3"><Star className="h-5 w-5 text-primary" /><span className="font-medium">Popular Data Products</span></div>
        {productsLoading ? (
          <div className="flex items-center justify-center h-32"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>
        ) : productsError ? (
          <Alert variant="destructive" className="mb-4"><AlertCircle className="h-4 w-4" /><AlertDescription>{productsError}</AlertDescription></Alert>
        ) : filteredProducts.length === 0 ? (
          <p className="text-center text-muted-foreground">No data products found.</p>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {filteredProducts
              .slice()
              .sort((a, b) => new Date(b.updated_at || '').getTime() - new Date(a.updated_at || '').getTime())
              .slice(0, maxItems)
              .map(p => (
                <div key={p.id || p.info.title} className="group">
                  <Card className="transition-shadow group-hover:shadow-md h-full">
                    <CardHeader>
                      <div className="flex items-center gap-2">
                        <Database className="h-5 w-5 text-primary" />
                        <CardTitle className="truncate flex-1">
                          <Link to={p.id ? `/data-products/${p.id}` : '/data-products'} className="hover:underline">
                            {p.info?.title || 'Untitled'}
                          </Link>
                        </CardTitle>
                        <button
                          className="inline-flex items-center justify-center text-foreground/80 hover:text-foreground transition-colors"
                          title="Info"
                          aria-label="Info"
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
                      <div className="flex justify-between text-xs text-muted-foreground">
                        <span>{p.info?.owner || 'Unknown owner'}</span>
                        <span>{p.info?.status || 'N/A'}</span>
                      </div>
                    </CardContent>
                  </Card>
                </div>
            ))}
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


