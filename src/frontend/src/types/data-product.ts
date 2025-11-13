import { AssignedTag } from '@/components/ui/tag-chip';

/**
 * ODPS v1.0.0 (Open Data Product Standard) TypeScript Types
 *
 * Based on: https://github.com/bitol-io/open-data-product-standard/blob/main/schema/odps-json-schema-v1.0.0.json
 */

// ============================================================================
// ODPS v1.0.0 Enums
// ============================================================================

export enum DataProductStatus {
  DRAFT = 'draft',
  SANDBOX = 'sandbox',
  PROPOSED = 'proposed',
  UNDER_REVIEW = 'under_review',
  APPROVED = 'approved',
  ACTIVE = 'active',
  CERTIFIED = 'certified',
  DEPRECATED = 'deprecated',
  RETIRED = 'retired'
}

// ============================================================================
// ODPS v1.0.0 Shared Models
// ============================================================================

export interface AuthoritativeDefinition {
  type: string; // businessDefinition, transformationImplementation, videoTutorial, tutorial, implementation
  url: string;
  description?: string;
}

export interface CustomProperty {
  property: string; // camelCase name
  value: any; // Can be any type
  description?: string;
}

export interface Description {
  purpose?: string;
  limitations?: string;
  usage?: string;
  authoritativeDefinitions?: AuthoritativeDefinition[];
  customProperties?: CustomProperty[];
}

// ============================================================================
// ODPS v1.0.0 Port Models
// ============================================================================

// Databricks extension - Connection details for output ports
export interface Server {
  project?: string;
  dataset?: string;
  account?: string;
  database?: string;
  schema?: string; // Use 'schema' to match API (not schema_name)
  host?: string;
  topic?: string;
  location?: string;
  delimiter?: string;
  format?: string;
  table?: string;
  view?: string;
  share?: string;
  additionalProperties?: string;
}

export interface InputPort {
  // ODPS required fields
  name: string;
  version: string;
  contractId: string; // REQUIRED in ODPS!

  // ODPS optional fields
  tags?: string[];
  customProperties?: CustomProperty[];
  authoritativeDefinitions?: AuthoritativeDefinition[];

  // Databricks extensions
  assetType?: string; // table, notebook, job
  assetIdentifier?: string; // catalog.schema.table, /path/to/notebook, job_id
}

export interface SBOM {
  type: string; // Default: "external"
  url: string;
}

export interface InputContract {
  id: string; // Contract ID
  version: string; // Contract version
}

export interface OutputPort {
  // ODPS required fields
  name: string;
  version: string;

  // ODPS optional fields
  description?: string;
  type?: string; // Type of output port
  contractId?: string; // Optional link to contract
  sbom?: SBOM[];
  inputContracts?: InputContract[];
  tags?: string[];
  customProperties?: CustomProperty[];
  authoritativeDefinitions?: AuthoritativeDefinition[];

  // Databricks extensions
  assetType?: string;
  assetIdentifier?: string;
  status?: string;
  server?: Server;
  containsPii?: boolean;
  autoApprove?: boolean;
}

// ============================================================================
// ODPS v1.0.0 Management Port (NEW)
// ============================================================================

export interface ManagementPort {
  // ODPS required fields
  name: string; // Endpoint identifier or unique name
  content: string; // discoverability, observability, control, dictionary

  // ODPS optional fields
  type?: string; // rest or topic (default: "rest")
  url?: string;
  channel?: string;
  description?: string;
  tags?: string[];
  customProperties?: CustomProperty[];
  authoritativeDefinitions?: AuthoritativeDefinition[];
}

// ============================================================================
// ODPS v1.0.0 Support Channel
// ============================================================================

export interface Support {
  // ODPS required fields
  channel: string;
  url: string;

  // ODPS optional fields
  description?: string;
  tool?: string; // email, slack, teams, discord, ticket, other
  scope?: string; // interactive, announcements, issues
  invitationUrl?: string;
  tags?: string[];
  customProperties?: CustomProperty[];
  authoritativeDefinitions?: AuthoritativeDefinition[];
}

// ============================================================================
// ODPS v1.0.0 Team
// ============================================================================

export interface TeamMember {
  // ODPS required fields
  username: string; // User's username or email

  // ODPS optional fields
  name?: string;
  description?: string;
  role?: string; // owner, data steward, contributor, etc.
  dateIn?: string; // ISO date string
  dateOut?: string; // ISO date string
  replacedByUsername?: string;
  tags?: string[];
  customProperties?: CustomProperty[];
  authoritativeDefinitions?: AuthoritativeDefinition[];
}

export interface Team {
  name?: string;
  description?: string;
  members?: TeamMember[];
  tags?: string[];
  customProperties?: CustomProperty[];
  authoritativeDefinitions?: AuthoritativeDefinition[];
}

// ============================================================================
// ODPS v1.0.0 Data Product (Main Model)
// ============================================================================

export interface DataProduct {
  // ODPS v1.0.0 required fields
  apiVersion: string; // "v1.0.0"
  
  // Extensions
  owner_team_id?: string // UUID of the owning team
  owner_team_name?: string // Display name of the owning team
  kind: string; // "DataProduct"
  id: string;
  status: string; // proposed, draft, active, deprecated, retired

  // ODPS v1.0.0 optional fields
  name?: string;
  version?: string;
  domain?: string;
  tenant?: string;
  authoritativeDefinitions?: AuthoritativeDefinition[];
  description?: Description;
  customProperties?: CustomProperty[];
  tags?: (string | AssignedTag)[]; // Support both formats for flexibility
  inputPorts?: InputPort[];
  outputPorts?: OutputPort[];
  managementPorts?: ManagementPort[];
  support?: Support[];
  team?: Team;
  productCreatedTs?: string; // ISO timestamp

  // Audit fields (not in ODPS, but useful)
  created_at?: string;
  updated_at?: string;

  // Databricks extension
  project_id?: string;
}

// ============================================================================
// Request/Response Models
// ============================================================================

export interface GenieSpaceRequest {
  product_ids: string[];
}

export interface NewVersionRequest {
  new_version: string;
}

// ============================================================================
// Legacy type aliases for backward compatibility (can be removed later)
// ============================================================================

export type DataProductArchetype = string;
export type DataProductOwner = string;
export type DataProductType = string;

// ============================================================================
// Helper Types
// ============================================================================

// Type for metastore table info from the backend
export interface MetastoreTableInfo {
  catalog_name: string;
  schema_name: string;
  table_name: string;
  full_name: string;
}

// Form data types for creating/updating products
export interface DataProductFormData extends Partial<DataProduct> {
  // Additional form-specific fields if needed
}
