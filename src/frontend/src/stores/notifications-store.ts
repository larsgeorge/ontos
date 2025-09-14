import { create } from 'zustand';
// Removed useApi import as we use direct fetch below
import { Notification } from '@/types/notification';

interface NotificationsState {
  notifications: Notification[];
  unreadCount: number;
  isLoading: boolean;
  error: string | null;
  fetchNotifications: () => Promise<void>;
  refreshNotifications: () => void; // Simple alias to trigger fetch
  markAsRead: (notificationId: string) => Promise<void>;
  deleteNotification: (notificationId: string) => Promise<void>;
  startPolling: () => void; // Action to start polling
  stopPolling: () => void; // Action to stop polling
}

// --- API Helper Functions (using fetch directly) ---
// Base URL - adjust if needed, or use environment variables
const API_BASE_URL = ''; // Assuming API routes start from the root

const apiGet = async <T>(endpoint: string): Promise<{ data?: T, error?: string }> => {
    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`);
        if (!response.ok) {
            throw new Error(`API Error: ${response.status} ${response.statusText}`);
        }
        // Handle potential empty response for GET (though list usually returns [])
        const text = await response.text();
        const data: T = text ? JSON.parse(text) : []; // Default to empty array for lists
        return { data };
    } catch (error: any) {
         console.error(`[Store] API Error fetching ${API_BASE_URL}${endpoint}:`, error);
         return { error: error.message || 'Failed to fetch' };
    }
};

const apiPut = async (endpoint: string): Promise<{ error?: string }> => {
     try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, { method: 'PUT' });
        if (!response.ok) {
            throw new Error(`API Error: ${response.status} ${response.statusText}`);
        }
        return {}; // Success
    } catch (error: any) {
         console.error(`[Store] API Error PUT ${API_BASE_URL}${endpoint}:`, error);
         return { error: error.message || 'Failed to update' };
    }
};

const apiDelete = async (endpoint: string): Promise<{ error?: string }> => {
     try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, { method: 'DELETE' });
         if (!response.ok && response.status !== 204) { // Allow 204 No Content
            throw new Error(`API Error: ${response.status} ${response.statusText}`);
        }
        return {}; // Success
    } catch (error: any) {
         console.error(`[Store] API Error DELETE ${API_BASE_URL}${endpoint}:`, error);
         return { error: error.message || 'Failed to delete' };
    }
};

// Variable to hold the interval ID
let pollingIntervalId: NodeJS.Timeout | null = null;
const POLLING_INTERVAL = 60 * 1000; // 60 seconds

export const useNotificationsStore = create<NotificationsState>((set, get) => ({
  notifications: [],
  unreadCount: 0,
  isLoading: false,
  error: null,

  fetchNotifications: async () => {
    // Only set loading if not already loading (prevent visual flicker during polling)
    if (!get().isLoading) {
      set({ isLoading: true, error: null });
    }
    try {
      const response = await apiGet<Notification[]>('/api/notifications');

      if (response.error || !response.data) {
        throw new Error(response.error || 'Failed to fetch notifications: No data received');
      }

      const fetchedNotifications = response.data;
      const unread = fetchedNotifications.filter(n => !n.read).length;

      // Only update state if data has changed to prevent unnecessary re-renders
      if (JSON.stringify(fetchedNotifications) !== JSON.stringify(get().notifications) || unread !== get().unreadCount) {
        set({
            notifications: fetchedNotifications,
            unreadCount: unread,
            isLoading: false,
            error: null,
        });
      } else {
         // If no change, just ensure loading is false
         set({ isLoading: false, error: null }); 
      }

    } catch (error: any) {
      console.error("Error fetching notifications:", error);
      // Don't clear notifications on a failed poll, keep stale data + error
      set({ isLoading: false, error: error.message || 'An unknown error occurred' });
    }
  },

  refreshNotifications: () => {
    // Simply call fetchNotifications to refresh the data
    get().fetchNotifications();
  },

  markAsRead: async (notificationId: string) => {
    const originalNotifications = get().notifications;
    const notificationToMark = originalNotifications.find(n => n.id === notificationId);
    const originalUnreadCount = get().unreadCount;

    // Optimistic UI update
    set(state => ({
        notifications: state.notifications.map(n =>
            n.id === notificationId ? { ...n, read: true } : n
        ),
        unreadCount: notificationToMark && !notificationToMark.read
                     ? Math.max(0, state.unreadCount - 1)
                     : state.unreadCount,
    }));

    try {
       const response = await apiPut(`/api/notifications/${notificationId}/read`);
       if (response.error) {
            throw new Error(response.error);
       }
    } catch (error: any) {
       console.error(`Error marking notification ${notificationId} as read:`, error);
       // Revert optimistic update on error
       set({
            notifications: originalNotifications,
            unreadCount: originalUnreadCount,
            error: `Failed to mark as read: ${error.message}`
       });
       // Optionally trigger a toast notification here
    }
  },

  deleteNotification: async (notificationId: string) => {
    const originalNotifications = get().notifications;
    const notificationToDelete = originalNotifications.find(n => n.id === notificationId);
    const originalUnreadCount = get().unreadCount;

    // Optimistic UI update
    set(state => ({
        notifications: state.notifications.filter(n => n.id !== notificationId),
        unreadCount: notificationToDelete && !notificationToDelete.read
                     ? Math.max(0, state.unreadCount - 1)
                     : state.unreadCount,
    }));

    try {
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
         // Optionally trigger a toast notification here
    }
  },
  
  // --- Polling Actions --- 
  startPolling: () => {
      // Clear existing interval before starting a new one
      get().stopPolling(); 
      pollingIntervalId = setInterval(() => {
          get().fetchNotifications();
      }, POLLING_INTERVAL);
      // Fetch immediately when polling starts
      get().fetchNotifications(); 
  },

  stopPolling: () => {
      if (pollingIntervalId) {
          clearInterval(pollingIntervalId);
          pollingIntervalId = null;
      }
  },
}));

// --- Auto-start Polling (Optional) ---
// This starts polling as soon as the store is initialized.
// Alternatively, call startPolling() from a main component (e.g., App.tsx) after user logs in.
// useNotificationsStore.getState().startPolling(); 


// Previous notes kept for context:
// Note: We need a type definition for Notification
// Create src/types/notification.ts if it doesn't exist
/* Example src/types/notification.ts
export interface Notification {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error' | 'action_required';
  title: string;
  subtitle?: string | null;
  description?: string | null;
  link?: string | null; // Added optional link field
  created_at: string; // ISO date string
  read: boolean;
  can_delete: boolean;
  recipient?: string | null;
  action_type?: string | null;
  action_payload?: Record<string, any> | null;
}
*/ 