from typing import List, Optional
from pathlib import Path
from rdflib import Graph
from rdflib.namespace import RDF, RDFS
from rdflib import URIRef
from sqlalchemy.orm import Session

from src.db_models.semantic_models import SemanticModelDb
from src.models.semantic_models import (
    SemanticModel,
    SemanticModelCreate,
    SemanticModelUpdate,
    SemanticModelPreview,
)
from src.repositories.semantic_models_repository import semantic_models_repo
from src.common.logging import get_logger


logger = get_logger(__name__)


class SemanticModelsManager:
    def __init__(self, db: Session, data_dir: Optional[Path] = None):
        self._db = db
        self._data_dir = data_dir or Path(__file__).parent.parent / "data"
        self._graph = Graph()

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

    def rebuild_graph_from_enabled(self) -> None:
        self._graph = Graph()
        items = semantic_models_repo.get_multi(self._db)
        for it in items:
            if not it.enabled:
                continue
            try:
                self._parse_into_graph(it.content_text or "", it.format)
            except Exception as e:
                logger.warning(f"Skipping model '{it.name}' due to parse error: {e}")
        # Always-on ontologies from src/schemas/rdf
        try:
            rdf_dir = Path(__file__).parent.parent / "schemas" / "rdf"
            if rdf_dir.exists() and rdf_dir.is_dir():
                for f in rdf_dir.iterdir():
                    if not f.is_file():
                        continue
                    name = f.name.lower()
                    try:
                        if name.endswith('.ttl'):
                            self._graph.parse(f.as_posix(), format='turtle')
                        elif name.endswith('.rdf') or name.endswith('.xml'):
                            self._graph.parse(f.as_posix(), format='xml')
                    except Exception as e:
                        logger.warning(f"Failed loading ontology {f.name}: {e}")
        except Exception as e:
            logger.warning(f"Failed to load built-in ontologies: {e}")
        # Add rdfs:seeAlso links from entity-semantic links
        try:
            from src.repositories.semantic_links_repository import entity_semantic_links_repo
            links = entity_semantic_links_repo.list_all(self._db)
            for link in links:
                subj = URIRef(f"urn:ucapp:{link.entity_type}:{link.entity_id}")
                obj = URIRef(link.iri)
                self._graph.add((subj, RDFS.seeAlso, obj))
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


