import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

interface LayoutState {
  isSidebarCollapsed: boolean;
  actions: {
    toggleSidebar: () => void;
    setSidebarCollapsed: (isCollapsed: boolean) => void; // Optional: Action to set specific state
  };
}

export const useLayoutStore = create<LayoutState>()(
  persist(
    (set) => ({
      isSidebarCollapsed: false, // Default state (not collapsed)
      actions: {
        toggleSidebar: () => set((state) => ({ isSidebarCollapsed: !state.isSidebarCollapsed })),
        setSidebarCollapsed: (isCollapsed) => set({ isSidebarCollapsed: isCollapsed }),
      },
    }),
    {
      name: 'layout-storage', // Name for localStorage key
      storage: createJSONStorage(() => localStorage), // Use localStorage
      // Only persist the state itself
      partialize: (state) => ({
        isSidebarCollapsed: state.isSidebarCollapsed,
      }),
    }
  )
);

// Export actions separately if preferred
export const useLayoutActions = () => useLayoutStore((state) => state.actions);
