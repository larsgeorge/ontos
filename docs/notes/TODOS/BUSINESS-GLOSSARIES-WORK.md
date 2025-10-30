> Do a deep analysis how we are currently handling Business Glossaries. We used to define our own in
 @src/backend/src/controller/business_glossaries_manager.py 
@src/backend/src/models/business_glossary.py but never completed the implementation. We then 
switched to loading taxonomies and ontologies using 
@src/backend/src/controller/semantic_models_manager.py and display them in 
@src/frontend/src/views/business-glossary.tsx now and select them via 
@src/frontend/src/components/semantic/concept-select-dialog.tsx . We want to enable users to create 
their own entries still, how could we combine the two approaches? 
  ⎿  Read src/backend/src/controller/business_glossaries_manager.py (548 lines)
  ⎿  Read src/backend/src/models/business_glossary.py (71 lines)
  ⎿  Read src/backend/src/controller/semantic_models_manager.py (1135 lines)
  ⎿  Read src/frontend/src/views/business-glossary.tsx (1584 lines)
  ⎿  Read src/frontend/src/components/semantic/concept-select-dialog.tsx (110 lines)

⏺ 🌿 Branch: main | 🌲 Worktree: /Users/lars.george/Documents/dev/dbapp/ucapp | 🆔
  01JJA9RXS4PPYQE5HC9B3Z48YA | 📌 claude-deep-analysis | 🤖 claude-sonnet-4-5-20250929

  Deep Analysis: Business Glossaries Architecture

  Current State

  1. Legacy Custom Glossary System (Incomplete)

  Data Models:
  - BusinessGlossary: Hierarchical glossaries with scope (company/division/department/team)
  - GlossaryTerm: Terms with definitions, synonyms, examples, tags, and asset linkages
  - Domain: Business domain categorization

  Manager Capabilities:
  - CRUD operations for glossaries, terms, and domains
  - Hierarchical organization with parent-child relationships
  - Term inheritance and override semantics (more specific terms override general ones)
  - YAML persistence for glossaries
  - Search functionality
  - SearchableAsset integration for cross-feature search

  Key Features:
  - Organizational unit-based scoping
  - Bottom-up merging of glossaries
  - Tagged asset associations
  - Lifecycle status tracking (draft/active/deprecated)

  Gaps:
  - No frontend UI implementation
  - No API routes connected
  - No database persistence (only YAML)
  - Terms use taggedAssets field but semantic linking isn't fully utilized

  2. Ontology/Taxonomy System (Current Active Implementation)

  Data Source:
  - RDF/SKOS taxonomies loaded from files (TTL, RDF, XML)
  - Database-backed semantic models
  - Built-in schemas from src/schemas/rdf
  - Application entities (data domains, products, contracts) exposed as RDF

  Manager Capabilities (SemanticModelsManager):
  - RDF graph management using rdflib (ConjunctiveGraph with named contexts)
  - SPARQL querying
  - Concept/property search with hierarchical suggestions
  - Taxonomy statistics and metadata
  - Semantic link management (entity → concept IRI associations)
  - Incremental graph updates for performance

  Frontend Integration:
  - business-glossary.tsx: Rich UI with tree view, knowledge graph visualization, concept details
  - concept-select-dialog.tsx: Searchable picker with parent-based suggestions
  - URL-driven concept selection for deep linking
  - Interactive lineage/hierarchy visualization (ReactFlow)
  - Force-directed graph (ForceGraph2D) for knowledge exploration

  Key Features:
  - Standards-based (RDFS, SKOS, OWL)
  - Multiple taxonomy sources (files, DB, schemas)
  - Parent-child concept hierarchies
  - Visual exploration tools
  - Semantic asset tagging via IRIs

  Gaps:
  - Read-only (no user-created concepts via UI)
  - Complex for business users (technical IRIs, RDF semantics)
  - No simple term creation workflow

  ---
  Analysis: Combining Both Approaches

  Strategic Vision

  Create a hybrid system where:
  1. External taxonomies provide standardized, authoritative concepts (industry standards,
  enterprise ontologies)
  2. Custom business glossaries allow domain experts to create organization-specific terms
  3. Semantic linking connects custom terms to standard concepts for interoperability

  Proposed Architecture

  ┌─────────────────────────────────────────────────────────────┐
  │                    Business Glossary Layer                   │
  │  (User-facing, business-friendly terms & definitions)        │
  └──────────────────┬──────────────────────────────────────────┘
                     │
            ┌────────┴────────┐
            │                 │
  ┌─────────▼──────┐  ┌──────▼─────────────────────────────────┐
  │  Custom Terms  │  │  Ontology Concepts (External)          │
  │  (DB-backed)   │  │  (RDF/SKOS from files/semantic models) │
  │                │  │                                         │
  │  - Created by  │  │  - Standardized taxonomies             │
  │    users       │  │  - Industry ontologies                 │
  │  - Simple      │  │  - Enterprise-wide concepts            │
  │    CRUD        │  │  - Read-only from user perspective     │
  │  - Linked to   │◄─┤  - Used as semantic anchors            │
  │    concepts    │  │                                         │
  └────────────────┘  └────────────────────────────────────────┘
           │                           │
           └───────────┬───────────────┘
                       │
           ┌───────────▼──────────────┐
           │   Unified Search Index   │
           │   (Both term types)      │
           └──────────────────────────┘

  ---
  Implementation Strategy

  Phase 1: Extend RDF Graph with Custom Terms

  Convert custom glossary terms to RDF triples in named graphs:

  # In SemanticModelsManager
  def load_custom_glossaries_into_graph(self) -> None:
      """Load custom business glossary terms as SKOS concepts"""
      try:
          # Fetch from BusinessGlossariesManager
          glossaries = self._business_glossaries_manager.list_glossaries()

          for glossary in glossaries:
              context_name = f"urn:custom-glossary:{glossary.id}"
              context = self._graph.get_context(context_name)

              for term in glossary.terms.values():
                  term_uri = URIRef(f"urn:ontos:glossary-term:{term.id}")

                  # Add SKOS concept type
                  context.add((term_uri, RDF.type, SKOS.Concept))

                  # Add labels and definitions
                  context.add((term_uri, SKOS.prefLabel, Literal(term.name)))
                  if term.definition:
                      context.add((term_uri, SKOS.definition, Literal(term.definition)))

                  # Add synonyms as altLabels
                  for synonym in term.synonyms:
                      context.add((term_uri, SKOS.altLabel, Literal(synonym)))

                  # Link to external concepts if semantic_iri is set
                  if hasattr(term, 'semantic_iri') and term.semantic_iri:
                      context.add((term_uri, SKOS.related, URIRef(term.semantic_iri)))

                  # Add custom metadata
                  context.add((term_uri, URIRef("urn:ontos:source"), Literal("custom")))
                  context.add((term_uri, URIRef("urn:ontos:status"), Literal(term.status)))
                  context.add((term_uri, URIRef("urn:ontos:owner"), Literal(term.owner)))
      except Exception as e:
          logger.error(f"Failed to load custom glossaries: {e}")

  Benefits:
  - Custom terms become first-class citizens in the graph
  - Unified querying via SPARQL
  - Semantic linking to external concepts works automatically
  - Knowledge graph visualizations include custom terms

  ---
  Phase 2: Enhance Data Models

  Extend GlossaryTerm model:

  @dataclass
  class GlossaryTerm:
      id: str
      name: str
      definition: str
      domain: str

      # NEW: Link to ontology concept
      semantic_iri: Optional[str] = None  # IRI of related SKOS concept
      semantic_label: Optional[str] = None  # Display name of linked concept

      # NEW: Source indicator
      source_type: str = "custom"  # "custom" | "ontology"

      # Existing fields...
      abbreviation: Optional[str] = None
      synonyms: List[str] = field(default_factory=list)
      examples: List[str] = field(default_factory=list)
      tags: List[AssignedTag] = field(default_factory=list)
      owner: str = ""
      status: str = "draft"
      created_at: datetime = field(default_factory=datetime.utcnow)
      updated_at: datetime = field(default_factory=datetime.utcnow)
      source_glossary_id: str = ""
      taggedAssets: List[Dict] = field(default_factory=list)

  Add DB persistence:

  # In db_models/business_glossary.py
  class GlossaryTermDb(Base):
      __tablename__ = "glossary_terms"

      id = Column(String, primary_key=True)
      name = Column(String, nullable=False)
      definition = Column(Text, nullable=False)
      domain = Column(String, nullable=False)

      semantic_iri = Column(String, nullable=True)  # NEW
      semantic_label = Column(String, nullable=True)  # NEW
      source_type = Column(String, default="custom")  # NEW

      abbreviation = Column(String, nullable=True)
      synonyms = Column(JSON, default=list)
      examples = Column(JSON, default=list)
      tags = Column(JSON, default=list)
      owner = Column(String, default="")
      status = Column(String, default="draft")
      created_at = Column(DateTime, default=datetime.utcnow)
      updated_at = Column(DateTime, default=datetime.utcnow)
      source_glossary_id = Column(String, nullable=False)
      tagged_assets = Column(JSON, default=list)

  ---
  Phase 3: Unified Frontend UI

  Enhance business-glossary.tsx to support custom term creation:

  // Add creation mode state
  const [creationMode, setCreationMode] = useState<'view' | 'create-term' | 'link-concept'>('view');
  const [editingTerm, setEditingTerm] = useState<GlossaryTerm | null>(null);

  // Concept tree shows both custom and ontology concepts
  <UnifiedConceptTree
    concepts={[
      ...Object.values(groupedConcepts).flat(), // Ontology concepts
      ...customTerms  // Custom terms as pseudo-concepts
    ]}
    selectedConcept={selectedConcept}
    onSelectConcept={handleSelectConcept}
    onCreateCustomTerm={() => setCreationMode('create-term')}
    allowCreate={hasPermission('business-glossary', FeatureAccessLevel.READ_WRITE)}
  />

  // Creation dialog
  {creationMode === 'create-term' && (
    <CreateTermDialog
      open={true}
      onClose={() => setCreationMode('view')}
      onSave={async (term) => {
        await fetch('/api/business-glossaries/terms', {
          method: 'POST',
          body: JSON.stringify(term)
        });
        fetchData(); // Refresh
      }}
      onLinkConcept={() => setCreationMode('link-concept')}
    />
  )}

  // Concept linking dialog (reuse existing)
  {creationMode === 'link-concept' && (
    <ConceptSelectDialog
      isOpen={true}
      onOpenChange={(open) => !open && setCreationMode('create-term')}
      onSelect={(iri) => {
        setEditingTerm(prev => ({ ...prev, semantic_iri: iri }));
        setCreationMode('create-term');
      }}
      entityType="class"
    />
  )}

  Visual Distinction:

  // In tree rendering
  const getConceptIcon = (concept: OntologyConcept | GlossaryTerm) => {
    if ('source_type' in concept && concept.source_type === 'custom') {
      return <FileText className="h-4 w-4 text-purple-500" />;  // Custom term
    }
    // Existing ontology icons...
  };

  // Add badges
  {concept.source_type === 'custom' && (
    <Badge variant="secondary" className="text-xs">Custom</Badge>
  )}
  {concept.semantic_iri && (
    <Badge variant="outline" className="text-xs">
      Linked to {concept.semantic_label}
    </Badge>
  )}

  ---
  Phase 4: API Routes

  Create/Update Custom Terms:

  # In routes/business_glossary_routes.py
  @router.post("/terms", response_model=GlossaryTerm)
  async def create_term(
      term_data: GlossaryTermCreate,
      manager: BusinessGlossariesManager = Depends(get_business_glossaries_manager),
      _: None = Depends(PermissionChecker("business-glossary", FeatureAccessLevel.READ_WRITE))
  ):
      term = manager.create_term(**term_data.dict())

      # Trigger RDF graph update
      semantic_manager = get_semantic_models_manager()
      semantic_manager.add_custom_term_to_graph(term)

      return term

  @router.put("/terms/{term_id}", response_model=GlossaryTerm)
  async def update_term(
      term_id: str,
      updates: GlossaryTermUpdate,
      manager: BusinessGlossariesManager = Depends(get_business_glossaries_manager),
      _: None = Depends(PermissionChecker("business-glossary", FeatureAccessLevel.READ_WRITE))
  ):
      term = manager.update_term(term_id, **updates.dict(exclude_unset=True))
      if not term:
          raise HTTPException(404, "Term not found")

      # Update RDF graph incrementally
      semantic_manager = get_semantic_models_manager()
      semantic_manager.update_custom_term_in_graph(term)

      return term

  Unified Concept Endpoint:

  @router.get("/concepts-unified")
  async def get_unified_concepts(
      manager: BusinessGlossariesManager = Depends(get_business_glossaries_manager)
  ):
      """Return both ontology concepts and custom terms in unified format"""

      # Get ontology concepts from semantic manager
      ontology_concepts = manager.get_concepts_by_taxonomy()

      # Get custom terms and convert to concept format
      custom_terms = manager.list_terms()
      custom_concepts = [
          OntologyConcept(
              iri=f"urn:ontos:glossary-term:{term.id}",
              label=term.name,
              comment=term.definition,
              concept_type="custom_term",
              source_context="Custom Glossary",
              parent_concepts=[term.semantic_iri] if term.semantic_iri else [],
              child_concepts=[],
              tagged_assets=term.taggedAssets,
              properties={
                  "status": term.status,
                  "owner": term.owner,
                  "editable": True  # Flag for frontend
              }
          )
          for term in custom_terms
      ]

      return {
          "ontology": ontology_concepts,
          "custom": custom_concepts,
          "unified": ontology_concepts + custom_concepts
      }

  ---
  Benefits of Hybrid Approach

  1. Best of Both Worlds:
    - External taxonomies provide standardization
    - Custom terms enable domain-specific vocabulary
  2. Semantic Interoperability:
    - Custom terms link to standard concepts via semantic_iri
    - Knowledge graph shows relationships across both domains
  3. Progressive Enhancement:
    - Start with simple custom terms
    - Optionally link to ontology concepts for richer semantics
    - Doesn't break existing ontology-only workflows
  4. User Experience:
    - Business users create terms with familiar CRUD interface
    - Technical users leverage full ontology power
    - Visual distinction (icons, badges) clarifies term provenance
  5. Search & Discovery:
    - Unified search across custom and ontology concepts
    - Hierarchy preserved in tree view
    - Knowledge graph visualizes both types
  6. Governance:
    - Custom terms have lifecycle (draft → active → deprecated)
    - Ownership and approval workflows
    - Audit trail via created_at/updated_at

  ---
  Migration Path

  1. Immediate (No Breaking Changes):
    - Add semantic_iri field to GlossaryTerm
    - Implement /terms CRUD endpoints
    - Add "Create Custom Term" button to UI
  2. Short Term:
    - Integrate custom terms into RDF graph
    - Update unified search to include custom terms
    - Add visual distinction in tree view
  3. Medium Term:
    - Implement approval workflow for custom terms
    - Add bulk import/export (CSV/YAML)
    - Create term suggestion system (AI-powered)
  4. Long Term:
    - Term usage analytics
    - Automatic semantic linking suggestions
    - Collaborative glossary editing

  ---
  Open Questions

  1. Authority Model:
    - Who can create/edit custom terms? (Role-based? Per-glossary?)
    - Should custom terms require approval before appearing in search?
  2. Conflict Resolution:
    - What if custom term name conflicts with ontology concept label?
    - Should custom terms be able to "shadow" or "override" ontology concepts?
  3. Sync Strategy:
    - Should custom terms persist to Git (like other configs)?
    - Real-time RDF graph updates vs. batch rebuilds?
  4. Schema Evolution:
    - Custom fields beyond standard SKOS properties?
    - How to handle custom term versioning?

  Let me know which direction you'd like to pursue first, and I can draft a detailed implementation
  plan!