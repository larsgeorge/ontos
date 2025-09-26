export interface DataDomainBasicInfo {
  id: string;
  name: string;
}

export interface DataDomain {
  id: string;
  name: string;
  description?: string | null;
  owner_team_id?: string | null; // UUID of the owning team
  tags?: string[] | null; // Added tags based on Pydantic model
  parent_id?: string | null;
  parent_name?: string | null; // Kept for now, but parent_info should be primary
  children_count?: number;
  parent_info?: DataDomainBasicInfo | null;
  children_info?: DataDomainBasicInfo[];
  created_at?: string; // Assuming ISO string format from backend
  updated_at?: string; // Assuming ISO string format from backend
  created_by?: string; // Optional based on backend model
}

export interface DataDomainCreate {
  name: string;
  description?: string | null;
  owner_team_id?: string | null; // UUID of the owning team
  tags?: string[] | null;
  parent_id?: string | null;
}

export type DataDomainUpdate = Partial<DataDomainCreate>; 