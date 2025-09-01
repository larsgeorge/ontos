export type DataContractListItem = {
  id: string
  name: string
  description?: string
  version: string
  status: string
  owner: string
  format?: string
  created?: string
  updated?: string
}

export type DataContractDraft = {
  name: string
  version: string
  status: string
  owner: string
  kind?: string
  apiVersion?: string
  domainId?: string
  contract_text: string
  format: 'json' | 'yaml' | 'text'
}

export interface DataContract {
  id: string;
  name: string;
  description?: string;
  version: string;
  status: string;
  owner: string;
  format: string;
  contract_text: string;
  created: string;
  updated: string;
  schema?: {
    fields: Array<{
      name: string;
      type: string;
      required: boolean;
    }>;
  };
  validation_rules?: string[];
  dataProducts: string[];
} 