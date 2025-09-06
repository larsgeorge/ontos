from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from datetime import datetime


class OntologyProperty(BaseModel):
    iri: str
    label: Optional[str] = None
    comment: Optional[str] = None
    domain: Optional[str] = None
    range: Optional[str] = None
    property_type: str  # 'datatype' | 'object' | 'annotation'


class OntologyConcept(BaseModel):
    iri: str
    label: Optional[str] = None
    comment: Optional[str] = None
    concept_type: str  # 'class' | 'concept' | 'individual'
    source_context: Optional[str] = None  # The taxonomy/ontology source
    parent_concepts: List[str] = []  # Parent class/concept IRIs
    child_concepts: List[str] = []   # Child class/concept IRIs
    properties: List[OntologyProperty] = []
    tagged_assets: List[Dict[str, Any]] = []  # Linked data assets
    synonyms: List[str] = []
    examples: List[str] = []
    
    
class OntologyTaxonomy(BaseModel):
    """Represents a taxonomy/ontology source"""
    name: str
    description: Optional[str] = None
    source_type: str  # 'file' | 'database' | 'external'
    format: Optional[str] = None  # 'ttl' | 'rdf' | 'owl'
    concepts_count: int = 0
    properties_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ConceptHierarchy(BaseModel):
    """Represents hierarchical relationships for visualization"""
    concept: OntologyConcept
    ancestors: List[OntologyConcept] = []
    descendants: List[OntologyConcept] = []
    siblings: List[OntologyConcept] = []


class ConceptSearchResult(BaseModel):
    concept: OntologyConcept
    relevance_score: float = 0.0
    match_type: str = "label"  # 'label' | 'comment' | 'iri'


class TaxonomyStats(BaseModel):
    total_concepts: int
    total_properties: int
    taxonomies: List[OntologyTaxonomy]
    concepts_by_type: Dict[str, int] = {}
    top_level_concepts: int = 0