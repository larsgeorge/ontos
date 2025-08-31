export type EntityType = 'data_domain' | 'data_product' | 'data_contract';

export interface EntitySemanticLink {
  id: string;
  entity_id: string;
  entity_type: EntityType;
  iri: string;
  label?: string;
}


