import { useState, useEffect } from 'react'
import { ChevronDown, History } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Badge } from '@/components/ui/badge'
import { useToast } from '@/hooks/use-toast'

type ContractVersion = {
  id: string
  name: string
  version: string
  status: string
  baseName?: string
  parentContractId?: string
  changeSummary?: string
  createdAt: string
}

type VersionSelectorProps = {
  currentContractId: string
  currentVersion?: string
  onVersionChange: (contractId: string) => void
}

export default function VersionSelector({
  currentContractId,
  currentVersion,
  onVersionChange,
}: VersionSelectorProps) {
  const { toast } = useToast()
  const [versions, setVersions] = useState<ContractVersion[]>([])
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    fetchVersions()
  }, [currentContractId])

  const fetchVersions = async () => {
    setIsLoading(true)
    try {
      const response = await fetch(`/api/data-contracts/${currentContractId}/versions`)
      if (response.ok) {
        const data = await response.json()
        setVersions(data || [])
      } else {
        console.error('Failed to fetch versions')
        setVersions([])
      }
    } catch (error) {
      console.error('Error fetching versions:', error)
      toast({
        title: 'Error',
        description: 'Failed to load contract versions',
        variant: 'destructive',
      })
      setVersions([])
    } finally {
      setIsLoading(false)
    }
  }

  const handleVersionSelect = (versionId: string) => {
    if (versionId !== currentContractId) {
      onVersionChange(versionId)
    }
  }

  const getStatusBadgeVariant = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'published':
        return 'default'
      case 'draft':
        return 'secondary'
      case 'deprecated':
        return 'outline'
      default:
        return 'secondary'
    }
  }

  if (versions.length <= 1) {
    // Don't show selector if there's only one version
    return null
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="sm" disabled={isLoading}>
          <History className="h-4 w-4 mr-2" />
          {currentVersion || 'Version'}
          <ChevronDown className="h-4 w-4 ml-2" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-[320px]">
        <DropdownMenuLabel>Available Versions ({versions.length})</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {versions.map((version) => (
          <DropdownMenuItem
            key={version.id}
            onClick={() => handleVersionSelect(version.id)}
            className={version.id === currentContractId ? 'bg-accent' : ''}
          >
            <div className="flex flex-col gap-1 w-full">
              <div className="flex items-center justify-between">
                <span className="font-medium">
                  {version.version || 'Unknown'}
                  {version.id === currentContractId && (
                    <span className="ml-2 text-xs text-muted-foreground">(current)</span>
                  )}
                </span>
                <Badge variant={getStatusBadgeVariant(version.status)} className="text-xs">
                  {version.status}
                </Badge>
              </div>
              {version.changeSummary && (
                <span className="text-xs text-muted-foreground line-clamp-2">
                  {version.changeSummary}
                </span>
              )}
              <span className="text-xs text-muted-foreground">
                {new Date(version.createdAt).toLocaleDateString()}
              </span>
            </div>
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
