import React, { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { AlertCircle, Download, Pencil, Trash2, Loader2, ArrowLeft, FileText } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Label } from '@/components/ui/label'
import DataContractWizardDialog from '@/components/data-contracts/data-contract-wizard-dialog'
import { useToast } from '@/hooks/use-toast'
import EntityMetadataPanel from '@/components/metadata/entity-metadata-panel'
import { CommentSidebar } from '@/components/comments'
import useBreadcrumbStore from '@/stores/breadcrumb-store'

type Contract = {
  id: string
  name: string
  version: string
  status: string
  owner: string
  format?: string
  contract_text?: string
  created?: string
  updated?: string
}

export default function DataContractDetails() {
  const { contractId } = useParams<{ contractId: string }>()
  const navigate = useNavigate()
  const { toast } = useToast()
  
  const setStaticSegments = useBreadcrumbStore((state) => state.setStaticSegments)
  const setDynamicTitle = useBreadcrumbStore((state) => state.setDynamicTitle)

  const [contract, setContract] = useState<Contract | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isWizardOpen, setIsWizardOpen] = useState(false)
  const [isCommentSidebarOpen, setIsCommentSidebarOpen] = useState(false)

  const fetchDetails = async () => {
    if (!contractId) return
    setLoading(true)
    setError(null)
    setDynamicTitle('Loading...')
    try {
      const res = await fetch(`/api/data-contracts/${contractId}`)
      if (!res.ok) throw new Error('Failed to load contract')
      const data = await res.json()
      setContract(data)
      setDynamicTitle(data.name)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load')
      setDynamicTitle('Error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { 
    setStaticSegments([{ label: 'Data Contracts', path: '/data-contracts' }])
    fetchDetails()
    
    return () => {
      setStaticSegments([])
      setDynamicTitle(null)
    }
  }, [contractId, setStaticSegments, setDynamicTitle])

  const handleDelete = async () => {
    if (!contractId) return
    if (!confirm('Delete this contract?')) return
    try {
      const res = await fetch(`/api/data-contracts/${contractId}`, { method: 'DELETE' })
      if (!res.ok) throw new Error('Delete failed')
      toast({ title: 'Deleted', description: 'Contract deleted.' })
      navigate('/data-contracts')
    } catch (e) {
      toast({ title: 'Error', description: e instanceof Error ? e.message : 'Failed to delete', variant: 'destructive' })
    }
  }

  const exportRaw = async () => {
    if (!contractId || !contract) return
    try {
      const res = await fetch(`/api/data-contracts/${contractId}/export`)
      if (!res.ok) throw new Error('Export failed')
      const text = await res.text()
      const blob = new Blob([text], { type: 'text/plain' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${contract.name.toLowerCase().replace(/\s+/g, '_')}.${contract.format || 'txt'}`
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      toast({ title: 'Export failed', description: e instanceof Error ? e.message : 'Unable to export', variant: 'destructive' })
    }
  }

  const exportOdcs = async () => {
    if (!contractId || !contract) return
    try {
      const res = await fetch(`/api/data-contracts/${contractId}/odcs/export`)
      if (!res.ok) throw new Error('Export ODCS failed')
      const data = await res.json()
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${contract.name.toLowerCase().replace(/\s+/g, '_')}-odcs.json`
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      toast({ title: 'Export failed', description: e instanceof Error ? e.message : 'Unable to export', variant: 'destructive' })
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="h-12 w-12 animate-spin text-primary" />
      </div>
    )
  }
  if (error || !contract) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>{error || 'Contract not found.'}</AlertDescription>
      </Alert>
    )
  }

  return (
    <div className="py-6 space-y-6">
      <div className="flex items-center justify-between">
        <Button variant="outline" onClick={() => navigate('/data-contracts')} size="sm">
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to List
        </Button>
        <div className="flex items-center gap-2">
          <CommentSidebar
            entityType="data_contract"
            entityId={contractId!}
            isOpen={isCommentSidebarOpen}
            onToggle={() => setIsCommentSidebarOpen(!isCommentSidebarOpen)}
            className="h-8"
          />
          <Button variant="outline" onClick={() => setIsWizardOpen(true)} size="sm"><Pencil className="mr-2 h-4 w-4" /> Edit</Button>
          <Button variant="outline" onClick={exportOdcs} size="sm"><Download className="mr-2 h-4 w-4" /> Export ODCS</Button>
          <Button variant="outline" onClick={exportRaw} size="sm"><Download className="mr-2 h-4 w-4" /> Export</Button>
          <Button variant="destructive" onClick={handleDelete} size="sm"><Trash2 className="mr-2 h-4 w-4" /> Delete</Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-2xl font-bold flex items-center">
            <FileText className="mr-3 h-7 w-7 text-primary" />{contract.name}
          </CardTitle>
          <CardDescription className="pt-1">Core contract metadata</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid md:grid-cols-4 gap-4">
            <div className="space-y-1"><Label>Owner:</Label> <span className="text-sm block">{contract.owner}</span></div>
            <div className="space-y-1"><Label>Status:</Label> <Badge variant="secondary" className="ml-1">{contract.status}</Badge></div>
            <div className="space-y-1"><Label>Version:</Label> <Badge variant="outline" className="ml-1">{contract.version}</Badge></div>
            <div className="space-y-1"><Label>Format:</Label> <span className="text-sm block">{contract.format}</span></div>
            <div className="space-y-1"><Label>Created:</Label> <span className="text-sm block">{contract.created || 'N/A'}</span></div>
            <div className="space-y-1"><Label>Updated:</Label> <span className="text-sm block">{contract.updated || 'N/A'}</span></div>
          </div>
          <div className="space-y-1">
            <Label>Contract Text</Label>
            <pre className="p-3 rounded bg-muted text-sm overflow-x-auto whitespace-pre-wrap">{contract.contract_text}</pre>
          </div>
        </CardContent>
      </Card>

      {/* Metadata Panel */}
      {contract.id && (
        <EntityMetadataPanel entityId={contract.id} entityType="data_contract" />
      )}

      <DataContractWizardDialog
        isOpen={isWizardOpen}
        onOpenChange={setIsWizardOpen}
        initial={{
          name: contract.name,
          version: contract.version,
          status: contract.status,
          owner: contract.owner,
        }}
        onSubmit={async (payload) => {
          try {
            const res = await fetch(`/api/data-contracts/${contract.id}`, {
              method: 'PUT',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                name: payload.name,
                version: payload.version,
                status: payload.status,
                owner: payload.owner,
              })
            })
            if (!res.ok) throw new Error('Update failed')
            setIsWizardOpen(false)
            await fetchDetails()
            toast({ title: 'Updated', description: 'Contract updated.' })
          } catch (e) {
            toast({ title: 'Error', description: e instanceof Error ? e.message : 'Failed to update', variant: 'destructive' })
          }
        }}
      />
    </div>
  )
}


