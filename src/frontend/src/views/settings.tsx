import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useToast } from '@/hooks/use-toast';
import { useApi } from '@/hooks/use-api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Settings as SettingsIcon, History } from 'lucide-react';
import RolesSettings from '@/components/settings/roles-settings';
import SemanticModelsSettings from '@/components/settings/semantic-models-settings';
import TagsSettings from '@/components/settings/tags-settings';
import { JobRunsDialog } from '@/components/settings/job-runs-dialog';

interface AppSettings {
  id: string;
  name: string;
  value: any;
  enableBackgroundJobs: boolean;
  databricksHost: string;
  databricksToken: string;
  databricksWarehouseId: string;
  databricksCatalog: string;
  databricksSchema: string;
  gitRepoUrl: string;
  gitBranch: string;
  gitToken: string;
}

// Shape returned by /api/settings for jobs/workflows configuration
interface SettingsApiResponse {
  job_cluster_id?: string | null;
  enabled_jobs?: string[];
  available_workflows?: { id: string; name: string; description?: string }[];
  current_settings?: {
    job_cluster_id?: string | null;
    enabled_jobs?: string[];
  };
}

export default function Settings() {
  const { t } = useTranslation(['settings', 'common']);
  const { toast } = useToast();
  const { get, post, put } = useApi();
  // Legacy general/databricks/git settings state (kept for existing tabs)
  const [settings, setSettings] = useState<AppSettings>({
    id: '',
    name: '',
    value: null,
    enableBackgroundJobs: false,
    databricksHost: '',
    databricksToken: '',
    databricksWarehouseId: '',
    databricksCatalog: '',
    databricksSchema: '',
    gitRepoUrl: '',
    gitBranch: '',
    gitToken: ''
  });
  // New jobs/workflows settings state
  const [jobClusterId, setJobClusterId] = useState<string>('');
  const [availableWorkflows, setAvailableWorkflows] = useState<{ id: string; name: string; description?: string }[]>([]);
  const [enabledJobs, setEnabledJobs] = useState<Record<string, boolean>>({});
  const [isLoading, setIsLoading] = useState(false);

  // Job runs dialog state
  const [selectedWorkflow, setSelectedWorkflow] = useState<{ id: string; name: string } | null>(null);
  const [jobRunsDialogOpen, setJobRunsDialogOpen] = useState(false);

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      const response = await get<SettingsApiResponse>('/api/settings');
      const data = response.data || {};
      const clusterId = data.job_cluster_id ?? data.current_settings?.job_cluster_id ?? '';
      setJobClusterId(clusterId || '');
      const workflows = data.available_workflows || [];
      setAvailableWorkflows(workflows);
      const enabledSet = new Set<string>(data.enabled_jobs || data.current_settings?.enabled_jobs || []);
      const toggles: Record<string, boolean> = {};
      workflows.forEach(w => { toggles[w.id] = enabledSet.has(w.id); });
      setEnabledJobs(toggles);
    } catch (error) {
      console.error('Error fetching settings:', error);
    }
  };

  const handleSave = async () => {
    setIsLoading(true);
    try {
      const payload = {
        job_cluster_id: jobClusterId || null,
        enabled_jobs: Object.entries(enabledJobs).filter(([, v]) => v).map(([k]) => k),
      };
      
      const response = await put('/api/settings', payload);
      
      // Check if the API returned an error
      if (response.error) {
        toast({
          title: t('common:status.error'),
          description: response.error,
          variant: 'destructive',
        });
        return;
      }

      // Success case
      toast({
        title: t('common:status.success'),
        description: t('settings:jobs.messages.saveSuccess'),
      });
    } catch (error: any) {
      console.error('Settings save error:', error);
      
      // Extract error message from network/other errors
      let errorMessage = 'Failed to save settings';
      if (error?.message) {
        errorMessage = error.message;
      }
      
      toast({
        title: t('common:status.error'),
        description: errorMessage,
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  };

  const toggleWorkflow = (workflow: string) => {
    setEnabledJobs(prev => ({ ...prev, [workflow]: !prev[workflow] }));
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    if (!settings) return;
    const { name, value } = e.target;
    setSettings({ ...settings, [name]: value });
  };

  const handleSwitchChange = (checked: boolean) => {
    if (!settings) return;
    setSettings({ ...settings, enableBackgroundJobs: checked });
  };

  return (
    <div className="py-6">
      <h1 className="text-3xl font-bold mb-6 flex items-center gap-2">
        <SettingsIcon className="w-8 h-8" /> {t('settings:title')}
      </h1>

      <Tabs defaultValue="general" className="space-y-4">
        <TabsList>
          <TabsTrigger value="general">General</TabsTrigger>
          <TabsTrigger value="databricks">Databricks</TabsTrigger>
          <TabsTrigger value="git">Git</TabsTrigger>
          <TabsTrigger value="jobs">{t('settings:tabs.jobs')}</TabsTrigger>
          <TabsTrigger value="roles">{t('settings:tabs.roles')}</TabsTrigger>
          <TabsTrigger value="tags">{t('settings:tabs.tags')}</TabsTrigger>
          <TabsTrigger value="semantic-models">{t('settings:tabs.semanticModels')}</TabsTrigger>
        </TabsList>

        <TabsContent value="general">
          <Card>
            <CardHeader>
              <CardTitle>General Settings</CardTitle>
              <CardDescription>Configure basic application settings</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center space-x-2">
                <Switch
                  id="background-jobs"
                  checked={settings.enableBackgroundJobs}
                  onCheckedChange={handleSwitchChange}
                />
                <Label htmlFor="background-jobs">Enable Background Jobs</Label>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="databricks">
          <Card>
            <CardHeader>
              <CardTitle>Databricks Settings</CardTitle>
              <CardDescription>Configure Databricks connection settings</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="host">Host</Label>
                <Input
                  id="host"
                  name="databricksHost"
                  value={settings.databricksHost}
                  onChange={handleChange}
                  placeholder="https://<your-workspace>.cloud.databricks.com"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="token">Token</Label>
                <Input
                  id="token"
                  name="databricksToken"
                  type="password"
                  value={settings.databricksToken}
                  onChange={handleChange}
                  placeholder="dapi..."
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="warehouse">Warehouse ID</Label>
                <Input
                  id="warehouse"
                  name="databricksWarehouseId"
                  value={settings.databricksWarehouseId}
                  onChange={handleChange}
                  placeholder="1234abcd5678efgh"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="catalog">Catalog</Label>
                <Input
                  id="catalog"
                  name="databricksCatalog"
                  value={settings.databricksCatalog}
                  onChange={handleChange}
                  placeholder="main"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="schema">Schema</Label>
                <Input
                  id="schema"
                  name="databricksSchema"
                  value={settings.databricksSchema}
                  onChange={handleChange}
                  placeholder="uc_swiss_knife"
                />
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="git">
          <Card>
            <CardHeader>
              <CardTitle>Git Settings</CardTitle>
              <CardDescription>Configure Git repository for YAML storage</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="repo">Repository URL</Label>
                <Input
                  id="repo"
                  name="gitRepoUrl"
                  value={settings.gitRepoUrl}
                  onChange={handleChange}
                  placeholder="https://github.com/your-org/your-repo.git"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="branch">Branch</Label>
                <Input
                  id="branch"
                  name="gitBranch"
                  value={settings.gitBranch}
                  onChange={handleChange}
                  placeholder="main"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="git-token">Token</Label>
                <Input
                  id="git-token"
                  name="gitToken"
                  type="password"
                  value={settings.gitToken}
                  onChange={handleChange}
                  placeholder="ghp_... or similar"
                />
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="jobs">
          <Card>
            <CardHeader>
              <CardTitle>{t('settings:jobs.title')}</CardTitle>
              <CardDescription>{t('settings:jobs.description')}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="job-cluster-id">{t('settings:jobs.jobClusterId.label')}</Label>
                <Input
                  id="job-cluster-id"
                  value={jobClusterId}
                  onChange={(e) => setJobClusterId(e.target.value)}
                  placeholder={t('settings:jobs.jobClusterId.placeholder')}
                />
              </div>
              {availableWorkflows.length === 0 ? (
                <p className="text-sm text-muted-foreground">{t('settings:jobs.noWorkflows')}</p>
              ) : (
                <>
                  <div className="space-y-2">
                    <Label>{t('settings:jobs.availableWorkflows.label')}</Label>
                    <p className="text-sm text-muted-foreground">{t('settings:jobs.availableWorkflows.description')}</p>
                  </div>
                  {availableWorkflows.map((wf) => (
                    <div key={wf.id} className="flex items-center justify-between">
                      <div>
                        <h3 className="font-medium">{wf.name}</h3>
                        {wf.description && (
                          <p className="text-sm text-muted-foreground">{wf.description}</p>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8"
                          onClick={() => {
                            setSelectedWorkflow({ id: wf.id, name: wf.name });
                            setJobRunsDialogOpen(true);
                          }}
                          title={t('settings:jobRuns.viewHistory')}
                        >
                          <History className="h-4 w-4" />
                        </Button>
                        <Switch checked={!!enabledJobs[wf.id]} onCheckedChange={() => toggleWorkflow(wf.id)} />
                      </div>
                    </div>
                  ))}
                </>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="roles">
            <RolesSettings />
        </TabsContent>
        <TabsContent value="tags">
            <TagsSettings />
        </TabsContent>
        <TabsContent value="semantic-models">
            <SemanticModelsSettings />
        </TabsContent>
      </Tabs>

      <div className="mt-6">
        <Button onClick={handleSave} disabled={isLoading}>
          {isLoading ? t('common:actions.saving') : t('settings:jobs.saveButton')}
        </Button>
      </div>

      {/* Job Runs Dialog */}
      {selectedWorkflow && (
        <JobRunsDialog
          workflowId={selectedWorkflow.id}
          workflowName={selectedWorkflow.name}
          open={jobRunsDialogOpen}
          onOpenChange={setJobRunsDialogOpen}
        />
      )}
    </div>
  );
} 