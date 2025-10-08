// Simplified type for list view
export type DataContractListItem = {
  id: string
  name: string
  version: string
  status: string
  owner_team_id?: string // UUID of the owning team
  created?: string
  updated?: string
}

// ODCS compliant column property
export type ColumnProperty = {
  name: string
  logicalType: string
  required?: boolean
  unique?: boolean
  description?: string
  // ODCS v3.0.2 additional property fields
  businessName?: string
  encryptedName?: string
  criticalDataElement?: boolean
  transformLogic?: string
  transformSourceObjects?: string
  transformDescription?: string
}

// ODCS compliant schema object
export type SchemaObject = {
  name: string
  physicalName?: string
  properties: ColumnProperty[]
  // Extended UC metadata
  description?: string
  tableType?: string
  owner?: string
  createdAt?: string
  updatedAt?: string
  tableProperties?: Record<string, any>
  // ODCS v3.0.2 fields
  businessName?: string
  physicalType?: string
  dataGranularityDescription?: string
}

// ODCS compliant description
export type ContractDescription = {
  usage?: string
  purpose?: string
  limitations?: string
}

// ODCS compliant team member
export type TeamMember = {
  role: string
  email: string
  name?: string
}

// ODCS compliant access control
export type AccessControl = {
  readGroups?: string[]
  writeGroups?: string[]
  adminGroups?: string[]
  classification?: string
  containsPii?: boolean
  requiresEncryption?: boolean
}

// ODCS compliant support channels
export type SupportChannels = {
  email?: string
  slack?: string
  documentation?: string
  [key: string]: string | undefined
}

// ODCS compliant SLA requirements
export type SLARequirements = {
  uptimeTarget?: number
  maxDowntimeMinutes?: number
  queryResponseTimeMs?: number
  dataFreshnessMinutes?: number
}

// ODCS v3.0.2 compliant quality rule (matches backend QualityRule model)
export type QualityRule = {
  name?: string
  description?: string
  level?: string // 'contract', 'object', 'property'
  dimension?: string // 'accuracy', 'completeness', 'conformity', 'consistency', 'coverage', 'timeliness', 'uniqueness'
  businessImpact?: string // 'operational', 'regulatory'
  severity?: string // 'info', 'warning', 'error'
  type?: string // 'text', 'library', 'sql', 'custom'
  method?: string
  schedule?: string
  scheduler?: string
  unit?: string
  tags?: string
  rule?: string
  query?: string
  engine?: string
  implementation?: string
  mustBe?: string
  mustNotBe?: string
  mustBeGt?: number
  mustBeGe?: number
  mustBeLt?: number
  mustBeLe?: number
  mustBeBetweenMin?: number
  mustBeBetweenMax?: number
}

// Server configuration (ODCS compliant)
export type ServerConfig = {
  server?: string
  type?: string
  description?: string
  environment?: string
  host?: string
  port?: number
  database?: string
  schema?: string
  catalog?: string
  project?: string
  account?: string
  region?: string
  location?: string
  properties?: Record<string, string>
}

// Full ODCS v3.0.2 compliant data contract
export interface DataContract {
  id: string
  kind: string
  apiVersion: string
  version: string
  status: string
  name: string
  tenant?: string
  domain?: string // Legacy field (domain name)
  domainId?: string // Domain ID for backend API
  dataProduct?: string
  owner_team_id?: string // UUID of the owning team
  description?: ContractDescription
  schema?: SchemaObject[]
  qualityRules?: QualityRule[]
  team?: TeamMember[]
  accessControl?: AccessControl
  support?: SupportChannels
  sla?: SLARequirements
  servers?: ServerConfig | ServerConfig[]
  customProperties?: Record<string, any>
  created?: string
  updated?: string
}

// For creating new contracts
export type DataContractCreate = {
  name: string
  version?: string
  status?: string
  owner_team_id?: string // UUID of the owning team
  kind?: string
  apiVersion?: string
  domain?: string
  domainId?: string
  tenant?: string
  dataProduct?: string
  description?: ContractDescription
  schema?: SchemaObject[]
  qualityRules?: QualityRule[]
  team?: TeamMember[]
  accessControl?: AccessControl
  support?: SupportChannels
  sla?: SLARequirements
  servers?: ServerConfig | ServerConfig[]
  customProperties?: Record<string, any>
} 