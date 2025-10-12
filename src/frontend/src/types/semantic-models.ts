interface TaggedAsset {
  id: string;
  name: string;
  type: string;
  path: string;
}

export interface SemanticTerm {
  id: string;
  name: string;
  definition: string;
  domain: string;
  abbreviation?: string;
  synonyms: string[];
  examples: string[];
  tags: string[];
  owner: string;
  status: string;
  created_at: string;
  updated_at: string;
  source_model_id: string;
  taggedAssets?: TaggedAsset[];
}

export interface SemanticModelDefinition {
  id: string;
  name: string;
  description: string;
  scope: string;
  org_unit: string;
  domain: string;
  owner: string;
  status: string;
  tags: string[];
  terms: { [key: string]: SemanticTerm };
  parent_model_ids: string[];
  children?: SemanticModelDefinition[];
  created_at: string;
  updated_at: string;
  taggedAssets?: TaggedAsset[];
} 