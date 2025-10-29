import { create } from 'zustand';
import { UserInfo } from '@/types/user'; // Assuming this type exists or needs creation

interface UserState {
  userInfo: UserInfo | null;
  isLoading: boolean;
  error: string | null;
  fetchUserInfo: () => Promise<void>;
}

// Placeholder for API calls - Replace with actual implementation (similar to notifications store)
const apiGet = async <T>(endpoint: string): Promise<{ data?: T, error?: string }> => {
    try {
        const response = await fetch(endpoint);
        if (!response.ok) {
            // Handle specific errors like 401/403 if needed
            throw new Error(`API Error: ${response.status} ${response.statusText}`);
        }
        const data: T = await response.json();
        return { data };
    } catch (error: any) {
         console.error("[UserStore] API Error fetching", endpoint, ":", error);
         // Return null data and error message
         return { data: undefined, error: error.message || 'Failed to fetch user info' };
    }
};

export const useUserStore = create<UserState>((set, get) => ({
  userInfo: null,
  isLoading: false,
  error: null,

  fetchUserInfo: async () => {
    if (get().isLoading) return;
    set({ isLoading: true, error: null });
    try {
      const response = await apiGet<UserInfo>('/api/user/details');

      if (response.error || !response.data) {
        // Set error state, keep userInfo as null
        throw new Error(response.error || 'Failed to fetch user details: No data received');
      }

      set({
        userInfo: response.data,
        isLoading: false,
        error: null,
      });
    } catch (error: any) {
      console.error("Error fetching user details:", error);
      // Set error state, ensure userInfo is null
      set({ isLoading: false, error: error.message || 'An unknown error occurred', userInfo: null });
    }
  },
}));

// Note: We need a type definition for UserInfo
// Create src/types/user.ts if it doesn't exist
/* Example src/types/user.ts
export interface UserInfo {
  email: string | null;
  username: string | null;
  user: string | null; // Often the display name or username again
  ip: string | null;
  groups: string[] | null; // The crucial part!
}
*/ 