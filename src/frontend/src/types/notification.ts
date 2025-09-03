export type NotificationType = 'info' | 'success' | 'warning' | 'error' | 'action_required' | 'job_progress';

export interface Notification {
  id: string;
  type: NotificationType;
  title: string;
  subtitle?: string | null;
  description?: string | null;
  message?: string | null;  // Alternative to description for job progress
  link?: string | null;
  created_at: string; // ISO 8601 date string from backend
  updated_at?: string | null; // For tracking updates
  read: boolean;
  can_delete: boolean;
  recipient?: string | null;
  target_roles?: string[] | null;  // For role-based notifications
  action_type?: string | null;
  action_payload?: Record<string, any> | null;
  data?: Record<string, any> | null;  // Additional data for job progress etc.
} 