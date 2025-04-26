export type NotificationType = 'info' | 'success' | 'warning' | 'error' | 'action_required';

export interface Notification {
  id: string;
  type: NotificationType;
  title: string;
  subtitle?: string | null;
  description?: string | null;
  created_at: string; // ISO 8601 date string from backend
  read: boolean;
  can_delete: boolean;
  recipient?: string | null;
  action_type?: string | null;
  action_payload?: Record<string, any> | null;
} 