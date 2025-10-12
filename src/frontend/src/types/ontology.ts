export interface OntologyProperty {
  iri: string;
  label?: string;
  comment?: string;
  domain?: string;
  range?: string;
  property_type: 'datatype' | 'object' | 'annotation';
}

export interface OntologyConcept {
  iri: string;
  label?: string;
  comment?: string;
  concept_type: 'class' | 'concept' | 'individual';
  source_context?: string;
  parent_concepts: string[];
  child_concepts: string[];
  properties: OntologyProperty[];
  tagged_assets: Array<{
    id: string;
    name: string;
    type?: string;
    path?: string;
  }>;
  synonyms: string[];
  examples: string[];
}

export interface SemanticModel {
  name: string;
  description?: string;
  source_type: 'file' | 'database' | 'external' | 'schema';
  format?: string;
  concepts_count: number;
  properties_count: number;
  created_at?: string;
  updated_at?: string;
}

export interface ConceptHierarchy {
  concept: OntologyConcept;
  ancestors: OntologyConcept[];
  descendants: OntologyConcept[];
  siblings: OntologyConcept[];
}

export interface ConceptSearchResult {
  concept: OntologyConcept;
  relevance_score: number;
  match_type: 'label' | 'comment' | 'iri';
}

export interface TaxonomyStats {
  total_concepts: number;
  total_properties: number;
  taxonomies: SemanticModel[];
  concepts_by_type: Record<string, number>;
  top_level_concepts: number;
}

// Tree node structure for the UI
export interface ConceptTreeNode {
  concept: OntologyConcept;
  children: ConceptTreeNode[];
  isExpanded: boolean;
  level: number;
}

// Grouped concepts for tree view
export interface GroupedConcepts {
  [taxonomyName: string]: OntologyConcept[];
}