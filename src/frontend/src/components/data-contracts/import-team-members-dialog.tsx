import { useEffect, useState } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Checkbox } from '@/components/ui/checkbox'
import { useToast } from '@/hooks/use-toast'
import { Loader2 } from 'lucide-react'
import type { TeamMemberForImport, TeamMember } from '@/types/data-contract'

type ImportTeamMembersDialogProps = {
  isOpen: boolean
  onOpenChange: (open: boolean) => void
  entityId: string // Contract or Product ID
  entityType: 'contract' | 'product' // Type of entity
  teamId: string
  teamName: string
  onImport: (members: TeamMember[]) => Promise<void>
}

type MemberSelection = {
  member: TeamMemberForImport
  selected: boolean
  role: string
  description: string
}

export default function ImportTeamMembersDialog({
  isOpen,
  onOpenChange,
  entityId,
  entityType,
  teamId,
  teamName,
  onImport
}: ImportTeamMembersDialogProps) {
  const { toast } = useToast()
  const [loading, setLoading] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [members, setMembers] = useState<MemberSelection[]>([])

  // Fetch team members when dialog opens
  useEffect(() => {
    if (isOpen && entityId && teamId) {
      setLoading(true)
      const apiPath = entityType === 'product' 
        ? `/api/data-products/${entityId}/import-team-members?team_id=${teamId}`
        : `/api/data-contracts/${entityId}/import-team-members?team_id=${teamId}`
      fetch(apiPath)
        .then(res => {
          if (!res.ok) throw new Error('Failed to fetch team members')
          return res.json()
        })
        .then((data: TeamMemberForImport[]) => {
          // Initialize selection state with all members selected
          setMembers(data.map(member => ({
            member,
            selected: true,
            role: member.suggested_role || 'team_member',
            description: ''
          })))
        })
        .catch(err => {
          console.error('Failed to fetch team members:', err)
          toast({
            title: 'Error',
            description: err.message || 'Failed to fetch team members',
            variant: 'destructive'
          })
          setMembers([])
        })
        .finally(() => setLoading(false))
    }
  }, [isOpen, entityId, entityType, teamId, toast])

  const toggleSelection = (index: number) => {
    setMembers(prev => prev.map((m, i) => 
      i === index ? { ...m, selected: !m.selected } : m
    ))
  }

  const updateRole = (index: number, role: string) => {
    setMembers(prev => prev.map((m, i) => 
      i === index ? { ...m, role } : m
    ))
  }

  const updateDescription = (index: number, description: string) => {
    setMembers(prev => prev.map((m, i) => 
      i === index ? { ...m, description } : m
    ))
  }

  const handleImport = async () => {
    const selectedMembers = members.filter(m => m.selected)
    
    if (selectedMembers.length === 0) {
      toast({
        title: 'No members selected',
        description: 'Please select at least one team member to import',
        variant: 'destructive'
      })
      return
    }

    setIsSubmitting(true)
    try {
      // Map to ODCS TeamMember format
      const odcsMembers: TeamMember[] = selectedMembers.map(({ member, role, description }) => ({
        username: member.member_identifier,
        email: member.member_type === 'user' ? member.member_identifier : undefined,
        name: member.member_name,
        role: role,
        description: description || undefined,
      }))

      await onImport(odcsMembers)
      onOpenChange(false)
    } catch (error: any) {
      toast({
        title: 'Import failed',
        description: error?.message || 'Failed to import team members',
        variant: 'destructive'
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  const selectedCount = members.filter(m => m.selected).length

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Import Team Members from {teamName}</DialogTitle>
          <DialogDescription>
            Select team members to import into the ODCS team array. You can customize their roles and descriptions.
          </DialogDescription>
        </DialogHeader>

        <div className="py-4">
          {loading ? (
            <div className="flex justify-center items-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
          ) : members.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              No members found in this team
            </div>
          ) : (
            <div className="space-y-4">
              <div className="text-sm text-muted-foreground">
                {selectedCount} of {members.length} members selected
              </div>

              <div className="space-y-3 border rounded-lg p-4 max-h-[400px] overflow-y-auto">
                {members.map((memberSelection, index) => (
                  <div 
                    key={memberSelection.member.member_identifier}
                    className="flex items-start gap-3 p-3 border rounded-lg"
                  >
                    <Checkbox
                      checked={memberSelection.selected}
                      onCheckedChange={() => toggleSelection(index)}
                      className="mt-1"
                    />
                    
                    <div className="flex-1 space-y-3">
                      <div>
                        <div className="font-medium">{memberSelection.member.member_name}</div>
                        <div className="text-sm text-muted-foreground">
                          {memberSelection.member.member_type === 'user' ? 'User' : 'Group'}
                        </div>
                      </div>

                      <div className="grid grid-cols-2 gap-3">
                        <div className="space-y-1.5">
                          <Label className="text-xs">Role</Label>
                          <Select 
                            value={memberSelection.role} 
                            onValueChange={(role) => updateRole(index, role)}
                            disabled={!memberSelection.selected}
                          >
                            <SelectTrigger className="h-8 text-xs">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="team_member">Team Member</SelectItem>
                              <SelectItem value="owner">Owner</SelectItem>
                              <SelectItem value="steward">Steward</SelectItem>
                              <SelectItem value="consumer">Consumer</SelectItem>
                              <SelectItem value="expert">Expert</SelectItem>
                              <SelectItem value="admin">Admin</SelectItem>
                              <SelectItem value="engineer">Engineer</SelectItem>
                              <SelectItem value="analyst">Analyst</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>

                        <div className="space-y-1.5">
                          <Label className="text-xs">Description (optional)</Label>
                          <input
                            type="text"
                            value={memberSelection.description}
                            onChange={(e) => updateDescription(index, e.target.value)}
                            disabled={!memberSelection.selected}
                            placeholder="e.g., Data Engineer"
                            className="flex h-8 w-full rounded-md border border-input bg-background px-3 py-2 text-xs ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                          />
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button 
            variant="outline" 
            onClick={() => onOpenChange(false)} 
            disabled={isSubmitting}
          >
            Cancel
          </Button>
          <Button 
            onClick={handleImport} 
            disabled={isSubmitting || loading || selectedCount === 0}
          >
            {isSubmitting ? 'Importing...' : `Import ${selectedCount} ${selectedCount === 1 ? 'Member' : 'Members'}`}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

