import { type } from "os";

// Based on dataproduct_schema_v0_0_1.json defined in Pydantic

// Interface for Server (matching Pydantic Server model)
export interface Server { 
  project?: string;
  dataset?: string;
  account?: string;
  database?: string;
  schema_name?: string; // aliased as 'schema' in Pydantic
  host?: string;
  topic?: string;
  location?: string;
  delimiter?: string;
  format?: string;
  table?: string;
  view?: string;
  share?: string;
  additionalProperties?: { [key: string]: string };
}

// Interface for Port (base for Input/Output)
export interface Port {
  id: string;
  name: string;
  description?: string;
  type?: string;
  location?: string;
  links?: { [key: string]: string };
  custom?: { [key: string]: any };
  tags?: string[];
}

// Interface for InputPort
export interface InputPort extends Port {
  sourceSystemId: string;
  sourceOutputPortId?: string;
}

// Interface for OutputPort
export interface OutputPort extends Port {
  status?: string;
  server?: Server;
  containsPii?: boolean;
  autoApprove?: boolean;
  dataContractId?: string;
}

// Interface for Info (matching Pydantic Info model)
export interface Info {
  title: string;
  owner_team_id?: string; // UUID of the owning team
  domain?: string;
  description?: string;
  status?: string;
  archetype?: string;
  maturity?: string; // Note: Deprecated
}

// Interface for Link (basic structure)
export interface Link {
  url: string;
  description?: string;
}

// Main DataProduct Interface (matching Pydantic DataProduct model)
export interface DataProduct {
  dataProductSpecification: string;
  id?: string;
  info: Info;
  inputPorts: InputPort[];
  outputPorts: OutputPort[];
  links: Record<string, Link>;
  custom: Record<string, any>;
  tags: string[];
  created_at?: string;
  updated_at: string;
  version: string;
  productType: string; // Use string for now, can refine to enum/union later
}

// Type for distinct values - can be simple strings or objects if needed
export type DataProductStatus = string;
export type DataProductArchetype = string;
export type DataProductOwner = string;
export type DataProductType = string; // Added for new product types

// Type for metastore table info from the backend
export interface MetastoreTableInfo {
    catalog_name: string;
    schema_name: string;
    table_name: string;
    full_name: string; // Helper for display/selection
} 