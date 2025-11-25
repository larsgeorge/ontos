import { create } from 'zustand';
import { useEffect } from 'react';
import { UserPermissions, FeatureAccessLevel, AppRole } from '@/types/settings'; // Import AppRole
import { ACCESS_LEVEL_ORDER } from '@/lib/permissions';

interface PermissionsState {
    permissions: UserPermissions; // User's effective permissions (may be overridden)
    actualPermissions: UserPermissions; // User's actual permissions based on groups (never overridden)
    isLoading: boolean;
    error: string | null;
    availableRoles: AppRole[];    // List of all possible roles
    appliedRoleId: string | null; // ID of the role currently being impersonated/applied
    _isInitializing: boolean; // Internal flag to prevent concurrent initializations
    fetchPermissions: () => Promise<void>;
    fetchActualPermissions: () => Promise<void>; // Fetch actual non-overridden permissions
    fetchAvailableRoles: () => Promise<void>; // New action
    fetchAppliedOverride: () => Promise<void>; // New action to read persisted override
    setRoleOverride: (roleId: string | null) => void; // New action
    hasPermission: (featureId: string, requiredLevel: FeatureAccessLevel) => boolean;
    getPermissionLevel: (featureId: string) => FeatureAccessLevel;
    initializeStore: () => Promise<void>; // New action
}

// Helper function to get permission level, considering override
const getPermissionLevelFromState = (
    permissions: UserPermissions,
    appliedRoleId: string | null,
    availableRoles: AppRole[],
    featureId: string
): FeatureAccessLevel => {
    if (appliedRoleId) {
        const overrideRole = availableRoles.find(role => role.id === appliedRoleId);
        return overrideRole?.feature_permissions?.[featureId] || FeatureAccessLevel.NONE;
    }
    // Default to actual user permissions if no override
    return permissions[featureId] || FeatureAccessLevel.NONE;
};

