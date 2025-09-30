export enum CommentStatus {
  ACTIVE = "active",
  DELETED = "deleted"
}

export interface Comment {
  id: string;
  entity_id: string;
  entity_type: string;
  title?: string | null;
  comment: string;
  audience?: string[] | null; // Groups who can see the comment
  status: CommentStatus;
  created_by: string;
  updated_by?: string | null;
  created_at: string; // ISO string format
  updated_at: string; // ISO string format
}

export interface CommentCreate {
  entity_id: string;
  entity_type: string;
  title?: string | null;
  comment: string;
  audience?: string[] | null;
}

export interface CommentUpdate {
  title?: string | null;
  comment?: string | null;
  audience?: string[] | null;
}

export interface CommentListResponse {
  comments: Comment[];
  total_count: number;
  visible_count: number; // Number of comments visible to current user
}

export interface CommentPermissions {
  can_modify: boolean;
  is_admin: boolean;
}

// Props for comment-related components
export interface CommentSidebarProps {
  entityType: string;
  entityId: string;
  isOpen: boolean;
  onToggle: () => void;
  className?: string;
  fetchCountOnMount?: boolean;
}

export interface CommentItemProps {
  comment: Comment;
  canModify: boolean;
  onEdit: (comment: Comment) => void;
  onDelete: (commentId: string) => void;
}