import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { useToast } from '@/hooks/use-toast'
import { ArrowLeftRight, Plus, Trash2, Edit2, Clock, CheckCircle2, XCircle } from 'lucide-react'
import { ColumnDef } from "@tanstack/react-table"
import useBreadcrumbStore from '@/stores/breadcrumb-store'
import { DataTable } from '@/components/ui/data-table'

interface EntitlementsSyncConfig {
  id: string
  name: string
  connection: string
  schedule: string
  enabled: boolean
  catalogs: string[]
  lastSync?: {
    status: 'success' | 'error' | 'running'
    timestamp?: string
    error?: string
  }
}

export default function EntitlementsSync() {
  const [configs, setConfigs] = useState<EntitlementsSyncConfig[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [editingConfig, setEditingConfig] = useState<EntitlementsSyncConfig | null>(null)
  const [connections, setConnections] = useState<{ id: string; name: string }[]>([])
  const [catalogs, setCatalogs] = useState<string[]>([])
  const { toast } = useToast()

  const setStaticSegments = useBreadcrumbStore((state) => state.setStaticSegments)
  const setDynamicTitle = useBreadcrumbStore((state) => state.setDynamicTitle)

  useEffect(() => {
    fetchConfigs()
    setStaticSegments([])
    setDynamicTitle('Entitlements Sync')

    return () => {
      setStaticSegments([])
      setDynamicTitle(null)
    }
  }, [setStaticSegments, setDynamicTitle])

  // Load connections and catalogs when dialog opens
  useEffect(() => {
    if (isDialogOpen) {
      fetchConnections()
      fetchCatalogs()
    }
  }, [isDialogOpen])

  const fetchConfigs = async () => {
    try {
      const response = await fetch('/api/entitlements-sync/configs')
      if (!response.ok) throw new Error('Failed to load configurations')
      const data = await response.json()
      setConfigs(data)
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to load configurations',
        variant: 'destructive',
      })
    } finally {
      setIsLoading(false)
    }
  }

  const fetchConnections = async () => {
    try {
      const response = await fetch('/api/entitlements-sync/connections')
      if (!response.ok) throw new Error('Failed to load connections')
      const data = await response.json()
      setConnections(data)
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to load connections',
        variant: 'destructive',
      })
    }
  }

  const fetchCatalogs = async () => {
    try {
      const response = await fetch('/api/entitlements-sync/catalogs')
      if (!response.ok) throw new Error('Failed to load catalogs')
      const data = await response.json()
      setCatalogs(data)
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to load catalogs',
        variant: 'destructive',
      })
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const formData = new FormData(e.target as HTMLFormElement)
    const config: Partial<EntitlementsSyncConfig> = {
      name: formData.get('name') as string,
      connection: formData.get('connection') as string,
      schedule: formData.get('schedule') as string,
      enabled: formData.get('enabled') === 'on',
      catalogs: formData.getAll('catalogs') as string[],
    }

    try {
      const url = editingConfig
        ? `/api/entitlements-sync/configs/${editingConfig.id}`
        : '/api/entitlements-sync/configs'
      const method = editingConfig ? 'PUT' : 'POST'

      const response = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      })

      if (!response.ok) throw new Error('Failed to save configuration')

      toast({
        title: 'Success',
        description: `Configuration ${editingConfig ? 'updated' : 'created'} successfully`,
      })

      setIsDialogOpen(false)
      setEditingConfig(null)
      fetchConfigs()
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to save configuration',
        variant: 'destructive',
      })
    }
  }

  const handleDelete = async (id: string) => {
    if (!window.confirm('Are you sure you want to delete this configuration?')) return

    try {
      const response = await fetch(`/api/entitlements-sync/configs/${id}`, {
        method: 'DELETE',
      })

      if (!response.ok) throw new Error('Failed to delete configuration')

      toast({
        title: 'Success',
        description: 'Configuration deleted successfully',
      })

      fetchConfigs()
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to delete configuration',
        variant: 'destructive',
      })
    }
  }

  const handleEdit = (config: EntitlementsSyncConfig) => {
    setEditingConfig(config)
    setIsDialogOpen(true)
  }

  const columns: ColumnDef<EntitlementsSyncConfig>[] = [
    {
      accessorKey: "name",
      header: "Name",
      cell: ({ row }) => <div className="font-medium">{row.getValue("name")}</div>,
    },
    {
      accessorKey: "connection",
      header: "Connection",
      cell: ({ row }) => <div>{row.getValue("connection")}</div>,
    },
    {
      accessorKey: "schedule",
      header: "Schedule",
      cell: ({ row }) => <div>{row.getValue("schedule")}</div>,
    },
    {
      accessorKey: "enabled",
      header: "Status",
      cell: ({ row }) => (
        <div className="flex items-center">
          {row.getValue("enabled") ? (
            <span className="flex items-center text-green-600">
              <CheckCircle2 className="w-4 h-4 mr-1" />
              Enabled
            </span>
          ) : (
            <span className="flex items-center text-gray-500">
              <XCircle className="w-4 h-4 mr-1" />
              Disabled
            </span>
          )}
        </div>
      ),
    },
    {
      accessorKey: "lastSync",
      header: "Last Sync",
      cell: ({ row }) => {
        const lastSync = row.getValue("lastSync") as any;
        return (
          <div className="flex items-center">
            {lastSync?.status === 'running' && (
              <Clock className="w-4 h-4 mr-1 text-blue-600" />
            )}
            {lastSync?.status === 'success' && (
              <CheckCircle2 className="w-4 h-4 mr-1 text-green-600" />
            )}
            {lastSync?.status === 'error' && (
              <XCircle className="w-4 h-4 mr-1 text-red-600" />
            )}
            {lastSync?.timestamp || 'Never'}
          </div>
        );
      },
    },
    {
      id: "actions",
      enableHiding: false,
      cell: ({ row }) => {
        const config = row.original;
        return (
          <div className="flex space-x-2">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => handleEdit(config)}
            >
              <Edit2 className="w-4 h-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => handleDelete(config.id)}
            >
              <Trash2 className="w-4 h-4" />
            </Button>
          </div>
        );
      },
    },
  ];

  return (
    <div className="py-6">
      <h1 className="text-3xl font-bold mb-6 flex items-center gap-2">
        <ArrowLeftRight className="w-8 h-8" /> Entitlements Sync
      </h1>
      <div className="flex justify-between items-center mb-8">
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="w-4 h-4 mr-2" />
              New Configuration
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>
                {editingConfig ? 'Edit Configuration' : 'New Configuration'}
              </DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name">Name</Label>
                <Input
                  id="name"
                  name="name"
                  defaultValue={editingConfig?.name}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="connection">Connection</Label>
                <Select name="connection" defaultValue={editingConfig?.connection}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select a connection" />
                  </SelectTrigger>
                  <SelectContent>
                    {connections.map((conn) => (
                      <SelectItem key={conn.id} value={conn.id}>
                        {conn.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="schedule">Schedule (Cron)</Label>
                <Input
                  id="schedule"
                  name="schedule"
                  defaultValue={editingConfig?.schedule}
                  placeholder="0 0 * * *"
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="catalogs">Catalogs</Label>
                <Select name="catalogs" defaultValue={editingConfig?.catalogs[0]}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select catalogs" />
                  </SelectTrigger>
                  <SelectContent>
                    {catalogs.map((catalog) => (
                      <SelectItem key={catalog} value={catalog}>
                        {catalog}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex items-center space-x-2">
                <Switch
                  id="enabled"
                  name="enabled"
                  defaultChecked={editingConfig?.enabled}
                />
                <Label htmlFor="enabled">Enabled</Label>
              </div>
              <div className="flex justify-end space-x-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => {
                    setIsDialogOpen(false)
                    setEditingConfig(null)
                  }}
                >
                  Cancel
                </Button>
                <Button type="submit">Save</Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      <DataTable
        columns={columns}
        data={configs}
        searchColumn="name"
        storageKey="entitlements-sync-sort"
        isLoading={isLoading}
      />
    </div>
  )
} 