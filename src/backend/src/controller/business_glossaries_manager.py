import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
import os
from pathlib import Path
from sqlalchemy.orm import Session

import yaml

from src.models.business_glossary import BusinessGlossary, Domain, GlossaryTerm
from src.models.ontology import (
    OntologyConcept,
    OntologyTaxonomy, 
    ConceptHierarchy,
    TaxonomyStats,
    ConceptSearchResult
)

# Import Search Interfaces
from src.common.search_interfaces import SearchableAsset, SearchIndexItem
# Import the registry decorator
from src.common.search_registry import searchable_asset

from src.common.logging import get_logger
logger = get_logger(__name__)

# Inherit from SearchableAsset
@searchable_asset
class BusinessGlossariesManager(SearchableAsset):
    def __init__(self, data_dir: Path, semantic_models_manager=None):
        self._domains: Dict[str, Domain] = {}
        self._glossaries: Dict[str, BusinessGlossary] = {}
        self._data_dir = data_dir
        self._semantic_models_manager = semantic_models_manager
        self._load_initial_data()

    def _load_initial_data(self):
        """Loads initial data from the YAML file if it exists."""
        yaml_path = self._data_dir / 'business_glossaries.yaml'
        if yaml_path.exists():
            try:
                self.load_from_yaml(str(yaml_path))
                logger.info(f"Successfully loaded initial business glossary data from {yaml_path}")
            except Exception as e:
                logger.error(f"Error loading initial business glossary data from {yaml_path}: {e!s}")
        else:
            logger.warning(f"Initial business glossary YAML file not found at {yaml_path}")
    
    def set_semantic_models_manager(self, semantic_models_manager):
        """Set the semantic models manager after initialization"""
        self._semantic_models_manager = semantic_models_manager

    def create_term(self,
                   name: str,
                   definition: str,
                   domain: str,
                   owner: str,
                   synonyms: List[str] = None,
                   related_terms: List[str] = None,
                   tags: List[str] = None,
                   examples: List[str] = None,
                   source: str = None,
                   taggedAssets: List[Dict[str, Any]] = None) -> GlossaryTerm:
        """Create a new glossary term"""
        term_id = str(uuid.uuid4())
        now = datetime.utcnow()

        term = GlossaryTerm(
            id=term_id,
            name=name,
            definition=definition,
            domain=domain,
            owner=owner,
            status="active",
            created=now,
            updated=now,
            synonyms=synonyms or [],
            related_terms=related_terms or [],
            tags=tags or [],
            examples=examples or [],
            source=source,
            taggedAssets=taggedAssets or []
        )

        return term

    def get_term(self, term_id: str) -> Optional[GlossaryTerm]:
        """Get a glossary term by ID"""
        for glossary in self._glossaries.values():
            if term_id in glossary.terms:
                return glossary.terms[term_id]
        return None

    def list_terms(self) -> List[GlossaryTerm]:
        """List all glossary terms"""
        terms = []
        for glossary in self._glossaries.values():
            terms.extend(list(glossary.terms.values()))
        return terms

    def update_term(self, term_id: str, **kwargs) -> Optional[GlossaryTerm]:
        """Update a glossary term"""
        for glossary in self._glossaries.values():
            if term_id in glossary.terms:
                term = glossary.terms[term_id]
                for key, value in kwargs.items():
                    if hasattr(term, key):
                        setattr(term, key, value)
                term.updated = datetime.utcnow()
                return term
        return None

    def delete_term(self, term_id: str) -> bool:
        """Delete a glossary term"""
        for glossary in self._glossaries.values():
            if term_id in glossary.terms:
                del glossary.terms[term_id]
                return True
        return False

    def search_terms(self, query: str) -> List[GlossaryTerm]:
        """Search for glossary terms"""
        query = query.lower()
        results = []

        for glossary in self._glossaries.values():
            for term in glossary.terms.values():
                if (query in term.name.lower() or
                    query in term.definition.lower() or
                    any(query in syn.lower() for syn in term.synonyms)):
                    results.append(term)

        return results

    # Domain methods
    def create_domain(self, id: str, name: str, description: str = None) -> Domain:
        """Create a new domain"""
        domain = Domain(
            id=id,
            name=name,
            description=description
        )
        self._domains[id] = domain
        return domain

    def get_domain(self, domain_id: str) -> Optional[Domain]:
        """Get a domain by ID"""
        return self._domains.get(domain_id)

    def list_domains(self) -> List[Domain]:
        """List all domains"""
        return list(self._domains.values())

    def update_domain(self, domain_id: str, **kwargs) -> Optional[Domain]:
        """Update a domain"""
        domain = self._domains.get(domain_id)
        if not domain:
            return None

        for key, value in kwargs.items():
            if hasattr(domain, key):
                setattr(domain, key, value)

        return domain

    def delete_domain(self, domain_id: str) -> bool:
        """Delete a domain"""
        if domain_id in self._domains:
            del self._domains[domain_id]
            return True
        return False

    def load_from_yaml(self, file_path: str):
        """Load glossaries from YAML file"""
        with open(file_path) as f:
            data = yaml.safe_load(f)
            if not data:
                return

        # Clear existing data
        self._glossaries.clear()
        self._domains.clear()

        # Load domains
        for domain_data in data.get('domains', []):
            domain = Domain(
                id=domain_data['id'],
                name=domain_data['name'],
                description=domain_data.get('description')
            )
            self._domains[domain.id] = domain

        # Load glossaries
        for glossary_data in data.get('glossaries', []):
            # Convert terms list to dictionary if needed
            terms_data = glossary_data.get('terms', [])
            terms_dict = {}

            # Handle both list and dict formats
            if isinstance(terms_data, list):
                for term in terms_data:
                    terms_dict[term['id']] = GlossaryTerm(
                        id=term['id'],
                        name=term['name'],
                        definition=term['definition'],
                        domain=term['domain'],
                        abbreviation=term.get('abbreviation'),
                        synonyms=term.get('synonyms', []),
                        examples=term.get('examples', []),
                        tags=term.get('tags', []),
                        owner=term.get('owner', ''),
                        status=term.get('status', 'active'),
                        created_at=datetime.fromisoformat(term['created_at'].replace('Z', '+00:00')),
                        updated_at=datetime.fromisoformat(term['updated_at'].replace('Z', '+00:00')),
                        source_glossary_id=glossary_data['id'],
                        taggedAssets=term.get('taggedAssets', [])
                    )
            else:
                for term_id, term in terms_data.items():
                    terms_dict[term_id] = GlossaryTerm(
                        id=term['id'],
                        name=term['name'],
                        definition=term['definition'],
                        domain=term['domain'],
                        abbreviation=term.get('abbreviation'),
                        synonyms=term.get('synonyms', []),
                        examples=term.get('examples', []),
                        tags=term.get('tags', []),
                        owner=term.get('owner', ''),
                        status=term.get('status', 'active'),
                        created_at=datetime.fromisoformat(term['created_at'].replace('Z', '+00:00')),
                        updated_at=datetime.fromisoformat(term['updated_at'].replace('Z', '+00:00')),
                        source_glossary_id=glossary_data['id'],
                        taggedAssets=term.get('taggedAssets', [])
                    )

            # Create glossary with converted terms
            glossary = BusinessGlossary(
                id=glossary_data['id'],
                name=glossary_data['name'],
                description=glossary_data['description'],
                scope=glossary_data['scope'],
                org_unit=glossary_data['org_unit'],
                domain=glossary_data['domain'],
                parent_glossary_ids=glossary_data.get('parent_glossary_ids', []),
                tags=glossary_data.get('tags', []),
                owner=glossary_data.get('owner', ''),
                status=glossary_data.get('status', 'active'),
                created_at=datetime.fromisoformat(glossary_data['created_at'].replace('Z', '+00:00')),
                updated_at=datetime.fromisoformat(glossary_data['updated_at'].replace('Z', '+00:00')),
                terms=terms_dict
            )

            self._glossaries[glossary.id] = glossary

        return True

    def create_glossary(self, name: str, description: str, scope: str, org_unit: str,
                       domain: str, parent_glossary_ids: List[str] = None, tags: List[str] = None) -> BusinessGlossary:
        """Create a new business glossary"""
        glossary = BusinessGlossary(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            scope=scope,
            org_unit=org_unit,
            domain=domain,
            parent_glossary_ids=parent_glossary_ids or [],
            tags=tags or []
        )
        self._glossaries[glossary.id] = glossary
        return glossary

    def get_glossary(self, glossary_id: str) -> Optional[BusinessGlossary]:
        """Get a glossary by ID"""
        return self._glossaries.get(glossary_id)

    def list_glossaries(self) -> List[BusinessGlossary]:
        """Get all glossaries"""
        return list(self._glossaries.values())

    def get_combined_terms(self, org_unit: str) -> List[GlossaryTerm]:
        """Get combined terms for an organizational unit"""
        # Find all relevant glossaries
        relevant_glossaries = self._get_relevant_glossaries(org_unit)

        # Combine terms, with more specific terms overriding general ones
        combined_terms: Dict[str, GlossaryTerm] = {}
        for glossary in relevant_glossaries:
            for term in glossary.terms.values():
                # Terms from more specific glossaries override general ones
                if term.name not in combined_terms:
                    combined_terms[term.name] = term

        return list(combined_terms.values())

    def _get_relevant_glossaries(self, org_unit: str) -> List[BusinessGlossary]:
        """Get all glossaries relevant to an organizational unit"""
        relevant_glossaries = []
        visited: Set[str] = set()

        def add_glossary_and_parents(glossary: BusinessGlossary):
            if glossary.id in visited:
                return
            visited.add(glossary.id)
            relevant_glossaries.append(glossary)

            # Add parent glossaries
            for parent_id in glossary.parent_glossary_ids:
                parent = self._glossaries.get(parent_id)
                if parent:
                    add_glossary_and_parents(parent)

        # Find glossaries for this org unit and add them with their parents
        for glossary in self._glossaries.values():
            if glossary.org_unit == org_unit:
                add_glossary_and_parents(glossary)

        # Sort by scope specificity (company -> division -> department -> team)
        scope_order = {"company": 0, "division": 1, "department": 2, "team": 3}
        relevant_glossaries.sort(key=lambda g: scope_order.get(g.scope, 99))

        return relevant_glossaries

    def update_glossary(self, glossary_id: str, updates: dict) -> Optional[BusinessGlossary]:
        """Update a glossary"""
        glossary = self._glossaries.get(glossary_id)
        if not glossary:
            return None

        for key, value in updates.items():
            if hasattr(glossary, key):
                setattr(glossary, key, value)
        glossary.updated_at = datetime.utcnow()
        return glossary

    def delete_glossary(self, glossary_id: str) -> bool:
        """Delete a glossary"""
        return bool(self._glossaries.pop(glossary_id, None))

    def save_to_yaml(self, file_path: str) -> bool:
        """Save glossaries to YAML file"""
        try:
            data = {
                'glossaries': [
                    {
                        **g.to_dict(),
                        'terms': [t.to_dict() for t in g.terms.values()]
                    }
                    for g in self._glossaries.values()
                ]
            }
            with open(file_path, 'w') as f:
                yaml.safe_dump(data, f, sort_keys=False)
            return True
        except Exception as e:
            print(f"Error saving to YAML: {e}")
            return False

    def term_to_dict(self, term: GlossaryTerm) -> dict:
        """Convert a term to dictionary"""
        return {
            'id': term.id,
            'name': term.name,
            'definition': term.definition,
            'domain': term.domain,
            'abbreviation': term.abbreviation,
            'synonyms': term.synonyms,
            'examples': term.examples,
            'tags': term.tags,
            'owner': term.owner,
            'status': term.status,
            'created_at': term.created_at.isoformat(),
            'updated_at': term.updated_at.isoformat(),
            'source_glossary_id': term.source_glossary_id
        }

    def glossary_to_dict(self, glossary: BusinessGlossary) -> dict:
        """Convert a glossary to dictionary"""
        return {
            'id': glossary.id,
            'name': glossary.name,
            'description': glossary.description,
            'scope': glossary.scope,
            'org_unit': glossary.org_unit,
            'domain': glossary.domain,
            'parent_glossary_ids': glossary.parent_glossary_ids,
            'tags': glossary.tags,
            'owner': glossary.owner,
            'status': glossary.status,
            'created_at': glossary.created_at.isoformat(),
            'updated_at': glossary.updated_at.isoformat()
        }

    def add_term_to_glossary(self, glossary: BusinessGlossary, term: GlossaryTerm) -> None:
        """Add a term to a glossary"""
        term.source_glossary_id = glossary.id
        glossary.terms[term.id] = term

    def get_term_from_glossary(self, glossary: BusinessGlossary, term_id: str) -> Optional[GlossaryTerm]:
        """Get a term from a glossary"""
        return glossary.terms.get(term_id)

    def update_term_in_glossary(self, glossary: BusinessGlossary, term_id: str, updates: dict) -> Optional[GlossaryTerm]:
        """Update a term in a glossary"""
        if term_id not in glossary.terms:
            return None
        term = glossary.terms[term_id]
        for key, value in updates.items():
            if hasattr(term, key):
                setattr(term, key, value)
        term.updated_at = datetime.utcnow()
        return term

    def delete_term_from_glossary(self, glossary: BusinessGlossary, term_id: str) -> bool:
        """Delete a term from a glossary"""
        return bool(glossary.terms.pop(term_id, None))

    def get_counts(self):
        domain_count = len(self._domains)
        glossary_count = len(self._glossaries)
        term_count = sum(len(g.terms) for g in self._glossaries.values())
        return {
            "domains": domain_count,
            "glossaries": glossary_count,
            "terms": term_count
        }

    # --- Implementation of SearchableAsset --- 
    def get_search_index_items(self) -> List[SearchIndexItem]:
        """Fetches glossary terms and maps them to SearchIndexItem format."""
        logger.info("Fetching glossary terms for search indexing...")
        items = []
        try:
            # Use the existing list_terms method
            terms = self.list_terms()
            
            for term in terms:
                if not term.id or not term.name:
                    logger.warning(f"Skipping term due to missing id or name: {term}")
                    continue
                    
                items.append(
                    SearchIndexItem(
                        id=f"term::{term.id}",
                        type="glossary-term",
                        feature_id="business-glossary",
                        title=term.name,
                        description=term.definition or "",
                        # Adjust link format based on frontend routing
                        link=f"/business-glossaries?termId={term.id}", 
                        tags=term.tags or []
                        # Add other fields if needed (e.g., domain, owner)
                        # domain=term.domain,
                        # owner=term.owner,
                    )
                )
            logger.info(f"Prepared {len(items)} glossary terms for search index.")
            return items
        except Exception as e:
            logger.error(f"Error fetching or mapping glossary terms for search: {e}", exc_info=True)
            return [] # Return empty list on error

    # --- New Ontology-based Methods ---
    
    def get_taxonomies(self) -> List[OntologyTaxonomy]:
        """Get all available taxonomies from the semantic knowledge graph"""
        if not self._semantic_models_manager:
            logger.warning("Semantic models manager not available")
            return []
        
        return self._semantic_models_manager.get_taxonomies()
    
    def get_concepts_by_taxonomy(self, taxonomy_name: str = None) -> List[OntologyConcept]:
        """Get concepts from a specific taxonomy or all taxonomies"""
        if not self._semantic_models_manager:
            logger.warning("Semantic models manager not available")
            return []
        
        return self._semantic_models_manager.get_concepts_by_taxonomy(taxonomy_name)
    
    def get_concept_details(self, concept_iri: str) -> Optional[OntologyConcept]:
        """Get detailed information about a specific concept"""
        if not self._semantic_models_manager:
            logger.warning("Semantic models manager not available")
            return None
        
        return self._semantic_models_manager.get_concept_details(concept_iri)
    
    def get_concept_hierarchy(self, concept_iri: str) -> Optional[ConceptHierarchy]:
        """Get hierarchical relationships for a concept"""
        if not self._semantic_models_manager:
            logger.warning("Semantic models manager not available")
            return None
        
        return self._semantic_models_manager.get_concept_hierarchy(concept_iri)
    
    def search_concepts(self, query: str, taxonomy_name: str = None, limit: int = 50) -> List[ConceptSearchResult]:
        """Search for concepts by text query"""
        if not self._semantic_models_manager:
            logger.warning("Semantic models manager not available")
            return []
        
        return self._semantic_models_manager.search_ontology_concepts(query, taxonomy_name, limit)
    
    def get_taxonomy_stats(self) -> TaxonomyStats:
        """Get statistics about loaded taxonomies"""
        if not self._semantic_models_manager:
            logger.warning("Semantic models manager not available")
            return TaxonomyStats(
                total_concepts=0,
                total_properties=0,
                taxonomies=[],
                concepts_by_type={},
                top_level_concepts=0
            )
        
        return self._semantic_models_manager.get_taxonomy_stats()
    
    def get_grouped_concepts(self) -> Dict[str, List[OntologyConcept]]:
        """Get all concepts grouped by taxonomy source"""
        if not self._semantic_models_manager:
            logger.warning("Semantic models manager not available")
            return {}
            
        concepts = self.get_concepts_by_taxonomy()
        grouped = {}
        
        logger.info(f"Processing {len(concepts)} total concepts from knowledge graph")
        
        for concept in concepts:
            source = concept.source_context or "Unassigned"
            if source not in grouped:
                grouped[source] = []
            grouped[source].append(concept)
        
        # Sort concepts within each group by label or IRI
        for source in grouped:
            grouped[source].sort(key=lambda c: c.label or c.iri)
            logger.info(f"Grouped taxonomy '{source}': {len(grouped[source])} concepts")
        
        return grouped
    
    def get_top_level_concepts_by_taxonomy(self, taxonomy_name: str = None) -> List[OntologyConcept]:
        """Get only top-level concepts (those without parents)"""
        all_concepts = self.get_concepts_by_taxonomy(taxonomy_name)
        return [c for c in all_concepts if not c.parent_concepts]
