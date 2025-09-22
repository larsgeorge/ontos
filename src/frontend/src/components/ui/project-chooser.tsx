import { useState, useEffect } from 'react';
import { Check, ChevronDown, FolderOpen, Plus, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useProjectContext } from '@/stores/project-store';
import { useToast } from '@/hooks/use-toast';
import { usePermissions } from '@/stores/permissions-store';
import { FeatureAccessLevel } from '@/types/settings';

export function ProjectChooser() {
  const {
    currentProject,
    availableProjects,
    isLoading,
    error,
    hasProjectContext,
    fetchUserProjects,
    switchProject,
    clearProject,
  } = useProjectContext();

  const { toast } = useToast();
  const { hasPermission } = usePermissions();
  const [isOpen, setIsOpen] = useState(false);

  const canManageProjects = hasPermission('projects', FeatureAccessLevel.READ_WRITE);

  useEffect(() => {
    // Fetch user projects on component mount
    fetchUserProjects();
  }, [fetchUserProjects]);

  const handleProjectSwitch = async (projectId: string) => {
    try {
      await switchProject(projectId);
      setIsOpen(false);
      toast({
        title: 'Project switched',
        description: `Switched to project: ${availableProjects.find(p => p.id === projectId)?.name}`,
      });
    } catch (error) {
      toast({
        variant: 'destructive',
        title: 'Failed to switch project',
        description: error instanceof Error ? error.message : 'Unknown error occurred',
      });
    }
  };

  const handleClearProject = async () => {
    try {
      clearProject();
      setIsOpen(false);
      toast({
        title: 'Project cleared',
        description: 'No longer working within a specific project context',
      });
    } catch (error) {
      toast({
        variant: 'destructive',
        title: 'Failed to clear project',
        description: error instanceof Error ? error.message : 'Unknown error occurred',
      });
    }
  };

  // Don't render if user has no projects and can't manage them
  if (!isLoading && availableProjects.length === 0 && !canManageProjects) {
    return null;
  }

  return (
    <DropdownMenu open={isOpen} onOpenChange={setIsOpen}>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          className="flex items-center gap-2 min-w-[200px] justify-between"
          disabled={isLoading}
        >
          <div className="flex items-center gap-2 flex-1 min-w-0">
            <FolderOpen className="h-4 w-4 flex-shrink-0" />
            {hasProjectContext ? (
              <div className="flex items-center gap-2 min-w-0">
                <span className="truncate font-medium">
                  {currentProject?.name || 'Unknown Project'}
                </span>
                <Badge variant="secondary" className="text-xs">
                  {currentProject?.team_count || 0} teams
                </Badge>
              </div>
            ) : (
              <span className="text-muted-foreground">
                {isLoading ? 'Loading...' : 'All Projects'}
              </span>
            )}
          </div>
          <ChevronDown className="h-4 w-4 flex-shrink-0" />
        </Button>
      </DropdownMenuTrigger>

      <DropdownMenuContent align="start" className="w-[280px]">
        <DropdownMenuLabel className="flex items-center justify-between">
          <span>Project Context</span>
          {hasProjectContext && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleClearProject}
              className="h-6 w-6 p-0"
            >
              <X className="h-3 w-3" />
              <span className="sr-only">Clear project</span>
            </Button>
          )}
        </DropdownMenuLabel>

        <DropdownMenuSeparator />

        {!hasProjectContext && (
          <DropdownMenuItem className="text-muted-foreground">
            <Check className="mr-2 h-4 w-4" />
            All Projects (No filter)
          </DropdownMenuItem>
        )}

        {availableProjects.length > 0 && (
          <>
            {availableProjects.map((project) => (
              <DropdownMenuItem
                key={project.id}
                onClick={() => handleProjectSwitch(project.id)}
                className="flex items-center justify-between"
              >
                <div className="flex items-center min-w-0 flex-1">
                  {currentProject?.id === project.id ? (
                    <Check className="mr-2 h-4 w-4 text-primary" />
                  ) : (
                    <div className="mr-6" />
                  )}
                  <div className="min-w-0 flex-1">
                    <div className="font-medium truncate">{project.name}</div>
                    {project.title && (
                      <div className="text-xs text-muted-foreground truncate">
                        {project.title}
                      </div>
                    )}
                  </div>
                </div>
                <Badge variant="outline" className="text-xs ml-2">
                  {project.team_count} teams
                </Badge>
              </DropdownMenuItem>
            ))}
          </>
        )}

        {availableProjects.length === 0 && !isLoading && (
          <DropdownMenuItem disabled className="text-muted-foreground">
            No projects available
          </DropdownMenuItem>
        )}

        {canManageProjects && (
          <>
            <DropdownMenuSeparator />
            <DropdownMenuItem asChild>
              <a href="/projects" className="flex items-center">
                <Plus className="mr-2 h-4 w-4" />
                Manage Projects
              </a>
            </DropdownMenuItem>
          </>
        )}

        {error && (
          <>
            <DropdownMenuSeparator />
            <DropdownMenuItem disabled className="text-destructive text-xs">
              Error: {error}
            </DropdownMenuItem>
          </>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}