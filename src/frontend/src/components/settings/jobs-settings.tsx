import { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useToast } from '@/hooks/use-toast';
import { useApi } from '@/hooks/use-api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { JobRunsDialog } from '@/components/settings/job-runs-dialog';
import WorkflowActions from '@/components/settings/workflow-actions';
import WorkflowConfigurationDialog from '@/components/settings/workflow-configuration-dialog';
import { WorkflowStatus } from '@/types/workflows';
import { WorkflowParameterDefinition } from '@/types/workflow-configurations';
import { History, Settings as SettingsIcon } from 'lucide-react';

interface SettingsApiResponse {
  job_cluster_id?: string | null;
  enabled_jobs?: string[];
  available_workflows?: { id: string; name: string; description?: string }[];
  current_settings?: {
    job_cluster_id?: string | null;
    enabled_jobs?: string[];
  };
}

type WorkflowsMap = Record<string, { id: string; name: string; description?: string }>;

export default function JobsSettings() {
  const { t } = useTranslation(['settings', 'common']);
  const { toast } = useToast();
  const { get, put, post } = useApi();

  const [jobClusterId, setJobClusterId] = useState<string>('');
  const [workflows, setWorkflows] = useState<WorkflowsMap>({});
  const [enabled, setEnabled] = useState<Record<string, boolean>>({});
  const [statuses, setStatuses] = useState<Record<string, WorkflowStatus>>({});
  const [isSaving, setIsSaving] = useState(false);

  // Job runs dialog state
  const [selectedWorkflow, setSelectedWorkflow] = useState<{ id: string; name: string } | null>(null);
  const [jobRunsDialogOpen, setJobRunsDialogOpen] = useState(false);
  
  // Configuration dialog state
  const [configDialogOpen, setConfigDialogOpen] = useState(false);
  const [configurableWorkflows, setConfigurableWorkflows] = useState<Set<string>>(new Set());

  const mergedList = useMemo(() => {
    return Object.values(workflows).map(w => ({
      ...w,
      status: statuses[w.id] || {
        workflow_id: w.id,
        // Until the backend confirms installation via status polling,
        // treat as not installed to hide actions (requires Save + deploy).
        installed: false,
        is_running: false,
        supports_pause: false,
      },
      enabled: !!enabled[w.id],
    }));
  }, [workflows, statuses, enabled]);

  useEffect(() => {
    const load = async () => {
      try {
        const response = await get<SettingsApiResponse>('/api/settings');
        const data = response.data || {};
        const clusterId = data.job_cluster_id ?? data.current_settings?.job_cluster_id ?? '';
        setJobClusterId(clusterId || '');
        const wfList = data.available_workflows || [];
        const wfMap: WorkflowsMap = {};
        wfList.forEach(w => { wfMap[w.id] = w; });
        setWorkflows(wfMap);
        const enabledSet = new Set<string>(data.enabled_jobs || data.current_settings?.enabled_jobs || []);
        const toggles: Record<string, boolean> = {};
        wfList.forEach(w => { toggles[w.id] = enabledSet.has(w.id); });
        setEnabled(toggles);
        
        // Check which workflows have configurable parameters
        const configurable = new Set<string>();
        for (const wf of wfList) {
          try {
            const defsResponse = await get<WorkflowParameterDefinition[]>(
              `/api/jobs/workflows/${encodeURIComponent(wf.id)}/parameter-definitions`
            );
            if (defsResponse.data && defsResponse.data.length > 0) {
              configurable.add(wf.id);
            }
          } catch (e) {
            // Workflow doesn't have configurable parameters or error occurred
            console.debug(`No configurable parameters for ${wf.id}`);
          }
        }
        setConfigurableWorkflows(configurable);
      } catch (e) {
        console.error('Error loading settings', e);
      }
    };
    load();
  }, [get]);

  // Poll workflow statuses
  useEffect(() => {
    let cancelled = false;
    const poll = async () => {
      try {
        const res = await get<Record<string, WorkflowStatus>>('/api/jobs/workflows/statuses');
        if (!cancelled && res.data) {
          setStatuses(res.data);
        }
      } catch (e) {
        if (!cancelled) {
          toast({ title: t('common:status.error'), description: 'Failed to fetch workflow statuses', variant: 'destructive' });
        }
      }
    };
    poll();
    const id = setInterval(poll, 10000);
    return () => { cancelled = true; clearInterval(id); };
  }, [get, toast, t]);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      const payload = {
        job_cluster_id: jobClusterId || null,
        enabled_jobs: Object.entries(enabled).filter(([, v]) => v).map(([k]) => k),
      };
      const response = await put('/api/settings', payload);
      if (response.error) {
        toast({ title: t('common:status.error'), description: response.error, variant: 'destructive' });
        return;
      }
      toast({ title: t('common:status.success'), description: t('settings:jobs.messages.saveSuccess') });
    } catch (e: any) {
      toast({ title: t('common:status.error'), description: e?.message || 'Failed to save', variant: 'destructive' });
    } finally {
      setIsSaving(false);
    }
  };

  const toggleWorkflow = (workflowId: string) => {
    setEnabled(prev => ({ ...prev, [workflowId]: !prev[workflowId] }));
  };

  const startRun = async (workflowId: string) => {
    try {
      const res = await post(`/api/jobs/workflows/${encodeURIComponent(workflowId)}/start`, {});
      if (res.error) throw new Error(res.error);
      toast({ title: t('common:status.success'), description: 'Started run' });
    } catch (e: any) {
      toast({ title: t('common:status.error'), description: e?.message || 'Failed to start', variant: 'destructive' });
    }
  };

  const stopRun = async (workflowId: string) => {
    try {
      const res = await post(`/api/jobs/workflows/${encodeURIComponent(workflowId)}/stop`, {});
      if (res.error) throw new Error(res.error);
      toast({ title: t('common:status.success'), description: 'Stopped run' });
    } catch (e: any) {
      toast({ title: t('common:status.error'), description: e?.message || 'Failed to stop', variant: 'destructive' });
    }
  };

  const pauseSchedule = async (workflowId: string) => {
    try {
      const res = await post(`/api/jobs/workflows/${encodeURIComponent(workflowId)}/pause`, {});
      if (res.error) throw new Error(res.error);
      toast({ title: t('common:status.success'), description: 'Paused schedule' });
    } catch (e: any) {
      toast({ title: t('common:status.error'), description: e?.message || 'Failed to pause', variant: 'destructive' });
    }
  };
  const resumeSchedule = async (workflowId: string) => {
    try {
      const res = await post(`/api/jobs/workflows/${encodeURIComponent(workflowId)}/resume`, {});
      if (res.error) throw new Error(res.error);
      toast({ title: t('common:status.success'), description: 'Resumed schedule' });
    } catch (e: any) {
      toast({ title: t('common:status.error'), description: e?.message || 'Failed to resume', variant: 'destructive' });
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t('settings:jobs.title')}</CardTitle>
        <CardDescription>{t('settings:jobs.description')}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="job-cluster-id">{t('settings:jobs.jobClusterId.label')}</Label>
          <Input id="job-cluster-id" value={jobClusterId} onChange={(e) => setJobClusterId(e.target.value)} placeholder={t('settings:jobs.jobClusterId.placeholder')} />
        </div>

        {Object.keys(workflows).length === 0 ? (
          <p className="text-sm text-muted-foreground">{t('settings:jobs.noWorkflows')}</p>
        ) : (
          <>
            <div className="space-y-2">
              <Label>{t('settings:jobs.availableWorkflows.label')}</Label>
              <p className="text-sm text-muted-foreground">{t('settings:jobs.availableWorkflows.description')}</p>
            </div>
            {mergedList.map((wf) => (
              <div key={wf.id} className="flex items-center justify-between">
                <div>
                  <h3 className="font-medium">{wf.name}</h3>
                  {wf.description && <p className="text-sm text-muted-foreground">{wf.description}</p>}
                </div>
                <div className="flex items-center gap-2">
                  {/* Action icons render only for installed jobs and when enabled */}
                  {wf.status?.installed && wf.enabled && (
                    <WorkflowActions
                      status={wf.status}
                      onStart={() => startRun(wf.id)}
                      onStop={() => stopRun(wf.id)}
                      onPause={() => pauseSchedule(wf.id)}
                      onResume={() => resumeSchedule(wf.id)}
                    />
                  )}

                  {/* History appears only for installed jobs */}
                  {wf.status?.installed && (
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8"
                      onClick={() => { setSelectedWorkflow({ id: wf.id, name: wf.name }); setJobRunsDialogOpen(true); }}
                      aria-label="History"
                      title={t('settings:jobRuns.viewHistory')}
                    >
                      <History className="h-4 w-4" />
                    </Button>
                  )}

                  {/* Configure button for workflows with configurable parameters */}
                  {configurableWorkflows.has(wf.id) && (
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8"
                      onClick={() => { setSelectedWorkflow({ id: wf.id, name: wf.name }); setConfigDialogOpen(true); }}
                      aria-label="Configure"
                      title="Configure workflow parameters"
                    >
                      <SettingsIcon className="h-4 w-4" />
                    </Button>
                  )}

                  {/* Toggle is always at far right */}
                  <Switch
                    checked={!!wf.enabled}
                    onCheckedChange={() => toggleWorkflow(wf.id)}
                    disabled={wf.status?.is_running}
                  />
                </div>
              </div>
            ))}
          </>
        )}

        <div className="mt-4">
          <Button onClick={handleSave} disabled={isSaving}>
            {isSaving ? t('common:actions.saving') : t('settings:jobs.saveButton')}
          </Button>
        </div>
      </CardContent>

      {/* Job Runs Dialog */}
      {selectedWorkflow && (
        <JobRunsDialog
          workflowId={selectedWorkflow.id}
          workflowName={selectedWorkflow.name}
          open={jobRunsDialogOpen}
          onOpenChange={setJobRunsDialogOpen}
        />
      )}

      {/* Configuration Dialog */}
      {selectedWorkflow && (
        <WorkflowConfigurationDialog
          workflowId={selectedWorkflow.id}
          workflowName={selectedWorkflow.name}
          open={configDialogOpen}
          onOpenChange={setConfigDialogOpen}
        />
      )}
    </Card>
  );
}


