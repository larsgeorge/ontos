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
}

// ODCS compliant schema object
export type SchemaObject = {
  name: string
  physicalName?: string
  properties: ColumnProperty[]
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
  qualityRules?: Array<{
    type: string
    enabled: boolean
    threshold?: number
    query?: string
  }>
  team?: TeamMember[]
  accessControl?: AccessControl
  support?: SupportChannels
  sla?: SLARequirements
  servers?: {
    serverType?: string
    connectionString?: string
    environment?: string
  } | Array<{
    serverType?: string
    connectionString?: string
    environment?: string
  }>
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
  tenant?: string
  dataProduct?: string
  description?: ContractDescription
  schema?: SchemaObject[]
  qualityRules?: Array<{
    type: string
    enabled: boolean
    threshold?: number
    query?: string
  }>
  team?: TeamMember[]
  accessControl?: AccessControl
  support?: SupportChannels
  sla?: SLARequirements
  servers?: {
    serverType?: string
    connectionString?: string
    environment?: string
  }
  customProperties?: Record<string, any>
} 