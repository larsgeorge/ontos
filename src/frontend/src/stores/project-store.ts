import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { ProjectSummary, UserProjectAccess, ProjectAccessRequest, ProjectAccessRequestResponse } from '@/types/project';

interface ProjectState {
  // Current project context
  currentProject: ProjectSummary | null;
  availableProjects: ProjectSummary[];
  allProjects: ProjectSummary[];
  isLoading: boolean;
  error: string | null;

  // Actions
  setCurrentProject: (project: ProjectSummary | null) => void;
  setAvailableProjects: (projects: ProjectSummary[]) => void;
  setAllProjects: (projects: ProjectSummary[]) => void;
  fetchUserProjects: () => Promise<void>;
  fetchAllProjects: () => Promise<void>;
  switchProject: (projectId: string) => Promise<void>;
  requestProjectAccess: (request: ProjectAccessRequest) => Promise<ProjectAccessRequestResponse>;
  clearProject: () => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

// Helper function to make API calls
const apiCall = async (endpoint: string, options?: RequestInit) => {
  const response = await fetch(`/api${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `HTTP ${response.status}`);
  }

  return response.json();
};

export const useProjectStore = create<ProjectState>()(
  persist(
    (set, get) => ({
      currentProject: null,
      availableProjects: [],
      allProjects: [],
      isLoading: false,
      error: null,

      setCurrentProject: (project) => {
        set({ currentProject: project, error: null });
      },

      setAvailableProjects: (projects) => {
        set({ availableProjects: projects });
      },

      setAllProjects: (projects) => {
        set({ allProjects: projects });
      },

      fetchUserProjects: async () => {
        const { setLoading, setError, setAvailableProjects, setCurrentProject, currentProject } = get();

        try {
          setLoading(true);
          setError(null);

          const data: UserProjectAccess = await apiCall('/user/projects');

          setAvailableProjects(data.projects || []);

          // Set current project if provided by backend
          if (data.current_project_id) {
            const currentProj = data.projects?.find(p => p.id === data.current_project_id);
            if (currentProj) {
              setCurrentProject(currentProj);
            }
          } else if (!currentProject && data.projects && data.projects.length > 0) {
            // If no current project is set, try to find and set "Admin Project" as default
            const adminProject = data.projects.find(p => p.name === 'Admin Project');
            if (adminProject) {
              setCurrentProject(adminProject);
            }
          }
        } catch (error) {
          console.error('Failed to fetch user projects:', error);
          setError(error instanceof Error ? error.message : 'Failed to fetch projects');
          setAvailableProjects([]);
          setCurrentProject(null);
        } finally {
          setLoading(false);
        }
      },

      fetchAllProjects: async () => {
        const { setLoading, setError, setAllProjects } = get();

        try {
          setLoading(true);
          setError(null);

          const data: ProjectSummary[] = await apiCall('/projects/summary');
          setAllProjects(data || []);
        } catch (error) {
          console.error('Failed to fetch all projects:', error);
          setError(error instanceof Error ? error.message : 'Failed to fetch all projects');
          setAllProjects([]);
        } finally {
          setLoading(false);
        }
      },

      switchProject: async (projectId: string) => {
        const { availableProjects, setCurrentProject, setLoading, setError } = get();

        try {
          setLoading(true);
          setError(null);

          // Find the project in available projects
          const project = availableProjects.find(p => p.id === projectId);
          if (!project) {
            throw new Error('Project not found in available projects');
          }

          // Call backend to switch project context
          await apiCall('/user/project-context', {
            method: 'POST',
            body: JSON.stringify({ project_id: projectId }),
          });

          // Update current project
          setCurrentProject(project);
        } catch (error) {
          console.error('Failed to switch project:', error);
          setError(error instanceof Error ? error.message : 'Failed to switch project');
        } finally {
          setLoading(false);
        }
      },

      clearProject: () => {
        set({
          currentProject: null,
          error: null
        });

        // Call backend to clear project context
        apiCall('/user/project-context', {
          method: 'POST',
          body: JSON.stringify({ project_id: null }),
        }).catch(error => {
          console.error('Failed to clear project context:', error);
        });
      },

      requestProjectAccess: async (request: ProjectAccessRequest): Promise<ProjectAccessRequestResponse> => {
        const { setLoading, setError } = get();

        try {
          setLoading(true);
          setError(null);

          const response = await apiCall('/user/request-project-access', {
            method: 'POST',
            body: JSON.stringify(request),
          });

          return response;
        } catch (error) {
          console.error('Failed to request project access:', error);
          const errorMessage = error instanceof Error ? error.message : 'Failed to request project access';
          setError(errorMessage);
          throw error;
        } finally {
          setLoading(false);
        }
      },

      setLoading: (loading) => {
        set({ isLoading: loading });
      },

      setError: (error) => {
        set({ error });
      },
    }),
    {
      name: 'ucapp-project-store',
      // Only persist the current project, not the loading state or errors
      partialize: (state) => ({
        currentProject: state.currentProject,
      }),
    }
  )
);

// Hook for easy access to project context
export const useProjectContext = () => {
  const store = useProjectStore();
  return {
    currentProject: store.currentProject,
    availableProjects: store.availableProjects,
    allProjects: store.allProjects,
    isLoading: store.isLoading,
    error: store.error,
    hasProjectContext: !!store.currentProject,
    fetchUserProjects: store.fetchUserProjects,
    fetchAllProjects: store.fetchAllProjects,
    switchProject: store.switchProject,
    requestProjectAccess: store.requestProjectAccess,
    clearProject: store.clearProject,
  };
};