import { AlertCircle, AlertTriangle, CheckCircle2, Info } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

interface ChangeAnalysis {
  change_type: string
  version_bump: string
  summary: string
  breaking_changes: string[]
  new_features: string[]
  fixes: string[]
  schema_changes?: Array<{
    change_type: string
    schema_name: string
    field_name?: string
    old_value?: string
    new_value?: string
    severity: string
  }>
  port_changes?: Array<{
    change_type: string
    port_type: string
    port_name: string
    field_name?: string
    old_value?: string
    new_value?: string
    severity: string
  }>
}

interface VersioningRecommendationDialogProps {
  isOpen: boolean
  onOpenChange: (open: boolean) => void
  analysis: ChangeAnalysis | null
  userCanOverride: boolean
  onUpdateInPlace: () => void
  onCreateNewVersion: () => void
  isUpdating?: boolean
}

export default function VersioningRecommendationDialog({
  isOpen,
  onOpenChange,
  analysis,
  userCanOverride,
  onUpdateInPlace,
  onCreateNewVersion,
  isUpdating = false
}: VersioningRecommendationDialogProps) {
  if (!analysis) return null

  const hasBreakingChanges = analysis.breaking_changes && analysis.breaking_changes.length > 0
  const hasNewFeatures = analysis.new_features && analysis.new_features.length > 0
  const hasFixes = analysis.fixes && analysis.fixes.length > 0

  const getVersionBumpBadge = (bump: string) => {
    switch (bump) {
      case 'major':
        return <Badge variant="destructive" className="text-xs">MAJOR {bump.toUpperCase()}</Badge>
      case 'minor':
        return <Badge className="bg-blue-500 text-xs">MINOR {bump.toUpperCase()}</Badge>
      case 'patch':
        return <Badge variant="secondary" className="text-xs">PATCH {bump.toUpperCase()}</Badge>
      default:
        return <Badge variant="outline" className="text-xs">{bump.toUpperCase()}</Badge>
    }
  }

  const getSeverityBadge = (severity: string) => {
    switch (severity) {
      case 'critical':
        return <Badge variant="destructive" className="text-xs">Critical</Badge>
      case 'moderate':
        return <Badge className="bg-blue-500 text-xs">Moderate</Badge>
      case 'minor':
        return <Badge variant="secondary" className="text-xs">Minor</Badge>
      default:
        return <Badge variant="outline" className="text-xs">{severity}</Badge>
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-yellow-500" />
            Changes Detected - Version Recommendation
          </DialogTitle>
          <DialogDescription>
            {userCanOverride
              ? "Review the detected changes and decide whether to update in place or create a new version."
              : "Breaking changes detected. A new version is required to maintain compatibility."}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Version Bump Recommendation */}
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium">Recommended Version Bump:</span>
            {getVersionBumpBadge(analysis.version_bump)}
          </div>

          {/* Breaking Changes Alert */}
          {hasBreakingChanges && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                <strong>Breaking Changes Detected!</strong> These changes may impact existing consumers and require a major version bump.
              </AlertDescription>
            </Alert>
          )}

          {/* Tabbed Change Details */}
          <Tabs defaultValue="summary" className="w-full">
            <TabsList className="grid w-full grid-cols-4">
              <TabsTrigger value="summary">Summary</TabsTrigger>
              {hasBreakingChanges && (
                <TabsTrigger value="breaking" className="text-red-600">
                  Breaking ({analysis.breaking_changes.length})
                </TabsTrigger>
              )}
              {hasNewFeatures && (
                <TabsTrigger value="features" className="text-blue-600">
                  Features ({analysis.new_features.length})
                </TabsTrigger>
              )}
              {hasFixes && (
                <TabsTrigger value="fixes">
                  Fixes ({analysis.fixes.length})
                </TabsTrigger>
              )}
            </TabsList>

            <TabsContent value="summary" className="space-y-3">
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">Change Summary</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="prose prose-sm max-w-none">
                    <pre className="whitespace-pre-wrap text-sm">{analysis.summary}</pre>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            {hasBreakingChanges && (
              <TabsContent value="breaking" className="space-y-2">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm flex items-center gap-2">
                      <AlertCircle className="h-4 w-4 text-red-600" />
                      Breaking Changes
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="space-y-2">
                      {analysis.breaking_changes.map((change, idx) => (
                        <li key={idx} className="flex items-start gap-2 text-sm">
                          <span className="text-red-600 mt-0.5">•</span>
                          <span>{change}</span>
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              </TabsContent>
            )}

            {hasNewFeatures && (
              <TabsContent value="features" className="space-y-2">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 text-blue-600" />
                      New Features
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="space-y-2">
                      {analysis.new_features.map((feature, idx) => (
                        <li key={idx} className="flex items-start gap-2 text-sm">
                          <span className="text-blue-600 mt-0.5">•</span>
                          <span>{feature}</span>
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              </TabsContent>
            )}

            {hasFixes && (
              <TabsContent value="fixes" className="space-y-2">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm flex items-center gap-2">
                      <Info className="h-4 w-4 text-gray-600" />
                      Improvements & Fixes
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="space-y-2">
                      {analysis.fixes.map((fix, idx) => (
                        <li key={idx} className="flex items-start gap-2 text-sm">
                          <span className="text-gray-600 mt-0.5">•</span>
                          <span>{fix}</span>
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              </TabsContent>
            )}
          </Tabs>

          {/* Detailed Schema/Port Changes */}
          {(analysis.schema_changes?.length || analysis.port_changes?.length) ? (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Detailed Changes</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2 max-h-40 overflow-y-auto">
                  {analysis.schema_changes?.map((change, idx) => (
                    <div key={`schema-${idx}`} className="flex items-center gap-2 text-xs border-b pb-2">
                      {getSeverityBadge(change.severity)}
                      <span className="font-mono">{change.schema_name}</span>
                      {change.field_name && <span className="text-gray-500">.{change.field_name}</span>}
                      <span className="text-gray-500">({change.change_type})</span>
                    </div>
                  ))}
                  {analysis.port_changes?.map((change, idx) => (
                    <div key={`port-${idx}`} className="flex items-center gap-2 text-xs border-b pb-2">
                      {getSeverityBadge(change.severity)}
                      <span className="font-mono">{change.port_name}</span>
                      <Badge variant="outline" className="text-xs">{change.port_type}</Badge>
                      <span className="text-gray-500">({change.change_type})</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          ) : null}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isUpdating}
          >
            Cancel
          </Button>
          {userCanOverride && (
            <Button
              variant="secondary"
              onClick={onUpdateInPlace}
              disabled={isUpdating}
            >
              Update In Place
            </Button>
          )}
          <Button
            onClick={onCreateNewVersion}
            disabled={isUpdating}
            className="bg-blue-600 hover:bg-blue-700"
          >
            {isUpdating ? 'Creating...' : 'Create New Version'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

