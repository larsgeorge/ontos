import { useState, useEffect, useCallback, useMemo } from 'react';
import { ColumnDef } from '@tanstack/react-table';
import { MoreHorizontal, PlusCircle, Loader2, AlertCircle, UserCheck } from 'lucide-react';
import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/ui/data-table";
import { TeamRead } from '@/types/team';
import { useApi } from '@/hooks/use-api';
import { useToast } from "@/hooks/use-toast";
import { RelativeDate } from '@/components/common/relative-date';
import {
    DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger
} from "@/components/ui/dropdown-menu";
import {
    AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle
} from "@/components/ui/alert-dialog";
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from "@/components/ui/badge";
import { usePermissions } from '@/stores/permissions-store';
import { FeatureAccessLevel } from '@/types/settings';
import { Toaster } from "@/components/ui/toaster";
import useBreadcrumbStore from '@/stores/breadcrumb-store';
import { useProjectContext } from '@/stores/project-store';
import { TeamFormDialog } from '@/components/teams/team-form-dialog';

// Check API response helper
const checkApiResponse = <T,>(response: { data?: T | { detail?: string }, error?: string | null | undefined }, name: string): T => {
    if (response.error) throw new Error(`${name} fetch failed: ${response.error}`);
    if (response.data && typeof response.data === 'object' && response.data !== null && 'detail' in response.data && typeof (response.data as { detail: string }).detail === 'string') {
        throw new Error(`${name} fetch failed: ${(response.data as { detail: string }).detail}`);
    }
    if (response.data === null || response.data === undefined) throw new Error(`${name} fetch returned null or undefined data.`);
    return response.data as T;
};

