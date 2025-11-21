import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertCircle, CheckSquare, XCircle } from 'lucide-react';
import { useNotificationsStore } from '@/stores/notifications-store';
import { Link } from 'react-router-dom';
import ConfirmRoleRequestDialog from '@/components/settings/confirm-role-request-dialog';

interface ApprovalsQueue {
  contracts: { id: string; name?: string; status?: string }[];
  products: { id: string; title?: string; status?: string }[];
}

export default function RequiredActionsSection() {
  const { t, i18n } = useTranslation('home');
  const { notifications, isLoading, fetchNotifications, markAsRead } = useNotificationsStore();
  const [approvals, setApprovals] = useState<ApprovalsQueue>({ contracts: [], products: [] });
  const [loadingApprovals, setLoadingApprovals] = useState<boolean>(true);
  const [approvalsError, setApprovalsError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [dialogPayload, setDialogPayload] = useState<Record<string, any> | null>(null);

  useEffect(() => {
    fetchNotifications();
  }, [fetchNotifications]);

  useEffect(() => {
    const fetchApprovals = async () => {
      setLoadingApprovals(true);
      setApprovalsError(null);
      try {
        const res = await fetch('/api/approvals/queue', { cache: 'no-store' });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        setApprovals({
          contracts: Array.isArray(data?.contracts) ? data.contracts : [],
          products: Array.isArray(data?.products) ? data.products : [],
        });
      } catch (e: any) {
        setApprovals({ contracts: [], products: [] });
        setApprovalsError(e?.message || 'Failed to load approvals');
      } finally {
        setLoadingApprovals(false);
      }
    };
    fetchApprovals();
  }, []);

  // Filter role access requests separately
  const roleRequests = notifications.filter(
    n => n.type === 'action_required' && n.action_type === 'handle_role_request'
  );

  // Filter other action items (excluding role requests)
  const actionItems = notifications.filter(
    n => n.type === 'action_required' && n.action_type !== 'handle_role_request'
  );

  const handleOpenConfirmDialog = (payload: Record<string, any> | null) => {
    setDialogPayload(payload);
    setDialogOpen(true);
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
    setDialogPayload(null);
    fetchNotifications(); // Refresh notifications after approval/denial
  };

  return (
    <section className="mb-16">
      <h2 className="text-2xl font-semibold mb-4">{t('requiredActionsSection.title')}</h2>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
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

        <Card>
          <CardHeader>
            <CardTitle>Approvals</CardTitle>
          </CardHeader>
          <CardContent className="p-6">
            {loadingApprovals || isLoading ? (
              <div className="flex justify-center items-center h-32">{t('requiredActionsSection.loading')}</div>
            ) : approvalsError ? (
              <div className="text-sm text-destructive">{approvalsError}</div>
            ) : (
              <div className="space-y-6">
                {/* Role Access Requests */}
                <div>
                  <div className="text-sm font-medium mb-2">Role access requests</div>
                  {roleRequests.length === 0 ? (
                    <div className="text-sm text-muted-foreground">None</div>
                  ) : (
                    <ul className="space-y-3">
                      {roleRequests.slice(0, 10).map(req => (
                        <li key={req.id} className="border rounded-lg p-3 space-y-2">
                          <div className="flex items-start justify-between gap-4">
                            <div className="min-w-0 flex-1">
                              <div className="font-medium">
                                {req.action_payload?.requester_email || 'Unknown user'}
                              </div>
                              <div className="text-sm text-muted-foreground">
                                Requesting: <span className="font-medium">{req.action_payload?.role_name || 'Unknown role'}</span>
                              </div>
                              {req.action_payload?.requester_message && (
                                <div className="text-sm text-muted-foreground mt-1 italic">
                                  "{req.action_payload.requester_message}"
                                </div>
                              )}
                              <div className="text-xs text-muted-foreground mt-1">
                                {new Date(req.created_at).toLocaleString(i18n.language)}
                              </div>
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            <Button
                              size="sm"
                              variant="default"
                              className="gap-1"
                              onClick={() => handleOpenConfirmDialog(req.action_payload)}
                            >
                              <CheckSquare className="h-3.5 w-3.5" />
                              Approve
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              className="gap-1"
                              onClick={() => handleOpenConfirmDialog(req.action_payload)}
                            >
                              <XCircle className="h-3.5 w-3.5" />
                              Deny
                            </Button>
                          </div>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>

                {/* Contracts */}
                <div>
                  <div className="text-sm font-medium mb-2">Contracts awaiting approval</div>
                  {approvals.contracts.length === 0 ? (
                    <div className="text-sm text-muted-foreground">None</div>
                  ) : (
                    <ul className="space-y-2">
                      {approvals.contracts.slice(0, 10).map(c => (
                        <li key={c.id} className="flex items-center justify-between">
                          <span className="truncate">{c.name || c.id} <span className="text-muted-foreground">({c.status})</span></span>
                          <Button asChild size="sm" variant="outline">
                            <Link to={`/data-contracts/${c.id}`}>Open</Link>
                          </Button>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>

                {/* Products */}
                <div>
                  <div className="text-sm font-medium mb-2">Products pending certification</div>
                  {approvals.products.length === 0 ? (
                    <div className="text-sm text-muted-foreground">None</div>
                  ) : (
                    <ul className="space-y-2">
                      {approvals.products.slice(0, 10).map(p => (
                        <li key={p.id} className="flex items-center justify-between">
                          <span className="truncate">{p.title || p.id} <span className="text-muted-foreground">({p.status})</span></span>
                          <Button asChild size="sm" variant="outline">
                            <Link to={`/data-products/${p.id}`}>Open</Link>
                          </Button>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
      <Alert variant="default" className="mt-4">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>{t('requiredActionsSection.alertMessage')}</AlertDescription>
      </Alert>

      {/* Role Request Confirmation Dialog */}
      {dialogPayload && (
        <ConfirmRoleRequestDialog
          isOpen={dialogOpen}
          onOpenChange={setDialogOpen}
          requesterEmail={dialogPayload.requester_email || ''}
          roleId={dialogPayload.role_id || ''}
          roleName={dialogPayload.role_name || ''}
          requesterMessage={dialogPayload.requester_message}
          onDecisionMade={handleCloseDialog}
        />
      )}
    </section>
  );
}


