import { useEffect, useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import SearchBar from '@/components/ui/search-bar';
import { Card, CardContent, CardTitle, CardHeader, CardDescription } from '@/components/ui/card';
import { Loader2, Database, TrendingUp, FileText as FileTextIcon, Network, Scale, Globe, AlertCircle } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { UnityCatalogLogo } from '@/components/unity-catalog-logo';
// import { Button } from '@/components/ui/button';
import { FeatureMaturity } from '@/config/features';
import { useFeatureVisibilityStore } from '@/stores/feature-visibility-store';
// import { cn } from '@/lib/utils';
import { usePermissions } from '@/stores/permissions-store';
import { FeatureAccessLevel, HomeSection } from '@/types/settings';
import { Alert, AlertDescription } from "@/components/ui/alert";
import DiscoverySection from '@/components/home/discovery-section';
import DataCurationSection from '@/components/home/data-curation-section';
import RequiredActionsSection from '@/components/home/required-actions-section';
import QuickActions from '@/components/home/quick-actions';
import RecentActivity from '@/components/home/recent-activity';
import { useUserStore } from '@/stores/user-store';

interface Stats {
  dataContracts: { count: number; loading: boolean; error: string | null };
  dataProducts: { count: number; loading: boolean; error: string | null };
  ontologies: {
    count: {
      models: number;  // database-sourced semantic models
      totalTerms: number;  // total concepts + properties
    };
    loading: boolean;
    error: string | null
  };
  personas: { count: number; loading: boolean; error: string | null };
  estates: {
    count: number;
    loading: boolean;
    error: string | null;
    lastSync: string | null;
    syncStatus: 'success' | 'failed' | 'in_progress' | 'unknown' | null;
  };
}

interface ComplianceData {
  date: string;
  compliance: number;
}

// Quick actions and recent activity are rendered via components

export default function Home() {
  const { t, i18n } = useTranslation(['home', 'common']);
  const [stats, setStats] = useState<Stats>({
    dataContracts: { count: 0, loading: true, error: null },
    dataProducts: { count: 0, loading: true, error: null },
    ontologies: { count: { models: 0, totalTerms: 0 }, loading: true, error: null },
    personas: { count: 0, loading: true, error: null },
    estates: {
      count: 0,
      loading: true,
      error: null,
      lastSync: null,
      syncStatus: null
    },
  });
  const [complianceData, setComplianceData] = useState<ComplianceData[]>([]);
  const [complianceLoading, setComplianceLoading] = useState(true);
  const [complianceError, setComplianceError] = useState<string | null>(null);
  const allowedMaturities = useFeatureVisibilityStore((state) => state.allowedMaturities);
  const { permissions, isLoading: permissionsLoading, hasPermission } = usePermissions();

  useEffect(() => {
    fetch('/api/data-products')
      .then(response => {
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        return response.json();
        })
      .then(data => {
        setStats(prev => ({
          ...prev,
          dataProducts: { count: Array.isArray(data) ? data.length : 0, loading: false, error: null }
        }));
      })
      .catch(error => {
        console.error('Error fetching data products:', error);
        setStats(prev => ({
          ...prev,
          dataProducts: { count: 0, loading: false, error: error.message }
        }));
      });

    fetch('/api/data-contracts')
       .then(response => {
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        return response.json();
        })
      .then(data => {
        setStats(prev => ({
          ...prev,
          dataContracts: { count: Array.isArray(data) ? data.length : 0, loading: false, error: null }
        }));
      })
      .catch(error => {
        console.error('Error fetching data contracts:', error);
        setStats(prev => ({
          ...prev,
          dataContracts: { count: 0, loading: false, error: error.message }
        }));
      });

    fetch('/api/semantic-models/stats')
       .then(response => {
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        return response.json();
        })
      .then(data => {
        // Count all loaded semantic models
        const modelsCount = data?.stats?.taxonomies?.length || 0;

        // Calculate total terms (concepts + properties)
        const totalTerms = (data?.stats?.total_concepts || 0) + (data?.stats?.total_properties || 0);

        setStats(prev => ({
          ...prev,
          ontologies: {
            count: {
              models: modelsCount,
              totalTerms: totalTerms
            },
            loading: false,
            error: null
          }
        }));
      })
      .catch(error => {
        console.error('Error fetching ontologies:', error);
        setStats(prev => ({
          ...prev,
          ontologies: {
            count: { models: 0, totalTerms: 0 },
            loading: false,
            error: error.message
          }
        }));
      });

    fetch('/api/entitlements/personas')
      .then(response => {
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        return response.json();
        })
      .then(data => {
        setStats(prev => ({
          ...prev,
          personas: { count: Array.isArray(data) ? data.length : 0, loading: false, error: null }
        }));
      })
      .catch(error => {
        console.error('Error fetching personas:', error);
        setStats(prev => ({
          ...prev,
          personas: { count: 0, loading: false, error: error.message }
        }));
      });

    fetch('/api/estates')
       .then(response => {
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        return response.json();
        })
      .then(data => {
        const estatesArray = Array.isArray(data) ? data : [];
        const lastSync = estatesArray.length > 0 && estatesArray.some(e => e.last_sync)
          ? new Date(Math.max(...estatesArray.filter(e => e.last_sync).map((estate: any) => new Date(estate.last_sync).getTime())))
          : null;

        let syncStatus: Stats['estates']['syncStatus'] = null;
        if (estatesArray.length > 0) {
            if (estatesArray.some((estate: any) => estate.sync_status === 'in_progress')) {
                syncStatus = 'in_progress';
            } else if (estatesArray.some((estate: any) => estate.sync_status === 'failed')) {
                syncStatus = 'failed';
            } else if (estatesArray.every((estate: any) => estate.sync_status === 'success')) {
                syncStatus = 'success';
            } else {
                syncStatus = 'unknown';
            }
        }


        setStats(prev => ({
          ...prev,
          estates: {
            count: estatesArray.length,
            loading: false,
            error: null,
            lastSync: lastSync?.toLocaleDateString() || null,
            syncStatus
          }
        }));
      })
      .catch(error => {
        console.error('Error fetching estates:', error);
        setStats(prev => ({
          ...prev,
          estates: {
            count: 0,
            loading: false,
            error: error.message,
            lastSync: null,
            syncStatus: null
          }
        }));
      });

    fetch('/api/compliance/trend')
       .then(response => {
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        return response.json();
        })
      .then(data => {
        setComplianceData(Array.isArray(data) ? data : []);
        setComplianceLoading(false);
      })
      .catch(error => {
        console.error('Error fetching compliance trend:', error);
        setComplianceError(error.message);
        setComplianceLoading(false);
      });
  }, []);

  const baseSummaryTiles = useMemo(() => [
    {
      id: 'compliance',
      title: t('home:overview.tiles.compliance.title'),
      value: complianceData.length > 0 ? `${complianceData[complianceData.length - 1].compliance}%` : t('home:overview.tiles.compliance.notAvailable'),
      loading: complianceLoading,
      error: complianceError,
      link: '/compliance',
      icon: <Scale className="h-4 w-4" />,
      description: t('home:overview.tiles.compliance.description'),
      maturity: 'ga',
    },
    {
      id: 'data-contracts',
      title: t('home:overview.tiles.dataContracts.title'),
      value: stats.dataContracts.count,
      loading: stats.dataContracts.loading,
      error: stats.dataContracts.error,
      link: '/data-contracts',
      icon: <FileTextIcon className="h-4 w-4" />,
      description: t('home:overview.tiles.dataContracts.description'),
      maturity: 'ga',
    },
    {
      id: 'data-products',
      title: t('home:overview.tiles.dataProducts.title'),
      value: stats.dataProducts.count,
      loading: stats.dataProducts.loading,
      error: stats.dataProducts.error,
      link: '/data-products',
      icon: <Database className="h-4 w-4" />,
      description: t('home:overview.tiles.dataProducts.description'),
      maturity: 'ga',
    },
    {
      id: 'semantic-models',
      title: t('home:overview.tiles.semanticModels.title'),
      value: `${stats.ontologies.count.models} / ${stats.ontologies.count.totalTerms}`,
      loading: stats.ontologies.loading,
      error: stats.ontologies.error,
      link: '/semantic-models',
      icon: <Network className="h-4 w-4" />,
      description: t('home:overview.tiles.semanticModels.description'),
       maturity: 'ga',
    },
    {
      id: 'estate-manager',
      title: t('home:overview.tiles.estates.title'),
      value: stats.estates.count,
      loading: stats.estates.loading,
      error: stats.estates.error,
      link: '/estate-manager',
      icon: <Globe className="h-4 w-4" />,
      description: stats.estates.lastSync
        ? t('home:overview.tiles.estates.lastSync', {
            date: stats.estates.lastSync,
            status: t(`home:overview.tiles.estates.syncStatus.${stats.estates.syncStatus || 'unknown'}`)
          })
        : t('home:overview.tiles.estates.description'),
      maturity: 'ga',
    },
  ], [t, complianceData, complianceLoading, complianceError, stats]);

  const filteredSummaryTiles = useMemo(() => {
      if (permissionsLoading) return [];
      return baseSummaryTiles.filter(tile =>
          allowedMaturities.includes(tile.maturity as FeatureMaturity) &&
          hasPermission(tile.id, FeatureAccessLevel.READ_ONLY)
      );
  }, [baseSummaryTiles, allowedMaturities, permissionsLoading, hasPermission]);

  // const summaryTiles = baseSummaryTiles.filter(tile => allowedMaturities.includes(tile.maturity as FeatureMaturity));
  const isComplianceVisible = filteredSummaryTiles.some(tile => tile.id === 'compliance');

  // Check if user has any permissions at all (besides NONE)
  const hasAnyAccess = useMemo(() => {
      if (permissionsLoading || !permissions) return false;
      return Object.values(permissions).some(level => level !== FeatureAccessLevel.NONE);
  }, [permissions, permissionsLoading]);

  // Determine configured home sections from applied role (if any)
  const { availableRoles, appliedRoleId } = usePermissions();
  const { userInfo } = useUserStore();
  const userGroups = (userInfo as any)?.groups || [];

  // Determine configured sections:
  // - If a role override is applied, use that role's sections.
  // - Otherwise, union sections from all roles assigned to user's groups.
  const configuredSections: HomeSection[] = useMemo(() => {
    // Applied override
    if (appliedRoleId) {
      const r = availableRoles.find(role => role.id === appliedRoleId);
      return (r?.home_sections || []) as HomeSection[];
    }
    // Union across matched roles
    if (Array.isArray(userGroups) && userGroups.length > 0) {
      const groupSet = new Set<string>(userGroups as string[]);
      const matched = availableRoles.filter(r => Array.isArray(r.assigned_groups) && r.assigned_groups.some(g => groupSet.has(g)));
      const union = new Set<HomeSection>();
      matched.forEach(r => (r.home_sections || []).forEach(s => union.add(s as HomeSection)));
      // Normalize order
      const order: HomeSection[] = [HomeSection.REQUIRED_ACTIONS, HomeSection.DATA_CURATION, HomeSection.DISCOVERY];
      const result = order.filter(s => union.has(s));
      return result.length > 0 ? result : [HomeSection.DISCOVERY];
    }
    return [];
  }, [availableRoles, appliedRoleId, userGroups]);

  // Fallback: If no sections configured on the role, default to Discovery only
  const defaultSections: HomeSection[] = [HomeSection.DISCOVERY];

  const orderedSections = configuredSections.length > 0 ? configuredSections : defaultSections;

  // Note: sections themselves handle fine-grained permission visibility internally

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="max-w-2xl mx-auto text-center mb-8">
        <div className="flex items-center justify-center mb-4">
          <UnityCatalogLogo className="h-16 w-16" />
          <h1 className="text-4xl font-bold ml-2">
            {t('home:title')}
          </h1>
        </div>
        <p className="text-lg text-muted-foreground mb-6">
          {t('home:tagline')}
        </p>
        <div className="mb-8">
          <SearchBar
            variant="large"
            placeholder={t('home:search.placeholder')}
          />
        </div>
      </div>

      <div className="mb-8">
        <h2 className="text-2xl font-semibold mb-4">{t('home:overview.title')}</h2>
         {permissionsLoading ? (
              <div className="flex justify-center items-center h-24 col-span-full">
                 <Loader2 className="h-8 w-8 animate-spin text-primary" />
              </div>
         ) : filteredSummaryTiles.length > 0 ? (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
            {filteredSummaryTiles.map((tile) => (
                <Link key={tile.title} to={tile.link} className="block group">
                <Card className="transition-colors h-full group-hover:bg-accent/50">
                    <CardContent className="p-6 flex flex-col justify-between h-full">
                    <div>
                        <div className="flex items-center justify-between">
                        <CardTitle className="text-sm font-medium">
                            {tile.title}
                        </CardTitle>
                        <div className="h-4 w-4 text-muted-foreground">
                            {tile.icon}
                        </div>
                        </div>
                        {tile.loading ? (
                        <div className="flex justify-center items-center h-16">
                            <Loader2 className="h-6 w-6 animate-spin text-primary" />
                        </div>
                        ) : tile.error ? (
                        <div className="text-center text-destructive mt-2">
                            {t('home:overview.error')}
                        </div>
                        ) : (
                        <div className="text-2xl font-bold mt-2">{tile.value}</div>
                        )}
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                        {tile.description}
                    </p>
                    </CardContent>
                </Card>
                </Link>
            ))}
            </div>
        ) : (
             <p className="text-muted-foreground text-center col-span-full">
                 {t('home:overview.noData')}
             </p>
         )}
      </div>

      {isComplianceVisible && (
          <div className="mb-8">
            <Card>
            <CardHeader>
                <div className="flex items-center space-x-4">
                    <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                        <TrendingUp className="h-6 w-6 text-primary" />
                    </div>
                    <div>
                        <CardTitle>{t('home:complianceTrend.title')}</CardTitle>
                        <CardDescription>{t('home:complianceTrend.period')}</CardDescription>
                    </div>
                </div>
            </CardHeader>
            <CardContent className="p-6 pt-0">
                <div className="h-[200px]">
                {complianceLoading ? (
                    <div className="flex items-center justify-center h-full">
                    <Loader2 className="h-8 w-8 animate-spin text-primary" />
                    </div>
                ) : complianceError ? (
                    <div className="flex items-center justify-center h-full text-destructive">
                    {t('home:complianceTrend.error', { error: complianceError })}
                    </div>
                ) : complianceData.length === 0 ? (
                    <div className="flex items-center justify-center h-full text-muted-foreground">
                        {t('home:complianceTrend.noData')}
                    </div>
                ) : (
                    <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={complianceData} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} />
                        <XAxis
                        dataKey="date"
                        tickFormatter={(date) => new Date(date).toLocaleDateString(i18n.language, { month: 'short', day: 'numeric' })}
                        axisLine={false}
                        tickLine={false}
                        style={{ fontSize: '0.75rem' }}
                        />
                        <YAxis
                        domain={[0, 100]}
                        tickFormatter={(value) => `${value}%`}
                        axisLine={false}
                        tickLine={false}
                        style={{ fontSize: '0.75rem' }}
                        width={50}
                        />
                        <Tooltip
                            contentStyle={{ fontSize: '0.875rem', borderRadius: '0.5rem', boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)' }}
                            labelFormatter={(label) => new Date(label).toLocaleDateString(i18n.language, { year: 'numeric', month: 'long', day: 'numeric' })}
                            formatter={(value: number) => [`${value}%`, t('home:complianceTrend.chartLabel')]}
                        />
                        <Line
                            type="monotone"
                            dataKey="compliance"
                            stroke="hsl(var(--primary))"
                            strokeWidth={2}
                            dot={false}
                            activeDot={{ r: 6, fill: 'hsl(var(--primary))' }}
                        />
                    </LineChart>
                    </ResponsiveContainer>
                )}
                </div>
            </CardContent>
            </Card>
         </div>
       )}

      {/* Message for users with no access */}
      {!permissionsLoading && !hasAnyAccess && (
          <Alert variant="default" className="mb-8 bg-blue-50 border-blue-200 text-blue-800">
            <AlertCircle className="h-4 w-4 !text-blue-600" /> {/* Use ! to force color */}
            <AlertDescription className="ml-2">
                 {t('home:noAccess.message')} {t('home:noAccess.action')} <Link to="/settings?tab=roles" className="font-semibold underline hover:text-blue-900">{t('home:noAccess.link')}</Link>.
            </AlertDescription>
          </Alert>
      )}

      {/* Role-based main sections - respect role configuration order */}
      {orderedSections.map(section => (
        section === HomeSection.REQUIRED_ACTIONS ? (
          <RequiredActionsSection key={section} />
        ) : section === HomeSection.DATA_CURATION ? (
          <DataCurationSection key={section} />
        ) : (
          <DiscoverySection key={section} />
        )
      ))}

      <section className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <QuickActions />
        <RecentActivity />
      </section>
    </div>
  );
}