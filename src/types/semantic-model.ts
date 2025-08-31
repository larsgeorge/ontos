export type SemanticFormat = 'rdfs' | 'skos';

export interface SemanticModel {
  id: string;
  name: string;
  format: SemanticFormat;
  original_filename?: string;
  content_type?: string;
  size_bytes?: number;
  enabled: boolean;
  createdAt?: string;
  updatedAt?: string;
}

export interface SemanticModelPreview {
  id: string;
  name: string;
  format: SemanticFormat;
  preview: string;
}


