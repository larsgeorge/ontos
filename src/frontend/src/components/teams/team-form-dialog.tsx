import { useState, useEffect } from 'react';
import { useForm, useFieldArray } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Loader2, Plus, Trash2, User, Users } from 'lucide-react';
import { useApi } from '@/hooks/use-api';
import { useToast } from '@/hooks/use-toast';
import { TeamRead, TeamCreate, TeamUpdate, MemberType, TeamMember } from '@/types/team';
import { DataDomain } from '@/types/data-domain';

// Form schema
const teamMemberSchema = z.object({
  member_type: z.enum(['user', 'group']),
  member_identifier: z.string().min(1, 'Member identifier is required'),
  app_role_override: z.string().optional(),
});

const teamFormSchema = z.object({
  name: z.string().min(1, 'Team name is required'),
  title: z.string().optional(),
  description: z.string().optional(),
  domain_id: z.string().optional(),
  tags: z.array(z.string()).optional(),
  members: z.array(teamMemberSchema).optional(),
});

type TeamFormData = z.infer<typeof teamFormSchema>;

interface TeamFormDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  team?: TeamRead | null;
  onSubmitSuccess: (team: TeamRead) => void;
  initialDomainId?: string;
}

export function TeamFormDialog({
  isOpen,
  onOpenChange,
  team,
  onSubmitSuccess,
  initialDomainId,
}: TeamFormDialogProps) {
  const [domains, setDomains] = useState<DataDomain[]>([]);
  const [availableRoles, setAvailableRoles] = useState<string[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { get: apiGet, post: apiPost, put: apiPut, delete: apiDelete } = useApi();
  const { toast } = useToast();

  const form = useForm<TeamFormData>({
    resolver: zodResolver(teamFormSchema),
    defaultValues: {
      name: '',
      title: '',
      description: '',
      domain_id: 'none',
      tags: [],
      members: [],
    },
  });

  const { fields: memberFields, append: addMember, remove: removeMember } = useFieldArray({
    control: form.control,
    name: 'members',
  });

  // Fetch data when dialog opens
  useEffect(() => {
    if (isOpen) {
      fetchDomains();
      fetchAvailableRoles();

      if (team) {
        // Edit mode - populate form with existing team data
        form.reset({
          name: team.name,
          title: team.title || '',
          description: team.description || '',
          domain_id: team.domain_id || 'none',
          tags: team.tags || [],
          members: team.members?.map(member => ({
            member_type: member.member_type,
            member_identifier: member.member_identifier,
            app_role_override: member.app_role_override || 'none',
          })) || [],
        });
      } else {
        // Create mode - reset form with initial domain if provided
        form.reset({
          name: '',
          title: '',
          description: '',
          domain_id: initialDomainId || 'none',
          tags: [],
          members: [],
        });
      }
    }
  }, [isOpen, team, form, initialDomainId]);

  const fetchDomains = async () => {
    try {
      const response = await apiGet<DataDomain[]>('/api/data-domains');
      if (response.data && !response.error) {
        setDomains(Array.isArray(response.data) ? response.data : []);
      }
    } catch (error) {
      console.error('Failed to fetch domains:', error);
    }
  };

  const fetchAvailableRoles = async () => {
    try {
      const response = await apiGet<{ name: string }[]>('/api/settings/roles');
      if (response.data && !response.error) {
        const roles = Array.isArray(response.data) ? response.data.map(role => role.name) : [];
        setAvailableRoles(roles);
      }
    } catch (error) {
      console.error('Failed to fetch available roles:', error);
    }
  };

  const handleAddMember = () => {
    addMember({
      member_type: 'user',
      member_identifier: '',
      app_role_override: 'none',
    });
  };

  const handleSubmit = async (data: TeamFormData) => {
    setIsSubmitting(true);
    try {
      // Filter out empty members and clean up data
      const cleanedData = {
        ...data,
        domain_id: data.domain_id === 'none' ? undefined : data.domain_id,
        tags: data.tags?.filter(tag => tag.trim() !== '') || [],
        members: data.members?.filter(member => member.member_identifier.trim() !== '').map(member => ({
          ...member,
          app_role_override: member.app_role_override === 'none' ? undefined : member.app_role_override?.trim() || undefined,
        })) || [],
      };

      let response;
      if (team) {
        // Update existing team
        const updateData: TeamUpdate = {
          name: cleanedData.name,
          title: cleanedData.title || undefined,
          description: cleanedData.description || undefined,
          domain_id: cleanedData.domain_id || undefined,
          tags: cleanedData.tags,
          metadata: undefined,
        };
        response = await apiPut<TeamRead>(`/api/teams/${team.id}`, updateData);

        if (response.error) {
          throw new Error(response.error);
        }

        // For updates, clear existing members and add new ones
        // First, get current members
        const currentMembersResponse = await apiGet<TeamMember[]>(`/api/teams/${team.id}/members`);
        if (currentMembersResponse.data && !currentMembersResponse.error) {
          // Remove all current members
          for (const currentMember of currentMembersResponse.data) {
            try {
              await apiDelete(`/api/teams/${team.id}/members/${encodeURIComponent(currentMember.member_identifier)}`);
            } catch (removeError) {
              console.warn('Failed to remove existing member:', removeError);
            }
          }
        }

        // Add new members
        for (const member of cleanedData.members) {
          try {
            await apiPost(`/api/teams/${team.id}/members`, {
              member_type: member.member_type,
              member_identifier: member.member_identifier,
              app_role_override: member.app_role_override
            });
          } catch (memberError) {
            console.warn('Failed to add member:', memberError);
          }
        }
      } else {
        // Create new team (without members)
        const createData: TeamCreate = {
          name: cleanedData.name,
          title: cleanedData.title || undefined,
          description: cleanedData.description || undefined,
          domain_id: cleanedData.domain_id || undefined,
          tags: cleanedData.tags,
          metadata: undefined,
        };
        response = await apiPost<TeamRead>('/api/teams', createData);

        if (response.error) {
          throw new Error(response.error);
        }

        // Add members separately after team creation
        if (response.data && cleanedData.members && cleanedData.members.length > 0) {
          const teamId = (response.data as TeamRead).id;
          for (const member of cleanedData.members) {
            try {
              await apiPost(`/api/teams/${teamId}/members`, {
                member_type: member.member_type,
                member_identifier: member.member_identifier,
                app_role_override: member.app_role_override
              });
            } catch (memberError) {
              // Continue with other members if one fails
              console.warn('Failed to add member during creation:', memberError);
            }
          }
        }
      }


      toast({
        title: team ? 'Team Updated' : 'Team Created',
        description: `Team "${cleanedData.name}" has been ${team ? 'updated' : 'created'} successfully.`,
      });

      onSubmitSuccess(response.data as TeamRead);
      onOpenChange(false);
    } catch (error) {
      toast({
        variant: 'destructive',
        title: team ? 'Failed to Update Team' : 'Failed to Create Team',
        description: error instanceof Error ? error.message : 'An unexpected error occurred.',
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{team ? 'Edit Team' : 'Create New Team'}</DialogTitle>
          <DialogDescription>
            {team ? 'Update team details and members.' : 'Create a new team with members and role overrides.'}
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-6">
            {/* Basic Team Information */}
            <div className="space-y-4">
              <h3 className="text-lg font-medium">Team Information</h3>

              <FormField
                control={form.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Team Name *</FormLabel>
                    <FormControl>
                      <Input placeholder="Enter team name" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="title"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Display Title</FormLabel>
                    <FormControl>
                      <Input placeholder="Enter display title (optional)" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="description"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Description</FormLabel>
                    <FormControl>
                      <Textarea placeholder="Enter team description (optional)" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="domain_id"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Data Domain</FormLabel>
                    <Select onValueChange={field.onChange} value={field.value}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Select a data domain (optional)" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="none">No domain</SelectItem>
                        {domains.map((domain) => (
                          <SelectItem key={domain.id} value={domain.id}>
                            {domain.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            {/* Team Members */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-medium">Team Members</h3>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleAddMember}
                >
                  <Plus className="w-4 h-4 mr-2" />
                  Add Member
                </Button>
              </div>

              {memberFields.length === 0 ? (
                <div className="text-center py-6 text-muted-foreground">
                  No team members added yet. Click "Add Member" to start building your team.
                </div>
              ) : (
                <div className="space-y-3">
                  {memberFields.map((field, index) => (
                    <div key={field.id} className="p-4 border rounded-lg">
                      <div className="flex items-start gap-4">
                        <div className="flex-1 grid grid-cols-1 md:grid-cols-3 gap-3">
                          <FormField
                            control={form.control}
                            name={`members.${index}.member_type`}
                            render={({ field }) => (
                              <FormItem>
                                <FormLabel>Type</FormLabel>
                                <Select onValueChange={field.onChange} value={field.value}>
                                  <FormControl>
                                    <SelectTrigger>
                                      <SelectValue />
                                    </SelectTrigger>
                                  </FormControl>
                                  <SelectContent>
                                    <SelectItem value="user">
                                      <div className="flex items-center gap-2">
                                        <User className="w-4 h-4" />
                                        User
                                      </div>
                                    </SelectItem>
                                    <SelectItem value="group">
                                      <div className="flex items-center gap-2">
                                        <Users className="w-4 h-4" />
                                        Group
                                      </div>
                                    </SelectItem>
                                  </SelectContent>
                                </Select>
                                <FormMessage />
                              </FormItem>
                            )}
                          />

                          <FormField
                            control={form.control}
                            name={`members.${index}.member_identifier`}
                            render={({ field }) => (
                              <FormItem>
                                <FormLabel>
                                  {form.watch(`members.${index}.member_type`) === 'user' ? 'Email' : 'Group Name'}
                                </FormLabel>
                                <FormControl>
                                  <Input
                                    placeholder={
                                      form.watch(`members.${index}.member_type`) === 'user'
                                        ? 'user@example.com'
                                        : 'group-name'
                                    }
                                    {...field}
                                  />
                                </FormControl>
                                <FormMessage />
                              </FormItem>
                            )}
                          />

                          <FormField
                            control={form.control}
                            name={`members.${index}.app_role_override`}
                            render={({ field }) => (
                              <FormItem>
                                <FormLabel>Role Override</FormLabel>
                                <Select onValueChange={field.onChange} value={field.value}>
                                  <FormControl>
                                    <SelectTrigger>
                                      <SelectValue placeholder="No override" />
                                    </SelectTrigger>
                                  </FormControl>
                                  <SelectContent>
                                    <SelectItem value="none">No override</SelectItem>
                                    {availableRoles.map((role) => (
                                      <SelectItem key={role} value={role}>
                                        {role}
                                      </SelectItem>
                                    ))}
                                  </SelectContent>
                                </Select>
                                <FormDescription>
                                  Override group-based role for this member
                                </FormDescription>
                                <FormMessage />
                              </FormItem>
                            )}
                          />
                        </div>

                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => removeMember(index)}
                          className="text-red-600 hover:text-red-700 mt-6"
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
                disabled={isSubmitting}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                {team ? 'Update Team' : 'Create Team'}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}