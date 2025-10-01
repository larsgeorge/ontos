import { useMemo } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Link } from 'react-router-dom';
import { usePermissions } from '@/stores/permissions-store';
import { FeatureAccessLevel } from '@/types/settings';

interface QuickAction { name: string; path: string; }

export default function QuickActions() {
  const { isLoading: permissionsLoading, hasPermission } = usePermissions();

  const actions: QuickAction[] = useMemo(() => {
    if (permissionsLoading) return [];
    const list: QuickAction[] = [];
    // Consumer
    if (hasPermission('data-products', FeatureAccessLevel.READ_ONLY)) list.push({ name: 'Browse Data Products', path: '/data-products' });
    if (hasPermission('business-glossary', FeatureAccessLevel.READ_ONLY)) list.push({ name: 'Browse Business Glossary', path: '/business-glossary' });
    // Producer
    if (hasPermission('data-products', FeatureAccessLevel.READ_WRITE)) list.push({ name: 'Create Data Product', path: '/data-products' });
    if (hasPermission('data-contracts', FeatureAccessLevel.READ_WRITE)) list.push({ name: 'Define Data Contract', path: '/data-contracts' });
    // Steward/Security/Admin
    if (hasPermission('data-asset-reviews', FeatureAccessLevel.READ_ONLY)) list.push({ name: 'Review Data Assets', path: '/data-asset-reviews' });
    if (hasPermission('entitlements', FeatureAccessLevel.READ_ONLY)) list.push({ name: 'Manage Entitlements', path: '/entitlements' });
    if (hasPermission('catalog-commander', FeatureAccessLevel.READ_ONLY)) list.push({ name: 'Catalog Commander', path: '/catalog-commander' });
    if (hasPermission('settings', FeatureAccessLevel.ADMIN)) list.push({ name: 'Settings', path: '/settings' });
    return list;
  }, [permissionsLoading, hasPermission]);

  return (
    <div>
      <h2 className="text-2xl font-semibold mb-4">Quick Actions</h2>
      <Card>
        <CardContent className="p-6">
          {permissionsLoading ? (
            <div className="text-sm text-muted-foreground">Loading...</div>
          ) : actions.length === 0 ? (
            <div className="text-sm text-muted-foreground">No actions available.</div>
          ) : (
            <ul className="space-y-3">
              {actions.map((action) => (
                <li key={action.name}>
                  <Button variant="link" className="p-0 h-auto" asChild>
                    <Link to={action.path}>{action.name}</Link>
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}


