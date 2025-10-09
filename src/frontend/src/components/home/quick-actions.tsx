import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Link } from 'react-router-dom';
import { usePermissions } from '@/stores/permissions-store';
import { FeatureAccessLevel } from '@/types/settings';

interface QuickAction { name: string; path: string; }

export default function QuickActions() {
  const { t } = useTranslation('home');
  const { isLoading: permissionsLoading, hasPermission } = usePermissions();

  const actions: QuickAction[] = useMemo(() => {
    if (permissionsLoading) return [];
    const list: QuickAction[] = [];
    // Consumer
    if (hasPermission('data-products', FeatureAccessLevel.READ_ONLY)) list.push({ name: t('quickActions.actions.browseProducts'), path: '/data-products' });
    if (hasPermission('semantic-models', FeatureAccessLevel.READ_ONLY)) list.push({ name: t('quickActions.actions.browseGlossary'), path: '/semantic-models' });
    // Producer
    if (hasPermission('data-products', FeatureAccessLevel.READ_WRITE)) list.push({ name: t('quickActions.actions.createProduct'), path: '/data-products' });
    if (hasPermission('data-contracts', FeatureAccessLevel.READ_WRITE)) list.push({ name: t('quickActions.actions.defineContract'), path: '/data-contracts' });
    // Steward/Security/Admin
    if (hasPermission('data-asset-reviews', FeatureAccessLevel.READ_ONLY)) list.push({ name: t('quickActions.actions.reviewAssets'), path: '/data-asset-reviews' });
    if (hasPermission('entitlements', FeatureAccessLevel.READ_ONLY)) list.push({ name: t('quickActions.actions.manageEntitlements'), path: '/entitlements' });
    if (hasPermission('catalog-commander', FeatureAccessLevel.READ_ONLY)) list.push({ name: t('quickActions.actions.catalogCommander'), path: '/catalog-commander' });
    if (hasPermission('settings', FeatureAccessLevel.ADMIN)) list.push({ name: t('quickActions.actions.settings'), path: '/settings' });
    return list;
  }, [permissionsLoading, hasPermission, t]);

  return (
    <div>
      <h2 className="text-2xl font-semibold mb-4">{t('quickActions.title')}</h2>
      <Card>
        <CardContent className="p-6">
          {permissionsLoading ? (
            <div className="text-sm text-muted-foreground">{t('quickActions.loading')}</div>
          ) : actions.length === 0 ? (
            <div className="text-sm text-muted-foreground">{t('quickActions.noActions')}</div>
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


