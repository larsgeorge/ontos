import React, { useState, useEffect } from 'react';
import { useToast } from '@/hooks/use-toast';
import { useApi } from '@/hooks/use-api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Settings as SettingsIcon, Users } from 'lucide-react';
import RolesSettings from '@/components/settings/roles-settings';

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

export default function Settings() {
  const { toast } = useToast();
  const { get, post } = useApi();
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
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      const response = await get<AppSettings>('/api/settings');
      setSettings(response.data);
    } catch (error) {
      console.error('Error fetching settings:', error);
    }
  };

  const handleSave = async () => {
    setIsLoading(true);
    try {
      await post('/api/settings', settings);
      toast({
        title: 'Success',
        description: 'Settings saved successfully',
      });
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to save settings',
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
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
        <SettingsIcon className="w-8 h-8" /> Settings
      </h1>
      
      <Tabs defaultValue="general" className="space-y-4">
        <TabsList>
          <TabsTrigger value="general">General</TabsTrigger>
          <TabsTrigger value="databricks">Databricks</TabsTrigger>
          <TabsTrigger value="git">Git</TabsTrigger>
          <TabsTrigger value="jobs">Background Jobs</TabsTrigger>
          <TabsTrigger value="roles">Roles</TabsTrigger>
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
              <CardTitle>Background Jobs</CardTitle>
              <CardDescription>Manage background jobs for data processing</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-medium">Data Product Sync</h3>
                  <p className="text-sm text-muted-foreground">Sync data products with Unity Catalog</p>
                </div>
                <Button variant="outline">Install</Button>
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-medium">Data Contract Validation</h3>
                  <p className="text-sm text-muted-foreground">Validate data contracts and quality rules</p>
                </div>
                <Button variant="outline">Install</Button>
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-medium">Business Glossary Sync</h3>
                  <p className="text-sm text-muted-foreground">Sync business glossary terms</p>
                </div>
                <Button variant="outline">Install</Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="roles">
            <RolesSettings />
        </TabsContent>
      </Tabs>

      <div className="mt-6">
        <Button onClick={handleSave} disabled={isLoading}>
          {isLoading ? 'Saving...' : 'Save Settings'}
        </Button>
      </div>
    </div>
  );
} 