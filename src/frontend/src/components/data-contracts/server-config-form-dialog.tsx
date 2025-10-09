import { useEffect, useState } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { useToast } from '@/hooks/use-toast'
import type { ServerConfig } from '@/types/data-contract'

type ServerConfigFormProps = {
  isOpen: boolean
  onOpenChange: (open: boolean) => void
  onSubmit: (server: ServerConfig) => Promise<void>
  initial?: ServerConfig
}

const SERVER_TYPES = [
  'api', 'athena', 'azure', 'bigquery', 'clickhouse', 'databricks', 'denodo', 'dremio',
  'duckdb', 'glue', 'cloudsql', 'db2', 'informix', 'kafka', 'kinesis', 'local',
  'mysql', 'oracle', 'postgresql', 'postgres', 'presto', 'pubsub',
  'redshift', 's3', 'sftp', 'snowflake', 'sqlserver', 'synapse', 'trino', 'vertica', 'custom'
]

const ENVIRONMENTS = ['production', 'staging', 'development', 'test']

export default function ServerConfigFormDialog({ isOpen, onOpenChange, onSubmit, initial }: ServerConfigFormProps) {
  const { toast } = useToast()
  const [isSubmitting, setIsSubmitting] = useState(false)

  const [server, setServer] = useState('')
  const [type, setType] = useState('databricks')
  const [description, setDescription] = useState('')
  const [environment, setEnvironment] = useState('production')
  const [host, setHost] = useState('')
  const [port, setPort] = useState('')
  const [database, setDatabase] = useState('')
  const [schema, setSchema] = useState('')
  const [location, setLocation] = useState('')
  const [properties, setProperties] = useState<Record<string, string>>({})

  useEffect(() => {
    if (isOpen && initial) {
      setServer(initial.server || '')
      setType(initial.type || 'databricks')
      setDescription(initial.description || '')
      setEnvironment(initial.environment || 'production')
      setHost(initial.host || '')
      setPort(initial.port?.toString() || '')
      setDatabase(initial.database || '')
      setSchema(initial.schema || '')
      setLocation(initial.location || '')
      setProperties(initial.properties || {})
    } else if (isOpen && !initial) {
      setServer('')
      setType('databricks')
      setDescription('')
      setEnvironment('production')
      setHost('')
      setPort('')
      setDatabase('')
      setSchema('')
      setLocation('')
      setProperties({})
    }
  }, [isOpen, initial])

  const handleSubmit = async () => {
    if (!server.trim()) {
      toast({ title: 'Validation Error', description: 'Server name is required', variant: 'destructive' })
      return
    }

    setIsSubmitting(true)
    try {
      const serverConfig: ServerConfig = {
        server: server.trim(),
        type: type || undefined,
        description: description.trim() || undefined,
        environment: environment || undefined,
        host: host.trim() || undefined,
        port: port ? parseInt(port, 10) : undefined,
        database: database.trim() || undefined,
        schema: schema.trim() || undefined,
        location: location.trim() || undefined,
        properties: Object.keys(properties).length > 0 ? properties : undefined,
      }

      await onSubmit(serverConfig)
      onOpenChange(false)
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error?.message || 'Failed to save server configuration',
        variant: 'destructive',
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{initial ? 'Edit Server Configuration' : 'Add Server Configuration'}</DialogTitle>
          <DialogDescription>
            Define server/connection details for this data contract.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="server">
              Server Name <span className="text-destructive">*</span>
            </Label>
            <Input
              id="server"
              value={server}
              onChange={(e) => setServer(e.target.value)}
              placeholder="e.g., prod-databricks"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="type">Type</Label>
              <Select value={type} onValueChange={setType}>
                <SelectTrigger id="type">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {SERVER_TYPES.map((t) => (
                    <SelectItem key={t} value={t}>
                      {t}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="environment">Environment</Label>
              <Select value={environment} onValueChange={setEnvironment}>
                <SelectTrigger id="environment">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {ENVIRONMENTS.map((env) => (
                    <SelectItem key={env} value={env}>
                      {env}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe this server configuration"
              rows={2}
            />
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div className="space-y-2 col-span-2">
              <Label htmlFor="host">Host</Label>
              <Input
                id="host"
                value={host}
                onChange={(e) => setHost(e.target.value)}
                placeholder="e.g., hostname.cloud.databricks.com"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="port">Port</Label>
              <Input
                id="port"
                type="number"
                value={port}
                onChange={(e) => setPort(e.target.value)}
                placeholder="e.g., 443"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="database">Database/Catalog</Label>
              <Input
                id="database"
                value={database}
                onChange={(e) => setDatabase(e.target.value)}
                placeholder="e.g., main"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="schema">Schema</Label>
              <Input
                id="schema"
                value={schema}
                onChange={(e) => setSchema(e.target.value)}
                placeholder="e.g., default"
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="location">Location / URI</Label>
            <Input
              id="location"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              placeholder="e.g., s3://bucket/path, abfss://container@storage/path"
            />
          </div>

          <div className="space-y-2">
            <Label>Custom Properties</Label>
            <div className="space-y-2">
              {Object.entries(properties).map(([key, value]) => (
                <div key={key} className="flex gap-2">
                  <Input
                    value={key}
                    disabled
                    className="flex-1"
                    placeholder="Key"
                  />
                  <Input
                    value={value}
                    onChange={(e) => {
                      const newProps = { ...properties }
                      newProps[key] = e.target.value
                      setProperties(newProps)
                    }}
                    className="flex-1"
                    placeholder="Value"
                  />
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={() => {
                      const newProps = { ...properties }
                      delete newProps[key]
                      setProperties(newProps)
                    }}
                  >
                    ×
                  </Button>
                </div>
              ))}
              <div className="flex gap-2">
                <Input
                  id="new-prop-key"
                  placeholder="New property key"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault()
                      const input = e.currentTarget
                      const key = input.value.trim()
                      if (key && !properties[key]) {
                        setProperties({ ...properties, [key]: '' })
                        input.value = ''
                      }
                    }
                  }}
                />
                <Button
                  variant="outline"
                  onClick={() => {
                    const input = document.getElementById('new-prop-key') as HTMLInputElement
                    const key = input?.value.trim()
                    if (key && !properties[key]) {
                      setProperties({ ...properties, [key]: '' })
                      input.value = ''
                    }
                  }}
                >
                  Add Property
                </Button>
              </div>
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={isSubmitting}>
            {isSubmitting ? 'Saving...' : initial ? 'Save Changes' : 'Add Server'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
