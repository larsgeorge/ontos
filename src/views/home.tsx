import { useEffect, useState, useMemo } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import SearchBar from '@/components/ui/search-bar';
import { Card, CardContent, CardTitle, CardHeader, CardDescription } from '@/components/ui/card';
import { Loader2, Database, Book, GitCompare, Shield, Gavel, FolderKanban, Settings, Info, TrendingUp, FileText as FileTextIcon, BookOpen, ArrowLeftRight, Scale, Globe, ArrowRight, BookOpenCheck, UserPlus, AlertCircle } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { UnityCatalogLogo } from '@/components/unity-catalog-logo';
import { Button } from '@/components/ui/button';
import { getLandingPageFeatures, FeatureConfig, FeatureMaturity } from '@/config/features';
import React from 'react';
import { useFeatureVisibilityStore } from '@/stores/feature-visibility-store';
import { cn } from '@/lib/utils';
import { usePermissions } from '@/stores/permissions-store';
import { FeatureAccessLevel } from '@/types/settings';
import { Alert, AlertDescription } from "@/components/ui/alert";

interface Stats {
  dataContracts: { count: number; loading: boolean; error: string | null };
  dataProducts: { count: number; loading: boolean; error: string | null };
  glossaries: { count: { glossaries: number; terms: number }; loading: boolean; error: string | null };
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

interface QuickAction {
    name: string;
    path: string;
}

interface RecentActivity {
    item: string;
    time: string;
}

const quickActions: QuickAction[] = [
  { name: 'Create Data Product', path: '/data-products/new' },
  { name: 'Define Data Contract', path: '/data-contracts/new' },
  { name: 'Add Glossary Term', path: '/business-glossary/new' },
  { name: 'Request Role Access', path: '/settings?tab=roles' },
];

const recentActivity: RecentActivity[] = [
  { item: 'Data Product "Customer Profiles" updated', time: '2 hours ago' },
  { item: 'Data Contract "Sales Data Quality" approved', time: '1 day ago' },
  { item: 'Glossary Term "KPI" defined', time: '3 days ago' },
];

export default function Home() {
  const [stats, setStats] = useState<Stats>({
    dataContracts: { count: 0, loading: true, error: null },
    dataProducts: { count: 0, loading: true, error: null },
    glossaries: { count: { glossaries: 0, terms: 0 }, loading: true, error: null },
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
  const navigate = useNavigate();

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

    fetch('/api/business-glossaries/counts')
       .then(response => {
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        return response.json();
        })
      .then(data => {
        setStats(prev => ({
          ...prev,
          glossaries: {
            count: {
              glossaries: data?.glossaries || 0,
              terms: data?.terms || 0
            },
            loading: false,
            error: null
          }
        }));
      })
      .catch(error => {
        console.error('Error fetching glossaries:', error);
        setStats(prev => ({
          ...prev,
          glossaries: {
            count: { glossaries: 0, terms: 0 },
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

  const baseSummaryTiles = [
    {
      id: 'compliance',
      title: 'Compliance',
      value: complianceData.length > 0 ? `${complianceData[complianceData.length - 1].compliance}%` : 'N/A',
      loading: complianceLoading,
      error: complianceError,
      link: '/compliance',
      icon: <Scale className="h-4 w-4" />,
      description: 'Current compliance score',
      maturity: 'ga',
    },
    {
      id: 'data-products',
      title: 'Data Products',
      value: stats.dataProducts.count,
      loading: stats.dataProducts.loading,
      error: stats.dataProducts.error,
      link: '/data-products',
      icon: <Database className="h-4 w-4" />,
      description: 'Total data products',
      maturity: 'ga',
    },
    {
       id: 'data-contracts',
      title: 'Data Contracts',
      value: stats.dataContracts.count,
      loading: stats.dataContracts.loading,
      error: stats.dataContracts.error,
      link: '/data-contracts',
      icon: <FileTextIcon className="h-4 w-4" />,
      description: 'Active contracts',
      maturity: 'ga',
    },
    {
      id: 'business-glossary',
      title: 'Business Glossary',
      value: `${stats.glossaries.count.glossaries} / ${stats.glossaries.count.terms}`,
      loading: stats.glossaries.loading,
      error: stats.glossaries.error,
      link: '/business-glossary',
      icon: <BookOpen className="h-4 w-4" />,
      description: 'Glossaries / Terms',
       maturity: 'ga',
    },
    {
      id: 'estate-manager',
      title: 'Estates',
      value: stats.estates.count,
      loading: stats.estates.loading,
      error: stats.estates.error,
      link: '/estate-manager',
      icon: <Globe className="h-4 w-4" />,
      description: stats.estates.lastSync
        ? `Last sync: ${stats.estates.lastSync} (${stats.estates.syncStatus?.replace('_', ' ') || 'unknown'})`
        : 'No estates configured',
      maturity: 'ga',
    },
  ];

  const filteredSummaryTiles = useMemo(() => {
      if (permissionsLoading) return [];
      return baseSummaryTiles.filter(tile =>
          allowedMaturities.includes(tile.maturity as FeatureMaturity) &&
          hasPermission(tile.id, FeatureAccessLevel.READ_ONLY)
      );
  }, [baseSummaryTiles, allowedMaturities, permissionsLoading, hasPermission]);

  const summaryTiles = baseSummaryTiles.filter(tile => allowedMaturities.includes(tile.maturity as FeatureMaturity));
  const features = getLandingPageFeatures(allowedMaturities);
  const isComplianceVisible = filteredSummaryTiles.some(tile => tile.id === 'compliance');
  const canViewCompliance = useMemo(() => !permissionsLoading && hasPermission('compliance', FeatureAccessLevel.READ_ONLY), [permissionsLoading, hasPermission]);

  // Check if user has any permissions at all (besides NONE)
  const hasAnyAccess = useMemo(() => {
      if (permissionsLoading || !permissions) return false;
      return Object.values(permissions).some(level => level !== FeatureAccessLevel.NONE);
  }, [permissions, permissionsLoading]);

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="max-w-2xl mx-auto text-center mb-8">
        <div className="flex items-center justify-center mb-4">
          <UnityCatalogLogo />
          <h1 className="text-4xl font-bold ml-2">
            Unity Catalog Swiss Army Knife
          </h1>
        </div>
        <p className="text-lg text-muted-foreground mb-6">
          Manage business glossaries, data contracts, data products, personas, and more
        </p>
        <div className="mb-8">
          <SearchBar
            variant="large"
            placeholder="Search for data products, business terms, contracts..."
          />
        </div>
      </div>

      <div className="mb-8">
        <h2 className="text-2xl font-semibold mb-4">Overview</h2>
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
                            Error
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
                 No overview data available for the selected feature previews or your permissions.
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
                        <CardTitle>Compliance Trend</CardTitle>
                        <CardDescription>Last 30 days</CardDescription>
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
                    Error loading trend data: {complianceError}
                    </div>
                ) : complianceData.length === 0 ? (
                    <div className="flex items-center justify-center h-full text-muted-foreground">
                        No compliance data available for the selected period.
                    </div>
                ) : (
                    <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={complianceData} margin={{ top: 5, right: 20, left: -10, bottom: 5 }}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} />
                        <XAxis
                        dataKey="date"
                        tickFormatter={(date) => new Date(date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
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
                        width={40}
                        />
                        <Tooltip
                            contentStyle={{ fontSize: '0.875rem', borderRadius: '0.5rem', boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)' }}
                            labelFormatter={(label) => new Date(label).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}
                            formatter={(value: number) => [`${value}%`, "Compliance Score"]}
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
                 You currently don't have a specific role assigned. 
                 To access features, please <Link to="/settings?tab=roles" className="font-semibold underline hover:text-blue-900">request access to a role</Link>.
            </AlertDescription>
          </Alert>
      )}

      <section className="mb-16">
        <h2 className="text-3xl font-semibold mb-8 text-center">Key Features</h2>
         {features.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {features.map((feature: FeatureConfig) => (
                    <Link key={feature.id} to={feature.path} className="block group">
                    <Card className="flex flex-col relative h-full transition-shadow group-hover:shadow-md">
                    {feature.maturity !== 'ga' && (
                         <span className={cn(
                            "absolute top-2 right-2 text-xs font-semibold px-2 py-0.5 rounded-full z-10",
                            feature.maturity === 'beta' ? "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300" : "",
                            feature.maturity === 'alpha' ? "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300" : ""
                         )}>
                            {feature.maturity.toUpperCase()}
                         </span>
                    )}
                    <CardHeader>
                        <div className="flex items-center gap-3 mb-2">
                        <feature.icon className="h-6 w-6 text-primary" />
                        <CardTitle>{feature.name}</CardTitle>
                        </div>
                        <CardDescription>{feature.description}</CardDescription>
                    </CardHeader>
                    <CardContent className="flex-grow flex flex-col justify-end">
                        <div className="mt-auto pt-2 text-right text-xs text-muted-foreground group-hover:text-primary">
                            View Details <ArrowRight className="inline-block ml-1 h-3 w-3" />
                        </div>
                    </CardContent>
                    </Card>
                    </Link>
                ))}
                </div>
          ) : (
             <p className="text-muted-foreground text-center">No features available for the selected feature previews.</p>
          )}
      </section>

      <section className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <div>
          <h2 className="text-2xl font-semibold mb-4">Quick Actions</h2>
          <Card>
            <CardContent className="p-6">
              <ul className="space-y-3">
                {quickActions.map((action: QuickAction) => (
                  <li key={action.name}>
                    <Button variant="link" className="p-0 h-auto" asChild>
                      <Link to={action.path}>{action.name}</Link>
                    </Button>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        </div>
        <div>
          <h2 className="text-2xl font-semibold mb-4">Recent Activity</h2>
          <Card>
            <CardContent className="p-6">
              <ul className="space-y-3">
                {recentActivity.map((activity: RecentActivity) => (
                  <li key={activity.item} className="text-sm text-muted-foreground">
                    {activity.item} - <span className="italic">{activity.time}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        </div>
      </section>
    </div>
  );
}