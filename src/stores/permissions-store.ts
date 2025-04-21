import { create } from 'zustand';
import { useEffect } from 'react';
import { UserPermissions, FeatureAccessLevel, AppRole } from '@/types/settings'; // Import AppRole
import { ACCESS_LEVEL_ORDER } from '@/lib/permissions';

interface PermissionsState {
    permissions: UserPermissions; // User's actual permissions based on groups
    isLoading: boolean;
    error: string | null;
    availableRoles: AppRole[];    // List of all possible roles
    appliedRoleId: string | null; // ID of the role currently being impersonated/applied
    _isInitializing: boolean; // Internal flag to prevent concurrent initializations
    fetchPermissions: () => Promise<void>;
    fetchAvailableRoles: () => Promise<void>; // New action
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
    isLoading: false,
    error: null,
    availableRoles: [],
    appliedRoleId: null,
    _isInitializing: false, // Initialize the flag

    fetchPermissions: async () => {
        try {
            const response = await fetch('/api/user/permissions');
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
            console.log("User permissions loaded:", data);
        } catch (error: any) {
            console.error("Failed to fetch user permissions:", error);
            set({ permissions: {}, error: error.message || 'Failed to load permissions.' });
            throw error;
        }
    },

    fetchAvailableRoles: async () => {
        try {
            const response = await fetch('/api/settings/roles');
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
            console.log("Available roles loaded:", data);
        } catch (error: any) {
             console.error("Failed to fetch available roles:", error);
             set({ availableRoles: [], error: error.message || 'Failed to load roles.' });
             throw error;
        }
    },

    initializeStore: async () => {
        console.log("Attempting to initialize permissions store..."); // Log entry

        // --- Guard 1: Already actively initializing? ---
        if (get()._isInitializing) {
            console.log("Initialization already in progress (_isInitializing=true). Skipping.");
            return;
        }

        // --- Guard 2: Already successfully loaded? ---
        // Check if *not* loading AND permissions OR roles exist
        const { isLoading, permissions, availableRoles } = get();
        const alreadyLoaded = !isLoading && (Object.keys(permissions).length > 0 || availableRoles.length > 0);
        if (alreadyLoaded) {
            console.log("Permissions store already initialized (previously loaded). Skipping.");
            return;
        }

        console.log("Proceeding with store initialization...");
        // Set flags IMMEDIATELY before any async work
        set({ isLoading: true, _isInitializing: true, error: null });

        try {
            console.log("Calling fetchPermissions and fetchAvailableRoles...");
            // Use the instance methods from get() to ensure the latest state is used
            await Promise.all([get().fetchPermissions(), get().fetchAvailableRoles()]);
            console.log("Permissions store initialized successfully.");
            // NOTE: isLoading and _isInitializing are reset in finally block
        } catch (error: any) {
            console.error("Error caught during permissions store initialization Promise.all:", error);
            set({ error: error.message || "Initialization failed." }); // Set error state
            // NOTE: isLoading and _isInitializing are reset in finally block
        } finally {
            console.log("Setting isLoading and _isInitializing to false in finally block.");
            set({ isLoading: false, _isInitializing: false }); // Reset flags regardless of outcome
        }
    },

    setRoleOverride: (roleId: string | null) => {
        console.log(`Setting role override to: ${roleId}`);
        set({ appliedRoleId: roleId });
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
        console.log("[Permissions Store] useEffect triggered. Checking initialization state.");
        
        // Determine if data is needed
        const hasPermissionsData = Object.keys(state.permissions).length > 0;
        const hasRolesData = state.availableRoles.length > 0;
        const needsData = !hasPermissionsData && !hasRolesData;

        // Determine if initialization can start
        const canInitialize = !state.isLoading && !state._isInitializing;

        console.log(`[Permissions Store] State Check: needsData=${needsData}, canInitialize=${canInitialize}, isLoading=${state.isLoading}, isInitializing=${state._isInitializing}`);

        if (needsData && canInitialize) {
            console.log("[Permissions Store] Conditions met: Needs data and can initialize. Calling initializeStore...");
            state.initializeStore();
        } else if (!needsData) {
            console.log("[Permissions Store] Initialization skipped: Store already has permissions or roles data.");
        } else if (state.isLoading) {
            console.log("[Permissions Store] Initialization skipped: Store is currently loading (isLoading=true).");
        } else if (state._isInitializing) {
            console.log("[Permissions Store] Initialization skipped: Initialization already in progress (_isInitializing=true).");
        }

    }, [
        // Keep dependencies that signal when state *changes* relevant to initialization
        state.initializeStore, // The function itself
        state.isLoading,       // Whether a load is active
        state._isInitializing, // The lock flag
        state.permissions,     // The permissions data
        state.availableRoles   // The roles data
    ]); 

    return state;
};

export default usePermissionsStore;