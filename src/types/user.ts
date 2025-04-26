export interface UserInfo {
  email: string | null;
  username: string | null;
  user: string | null; // Often the display name or username again
  ip: string | null;
  groups: string[] | null; // List of group names
} 