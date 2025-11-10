import { useState } from 'react'
import { Copy, AlertCircle, CheckCircle2 } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { useToast } from '@/hooks/use-toast'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'

type VersioningWorkflowDialogProps = {
  isOpen: boolean
  onOpenChange: (open: boolean) => void
  contractId: string
  currentVersion: string
  onSuccess: (newContractId: string) => void
}

export default function VersioningWorkflowDialog({
  isOpen,
  onOpenChange,
  contractId,
  currentVersion,
  onSuccess,
}: VersioningWorkflowDialogProps) {
  const { toast } = useToast()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [versionBumpType, setVersionBumpType] = useState<'major' | 'minor' | 'patch' | 'custom'>(
    'minor'
  )
  const [customVersion, setCustomVersion] = useState('')
  const [changeSummary, setChangeSummary] = useState('')
  const [error, setError] = useState('')

  const calculateNewVersion = () => {
    if (versionBumpType === 'custom') {
      return customVersion
    }

    const parts = currentVersion.split('.').map(Number)
    if (parts.length !== 3 || parts.some(isNaN)) {
      return '1.0.0'
    }

    let [major, minor, patch] = parts
    switch (versionBumpType) {
      case 'major':
        return `${major + 1}.0.0`
      case 'minor':
        return `${major}.${minor + 1}.0`
      case 'patch':
        return `${major}.${minor}.${patch + 1}`
      default:
        return currentVersion
    }
  }

  const validateVersion = (version: string): boolean => {
    const semverRegex = /^\d+\.\d+\.\d+$/
    return semverRegex.test(version)
  }

  const handleSubmit = async () => {
    const newVersion = calculateNewVersion()

    // Validate version format
    if (!validateVersion(newVersion)) {
      setError('Version must be in format X.Y.Z (e.g., 2.0.0)')
      return
    }

    // Validate change summary
    if (!changeSummary.trim()) {
      setError('Please provide a change summary')
      return
    }

    setError('')
    setIsSubmitting(true)

    try {
      const response = await fetch(`/api/data-contracts/${contractId}/clone`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          new_version: newVersion,
          change_summary: changeSummary,
        }),
      })

      if (response.ok) {
        const newContract = await response.json()
        toast({
          title: 'Success',
          description: `Created new version ${newVersion}`,
        })
        onSuccess(newContract.id)
        onOpenChange(false)
        // Reset form
        setVersionBumpType('minor')
        setCustomVersion('')
        setChangeSummary('')
      } else {
        const errorData = await response.json().catch(() => ({}))
        setError(errorData.detail || 'Failed to create new version')
      }
    } catch (error) {
      console.error('Error creating version:', error)
      setError('Failed to create new version')
    } finally {
      setIsSubmitting(false)
    }
  }

  const newVersion = calculateNewVersion()

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Copy className="h-5 w-5" />
            Create New Version
          </DialogTitle>
          <DialogDescription>
            Clone this contract to create a new version. All content and settings will be copied.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Current Version Display */}
          <div className="flex items-center justify-between p-3 bg-muted rounded-lg">
            <div>
              <p className="text-sm font-medium">Current Version</p>
              <p className="text-2xl font-bold">{currentVersion}</p>
            </div>
            <div className="text-4xl text-muted-foreground">→</div>
            <div>
              <p className="text-sm font-medium">New Version</p>
              <p className="text-2xl font-bold text-primary">{newVersion}</p>
            </div>
          </div>

          {/* Version Bump Type */}
          <div className="space-y-3">
            <Label>Version Bump Type</Label>
            <RadioGroup
              value={versionBumpType}
              onValueChange={(value) => setVersionBumpType(value as any)}
            >
              <div className="flex items-start space-x-3 space-y-0 rounded-md border p-3">
                <RadioGroupItem value="major" id="major" />
                <div className="flex-1">
                  <Label htmlFor="major" className="font-medium cursor-pointer">
                    Major (Breaking Changes)
                  </Label>
                  <p className="text-xs text-muted-foreground">
                    Incompatible changes that break existing integrations
                  </p>
                </div>
              </div>

              <div className="flex items-start space-x-3 space-y-0 rounded-md border p-3">
                <RadioGroupItem value="minor" id="minor" />
                <div className="flex-1">
                  <Label htmlFor="minor" className="font-medium cursor-pointer">
                    Minor (New Features)
                  </Label>
                  <p className="text-xs text-muted-foreground">
                    Backward-compatible new features or improvements
                  </p>
                </div>
              </div>

              <div className="flex items-start space-x-3 space-y-0 rounded-md border p-3">
                <RadioGroupItem value="patch" id="patch" />
                <div className="flex-1">
                  <Label htmlFor="patch" className="font-medium cursor-pointer">
                    Patch (Bug Fixes)
                  </Label>
                  <p className="text-xs text-muted-foreground">
                    Backward-compatible bug fixes or minor improvements
                  </p>
                </div>
              </div>

              <div className="flex items-start space-x-3 space-y-0 rounded-md border p-3">
                <RadioGroupItem value="custom" id="custom" />
                <div className="flex-1 space-y-2">
                  <Label htmlFor="custom" className="font-medium cursor-pointer">
                    Custom Version
                  </Label>
                  <Input
                    placeholder="e.g., 3.5.2"
                    value={customVersion}
                    onChange={(e) => setCustomVersion(e.target.value)}
                    disabled={versionBumpType !== 'custom'}
                    className="h-8"
                  />
                </div>
              </div>
            </RadioGroup>
          </div>

          {/* Change Summary */}
          <div className="space-y-2">
            <Label htmlFor="changeSummary">
              Change Summary <span className="text-destructive">*</span>
            </Label>
            <Textarea
              id="changeSummary"
              placeholder="Describe what changed in this version..."
              value={changeSummary}
              onChange={(e) => setChangeSummary(e.target.value)}
              rows={4}
              className="resize-none"
            />
            <p className="text-xs text-muted-foreground">
              This summary will help users understand what changed in this version
            </p>
          </div>

          {/* Info Alert */}
          <Alert>
            <CheckCircle2 className="h-4 w-4" />
            <AlertTitle>What will be cloned?</AlertTitle>
            <AlertDescription>
              All contract content will be copied including schemas, properties, quality rules,
              servers, roles, team members, and all other settings. The new version will start in{' '}
              <strong>draft</strong> status.
            </AlertDescription>
          </Alert>

          {/* Error Display */}
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>Error</AlertTitle>
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={isSubmitting}>
            {isSubmitting ? 'Creating...' : `Create Version ${newVersion}`}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
