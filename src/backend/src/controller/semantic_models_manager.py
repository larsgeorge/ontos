from typing import List, Optional, Dict, Any
from pathlib import Path
from rdflib import Graph, ConjunctiveGraph, Dataset
from rdflib.namespace import RDF, RDFS, SKOS
from rdflib import URIRef, Literal, Namespace
from sqlalchemy.orm import Session

from src.db_models.semantic_models import SemanticModelDb
from src.models.semantic_models import (
    SemanticModel,
    SemanticModelCreate,
    SemanticModelUpdate,
    SemanticModelPreview,
)
from src.models.ontology import (
    OntologyConcept,
    OntologyProperty,
    OntologyTaxonomy,
    ConceptHierarchy,
    TaxonomyStats,
    ConceptSearchResult
)
from src.repositories.semantic_models_repository import semantic_models_repo
from src.common.logging import get_logger


logger = get_logger(__name__)


class SemanticModelsManager:
    def __init__(self, db: Session, data_dir: Optional[Path] = None):
        self._db = db
        self._data_dir = data_dir or Path(__file__).parent.parent / "data"
        # Use ConjunctiveGraph to support named graphs/contexts
        self._graph = ConjunctiveGraph()
        logger.info(f"SemanticModelsManager initialized with data_dir: {self._data_dir}")
        # Load file-based taxonomies immediately
        try:
            self.rebuild_graph_from_enabled()
        except Exception as e:
            logger.error(f"Failed to rebuild graph during initialization: {e}")

    def list(self) -> List[SemanticModel]:
        items = semantic_models_repo.get_multi(self._db)
        return [self._to_api(m) for m in items]

    def get(self, model_id: str) -> Optional[SemanticModel]:
        m = semantic_models_repo.get(self._db, id=model_id)
        return self._to_api(m) if m else None

    def create(self, data: SemanticModelCreate, created_by: Optional[str]) -> SemanticModel:
        db_obj = semantic_models_repo.create(self._db, obj_in=data)
        if created_by:
            db_obj.created_by = created_by
            db_obj.updated_by = created_by
            self._db.add(db_obj)
        self._db.flush()
        self._db.refresh(db_obj)
        return self._to_api(db_obj)

    def update(self, model_id: str, update: SemanticModelUpdate, updated_by: Optional[str]) -> Optional[SemanticModel]:
        db_obj = semantic_models_repo.get(self._db, id=model_id)
        if not db_obj:
            return None
        updated = semantic_models_repo.update(self._db, db_obj=db_obj, obj_in=update)
        if updated_by:
            updated.updated_by = updated_by
            self._db.add(updated)
        self._db.flush()
        self._db.refresh(updated)
        return self._to_api(updated)

    def replace_content(self, model_id: str, content_text: str, original_filename: Optional[str], content_type: Optional[str], size_bytes: Optional[int], updated_by: Optional[str]) -> Optional[SemanticModel]:
        db_obj = semantic_models_repo.get(self._db, id=model_id)
        if not db_obj:
            return None
        db_obj.content_text = content_text
        if original_filename is not None:
            db_obj.original_filename = original_filename
        if content_type is not None:
            db_obj.content_type = content_type
        if size_bytes is not None:
            db_obj.size_bytes = str(size_bytes)
        if updated_by:
            db_obj.updated_by = updated_by
        self._db.add(db_obj)
        self._db.flush()
        self._db.refresh(db_obj)
        return self._to_api(db_obj)

    def delete(self, model_id: str) -> bool:
        obj = semantic_models_repo.remove(self._db, id=model_id)
        return obj is not None

    def preview(self, model_id: str, max_chars: int = 2000) -> Optional[SemanticModelPreview]:
        db_obj = semantic_models_repo.get(self._db, id=model_id)
        if not db_obj:
            return None
        return SemanticModelPreview(
            id=db_obj.id,
            name=db_obj.name,
            format=db_obj.format,  # type: ignore
            preview=db_obj.content_text[:max_chars] if db_obj.content_text else ""
        )

    def _to_api(self, db_obj: SemanticModelDb) -> SemanticModel:
        return SemanticModel(
            id=db_obj.id,
            name=db_obj.name,
            format=db_obj.format,  # type: ignore
            original_filename=db_obj.original_filename,
            content_type=db_obj.content_type,
            size_bytes=int(db_obj.size_bytes) if db_obj.size_bytes is not None and str(db_obj.size_bytes).isdigit() else None,
            enabled=db_obj.enabled,
            createdAt=db_obj.created_at,
            updatedAt=db_obj.updated_at,
        )

    # --- Initial Data Loading ---
    def load_initial_data(self, db: Session) -> None:
        try:
            base_dir = Path(self._data_dir) / "semantic_models"
            if not base_dir.exists() or not base_dir.is_dir():
                logger.info(f"Semantic models directory not found: {base_dir}")
                return
            from src.models.semantic_models import SemanticModelCreate

            def detect_format(filename: str, content_type: Optional[str]) -> str:
                lower = (filename or "").lower()
                if lower.endswith(".ttl"):
                    return "skos"
                return "rdfs"

            for f in base_dir.iterdir():
                if not f.is_file():
                    continue
                if not any(str(f.name).lower().endswith(ext) for ext in [".ttl", ".rdf", ".xml", ".skos"]):
                    continue
                try:
                    content = f.read_text(encoding="utf-8")
                except Exception as e:
                    logger.warning(f"Skipping semantic model file {f}: {e}")
                    continue

                existing = semantic_models_repo.get_by_name(self._db, name=f.name)
                if existing:
                    logger.debug(f"Semantic model already exists, skipping: {f.name}")
                    continue

                fmt = detect_format(f.name, None)
                create = SemanticModelCreate(
                    name=f.name,
                    format=fmt,  # type: ignore
                    content_text=content,
                    original_filename=f.name,
                    content_type=None,
                    size_bytes=len(content.encode("utf-8")),
                    enabled=True,
                )
                self.create(create, created_by="system@startup")
            db.commit()
            logger.info("Semantic models initial data loaded (if any).")
            # Build the in-memory graph from enabled models after initial load
            self.on_models_changed()
        except Exception as e:
            logger.error(f"Failed loading initial semantic models: {e}")

    # --- Graph Management ---
    def _parse_into_graph(self, content_text: str, fmt: str) -> None:
        if fmt == "skos":
            # Common serializations for SKOS examples: turtle
            self._graph.parse(data=content_text, format="turtle")
        else:
            # Assume RDF/XML for RDFS
            self._graph.parse(data=content_text, format="xml")

    def _parse_into_graph_context(self, content_text: str, fmt: str, context: Graph) -> None:
        """Parse content into a specific named graph context"""
        if fmt == "skos":
            context.parse(data=content_text, format="turtle")
        else:
            # Assume RDF/XML for RDFS
            context.parse(data=content_text, format="xml")
    
    def _load_database_glossaries_into_graph(self) -> None:
        """Load database glossaries as RDF triples into named graphs"""
        try:
            # We'll need to import the business glossaries manager to avoid circular imports
            # For now, we'll defer this implementation
            logger.debug("Database glossary loading will be implemented when business glossaries manager is updated")
        except Exception as e:
            logger.warning(f"Failed to load database glossaries into graph: {e}")

    def rebuild_graph_from_enabled(self) -> None:
        logger.info("Starting to rebuild graph from enabled models and taxonomies")
        self._graph = ConjunctiveGraph()
        
        # Load database-backed semantic models into named graphs
        items = semantic_models_repo.get_multi(self._db)
        for it in items:
            if not it.enabled:
                continue
            try:
                context_name = f"urn:semantic-model:{it.name}"
                context = self._graph.get_context(context_name)
                self._parse_into_graph_context(it.content_text or "", it.format, context)
                logger.debug(f"Loaded semantic model '{it.name}' into context '{context_name}'")
            except Exception as e:
                logger.warning(f"Skipping model '{it.name}' due to parse error: {e}")
        
        # Load file-based taxonomies into named graphs
        try:
            taxonomy_dir = self._data_dir / "taxonomies"
            logger.info(f"Looking for taxonomies in directory: {taxonomy_dir}")
            if taxonomy_dir.exists() and taxonomy_dir.is_dir():
                taxonomy_files = list(taxonomy_dir.glob("*.ttl"))
                logger.info(f"Found {len(taxonomy_files)} TTL files: {[f.name for f in taxonomy_files]}")
                for f in taxonomy_files:
                    if not f.is_file():
                        continue
                    try:
                        context_name = f"urn:taxonomy:{f.stem}"
                        context = self._graph.get_context(context_name)
                        context.parse(f.as_posix(), format='turtle')
                        triples_count = len(context)
                        logger.info(f"Successfully loaded taxonomy '{f.name}' into context '{context_name}' with {triples_count} triples")
                    except Exception as e:
                        logger.error(f"Failed loading taxonomy {f.name}: {e}")
            else:
                logger.warning(f"Taxonomy directory does not exist or is not a directory: {taxonomy_dir}")
        except Exception as e:
            logger.error(f"Failed to load file-based taxonomies: {e}")
        
        # Always-on ontologies from src/schemas/rdf
        try:
            rdf_dir = Path(__file__).parent.parent / "schemas" / "rdf"
            if rdf_dir.exists() and rdf_dir.is_dir():
                for f in rdf_dir.iterdir():
                    if not f.is_file():
                        continue
                    name = f.name.lower()
                    try:
                        context_name = f"urn:schema:{f.stem}"
                        context = self._graph.get_context(context_name)
                        if name.endswith('.ttl'):
                            context.parse(f.as_posix(), format='turtle')
                        elif name.endswith('.rdf') or name.endswith('.xml'):
                            context.parse(f.as_posix(), format='xml')
                        logger.debug(f"Loaded schema '{f.name}' into context '{context_name}'")
                    except Exception as e:
                        logger.warning(f"Failed loading schema {f.name}: {e}")
        except Exception as e:
            logger.warning(f"Failed to load built-in schemas: {e}")
        
        # Load database glossaries into named graphs
        self._load_database_glossaries_into_graph()
        
        # Add rdfs:seeAlso links from entity-semantic links
        try:
            from src.repositories.semantic_links_repository import entity_semantic_links_repo
            links = entity_semantic_links_repo.list_all(self._db)
            context_name = "urn:semantic-links"
            context = self._graph.get_context(context_name)
            for link in links:
                subj = URIRef(f"urn:ucapp:{link.entity_type}:{link.entity_id}")
                obj = URIRef(link.iri)
                context.add((subj, RDFS.seeAlso, obj))
        except Exception as e:
            logger.warning(f"Failed to incorporate semantic entity links into graph: {e}")

    # Call after create/update/delete/enable/disable
    def on_models_changed(self) -> None:
        try:
            self.rebuild_graph_from_enabled()
        except Exception as e:
            logger.error(f"Failed to rebuild RDF graph: {e}")

    def query(self, sparql: str) -> List[dict]:
        # Return a simplified list of dicts for rows
        results = []
        qres = self._graph.query(sparql)
        for row in qres:
            # rdflib QueryResult rows are tuple-like
            result_row = {}
            for idx, var in enumerate(qres.vars):
                key = str(var)
                val = row[idx]
                result_row[key] = str(val) if val is not None else None
            results.append(result_row)
        return results

    # Simple prefix search over resources and properties (case-insensitive contains)
    def prefix_search(self, prefix: str, limit: int = 20) -> List[dict]:
        q = prefix.lower()
        seen = set()
        results: List[dict] = []
        for s, p, o in self._graph:
            for term, kind in ((s, 'resource'), (p, 'property')):
                if term is None:
                    continue
                name = str(term)
                if q in name.lower() and name not in seen:
                    results.append({ 'value': name, 'type': kind })
                    seen.add(name)
                    if len(results) >= limit:
                        return results
        return results

    # Search for classes/concepts with optional text filter
    def search_concepts(self, text_filter: str = "", limit: int = 50) -> List[dict]:
        sparql_query = f"""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        SELECT DISTINCT ?class_iri ?label
        WHERE {{
            {{
                ?class_iri a rdfs:Class .
            }}
            UNION
            {{
                ?class_iri rdfs:subClassOf ?other .
            }}
            UNION
            {{
                ?class_iri a skos:Concept .
            }}
            OPTIONAL {{ ?class_iri rdfs:label ?label }}
            OPTIONAL {{ ?class_iri skos:prefLabel ?label }}
            {f'FILTER(CONTAINS(LCASE(STR(?class_iri)), LCASE("{text_filter}")) || CONTAINS(LCASE(STR(?label)), LCASE("{text_filter}")))' if text_filter.strip() else ''}
        }}
        ORDER BY ?class_iri
        LIMIT {limit}
        """
        
        try:
            raw_results = self.query(sparql_query)
            results = []
            for row in raw_results:
                class_iri = row.get('class_iri', '')
                label = row.get('label', '')
                
                # Use label if available, otherwise extract last part of IRI
                if label and label.strip():
                    display_name = label.strip()
                else:
                    # Extract the last segment after # or /
                    if '#' in class_iri:
                        display_name = class_iri.split('#')[-1]
                    elif '/' in class_iri:
                        display_name = class_iri.split('/')[-1]
                    else:
                        display_name = class_iri
                
                results.append({
                    'value': class_iri,
                    'label': display_name,
                    'type': 'class'
                })
            
            return results
        except Exception as e:
            # If SPARQL fails, fall back to empty results
            return []

    # Outgoing neighbors of a resource: returns distinct predicate/object pairs
    def neighbors(self, resource_iri: str, limit: int = 200) -> List[dict]:
        from rdflib import URIRef
        from rdflib.namespace import RDF
        results: List[dict] = []
        seen: set[tuple[str, str, str]] = set()  # (direction, predicate, display)
        count = 0
        uri = URIRef(resource_iri)

        def detect_type(node: any) -> str:
            if not isinstance(node, URIRef):
                return 'literal'
            try:
                for _ in self._graph.triples((None, node, None)):
                    return 'property'
            except Exception:
                pass
            try:
                for _ in self._graph.triples((node, RDF.type, RDF.Property)):
                    return 'property'
            except Exception:
                pass
            return 'resource'

        def add(direction: str, predicate, display_node, step_node):
            nonlocal count
            display_str = str(display_node)
            key = (direction, str(predicate), display_str)
            if key in seen:
                return
            seen.add(key)
            item = {
                'direction': direction,
                'predicate': str(predicate),
                'display': display_str,
                'displayType': detect_type(display_node),
                'stepIri': str(step_node) if isinstance(step_node, URIRef) else None,
                'stepIsResource': isinstance(step_node, URIRef),
            }
            results.append(item)
            count += 1

        # 1) Outgoing (uri as subject) → show object
        for _, p, o in self._graph.triples((uri, None, None)):
            if count >= limit:
                break
            add('outgoing', p, o, o)

        # 2) Incoming (uri as object) → show subject
        for s, p, _ in self._graph.triples((None, None, uri)):
            if count >= limit:
                break
            add('incoming', p, s, s)

        # 3) Predicate usage (uri as predicate) → show both subject and object entries
        for s, _, o in self._graph.triples((None, uri, None)):
            if count >= limit:
                break
            add('predicate', uri, s, s)
            if count >= limit:
                break
            add('predicate', uri, o, o)

        return results

    # --- New Ontology Methods ---
    
    def get_taxonomies(self) -> List[OntologyTaxonomy]:
        """Get all available taxonomies/ontologies with their metadata"""
        taxonomies = []
        
        # Check if graph has any triples at all
        total_triples = len(self._graph)
        context_count = len(list(self._graph.contexts()))
        logger.info(f"Graph has {total_triples} total triples and {context_count} contexts")
        
        # Get contexts from the graph
        for context in self._graph.contexts():
            logger.debug(f"Processing context: {context} (type: {type(context)})")
            
            # Get the context identifier
            if hasattr(context, 'identifier'):
                context_id = context.identifier
            else:
                logger.debug(f"Context has no identifier attribute: {context}")
                continue
            
            if not isinstance(context_id, URIRef):
                logger.debug(f"Context identifier is not URIRef: {context_id} ({type(context_id)})")
                continue
            
            context_str = str(context_id)
            logger.debug(f"Processing context with identifier: {context_str}")
            
            # Count concepts and properties in this context using comprehensive SPARQL query
            try:
                # Use the same comprehensive query as in get_concepts_by_taxonomy for consistency
                class_count_query = """
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
                PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                SELECT (COUNT(DISTINCT ?concept) AS ?count) WHERE {
                    {
                        ?concept a rdfs:Class .
                    } UNION {
                        ?concept a skos:Concept .
                    } UNION {
                        ?concept a skos:ConceptScheme .
                    } UNION {
                        # Include any resource that is used as a class (has instances or subclasses)
                        ?concept rdfs:subClassOf ?parent .
                    } UNION {
                        ?instance a ?concept .
                        FILTER(?concept != rdfs:Class && ?concept != skos:Concept && ?concept != rdf:Property)
                    } UNION {
                        # Include resources with semantic properties that make them conceptual
                        ?concept rdfs:label ?someLabel .
                        ?concept rdfs:comment ?someComment .
                    }
                    # Filter out basic RDF/RDFS/SKOS vocabulary terms
                    FILTER(!STRSTARTS(STR(?concept), "http://www.w3.org/1999/02/22-rdf-syntax-ns#"))
                    FILTER(!STRSTARTS(STR(?concept), "http://www.w3.org/2000/01/rdf-schema#"))
                    FILTER(!STRSTARTS(STR(?concept), "http://www.w3.org/2004/02/skos/core#"))
                }
                """
                
                count_results = list(context.query(class_count_query))
                concepts_count = int(count_results[0][0]) if count_results and count_results[0][0] is not None else 0
                
                properties_count = len(list(context.subjects(RDF.type, RDF.Property)))
                
                logger.debug(f"Context {context_str}: {concepts_count} concepts, {properties_count} properties")
                
            except Exception as e:
                logger.warning(f"Error counting concepts in context {context_str}: {e}")
                concepts_count = 0
                properties_count = 0
            
            # Determine taxonomy type and name
            if context_str.startswith("urn:taxonomy:"):
                source_type = "file"
                name = context_str.replace("urn:taxonomy:", "")
                format_str = "ttl"
            elif context_str.startswith("urn:semantic-model:"):
                source_type = "database" 
                name = context_str.replace("urn:semantic-model:", "")
                format_str = "rdfs"
            elif context_str.startswith("urn:schema:"):
                source_type = "schema"
                name = context_str.replace("urn:schema:", "")
                format_str = "ttl"
            elif context_str.startswith("urn:glossary:"):
                source_type = "database"
                name = context_str.replace("urn:glossary:", "")
                format_str = "rdfs"
            else:
                source_type = "external"
                name = context_str
                format_str = None
            
            taxonomies.append(OntologyTaxonomy(
                name=name,
                description=f"{source_type.title()} taxonomy: {name}",
                source_type=source_type,
                format=format_str,
                concepts_count=concepts_count,
                properties_count=properties_count
            ))
        
        return sorted(taxonomies, key=lambda t: (t.source_type, t.name))
    
    def get_concepts_by_taxonomy(self, taxonomy_name: str = None) -> List[OntologyConcept]:
        """Get concepts, optionally filtered by taxonomy"""
        concepts = []
        
        # Determine which contexts to search
        contexts_to_search = []
        if taxonomy_name:
            # Find the specific context
            target_contexts = [
                f"urn:taxonomy:{taxonomy_name}",
                f"urn:semantic-model:{taxonomy_name}", 
                f"urn:schema:{taxonomy_name}",
                f"urn:glossary:{taxonomy_name}"
            ]
            for context in self._graph.contexts():
                if hasattr(context, 'identifier') and str(context.identifier) in target_contexts:
                    contexts_to_search.append((str(context.identifier), context))
        else:
            # Search all contexts
            contexts_to_search = [(str(context.identifier), context) 
                                for context in self._graph.contexts() 
                                if hasattr(context, 'identifier')]
        
        for context_name, context in contexts_to_search:
            # Find all classes and concepts in this context - expanded to catch all defined resources
            class_query = """
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            SELECT DISTINCT ?concept ?label ?comment WHERE {
                {
                    ?concept a rdfs:Class .
                } UNION {
                    ?concept a skos:Concept .
                } UNION {
                    ?concept a skos:ConceptScheme .
                } UNION {
                    # Include any resource that is used as a class (has instances or subclasses)
                    ?concept rdfs:subClassOf ?parent .
                } UNION {
                    ?instance a ?concept .
                    FILTER(?concept != rdfs:Class && ?concept != skos:Concept && ?concept != rdf:Property)
                } UNION {
                    # Include resources with semantic properties that make them conceptual
                    ?concept rdfs:label ?someLabel .
                    ?concept rdfs:comment ?someComment .
                }
                OPTIONAL { ?concept rdfs:label ?label }
                OPTIONAL { ?concept skos:prefLabel ?label }
                OPTIONAL { ?concept rdfs:comment ?comment }
                OPTIONAL { ?concept skos:definition ?comment }
                # Filter out basic RDF/RDFS/SKOS vocabulary terms
                FILTER(!STRSTARTS(STR(?concept), "http://www.w3.org/1999/02/22-rdf-syntax-ns#"))
                FILTER(!STRSTARTS(STR(?concept), "http://www.w3.org/2000/01/rdf-schema#"))
                FILTER(!STRSTARTS(STR(?concept), "http://www.w3.org/2004/02/skos/core#"))
            }
            ORDER BY ?concept
            """
            
            try:
                results = context.query(class_query)
                results_list = list(results)
                logger.debug(f"SPARQL query returned {len(results_list)} results for context {context_name}")
                
                # Process results
                results = results_list
                for row in results:
                    logger.debug(f"Processing SPARQL row: {row} (type: {type(row)}, length: {len(row) if hasattr(row, '__len__') else 'N/A'})")
                    
                    # Handle different ways SPARQL results can be accessed
                    try:
                        if hasattr(row, 'concept'):
                            concept_iri = str(row.concept)
                            label = str(row.label) if hasattr(row, 'label') and row.label else None
                            comment = str(row.comment) if hasattr(row, 'comment') and row.comment else None
                        else:
                            # Fallback to index-based access
                            concept_iri = str(row[0]) if len(row) > 0 else None
                            label = str(row[1]) if len(row) > 1 and row[1] else None
                            comment = str(row[2]) if len(row) > 2 and row[2] else None
                    except Exception as e:
                        logger.warning(f"Failed to parse SPARQL result row {row}: {e}")
                        continue
                    
                    if not concept_iri:
                        logger.debug("Skipping row with no concept IRI")
                        continue
                    
                    concept_uri = URIRef(concept_iri)
                    
                    # Determine concept type
                    if (concept_uri, RDF.type, RDFS.Class) in context:
                        concept_type = "class"
                    elif (concept_uri, RDF.type, SKOS.Concept) in context:
                        concept_type = "concept"
                    else:
                        concept_type = "individual"
                    
                    # Get parent concepts
                    parent_concepts = []
                    # Handle rdfs:subClassOf relationships (class-to-class)
                    for parent in context.objects(concept_uri, RDFS.subClassOf):
                        parent_concepts.append(str(parent))
                    # Handle SKOS broader relationships
                    for parent in context.objects(concept_uri, SKOS.broader):
                        parent_concepts.append(str(parent))
                    # Handle rdf:type relationships (instance-to-class)
                    for parent_type in context.objects(concept_uri, RDF.type):
                        # Only include custom types, not basic RDF/RDFS/SKOS types
                        parent_type_str = str(parent_type)
                        if not any(parent_type_str.startswith(prefix) for prefix in [
                            "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
                            "http://www.w3.org/2000/01/rdf-schema#", 
                            "http://www.w3.org/2004/02/skos/core#"
                        ]):
                            parent_concepts.append(parent_type_str)
                    
                    # Extract source context name
                    source_context = None
                    if context_name.startswith("urn:taxonomy:"):
                        source_context = context_name.replace("urn:taxonomy:", "")
                    elif context_name.startswith("urn:semantic-model:"):
                        source_context = context_name.replace("urn:semantic-model:", "")
                    elif context_name.startswith("urn:schema:"):
                        source_context = context_name.replace("urn:schema:", "")
                    elif context_name.startswith("urn:glossary:"):
                        source_context = context_name.replace("urn:glossary:", "")
                    
                    concepts.append(OntologyConcept(
                        iri=concept_iri,
                        label=label,
                        comment=comment,
                        concept_type=concept_type,
                        source_context=source_context,
                        parent_concepts=parent_concepts
                    ))
            except Exception as e:
                logger.warning(f"Failed to query concepts in context {context_name}: {e}")
        
        # Second pass: populate child_concepts
        concept_map = {concept.iri: concept for concept in concepts}
        for concept in concepts:
            # Find all concepts that list this concept as a parent
            for other_concept in concepts:
                if concept.iri in other_concept.parent_concepts:
                    if other_concept.iri not in concept.child_concepts:
                        concept.child_concepts.append(other_concept.iri)
        
        return concepts
    
    def get_concept_details(self, concept_iri: str) -> Optional[OntologyConcept]:
        """Get detailed information about a specific concept"""
        concept = None
        
        # Search all contexts for this concept
        for context in self._graph.contexts():
            if not hasattr(context, 'identifier'):
                continue
            context_id = context.identifier
            context_name = str(context_id)
            
            # Check if concept exists in this context
            concept_uri = URIRef(concept_iri)
            if (concept_uri, None, None) not in context:
                continue
            
            # Get basic info
            labels = list(context.objects(concept_uri, RDFS.label))
            labels.extend(list(context.objects(concept_uri, SKOS.prefLabel)))
            label = str(labels[0]) if labels else None
            
            comments = list(context.objects(concept_uri, RDFS.comment))  
            comments.extend(list(context.objects(concept_uri, SKOS.definition)))
            comment = str(comments[0]) if comments else None
            
            # Determine type
            concept_type = "individual"  # default
            if (concept_uri, RDF.type, RDFS.Class) in context:
                concept_type = "class"
            elif (concept_uri, RDF.type, SKOS.Concept) in context:
                concept_type = "concept"
            
            # Get parent concepts
            parent_concepts = []
            # Handle rdfs:subClassOf relationships (class-to-class)
            for parent in context.objects(concept_uri, RDFS.subClassOf):
                parent_concepts.append(str(parent))
            # Handle SKOS broader relationships
            for parent in context.objects(concept_uri, SKOS.broader):
                parent_concepts.append(str(parent))
            # Handle rdf:type relationships (instance-to-class)
            for parent_type in context.objects(concept_uri, RDF.type):
                # Only include custom types, not basic RDF/RDFS/SKOS types
                parent_type_str = str(parent_type)
                if not any(parent_type_str.startswith(prefix) for prefix in [
                    "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
                    "http://www.w3.org/2000/01/rdf-schema#", 
                    "http://www.w3.org/2004/02/skos/core#"
                ]):
                    parent_concepts.append(parent_type_str)
            
            # Get child concepts
            child_concepts = []
            # Handle rdfs:subClassOf relationships (find classes that are subclasses of this one)
            for child in context.subjects(RDFS.subClassOf, concept_uri):
                child_concepts.append(str(child))
            # Handle SKOS narrower relationships
            for child in context.subjects(SKOS.broader, concept_uri):
                child_concepts.append(str(child))
            # Handle rdf:type relationships (find instances of this class)
            for child in context.subjects(RDF.type, concept_uri):
                child_concepts.append(str(child))
            
            # Extract source context
            source_context = None
            if context_name.startswith("urn:taxonomy:"):
                source_context = context_name.replace("urn:taxonomy:", "")
            elif context_name.startswith("urn:semantic-model:"):
                source_context = context_name.replace("urn:semantic-model:", "")
            elif context_name.startswith("urn:schema:"):
                source_context = context_name.replace("urn:schema:", "")
            elif context_name.startswith("urn:glossary:"):
                source_context = context_name.replace("urn:glossary:", "")
            
            concept = OntologyConcept(
                iri=concept_iri,
                label=label,
                comment=comment,
                concept_type=concept_type,
                source_context=source_context,
                parent_concepts=parent_concepts,
                child_concepts=child_concepts
            )
            break  # Found in first matching context
        
        return concept
    
    def get_concept_hierarchy(self, concept_iri: str) -> Optional[ConceptHierarchy]:
        """Get hierarchical relationships for a concept"""
        concept = self.get_concept_details(concept_iri)
        if not concept:
            return None
        
        # Get ancestors (recursive parent lookup)
        ancestors = []
        visited = set()
        
        def get_ancestors_recursive(iri: str):
            if iri in visited:
                return
            visited.add(iri)
            
            parent_concept = self.get_concept_details(iri)
            if not parent_concept:
                return
                
            for parent_iri in parent_concept.parent_concepts:
                parent = self.get_concept_details(parent_iri)
                if parent and parent not in ancestors:
                    ancestors.append(parent)
                    get_ancestors_recursive(parent_iri)
        
        for parent_iri in concept.parent_concepts:
            get_ancestors_recursive(parent_iri)
        
        # Get descendants (recursive child lookup)
        descendants = []
        visited = set()
        
        def get_descendants_recursive(iri: str):
            if iri in visited:
                return
            visited.add(iri)
            
            child_concept = self.get_concept_details(iri)
            if not child_concept:
                return
                
            for child_iri in child_concept.child_concepts:
                child = self.get_concept_details(child_iri)
                if child and child not in descendants:
                    descendants.append(child)
                    get_descendants_recursive(child_iri)
        
        for child_iri in concept.child_concepts:
            get_descendants_recursive(child_iri)
        
        # Get siblings (concepts that share the same parents)
        siblings = []
        if concept.parent_concepts:
            for parent_iri in concept.parent_concepts:
                parent = self.get_concept_details(parent_iri)
                if parent:
                    for sibling_iri in parent.child_concepts:
                        if sibling_iri != concept_iri:
                            sibling = self.get_concept_details(sibling_iri)
                            if sibling and sibling not in siblings:
                                siblings.append(sibling)
        
        return ConceptHierarchy(
            concept=concept,
            ancestors=ancestors,
            descendants=descendants,
            siblings=siblings
        )
    
    def search_ontology_concepts(self, query: str, taxonomy_name: str = None, limit: int = 50) -> List[ConceptSearchResult]:
        """Search for concepts by text query"""
        results = []
        
        # Get concepts to search through
        concepts = self.get_concepts_by_taxonomy(taxonomy_name)
        
        query_lower = query.lower()
        
        for concept in concepts:
            score = 0.0
            match_type = None
            
            # Check label match
            if concept.label and query_lower in concept.label.lower():
                score += 10.0
                match_type = 'label'
                # Exact match gets higher score
                if concept.label.lower() == query_lower:
                    score += 20.0
            
            # Check comment/description match
            if concept.comment and query_lower in concept.comment.lower():
                score += 5.0
                if not match_type:
                    match_type = 'comment'
            
            # Check IRI match
            if query_lower in concept.iri.lower():
                score += 3.0
                if not match_type:
                    match_type = 'iri'
            
            if score > 0:
                results.append(ConceptSearchResult(
                    concept=concept,
                    relevance_score=score,
                    match_type=match_type or 'iri'
                ))
        
        # Sort by relevance score (descending)
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        
        return results[:limit]
    
    def get_taxonomy_stats(self) -> TaxonomyStats:
        """Get statistics about loaded taxonomies"""
        taxonomies = self.get_taxonomies()
        
        total_concepts = sum(t.concepts_count for t in taxonomies)
        total_properties = sum(t.properties_count for t in taxonomies)
        
        # Get concepts by type
        concepts_by_type = {}
        all_concepts = self.get_concepts_by_taxonomy()
        for concept in all_concepts:
            concept_type = concept.concept_type
            concepts_by_type[concept_type] = concepts_by_type.get(concept_type, 0) + 1
        
        # Count top-level concepts (those without parents)
        top_level_concepts = sum(1 for concept in all_concepts if not concept.parent_concepts)
        
        return TaxonomyStats(
            total_concepts=total_concepts,
            total_properties=total_properties,
            taxonomies=taxonomies,
            concepts_by_type=concepts_by_type,
            top_level_concepts=top_level_concepts
        )

