import { create } from 'zustand';
import { useApi } from '@/hooks/use-api'; // Assuming useApi can be used outside component context (might need adjustment)
import { Notification } from '@/types/notification'; // Assuming this type exists or needs creation

interface NotificationsState {
  notifications: Notification[];
  unreadCount: number;
  isLoading: boolean;
  error: string | null;
  fetchNotifications: () => Promise<void>;
  refreshNotifications: () => void; // Simple alias to trigger fetch
  markAsRead: (notificationId: string) => Promise<void>;
  deleteNotification: (notificationId: string) => Promise<void>;
}

// Helper to get the API hook instance - this might be tricky outside React context
// Option 1: Pass the api instance if possible (e.g., during app initialization)
// Option 2: Re-create fetch logic here (less ideal)
// Option 3: Assume useApi() works globally (unlikely without context/singleton setup)
// For now, let's *assume* a way to get the api functions is available.
// A more realistic approach might involve calling API methods directly.

// Placeholder for API calls - Replace with actual implementation
const apiGet = async <T>(endpoint: string): Promise<{ data?: T, error?: string }> => {
    // Replace with actual fetch call, potentially using a shared API client instance
    console.log(`[Store] Fetching ${endpoint}`);
    // Example fetch
    try {
        const response = await fetch(endpoint);
        if (!response.ok) {
            throw new Error(`API Error: ${response.status} ${response.statusText}`);
        }
        const data: T = await response.json();
        return { data };
    } catch (error: any) {
         console.error(`[Store] API Error fetching ${endpoint}:`, error);
         return { error: error.message || 'Failed to fetch' };
    }
};
const apiPut = async (endpoint: string): Promise<{ error?: string }> => {
    console.log(`[Store] PUT ${endpoint}`);
     try {
        const response = await fetch(endpoint, { method: 'PUT' });
        if (!response.ok) {
            throw new Error(`API Error: ${response.status} ${response.statusText}`);
        }
        return {}; // Success
    } catch (error: any) {
         console.error(`[Store] API Error PUT ${endpoint}:`, error);
         return { error: error.message || 'Failed to update' };
    }
};
const apiDelete = async (endpoint: string): Promise<{ error?: string }> => {
    console.log(`[Store] DELETE ${endpoint}`);
     try {
        const response = await fetch(endpoint, { method: 'DELETE' });
         if (!response.ok && response.status !== 204) { // Allow 204 No Content
            throw new Error(`API Error: ${response.status} ${response.statusText}`);
        }
        return {}; // Success
    } catch (error: any) {
         console.error(`[Store] API Error DELETE ${endpoint}:`, error);
         return { error: error.message || 'Failed to delete' };
    }
};


export const useNotificationsStore = create<NotificationsState>((set, get) => ({
  notifications: [],
  unreadCount: 0,
  isLoading: false,
  error: null,

  fetchNotifications: async () => {
    if (get().isLoading) return; // Prevent concurrent fetches
    set({ isLoading: true, error: null });
    try {
      // Replace with actual useApi().get or fetch call
      const response = await apiGet<Notification[]>('/api/notifications');

      if (response.error || !response.data) {
        throw new Error(response.error || 'Failed to fetch notifications: No data received');
      }

      const fetchedNotifications = response.data;
      const unread = fetchedNotifications.filter(n => !n.read).length;

      set({
        notifications: fetchedNotifications,
        unreadCount: unread,
        isLoading: false,
        error: null,
      });
    } catch (error: any) {
      console.error("Error fetching notifications:", error);
      set({ isLoading: false, error: error.message || 'An unknown error occurred', notifications: [], unreadCount: 0 });
    }
  },

  refreshNotifications: () => {
    // Simply call fetchNotifications to refresh the data
    get().fetchNotifications();
  },

  markAsRead: async (notificationId: string) => {
    // Optimistic UI update (optional but good UX)
    set(state => ({
        notifications: state.notifications.map(n =>
            n.id === notificationId ? { ...n, read: true } : n
        ),
        // Decrement unread count optimistically if the notification was unread
        unreadCount: state.notifications.find(n => n.id === notificationId && !n.read)
                     ? Math.max(0, state.unreadCount - 1)
                     : state.unreadCount,
    }));

    try {
       // Replace with actual useApi().put or fetch call
       const response = await apiPut(`/api/notifications/${notificationId}/read`);
       if (response.error) {
            throw new Error(response.error);
       }
       // No need to refetch if optimistic update is correct, but can refetch for consistency
       // get().fetchNotifications(); 
    } catch (error: any) {
       console.error(`Error marking notification ${notificationId} as read:`, error);
       // Revert optimistic update on error
       set(state => ({
            // Find the original state or refetch
            // This requires storing original state or simply refetching fully
            error: `Failed to mark as read: ${error.message}`
       }));
       get().fetchNotifications(); // Refetch to get actual state on error
    }
  },

  deleteNotification: async (notificationId: string) => {
    // Optimistic UI update
    const originalNotifications = get().notifications;
    const notificationToDelete = originalNotifications.find(n => n.id === notificationId);
    const originalUnreadCount = get().unreadCount;

    set(state => ({
        notifications: state.notifications.filter(n => n.id !== notificationId),
        unreadCount: notificationToDelete && !notificationToDelete.read
                     ? Math.max(0, state.unreadCount - 1)
                     : state.unreadCount,
    }));

    try {
       // Replace with actual useApi().delete or fetch call
       const response = await apiDelete(`/api/notifications/${notificationId}`);
        if (response.error) {
            throw new Error(response.error);
        }
       // Successfully deleted on backend
    } catch (error: any) {
        console.error(`Error deleting notification ${notificationId}:`, error);
        // Revert optimistic update on error
        set({
            notifications: originalNotifications,
            unreadCount: originalUnreadCount,
            error: `Failed to delete: ${error.message}`
        });
    }
  },
}));

// Note: We need a type definition for Notification
// Create src/types/notification.ts if it doesn't exist
/* Example src/types/notification.ts
export interface Notification {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error' | 'action_required';
  title: string;
  subtitle?: string | null;
  description?: string | null;
  created_at: string; // ISO date string
  read: boolean;
  can_delete: boolean;
  recipient?: string | null;
  action_type?: string | null;
  action_payload?: Record<string, any> | null;
}
*/

// Ensure useApi hook can be used here or replace apiGet/Put/Delete
// with direct fetch calls or a shared API client instance. 