const usePermissionsStore = create<PermissionsState>((set, get) => ({
    permissions: {},
    actualPermissions: {},
    isLoading: false,
    error: null,
    availableRoles: [],
    appliedRoleId: null,
    _isInitializing: false, // Initialize the flag

    fetchPermissions: async () => {
        try {
            const response = await fetch('/api/user/permissions', { cache: 'no-store' });
            if (!response.ok) {
                let errorMsg = `HTTP error! status: ${response.status}`;
                try {
                     const errData = await response.json();
                     errorMsg = errData.detail || errorMsg;
                } catch (e) { /* Ignore JSON parsing error */ }
                throw new Error(errorMsg);
            }
            const data: UserPermissions = await response.json();
            set({ permissions: data, error: null });
        } catch (error: any) {
            console.error("Failed to fetch user permissions:", error);
            set({ permissions: {}, error: error.message || 'Failed to load permissions.' });
            throw error;
        }
    },

    fetchActualPermissions: async () => {
        try {
            const response = await fetch('/api/user/actual-permissions', { cache: 'no-store' });
            if (!response.ok) {
                let errorMsg = `HTTP error! status: ${response.status}`;
                try {
                     const errData = await response.json();
                     errorMsg = errData.detail || errorMsg;
                } catch (e) { /* Ignore JSON parsing error */ }
                throw new Error(errorMsg);
            }
            const data: UserPermissions = await response.json();
            set({ actualPermissions: data, error: null });
        } catch (error: any) {
            console.error("Failed to fetch actual user permissions:", error);
            set({ actualPermissions: {}, error: error.message || 'Failed to load actual permissions.' });
            throw error;
        }
    },

    fetchAvailableRoles: async () => {
        try {
            const response = await fetch('/api/settings/roles', { cache: 'no-store' });
            if (!response.ok) {
                 let errorMsg = `HTTP error! status: ${response.status}`;
                 try {
                      const errData = await response.json();
                      errorMsg = errData.detail || errorMsg;
                 } catch (e) { /* Ignore */ }
                 throw new Error(errorMsg);
            }
            const data: AppRole[] = await response.json();
            set({ availableRoles: data, error: null });
        } catch (error: any) {
             console.error("Failed to fetch available roles:", error);
             set({ availableRoles: [], error: error.message || 'Failed to load roles.' });
             throw error;
        }
    },

    fetchAppliedOverride: async () => {
        try {
            const response = await fetch('/api/user/role-override', { cache: 'no-store' });
            if (!response.ok) {
                // If endpoint missing/fails, don't break UI
                return;
            }
            const data: { role_id: string | null } = await response.json();
            set({ appliedRoleId: data?.role_id ?? null });
        } catch {
            // ignore
        }
    },

    initializeStore: async () => {
        // --- Guard 1: Already actively initializing? ---
        if (get()._isInitializing) {
            return;
        }

        // --- Guard 2: Already successfully loaded? ---
        // Check if *not* loading AND permissions OR roles exist
        const { isLoading, permissions, actualPermissions, availableRoles } = get();
        const alreadyLoaded = !isLoading && (Object.keys(permissions).length > 0 || Object.keys(actualPermissions).length > 0 || availableRoles.length > 0);
        if (alreadyLoaded) {
            return;
        }

        // Set flags IMMEDIATELY before any async work
        set({ isLoading: true, _isInitializing: true, error: null });

        try {
            // Use the instance methods from get() to ensure the latest state is used
            await Promise.all([
                get().fetchPermissions(),
                get().fetchActualPermissions(),
                get().fetchAvailableRoles(),
                get().fetchAppliedOverride()
            ]);
            // NOTE: isLoading and _isInitializing are reset in finally block
        } catch (error: any) {
            console.error("Error caught during permissions store initialization Promise.all:", error);
            set({ error: error.message || "Initialization failed." }); // Set error state
            // NOTE: isLoading and _isInitializing are reset in finally block
        } finally {
            set({ isLoading: false, _isInitializing: false }); // Reset flags regardless of outcome
        }
    },

    setRoleOverride: (roleId: string | null) => {
        (async () => {
            // Optimistic local state update
            set({ appliedRoleId: roleId });
            try {
                await fetch('/api/user/role-override', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ role_id: roleId })
                });
            } catch { /* ignore */ }
            // Force-refresh state so views recompute immediately
            try {
                await Promise.all([
                    get().fetchPermissions(),
                    get().fetchAvailableRoles(),
                    get().fetchAppliedOverride()
                ]);
            } catch { /* ignore */ }
            // No full reload — views already recompute from refreshed store state
        })();
    },

    hasPermission: (featureId: string, requiredLevel: FeatureAccessLevel): boolean => {
        const state = get();
        const userLevel = getPermissionLevelFromState(
            state.permissions,
            state.appliedRoleId,
            state.availableRoles,
            featureId
        );
        return ACCESS_LEVEL_ORDER[userLevel] >= ACCESS_LEVEL_ORDER[requiredLevel];
    },

    getPermissionLevel: (featureId: string): FeatureAccessLevel => {
        const state = get();
        return getPermissionLevelFromState(
            state.permissions,
            state.appliedRoleId,
            state.availableRoles,
            featureId
        );
    },
}));

// Hook to initialize the store (fetch permissions AND roles on first use)
export const usePermissions = () => {
    const state = usePermissionsStore();
    
    // --- Refined useEffect for Initialization ---
    useEffect(() => {
        // Determine if data is needed
        const hasPermissionsData = Object.keys(state.permissions).length > 0;
        const hasActualPermissionsData = Object.keys(state.actualPermissions).length > 0;
        const hasRolesData = state.availableRoles.length > 0;
        const needsData = !hasPermissionsData && !hasActualPermissionsData && !hasRolesData;

        // Determine if initialization can start
        const canInitialize = !state.isLoading && !state._isInitializing;

        if (needsData && canInitialize) {
            state.initializeStore();
        }

    }, [
        // Keep dependencies that signal when state *changes* relevant to initialization
        state.initializeStore,     // The function itself
        state.isLoading,           // Whether a load is active
        state._isInitializing,     // The lock flag
        state.permissions,         // The permissions data
        state.actualPermissions,   // The actual permissions data
        state.availableRoles       // The roles data
    ]); 

    return state;
};

export default usePermissionsStore;