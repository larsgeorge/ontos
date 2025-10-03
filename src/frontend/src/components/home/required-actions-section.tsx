import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertCircle } from 'lucide-react';
import { useNotificationsStore } from '@/stores/notifications-store';
import { Link } from 'react-router-dom';

export default function RequiredActionsSection() {
  const { t, i18n } = useTranslation('home');
  const { notifications, isLoading, fetchNotifications, markAsRead } = useNotificationsStore();

  useEffect(() => {
    fetchNotifications();
  }, [fetchNotifications]);

  const actionItems = notifications.filter(n => n.type === 'action_required');

  return (
    <section className="mb-16">
      <h2 className="text-2xl font-semibold mb-4">{t('requiredActionsSection.title')}</h2>
      <Card>
        <CardHeader>
          <CardTitle>{t('requiredActionsSection.pendingNotifications')}</CardTitle>
        </CardHeader>
        <CardContent className="p-6">
          {isLoading ? (
            <div className="flex justify-center items-center h-32">{t('requiredActionsSection.loading')}</div>
          ) : actionItems.length === 0 ? (
            <p className="text-center text-muted-foreground">{t('requiredActionsSection.noActions')}</p>
          ) : (
            <ul className="divide-y">
              {actionItems.slice(0, 10).map(n => (
                <li key={n.id} className="py-3 flex items-center justify-between gap-4">
                  <div className="min-w-0">
                    <div className="font-medium truncate">{n.title}</div>
                    {n.subtitle ? <div className="text-sm text-muted-foreground truncate">{n.subtitle}</div> : null}
                    <div className="text-xs text-muted-foreground mt-1">{n.created_at ? new Date(n.created_at).toLocaleString(i18n.language) : ''}</div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    {n.link ? (
                      <Button asChild size="sm" variant="outline"><Link to={n.link}>{t('requiredActionsSection.openButton')}</Link></Button>
                    ) : null}
                    {!n.read ? (
                      <Button size="sm" onClick={() => markAsRead(n.id)}>{t('requiredActionsSection.markReadButton')}</Button>
                    ) : (
                      <span className="text-xs text-muted-foreground">{t('requiredActionsSection.readLabel')}</span>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
      <Alert variant="default" className="mt-4">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          {t('requiredActionsSection.alertMessage')}
        </AlertDescription>
      </Alert>
    </section>
  );
}


