import { AssignedTag } from '@/components/ui/tag-chip';

export enum MemberType {
  USER = "user",
  GROUP = "group"
}

export interface TeamMember {
  id: string;
  team_id: string;
  member_type: MemberType;
  member_identifier: string;
  member_name: string; // Display name for UI
  app_role_override?: string | null;
  role_override?: string | null; // Alias for compatibility
  created_at: string;
  updated_at: string;
  added_by: string;
}

export interface TeamMemberCreate {
  member_type: MemberType;
  member_identifier: string;
  app_role_override?: string | null;
}

export interface TeamMemberUpdate {
  app_role_override?: string | null;
}

export interface Team {
  id: string;
  name: string;
  title?: string | null;
  description?: string | null;
  domain_id?: string | null;
  domain_name?: string | null; // For display
  tags?: AssignedTag[] | null;
  metadata?: Record<string, any> | null;
  created_at: string;
  updated_at: string;
  created_by: string;
  updated_by: string;
  members: TeamMember[];
}

// Alias for compatibility with existing code
export type TeamRead = Team;

export interface TeamCreate {
  name: string;
  title?: string | null;
  description?: string | null;
  domain_id?: string | null;
  tags?: (string | AssignedTag)[] | null;
  metadata?: Record<string, any> | null;
}

export interface TeamUpdate {
  name?: string;
  title?: string | null;
  description?: string | null;
  domain_id?: string | null;
  tags?: (string | AssignedTag)[] | null;
  metadata?: Record<string, any> | null;
}

export interface TeamSummary {
  id: string;
  name: string;
  title?: string | null;
  domain_id?: string | null;
  member_count: number;
}