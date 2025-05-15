export interface DataDomain {
  id: string;
  name: string;
  description?: string | null;
  owner: string[]; // Added owner based on Pydantic model
  tags?: string[] | null; // Added tags based on Pydantic model
  parent_id?: string | null;
  parent_name?: string | null;
  children_count?: number;
  created_at?: string; // Assuming ISO string format from backend
  updated_at?: string; // Assuming ISO string format from backend
  created_by?: string; // Optional based on backend model
}

export interface DataDomainCreate {
  name: string;
  description?: string | null;
  owner: string[];
  tags?: string[] | null;
  parent_id?: string | null;
}

export type DataDomainUpdate = Partial<DataDomainCreate>; 