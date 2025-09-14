import React, { useEffect, useMemo, useState } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { TreeView } from '@/components/ui/tree-view'
import type { MetastoreTableInfo } from '@/types/data-product'

interface DatasetLookupDialogProps {
  isOpen: boolean
  onOpenChange: (open: boolean) => void
  onSelect: (table: MetastoreTableInfo) => void
}

type CatalogItem = { id: string; name: string; type: 'catalog' | 'schema' | 'table' | 'view'; children: CatalogItem[]; hasChildren: boolean }
type TreeViewItem = { id: string; name: string; children?: TreeViewItem[]; onClick?: () => void; expanded?: boolean; onExpand?: () => void; hasChildren: boolean; loading?: boolean }

export default function DatasetLookupDialog({ isOpen, onOpenChange, onSelect }: DatasetLookupDialogProps) {
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [items, setItems] = useState<CatalogItem[]>([])
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const [loadingNodes, setLoadingNodes] = useState<Set<string>>(new Set())

  const fetchCatalogs = async () => {
    try {
      setLoading(true)
      const res = await fetch('/api/catalogs')
      const data = await res.json()
      setItems(Array.isArray(data) ? data : [])
      setError(null)
    } catch (e) {
      setError('Failed to load catalogs')
    } finally {
      setLoading(false)
    }
  }

  const updateNodeChildren = (nodes: CatalogItem[], id: string, children: CatalogItem[]): CatalogItem[] =>
    nodes.map((n) => n.id === id ? { ...n, children } : (n.children ? { ...n, children: updateNodeChildren(n.children, id, children) } : n))

  const fetchChildren = async (nodeId: string, nodeType: string): Promise<CatalogItem[]> => {
    let url = ''
    if (nodeType === 'catalog') url = `/api/catalogs/${nodeId}/schemas`
    else if (nodeType === 'schema') {
      const [catalogName, schemaName] = nodeId.split('.')
      url = `/api/catalogs/${catalogName}/schemas/${schemaName}/tables`
    }
    const res = await fetch(url)
    if (!res.ok) return []
    return await res.json()
  }

  const handleExpand = async (item: CatalogItem) => {
    if (loadingNodes.has(item.id)) return
    setLoadingNodes((prev) => new Set(prev).add(item.id))
    try {
      const children = await fetchChildren(item.id, item.type)
      setItems((prev) => updateNodeChildren(prev, item.id, children))
      setExpanded((prev) => { const next = new Set(prev); next.add(item.id); return next })
    } finally {
      setLoadingNodes((prev) => { const next = new Set(prev); next.delete(item.id); return next })
    }
  }

  useEffect(() => { if (isOpen) fetchCatalogs() }, [isOpen])

  // Apply filter only at the current level; once navigating deeper, show all children
  const renderTree = (nodes: CatalogItem[], bypassFilter: boolean = false): TreeViewItem[] =>
    nodes
      .filter((n) => {
        if (bypassFilter) return true
        const q = search.trim().toLowerCase()
        if (!q) return true
        if (expanded.has(n.id)) return true
        return n.name.toLowerCase().includes(q)
      })
      .map((n) => ({
        id: n.id,
        name: n.name,
        hasChildren: n.hasChildren || (n.children && n.children.length > 0),
        expanded: expanded.has(n.id),
        onExpand: () => handleExpand(n),
        onClick: n.type === 'table' ? () => {
          const [catalog_name, schema_name, table_name] = n.id.split('.')
          onSelect({ catalog_name, schema_name, table_name, full_name: n.id })
          onOpenChange(false)
        } : undefined,
        // When a query is active, do not filter children at deeper levels
        children: n.children ? renderTree(n.children, Boolean(search.trim())) : [],
        loading: loadingNodes.has(n.id),
      }))

  // Memoized tree data to avoid re-render churn
  const treeData = useMemo(() => renderTree(items), [items, expanded, loadingNodes, search])

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-[90vw]">
        <DialogHeader>
          <DialogTitle>Find existing dataset</DialogTitle>
        </DialogHeader>
        <div className="space-y-3 text-sm leading-tight">
          <div className="flex gap-2">
            <Input className="h-8 text-sm" placeholder="Filter by name" value={search} onChange={(e) => setSearch(e.target.value)} />
            <Button className="h-8 px-2" type="button" variant="outline" onClick={fetchCatalogs} disabled={loading}>Refresh</Button>
          </div>
          {error && <div className="text-sm text-destructive">{error}</div>}
          <div className="h-72 overflow-auto overflow-x-auto border rounded">
            {loading ? (
              <div className="p-3 text-sm">Loading catalogs...</div>
            ) : (
              <TreeView data={treeData as any} className="p-1 text-sm leading-tight whitespace-nowrap min-w-max" />
            )}
          </div>
        </div>
        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Close</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}


