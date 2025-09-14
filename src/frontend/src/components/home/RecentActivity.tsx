import { useEffect, useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertCircle, Loader2 } from 'lucide-react';
import { usePermissions } from '@/stores/permissions-store';
import { FeatureAccessLevel } from '@/types/settings';

interface Entry { id: string; entity_type: string; entity_id: string; action: string; username?: string | null; timestamp?: string | null }

interface RecentActivityProps {
  limit?: number;
}

export default function RecentActivity({ limit = 10 }: RecentActivityProps) {
  const { isLoading: permissionsLoading, hasPermission } = usePermissions();
  const [entries, setEntries] = useState<Entry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      if (permissionsLoading || !hasPermission('audit', FeatureAccessLevel.READ_ONLY)) {
        setEntries([]);
        return;
      }
      try {
        setLoading(true);
        const resp = await fetch(`/api/change-log?limit=${limit}`);
        if (!resp.ok) throw new Error(`HTTP error! status: ${resp.status}`);
        const data = await resp.json();
        setEntries(Array.isArray(data) ? data : []);
        setError(null);
      } catch (e: any) {
        setEntries([]);
        setError(e.message || 'Failed to load recent activity');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [permissionsLoading, hasPermission, limit]);

  return (
    <div>
      <h2 className="text-2xl font-semibold mb-4">Recent Activity</h2>
      <Card>
        <CardContent className="p-6">
          {loading ? (
            <div className="flex items-center justify-center h-24"><Loader2 className="h-6 w-6 animate-spin text-primary" /></div>
          ) : error ? (
            <Alert variant="destructive"><AlertCircle className="h-4 w-4" /><AlertDescription>{error}</AlertDescription></Alert>
          ) : entries.length === 0 ? (
            <p className="text-sm text-muted-foreground">No recent activity.</p>
          ) : (
            <ul className="space-y-3">
              {entries.map(e => (
                <li key={e.id} className="text-sm text-muted-foreground">
                  <span className="font-medium">{e.entity_type}</span> {e.entity_id} — {e.action}
                  {e.username ? <> by <span className="italic">{e.username}</span></> : null}
                  {e.timestamp ? <> at {new Date(e.timestamp).toLocaleString()}</> : null}
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}