export default function TeamsView() {
  const [teams, setTeams] = useState<TeamRead[]>([]);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingTeam, setEditingTeam] = useState<TeamRead | null>(null);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [deletingTeamId, setDeletingTeamId] = useState<string | null>(null);
  const [componentError, setComponentError] = useState<string | null>(null);

  const { get: apiGet, delete: apiDelete, loading: apiIsLoading } = useApi();
  const { toast } = useToast();
  const { hasPermission, isLoading: permissionsLoading } = usePermissions();
  const setStaticSegments = useBreadcrumbStore((state) => state.setStaticSegments);
  const setDynamicTitle = useBreadcrumbStore((state) => state.setDynamicTitle);
  const { currentProject, hasProjectContext } = useProjectContext();

  const featureId = 'teams';
  const canRead = !permissionsLoading && hasPermission(featureId, FeatureAccessLevel.READ_ONLY);
  const canWrite = !permissionsLoading && hasPermission(featureId, FeatureAccessLevel.READ_WRITE);
  const canAdmin = !permissionsLoading && hasPermission(featureId, FeatureAccessLevel.ADMIN);

  const fetchTeams = useCallback(async () => {
    if (!canRead && !permissionsLoading) {
        setComponentError("Permission Denied: Cannot view teams.");
        return;
    }
    setComponentError(null);
    try {
      // Build URL with project context if available
      let endpoint = '/api/teams';
      if (hasProjectContext && currentProject) {
        endpoint += `?project_id=${currentProject.id}`;
      }

      const response = await apiGet<TeamRead[]>(endpoint);
      const data = checkApiResponse(response, 'Teams');
      const teamsData = Array.isArray(data) ? data : [];
      setTeams(teamsData);
      if (response.error) {
        setComponentError(response.error);
        setTeams([]);
        toast({ variant: "destructive", title: "Error fetching teams", description: response.error });
      }
    } catch (err: any) {
      setComponentError(err.message || 'Failed to load teams');
      setTeams([]);
      toast({ variant: "destructive", title: "Error fetching teams", description: err.message });
    }
  }, [canRead, permissionsLoading, apiGet, toast, setComponentError, hasProjectContext, currentProject]);

  useEffect(() => {
    fetchTeams();
    setStaticSegments([]);
    setDynamicTitle('Teams');
    return () => {
        setStaticSegments([]);
        setDynamicTitle(null);
    };
  }, [fetchTeams, setStaticSegments, setDynamicTitle]);

  const handleOpenCreateDialog = () => {
    if (!canWrite) {
        toast({ variant: "destructive", title: "Permission Denied", description: "You do not have permission to create teams." });
        return;
    }
    setEditingTeam(null);
    setIsFormOpen(true);
  };

  const handleOpenEditDialog = (team: TeamRead) => {
    if (!canWrite) {
        toast({ variant: "destructive", title: "Permission Denied", description: "You do not have permission to edit teams." });
        return;
    }
    setEditingTeam(team);
    setIsFormOpen(true);
  };

  const handleFormSubmitSuccess = (savedTeam: TeamRead) => {
    fetchTeams();
  };

  const openDeleteDialog = (teamId: string) => {
    if (!canAdmin) {
         toast({ variant: "destructive", title: "Permission Denied", description: "You do not have permission to delete teams." });
         return;
    }
    setDeletingTeamId(teamId);
    setIsDeleteDialogOpen(true);
  };

  const handleDeleteConfirm = async () => {
    if (!deletingTeamId || !canAdmin) return;
    try {
      const response = await apiDelete(`/api/teams/${deletingTeamId}`);
      if (response.error) {
        let errorMessage = response.error;
        if (response.data && typeof response.data === 'object' && response.data !== null && 'detail' in response.data && typeof (response.data as { detail: string }).detail === 'string') {
            errorMessage = (response.data as { detail: string }).detail;
        }
        throw new Error(errorMessage || 'Failed to delete team.');
      }
      toast({ title: "Team Deleted", description: "The team was successfully deleted." });
      fetchTeams();
    } catch (err: any) {
       toast({ variant: "destructive", title: "Error Deleting Team", description: err.message || 'Failed to delete team.' });
       setComponentError(err.message || 'Failed to delete team.');
    } finally {
       setIsDeleteDialogOpen(false);
       setDeletingTeamId(null);
    }
  };

  const columns = useMemo<ColumnDef<TeamRead>[]>(() => [
    {
      accessorKey: "name",
      header: "Name",
      cell: ({ row }) => {
        const team = row.original;
        return (
          <div>
            <span className="font-medium">{team.name}</span>
            {team.domain_name && (
              <div className="text-xs text-muted-foreground">
                Domain: {team.domain_name}
              </div>
            )}
          </div>
        );
      },
    },
    {
      accessorKey: "description",
      header: "Description",
      cell: ({ row }) => (
        <div className="truncate max-w-sm text-sm text-muted-foreground">
          {row.getValue("description") || '-'}
        </div>
      ),
    },
    {
      accessorKey: "members",
      header: "Members",
      cell: ({ row }) => {
        const members = row.original.members;
        if (!members || members.length === 0) return '-';
        return (
          <div className="flex flex-col space-y-0.5">
            {members.slice(0, 3).map((member, index) => (
              <div key={index} className="flex items-center gap-1">
                <Badge
                  variant={member.member_type === 'user' ? 'default' : 'secondary'}
                  className="text-xs truncate w-fit"
                >
                  {member.member_name || member.member_identifier}
                </Badge>
                {(member.role_override || member.app_role_override) && (
                  <Badge variant="outline" className="text-xs">
                    {member.role_override || member.app_role_override}
                  </Badge>
                )}
              </div>
            ))}
            {members.length > 3 && (
              <Badge variant="outline" className="text-xs">
                +{members.length - 3} more
              </Badge>
            )}
          </div>
        );
      }
    },
    {
      accessorKey: "updated_at",
      header: "Last Updated",
      cell: ({ row }) => {
         const dateValue = row.getValue("updated_at");
         return dateValue ? <RelativeDate date={dateValue as string | Date | number} /> : 'N/A';
      },
    },
    {
      id: "actions",
      cell: ({ row }) => {
        const team = row.original;
        return (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="h-8 w-8 p-0">
                <span className="sr-only">Open menu</span>
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuLabel>Actions</DropdownMenuLabel>
              <DropdownMenuItem onClick={() => handleOpenEditDialog(team)} disabled={!canWrite}>
                Edit Team
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                onClick={() => openDeleteDialog(team.id)}
                className="text-red-600 focus:text-red-600 focus:bg-red-50"
                disabled={!canAdmin}
              >
                Delete Team
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        );
      },
    },
  ], [canWrite, canAdmin]);

  return (
    <div className="py-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
             <UserCheck className="w-8 h-8" />
             Teams
          </h1>
          {hasProjectContext && currentProject && (
            <p className="text-muted-foreground mt-1">
              Showing teams for project: <span className="font-medium">{currentProject.name}</span>
            </p>
          )}
        </div>
        <Button onClick={handleOpenCreateDialog} disabled={!canWrite || permissionsLoading || apiIsLoading}>
            <PlusCircle className="mr-2 h-4 w-4" /> Add New Team
        </Button>
      </div>

      {(apiIsLoading || permissionsLoading) ? (
        <div className="flex justify-center items-center h-64">
          <Loader2 className="h-12 w-12 animate-spin text-primary" />
        </div>
      ) : !canRead ? (
         <Alert variant="destructive" className="mb-4">
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>Permission Denied</AlertTitle>
              <AlertDescription>You do not have permission to view teams.</AlertDescription>
         </Alert>
      ) : componentError ? (
          <Alert variant="destructive" className="mb-4">
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>Error Loading Data</AlertTitle>
              <AlertDescription>{componentError}</AlertDescription>
          </Alert>
      ) : (
        <>
          <DataTable
             columns={columns}
             data={teams}
             searchColumn="name"
             toolbarActions={null}
          />
          <TeamFormDialog
            isOpen={isFormOpen}
            onOpenChange={setIsFormOpen}
            team={editingTeam}
            onSubmitSuccess={handleFormSubmitSuccess}
          />
        </>
      )}

      <AlertDialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Are you absolutely sure?</AlertDialogTitle>
            <AlertDialogDescription>
              This action cannot be undone. This will permanently delete the team and all its members.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setDeletingTeamId(null)}>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDeleteConfirm} className="bg-red-600 hover:bg-red-700" disabled={apiIsLoading || permissionsLoading}>
               {(apiIsLoading || permissionsLoading) ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null} Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <Toaster />
    </div>
  );
}