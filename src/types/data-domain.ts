export interface DataDomain {
  id: string;
  name: string;
  description?: string | null;
  created_at?: string; // Assuming ISO string format from backend
  updated_at?: string; // Assuming ISO string format from backend
  created_by?: string; // Optional based on backend model
}

export interface DataDomainCreate {
  name: string;
  description?: string | null;
}

export type DataDomainUpdate = Partial<DataDomainCreate>; 