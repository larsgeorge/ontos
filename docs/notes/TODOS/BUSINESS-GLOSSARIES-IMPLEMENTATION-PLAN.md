# Business Glossaries Implementation Plan

## Overview

This document outlines the phased implementation plan for the Business Glossaries feature, combining external ontology/taxonomy loading with app-managed custom terms. The implementation is divided into distinct phases to ensure stability and incremental feature delivery.

---

## Phase 0: Clean Up Current Implementation (Ontology-Only Mode)

**Goal:** Stabilize the current ontology-based system by removing incomplete custom term UI elements and improving terminology clarity.

### Scope

This phase focuses on **read-only** access to loaded ontologies/taxonomies (RDFS/SKOS files) while removing all UI elements related to creating custom glossaries and terms.

### Tasks

#### 1. Update Home Page Tile
**File:** `src/frontend/src/views/home.tsx`

**Current State:**
- Shows count of "glossaries" and "terms" (from legacy custom glossary system)
- Uses `/api/business-glossaries/counts` endpoint

**Required Changes:**
- Update tile to show:
  - **"Loaded Ontologies"**: Count of taxonomies/semantic models (from `TaxonomyStats.taxonomies.length`)
  - **"Total Concepts"**: Total count of concepts across all ontologies (from `TaxonomyStats.total_concepts`)
- Update endpoint to `/api/business-glossaries/stats`
- Update labels and icons to reflect ontology terminology

**Example:**
```typescript
// Before
<StatCard
  icon={Book}
  title="Business Glossaries"
  value={`${stats.glossaries} glossaries, ${stats.terms} terms`}
/>

// After
<StatCard
  icon={Network}
  title="Knowledge Ontologies"
  value={`${stats.taxonomies.length} ontologies, ${stats.total_concepts} concepts`}
/>
```

#### 2. Remove Custom Term/Glossary Creation UI
**File:** `src/frontend/src/views/business-glossary.tsx`

**Elements to Remove/Hide:**
1. **Header Buttons:**
   - "Add Term" button (line ~1259)
   - "Add Glossary" button (line ~1263)
   - Remove entire button group `<div className="flex space-x-2">`

2. **Legacy Dialog:**
   - Remove entire `<Dialog>` component (lines ~1482-1581)
   - Remove associated state variables:
     - `openDialog`
     - `dialogType`
     - `name`, `description`, `scope`, `orgUnit`, `domain`, `owner`, `tags`, `status`
   - Remove handler functions:
     - `handleCreateGlossary`
     - `handleCreateTerm`
     - `handleSave`

3. **Action Buttons in Concept Details:**
   - Remove "Edit" and "Delete" buttons (lines ~1431-1436)
   - These are already disabled but should be removed entirely

**Example:**
```typescript
// Remove this entire section:
<div className="flex space-x-2">
  <Button onClick={handleCreateTerm}>
    <Plus className="h-4 w-4 mr-2" />
    Add Term
  </Button>
  <Button onClick={handleCreateGlossary} variant="outline">
    <Plus className="h-4 w-4 mr-2" />
    Add Glossary
  </Button>
</div>
```

#### 3. Update Feature Description
**File:** `src/frontend/src/config/features.ts`

**Current Description:**
```typescript
{
  id: 'business-glossary',
  name: 'Business Glossary',
  path: '/business-glossaries',
  icon: Book,
  description: 'Manage business terms and glossaries',
  // ...
}
```

**Updated Description:**
```typescript
{
  id: 'business-glossary',
  name: 'Knowledge Ontologies',
  path: '/business-glossaries',
  icon: Network, // Changed from Book
  description: 'Explore standardized ontologies and taxonomies from loaded semantic models',
  // ...
}
```

#### 4. Update Breadcrumbs and Page Title
**File:** `src/frontend/src/views/business-glossary.tsx`

**Changes:**
```typescript
// Line ~631
setDynamicTitle('Knowledge Ontologies'); // Changed from 'Business Glossary'

// Line ~1250
<h1 className="text-3xl font-bold mb-6 flex items-center gap-2">
  <Network className="w-8 h-8" /> Knowledge Ontologies
</h1>
```

#### 5. Update Backend Manager (Optional Cleanup)
**File:** `src/backend/src/controller/business_glossaries_manager.py`

**Changes:**
- Add docstring clarifying current read-only mode
- Optionally deprecate unused methods (mark with `# TODO: Phase 1` comments)

**Example:**
```python
class BusinessGlossariesManager(SearchableAsset):
    """
    Manages business glossaries and ontology concepts.

    Current Mode (Phase 0): Read-only access to loaded ontologies/taxonomies.
    Custom term creation is planned for Phase 1.
    """

    # Phase 0: Active methods
    def get_taxonomies(self) -> List[OntologyTaxonomy]: ...
    def get_concepts_by_taxonomy(self, taxonomy_name: str = None) -> List[OntologyConcept]: ...

    # Phase 1: Planned - Custom term management
    # def create_term(self, ...): ...
    # def update_term(self, ...): ...
```

#### 6. Update API Documentation Comments
**Files:**
- `src/backend/src/routes/business_glossary_routes.py`
- `src/backend/src/models/business_glossary.py`

**Add Phase Documentation:**
```python
# business_glossary_routes.py
"""
Business Glossary API Routes

Phase 0 (Current): Read-only ontology/taxonomy browsing
  - GET /taxonomies
  - GET /concepts
  - GET /concepts/{iri}/hierarchy
  - GET /stats
  - GET /search

Phase 1 (Planned): Custom term management
  - POST /terms
  - PUT /terms/{id}
  - DELETE /terms/{id}
"""
```

### Testing Checklist

- [ ] Home page shows correct ontology counts
- [ ] Business Glossary page loads without errors
- [ ] No "Add Term" or "Add Glossary" buttons visible
- [ ] Concept tree displays loaded ontologies correctly
- [ ] Concept details view works (read-only)
- [ ] Knowledge graph visualization works
- [ ] Search functionality works across ontologies
- [ ] Semantic link tagging to assets works
- [ ] No console errors related to removed components

### Expected Outcome

- Clean, consistent UI focused on ontology exploration
- All references to "glossaries/terms" replaced with "ontologies/concepts"
- No user-facing creation options (preparation for Phase 1)
- Stable baseline for custom term implementation

---

## Phase 1: App-Managed Custom Terms

**Goal:** Enable users to create, manage, and version custom business terms while maintaining integration with external ontologies.

### Architecture Overview

#### Hybrid Model
```
┌──────────────────────────────────────────────────────┐
│            Unified Business Glossary UI              │
└───────────────────┬──────────────────────────────────┘
                    │
        ┌───────────┴───────────┐
        │                       │
┌───────▼────────┐    ┌─────────▼──────────────────┐
│ Custom Terms   │    │ External Ontologies        │
│ (App-Managed)  │    │ (Loaded from Files/DB)     │
│                │    │                             │
│ • User CRUD    │    │ • RDFS/SKOS standards      │
│ • Versioned    │    │ • Read-only                │
│ • Reviewable   │    │ • Authoritative            │
│ • RDF export   │◄───┤ • Semantic anchors         │
└────────────────┘    └────────────────────────────┘
        │                       │
        └───────────┬───────────┘
                    │
        ┌───────────▼──────────────┐
        │  RDF Knowledge Graph     │
        │  (Named Contexts/Quads)  │
        └──────────────────────────┘
```

### Data Model Enhancements

#### 1. Extended `GlossaryTerm` Model
**File:** `src/backend/src/models/business_glossary.py`

```python
from enum import Enum
from typing import Optional, List, Dict
from datetime import datetime
from dataclasses import dataclass, field

class TermSourceType(str, Enum):
    """Source of term definition"""
    CUSTOM = "custom"          # User-created via app
    ONTOLOGY = "ontology"      # Loaded from external RDFS/SKOS
    IMPORTED = "imported"      # Imported from external system

class TermStatus(str, Enum):
    """Lifecycle status"""
    DRAFT = "draft"            # Being edited
    UNDER_REVIEW = "under_review"  # Submitted for approval
    APPROVED = "approved"      # Approved but not deployed
    PUBLISHED = "published"    # Active in production
    DEPRECATED = "deprecated"  # No longer recommended
    ARCHIVED = "archived"      # Historical record

@dataclass
class GlossaryTerm:
    id: str
    name: str
    definition: str
    domain: str

    # Source and versioning
    source_type: TermSourceType = TermSourceType.CUSTOM
    version: str = "1.0.0"

    # Semantic linking
    semantic_iri: Optional[str] = None  # Link to parent ontology concept
    semantic_label: Optional[str] = None
    broader_concepts: List[str] = field(default_factory=list)  # SKOS broader
    narrower_concepts: List[str] = field(default_factory=list)  # SKOS narrower
    related_concepts: List[str] = field(default_factory=list)  # SKOS related

    # Existing fields
    abbreviation: Optional[str] = None
    synonyms: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    # Governance
    owner: str = ""
    reviewers: List[str] = field(default_factory=list)
    status: TermStatus = TermStatus.DRAFT

    # Audit trail
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = ""
    updated_at: datetime = field(default_factory=datetime.utcnow)
    updated_by: str = ""
    published_at: Optional[datetime] = None
    published_by: Optional[str] = None

    # Context
    source_glossary_id: str = ""
    tagged_assets: List[Dict] = field(default_factory=list)

    # Metadata
    change_notes: str = ""  # Version change description
    review_comments: List[Dict] = field(default_factory=list)  # Review history
```

#### 2. Database Schema
**File:** `src/backend/src/db_models/business_glossary.py`

```python
from sqlalchemy import Column, String, Text, DateTime, JSON, Enum as SQLEnum
from sqlalchemy.sql import func
from src.common.database import Base

class GlossaryTermDb(Base):
    __tablename__ = "glossary_terms"

    # Primary key
    id = Column(String, primary_key=True)

    # Core fields
    name = Column(String, nullable=False, index=True)
    definition = Column(Text, nullable=False)
    domain = Column(String, nullable=False, index=True)

    # Source and versioning
    source_type = Column(String, default="custom", nullable=False)
    version = Column(String, default="1.0.0", nullable=False)

    # Semantic linking
    semantic_iri = Column(String, nullable=True, index=True)
    semantic_label = Column(String, nullable=True)
    broader_concepts = Column(JSON, default=list)
    narrower_concepts = Column(JSON, default=list)
    related_concepts = Column(JSON, default=list)

    # Vocabulary
    abbreviation = Column(String, nullable=True)
    synonyms = Column(JSON, default=list)
    examples = Column(JSON, default=list)
    tags = Column(JSON, default=list)

    # Governance
    owner = Column(String, default="", index=True)
    reviewers = Column(JSON, default=list)
    status = Column(String, default="draft", nullable=False, index=True)

    # Audit trail
    created_at = Column(DateTime, default=func.now(), nullable=False)
    created_by = Column(String, default="")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    updated_by = Column(String, default="")
    published_at = Column(DateTime, nullable=True)
    published_by = Column(String, nullable=True)

    # Context
    source_glossary_id = Column(String, nullable=False, index=True)
    tagged_assets = Column(JSON, default=list)

    # Metadata
    change_notes = Column(Text, default="")
    review_comments = Column(JSON, default=list)
```

#### 3. Review Workflow Model
**File:** `src/backend/src/models/business_glossary.py`

```python
@dataclass
class TermReviewComment:
    """Comment in the review sidebar"""
    id: str
    term_id: str
    author: str
    comment: str
    timestamp: datetime
    comment_type: str  # "review_request" | "change_request" | "approval" | "rejection" | "general"

@dataclass
class TermReviewRequest:
    """Review request for a term"""
    id: str
    term_id: str
    term_version: str
    requester: str
    reviewers: List[str]
    status: str  # "pending" | "approved" | "rejected" | "changes_requested"
    created_at: datetime
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
```

### Backend Implementation

#### 1. Repository Layer
**File:** `src/backend/src/repositories/business_glossary_repository.py`

```python
from typing import List, Optional
from sqlalchemy.orm import Session
from src.common.repository import CRUDBase
from src.db_models.business_glossary import GlossaryTermDb
from src.models.business_glossary import GlossaryTerm, TermStatus

class BusinessGlossaryRepository(CRUDBase[GlossaryTermDb, GlossaryTerm, GlossaryTerm]):
    def get_by_status(self, db: Session, status: TermStatus) -> List[GlossaryTermDb]:
        return db.query(GlossaryTermDb).filter(GlossaryTermDb.status == status.value).all()

    def get_by_owner(self, db: Session, owner: str) -> List[GlossaryTermDb]:
        return db.query(GlossaryTermDb).filter(GlossaryTermDb.owner == owner).all()

    def get_pending_reviews(self, db: Session, reviewer: str) -> List[GlossaryTermDb]:
        return db.query(GlossaryTermDb).filter(
            GlossaryTermDb.status == TermStatus.UNDER_REVIEW.value,
            GlossaryTermDb.reviewers.contains([reviewer])
        ).all()

    def search_by_name(self, db: Session, query: str, limit: int = 50) -> List[GlossaryTermDb]:
        return db.query(GlossaryTermDb).filter(
            GlossaryTermDb.name.ilike(f"%{query}%")
        ).limit(limit).all()

glossary_term_repo = BusinessGlossaryRepository(GlossaryTermDb)
```

#### 2. Manager Enhancements
**File:** `src/backend/src/controller/business_glossaries_manager.py`

**New Methods:**
```python
class BusinessGlossariesManager(SearchableAsset):
    # ... existing ontology methods ...

    # ===== Phase 1: Custom Term Management =====

    def create_custom_term(
        self,
        name: str,
        definition: str,
        domain: str,
        owner: str,
        created_by: str,
        glossary_id: str,
        **kwargs
    ) -> GlossaryTerm:
        """Create a new custom term in DRAFT status"""
        term_id = str(uuid.uuid4())
        now = datetime.utcnow()

        term = GlossaryTerm(
            id=term_id,
            name=name,
            definition=definition,
            domain=domain,
            owner=owner,
            created_by=created_by,
            created_at=now,
            updated_at=now,
            source_type=TermSourceType.CUSTOM,
            status=TermStatus.DRAFT,
            source_glossary_id=glossary_id,
            version="1.0.0",
            **kwargs
        )

        # Save to database
        term_db = glossary_term_repo.create(self._db, obj_in=term)

        # Add to RDF graph (in custom context)
        self._add_custom_term_to_graph(term)

        # Trigger search index update
        self._search_manager.index_item(term)

        return term

    def update_custom_term(
        self,
        term_id: str,
        updated_by: str,
        **updates
    ) -> Optional[GlossaryTerm]:
        """Update a custom term"""
        term_db = glossary_term_repo.get(self._db, id=term_id)
        if not term_db or term_db.source_type != TermSourceType.CUSTOM.value:
            return None

        # Only allow updates to DRAFT or APPROVED terms
        if term_db.status not in [TermStatus.DRAFT.value, TermStatus.APPROVED.value]:
            raise ValueError(f"Cannot edit term in {term_db.status} status")

        updates['updated_by'] = updated_by
        updates['updated_at'] = datetime.utcnow()

        term_db = glossary_term_repo.update(self._db, db_obj=term_db, obj_in=updates)

        # Update RDF graph
        self._update_custom_term_in_graph(term_db)

        return self._to_term_model(term_db)

    def submit_for_review(
        self,
        term_id: str,
        requester: str,
        reviewers: List[str]
    ) -> GlossaryTerm:
        """Submit term for review"""
        term_db = glossary_term_repo.get(self._db, id=term_id)
        if not term_db:
            raise ValueError("Term not found")

        if term_db.status != TermStatus.DRAFT.value:
            raise ValueError("Only DRAFT terms can be submitted for review")

        # Update status
        term_db.status = TermStatus.UNDER_REVIEW.value
        term_db.reviewers = reviewers
        term_db.updated_at = datetime.utcnow()
        term_db.updated_by = requester

        self._db.commit()

        # Create review request (via review manager)
        self._review_manager.create_review_request(
            entity_type="glossary_term",
            entity_id=term_id,
            requester=requester,
            reviewers=reviewers
        )

        return self._to_term_model(term_db)

    def approve_term(
        self,
        term_id: str,
        reviewer: str,
        comment: Optional[str] = None
    ) -> GlossaryTerm:
        """Approve a term under review"""
        term_db = glossary_term_repo.get(self._db, id=term_id)
        if not term_db:
            raise ValueError("Term not found")

        if term_db.status != TermStatus.UNDER_REVIEW.value:
            raise ValueError("Term is not under review")

        if reviewer not in term_db.reviewers:
            raise ValueError("User is not an assigned reviewer")

        # Update status to APPROVED (awaiting publication)
        term_db.status = TermStatus.APPROVED.value
        term_db.updated_at = datetime.utcnow()

        # Add review comment
        if not term_db.review_comments:
            term_db.review_comments = []
        term_db.review_comments.append({
            "id": str(uuid.uuid4()),
            "author": reviewer,
            "comment": comment or "Approved",
            "timestamp": datetime.utcnow().isoformat(),
            "type": "approval"
        })

        self._db.commit()

        return self._to_term_model(term_db)

    def publish_term(
        self,
        term_id: str,
        publisher: str
    ) -> GlossaryTerm:
        """Publish an approved term"""
        term_db = glossary_term_repo.get(self._db, id=term_id)
        if not term_db:
            raise ValueError("Term not found")

        if term_db.status != TermStatus.APPROVED.value:
            raise ValueError("Term must be approved before publishing")

        # Update status
        term_db.status = TermStatus.PUBLISHED.value
        term_db.published_at = datetime.utcnow()
        term_db.published_by = publisher

        self._db.commit()

        # Export to Git (if enabled)
        if self._settings_manager.is_git_sync_enabled():
            self._export_term_to_git(term_db)

        return self._to_term_model(term_db)

    def _add_custom_term_to_graph(self, term: GlossaryTerm) -> None:
        """Add custom term as SKOS concept to RDF graph"""
        context_name = f"urn:custom-glossary:{term.source_glossary_id}"
        context = self._semantic_manager._graph.get_context(context_name)

        term_uri = URIRef(f"urn:ontos:glossary-term:{term.id}")

        # Add type
        context.add((term_uri, RDF.type, SKOS.Concept))

        # Add labels
        context.add((term_uri, SKOS.prefLabel, Literal(term.name)))
        if term.definition:
            context.add((term_uri, SKOS.definition, Literal(term.definition)))

        # Add synonyms
        for synonym in term.synonyms:
            context.add((term_uri, SKOS.altLabel, Literal(synonym)))

        # Add broader/narrower/related
        if term.semantic_iri:
            context.add((term_uri, SKOS.broader, URIRef(term.semantic_iri)))

        for broader in term.broader_concepts:
            context.add((term_uri, SKOS.broader, URIRef(broader)))

        for narrower in term.narrower_concepts:
            context.add((term_uri, SKOS.narrower, URIRef(narrower)))

        for related in term.related_concepts:
            context.add((term_uri, SKOS.related, URIRef(related)))

        # Add custom metadata
        context.add((term_uri, URIRef("urn:ontos:source-type"), Literal(term.source_type.value)))
        context.add((term_uri, URIRef("urn:ontos:status"), Literal(term.status.value)))
        context.add((term_uri, URIRef("urn:ontos:version"), Literal(term.version)))
        context.add((term_uri, URIRef("urn:ontos:owner"), Literal(term.owner)))

    def _export_term_to_git(self, term_db: GlossaryTermDb) -> None:
        """Export term as RDFS file to Git repository"""
        # Convert to RDF graph
        g = Graph()
        term_uri = URIRef(f"urn:ontos:glossary-term:{term_db.id}")

        # ... build RDF triples ...

        # Serialize to Turtle
        ttl_content = g.serialize(format='turtle')

        # Write to Git repo
        repo_path = self._settings_manager.get_git_repo_path()
        glossary_dir = repo_path / "glossaries" / term_db.source_glossary_id
        glossary_dir.mkdir(parents=True, exist_ok=True)

        term_file = glossary_dir / f"{term_db.id}.ttl"
        term_file.write_text(ttl_content, encoding='utf-8')

        # Trigger Git commit workflow (via notifications)
        self._notifications_manager.notify_git_changes()
```

#### 3. API Routes
**File:** `src/backend/src/routes/business_glossary_routes.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from typing import List
from src.models.business_glossary import (
    GlossaryTerm,
    GlossaryTermCreate,
    GlossaryTermUpdate,
    TermReviewRequest
)
from src.common.authorization import PermissionChecker, get_current_user
from src.common.features import FeatureAccessLevel

router = APIRouter(prefix="/api/business-glossaries", tags=["Business Glossary"])

# ===== Phase 1: Custom Term CRUD =====

@router.post("/terms", response_model=GlossaryTerm)
async def create_term(
    term_data: GlossaryTermCreate,
    current_user: str = Depends(get_current_user),
    manager = Depends(get_business_glossaries_manager),
    _: None = Depends(PermissionChecker("business-glossary", FeatureAccessLevel.READ_WRITE))
):
    """Create a new custom term in DRAFT status"""
    try:
        term = manager.create_custom_term(
            created_by=current_user,
            **term_data.dict()
        )
        return term
    except ValueError as e:
        raise HTTPException(400, str(e))

@router.put("/terms/{term_id}", response_model=GlossaryTerm)
async def update_term(
    term_id: str,
    updates: GlossaryTermUpdate,
    current_user: str = Depends(get_current_user),
    manager = Depends(get_business_glossaries_manager),
    _: None = Depends(PermissionChecker("business-glossary", FeatureAccessLevel.READ_WRITE))
):
    """Update a custom term (DRAFT or APPROVED status only)"""
    try:
        term = manager.update_custom_term(
            term_id=term_id,
            updated_by=current_user,
            **updates.dict(exclude_unset=True)
        )
        if not term:
            raise HTTPException(404, "Term not found or not editable")
        return term
    except ValueError as e:
        raise HTTPException(400, str(e))

@router.delete("/terms/{term_id}")
async def delete_term(
    term_id: str,
    current_user: str = Depends(get_current_user),
    manager = Depends(get_business_glossaries_manager),
    _: None = Depends(PermissionChecker("business-glossary", FeatureAccessLevel.READ_WRITE))
):
    """Delete a custom term (DRAFT status only)"""
    success = manager.delete_custom_term(term_id, current_user)
    if not success:
        raise HTTPException(404, "Term not found or not deletable")
    return {"success": True}

@router.post("/terms/{term_id}/submit-review", response_model=GlossaryTerm)
async def submit_term_for_review(
    term_id: str,
    reviewers: List[str],
    current_user: str = Depends(get_current_user),
    manager = Depends(get_business_glossaries_manager),
    _: None = Depends(PermissionChecker("business-glossary", FeatureAccessLevel.READ_WRITE))
):
    """Submit term for review"""
    try:
        term = manager.submit_for_review(term_id, current_user, reviewers)
        return term
    except ValueError as e:
        raise HTTPException(400, str(e))

@router.post("/terms/{term_id}/approve", response_model=GlossaryTerm)
async def approve_term(
    term_id: str,
    comment: Optional[str] = None,
    current_user: str = Depends(get_current_user),
    manager = Depends(get_business_glossaries_manager),
    _: None = Depends(PermissionChecker("business-glossary", FeatureAccessLevel.REVIEWER))
):
    """Approve a term under review"""
    try:
        term = manager.approve_term(term_id, current_user, comment)
        return term
    except ValueError as e:
        raise HTTPException(400, str(e))

@router.post("/terms/{term_id}/publish", response_model=GlossaryTerm)
async def publish_term(
    term_id: str,
    current_user: str = Depends(get_current_user),
    manager = Depends(get_business_glossaries_manager),
    _: None = Depends(PermissionChecker("business-glossary", FeatureAccessLevel.ADMIN))
):
    """Publish an approved term"""
    try:
        term = manager.publish_term(term_id, current_user)
        return term
    except ValueError as e:
        raise HTTPException(400, str(e))

@router.get("/terms/my-drafts", response_model=List[GlossaryTerm])
async def get_my_draft_terms(
    current_user: str = Depends(get_current_user),
    manager = Depends(get_business_glossaries_manager),
    _: None = Depends(PermissionChecker("business-glossary", FeatureAccessLevel.READ))
):
    """Get all draft terms owned by current user"""
    return manager.get_terms_by_owner_and_status(current_user, TermStatus.DRAFT)

@router.get("/terms/pending-reviews", response_model=List[GlossaryTerm])
async def get_pending_reviews(
    current_user: str = Depends(get_current_user),
    manager = Depends(get_business_glossaries_manager),
    _: None = Depends(PermissionChecker("business-glossary", FeatureAccessLevel.REVIEWER))
):
    """Get all terms pending review by current user"""
    return manager.get_pending_reviews(current_user)
```

### Frontend Implementation

#### 1. Create Term Dialog
**New File:** `src/frontend/src/components/business-glossary/create-term-dialog.tsx`

```typescript
import { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import ConceptSelectDialog from '@/components/semantic/concept-select-dialog';

interface CreateTermDialogProps {
  open: boolean;
  onClose: () => void;
  onSave: (term: any) => Promise<void>;
  glossaryId: string;
}

export function CreateTermDialog({ open, onClose, onSave, glossaryId }: CreateTermDialogProps) {
  const [name, setName] = useState('');
  const [definition, setDefinition] = useState('');
  const [domain, setDomain] = useState('');
  const [abbreviation, setAbbreviation] = useState('');
  const [synonyms, setSynonyms] = useState('');
  const [examples, setExamples] = useState('');
  const [semanticIri, setSemanticIri] = useState<string | null>(null);
  const [semanticLabel, setSemanticLabel] = useState<string | null>(null);
  const [showConceptPicker, setShowConceptPicker] = useState(false);

  const handleSubmit = async () => {
    const termData = {
      name,
      definition,
      domain,
      abbreviation: abbreviation || undefined,
      synonyms: synonyms.split(',').map(s => s.trim()).filter(Boolean),
      examples: examples.split(',').map(s => s.trim()).filter(Boolean),
      semantic_iri: semanticIri,
      semantic_label: semanticLabel,
      source_glossary_id: glossaryId
    };

    await onSave(termData);
    onClose();
  };

  return (
    <>
      <Dialog open={open} onOpenChange={onClose}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Create Custom Term</DialogTitle>
          </DialogHeader>

          <div className="space-y-4">
            <div>
              <Label htmlFor="name">Term Name *</Label>
              <Input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g., Customer Lifetime Value"
                required
              />
            </div>

            <div>
              <Label htmlFor="definition">Definition *</Label>
              <Textarea
                id="definition"
                value={definition}
                onChange={(e) => setDefinition(e.target.value)}
                placeholder="Provide a clear, concise definition..."
                rows={3}
                required
              />
            </div>

            <div>
              <Label htmlFor="domain">Business Domain *</Label>
              <Input
                id="domain"
                value={domain}
                onChange={(e) => setDomain(e.target.value)}
                placeholder="e.g., Marketing, Finance, Operations"
                required
              />
            </div>

            <div>
              <Label htmlFor="abbreviation">Abbreviation (Optional)</Label>
              <Input
                id="abbreviation"
                value={abbreviation}
                onChange={(e) => setAbbreviation(e.target.value)}
                placeholder="e.g., CLV"
              />
            </div>

            <div>
              <Label htmlFor="synonyms">Synonyms (comma-separated)</Label>
              <Input
                id="synonyms"
                value={synonyms}
                onChange={(e) => setSynonyms(e.target.value)}
                placeholder="e.g., LTV, Lifetime Value"
              />
            </div>

            <div>
              <Label htmlFor="examples">Examples (comma-separated)</Label>
              <Textarea
                id="examples"
                value={examples}
                onChange={(e) => setExamples(e.target.value)}
                placeholder="Provide usage examples..."
                rows={2}
              />
            </div>

            <div>
              <Label>Link to Ontology Concept (Optional)</Label>
              <div className="flex gap-2 items-center">
                {semanticIri ? (
                  <>
                    <div className="flex-1 p-2 bg-muted rounded text-sm">
                      {semanticLabel || semanticIri}
                    </div>
                    <Button
                      variant="outline"
                      onClick={() => {
                        setSemanticIri(null);
                        setSemanticLabel(null);
                      }}
                    >
                      Clear
                    </Button>
                  </>
                ) : (
                  <Button
                    variant="outline"
                    onClick={() => setShowConceptPicker(true)}
                  >
                    Select Concept
                  </Button>
                )}
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                Link this term to a standardized ontology concept for semantic interoperability
              </p>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={onClose}>Cancel</Button>
            <Button onClick={handleSubmit} disabled={!name || !definition || !domain}>
              Create Term
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Concept Picker */}
      <ConceptSelectDialog
        isOpen={showConceptPicker}
        onOpenChange={setShowConceptPicker}
        onSelect={(iri) => {
          setSemanticIri(iri);
          // Fetch label from concepts list
          // setSemanticLabel(foundConcept.label);
          setShowConceptPicker(false);
        }}
        entityType="class"
      />
    </>
  );
}
```

#### 2. Review Sidebar Component
**New File:** `src/frontend/src/components/business-glossary/term-review-sidebar.tsx`

```typescript
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { CheckCircle, XCircle, MessageSquare } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

interface ReviewComment {
  id: string;
  author: string;
  comment: string;
  timestamp: string;
  type: 'approval' | 'rejection' | 'change_request' | 'general';
}

interface TermReviewSidebarProps {
  termId: string;
  status: string;
  reviewComments: ReviewComment[];
  isReviewer: boolean;
  onApprove: (comment: string) => void;
  onRequestChanges: (comment: string) => void;
  onAddComment: (comment: string) => void;
}

export function TermReviewSidebar({
  termId,
  status,
  reviewComments,
  isReviewer,
  onApprove,
  onRequestChanges,
  onAddComment
}: TermReviewSidebarProps) {
  const [comment, setComment] = useState('');

  const getCommentIcon = (type: string) => {
    switch (type) {
      case 'approval': return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'rejection': return <XCircle className="h-4 w-4 text-red-500" />;
      default: return <MessageSquare className="h-4 w-4 text-blue-500" />;
    }
  };

  return (
    <div className="border-l h-full flex flex-col">
      <div className="p-4 border-b">
        <h3 className="font-semibold mb-2">Review Activity</h3>
        <Badge variant={status === 'under_review' ? 'warning' : 'default'}>
          {status.replace('_', ' ').toUpperCase()}
        </Badge>
      </div>

      <ScrollArea className="flex-1 p-4">
        <div className="space-y-4">
          {reviewComments.map((rc) => (
            <div key={rc.id} className="flex gap-3">
              <Avatar className="h-8 w-8">
                <AvatarFallback>{rc.author[0].toUpperCase()}</AvatarFallback>
              </Avatar>
              <div className="flex-1 space-y-1">
                <div className="flex items-center gap-2">
                  {getCommentIcon(rc.type)}
                  <span className="font-medium text-sm">{rc.author}</span>
                  <span className="text-xs text-muted-foreground">
                    {formatDistanceToNow(new Date(rc.timestamp), { addSuffix: true })}
                  </span>
                </div>
                <p className="text-sm">{rc.comment}</p>
              </div>
            </div>
          ))}
        </div>
      </ScrollArea>

      {isReviewer && status === 'under_review' && (
        <div className="p-4 border-t space-y-3">
          <Textarea
            placeholder="Add a comment..."
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            rows={3}
          />
          <div className="flex gap-2">
            <Button
              size="sm"
              variant="default"
              onClick={() => {
                onApprove(comment);
                setComment('');
              }}
            >
              <CheckCircle className="h-4 w-4 mr-1" />
              Approve
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => {
                onRequestChanges(comment);
                setComment('');
              }}
            >
              Request Changes
            </Button>
          </div>
          <Button
            size="sm"
            variant="ghost"
            className="w-full"
            onClick={() => {
              onAddComment(comment);
              setComment('');
            }}
          >
            Add Comment Only
          </Button>
        </div>
      )}
    </div>
  );
}
```

#### 3. Updated Main View
**File:** `src/frontend/src/views/business-glossary.tsx`

**Add State:**
```typescript
const [showCreateDialog, setShowCreateDialog] = useState(false);
const [selectedGlossaryId, setSelectedGlossaryId] = useState<string>('default');
const [myDrafts, setMyDrafts] = useState<GlossaryTerm[]>([]);
const [pendingReviews, setPendingReviews] = useState<GlossaryTerm[]>([]);
```

**Add Buttons (conditional on permissions):**
```typescript
{hasPermission('business-glossary', FeatureAccessLevel.READ_WRITE) && (
  <div className="flex space-x-2">
    <Button onClick={() => setShowCreateDialog(true)}>
      <Plus className="h-4 w-4 mr-2" />
      Create Custom Term
    </Button>
  </div>
)}
```

**Add Tabs for Drafts/Reviews:**
```typescript
<Tabs defaultValue="ontologies" className="w-full">
  <TabsList>
    <TabsTrigger value="ontologies">Ontologies</TabsTrigger>
    <TabsTrigger value="my-drafts">My Drafts ({myDrafts.length})</TabsTrigger>
    {hasPermission('business-glossary', FeatureAccessLevel.REVIEWER) && (
      <TabsTrigger value="reviews">Pending Reviews ({pendingReviews.length})</TabsTrigger>
    )}
  </TabsList>

  <TabsContent value="ontologies">
    {/* Existing ontology tree */}
  </TabsContent>

  <TabsContent value="my-drafts">
    <DataTable
      columns={draftColumns}
      data={myDrafts}
      searchColumn="name"
    />
  </TabsContent>

  <TabsContent value="reviews">
    <DataTable
      columns={reviewColumns}
      data={pendingReviews}
      searchColumn="name"
    />
  </TabsContent>
</Tabs>
```

**Add Review Sidebar:**
```typescript
{selectedConcept?.source_type === 'custom' && (
  <TermReviewSidebar
    termId={selectedConcept.id}
    status={selectedConcept.status}
    reviewComments={selectedConcept.review_comments || []}
    isReviewer={hasPermission('business-glossary', FeatureAccessLevel.REVIEWER)}
    onApprove={async (comment) => {
      await fetch(`/api/business-glossaries/terms/${selectedConcept.id}/approve`, {
        method: 'POST',
        body: JSON.stringify({ comment })
      });
      fetchData();
    }}
    onRequestChanges={async (comment) => {
      // Implement change request
    }}
    onAddComment={async (comment) => {
      // Implement add comment
    }}
  />
)}
```

### Permissions & Roles

#### Required Permission Levels
**File:** `src/backend/src/common/features.py`

```python
# Add new access level
class FeatureAccessLevel(str, Enum):
    NO_ACCESS = "no_access"
    READ = "read"
    READ_WRITE = "read_write"
    REVIEWER = "reviewer"  # NEW: Can approve terms
    ADMIN = "admin"

# Update feature definition
{
    "id": "business-glossary",
    "name": "Business Glossary",
    "default_access": FeatureAccessLevel.READ,
    "roles": {
        "Data Consumer": FeatureAccessLevel.READ,
        "Data Producer": FeatureAccessLevel.READ_WRITE,
        "Data Steward": FeatureAccessLevel.REVIEWER,
        "Data Governance": FeatureAccessLevel.ADMIN
    }
}
```

#### Reviewer Assignment
- Terms in UNDER_REVIEW status must be assigned to specific reviewers
- Reviewers must have `REVIEWER` or `ADMIN` access level
- Owner/creator cannot approve their own terms
- Multiple reviewers can be assigned (any one approval moves to APPROVED)

### Review Workflow

```
DRAFT
  │
  ├─> [Submit for Review] → UNDER_REVIEW
  │                              │
  │                              ├─> [Approve] → APPROVED
  │                              │                   │
  │                              │                   └─> [Publish] → PUBLISHED
  │                              │
  │                              └─> [Request Changes] → DRAFT
  │
  └─> [Delete] → (removed)

PUBLISHED
  │
  └─> [Deprecate] → DEPRECATED
                         │
                         └─> [Archive] → ARCHIVED
```

### Git Integration

#### Export Format
Each custom term exported as individual `.ttl` file:

```turtle
# glossaries/{glossary-id}/{term-id}.ttl

@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix ontos: <urn:ontos:> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

ontos:glossary-term:abc-123
    a skos:Concept ;
    skos:prefLabel "Customer Lifetime Value"@en ;
    skos:altLabel "CLV"@en, "LTV"@en ;
    skos:definition "The total revenue expected from a customer over their relationship with the company."@en ;
    skos:broader <http://ontology.example.com/marketing#CustomerMetric> ;
    ucapp:status "published" ;
    ucapp:version "1.0.0" ;
    ucapp:owner "alice@company.com" ;
    ucapp:domain "Marketing" .
```

#### Commit Workflow
1. User publishes term → File written to Git repo
2. Notification sent to user: "Term published. Review Git changes?"
3. User reviews diff, edits commit message
4. User commits and pushes via app UI or external Git client

### Versioning Strategy

#### Version Numbering
Follow semantic versioning: `MAJOR.MINOR.PATCH`

- **MAJOR**: Breaking changes (e.g., definition fundamentally changes)
- **MINOR**: Additive changes (e.g., add synonyms, examples)
- **PATCH**: Fixes (e.g., typos, clarifications)

#### Version History
- Store all versions in database (`glossary_term_versions` table)
- UI shows version history and diff view
- Users can revert to previous versions

### Testing Plan

#### Backend Tests
- [ ] Repository CRUD operations
- [ ] Manager term lifecycle (create → review → publish)
- [ ] RDF graph integration (custom terms appear in queries)
- [ ] Permissions enforcement
- [ ] Review workflow state transitions

#### Frontend Tests
- [ ] Create term dialog validation
- [ ] Review sidebar interactions
- [ ] Term list filtering (drafts, reviews, published)
- [ ] Concept tree shows mixed custom/ontology terms
- [ ] Knowledge graph includes custom terms

#### Integration Tests
- [ ] End-to-end term creation and publishing
- [ ] Git export and re-import
- [ ] Search includes custom terms
- [ ] Asset tagging with custom terms

### Migration Steps

1. **Database Migration**
   - Create `glossary_terms` table
   - Create `glossary_term_versions` table (for Phase 2)

2. **Backend Changes**
   - Implement repository layer
   - Enhance manager with custom term methods
   - Add API routes
   - Update RDF graph loading

3. **Frontend Changes**
   - Add CreateTermDialog component
   - Add TermReviewSidebar component
   - Update main view with tabs and buttons
   - Add permission checks

4. **Testing**
   - Unit tests
   - Integration tests
   - UI testing with Playwright

5. **Documentation**
   - Update user guide
   - Add API documentation
   - Create admin guide for reviewers

---

## Phase 2: Advanced Features (Future)

### Planned Enhancements

1. **Bulk Import/Export**
   - Import terms from CSV/Excel
   - Export glossaries to standard formats (SKOS, CSV)

2. **Term Usage Analytics**
   - Track which terms are most frequently used in asset tagging
   - Show usage statistics in UI

3. **AI-Powered Suggestions**
   - Suggest semantic links based on term definition
   - Auto-complete for synonyms and related terms
   - Detect duplicate terms

4. **Collaborative Editing**
   - Multiple users can edit drafts simultaneously
   - Change tracking and conflict resolution

5. **Term Relationships Visualization**
   - Interactive graph showing term relationships
   - Broader/narrower/related concept navigation

6. **Governance Reports**
   - Term coverage reports (% of assets with semantic tags)
   - Review velocity metrics
   - Term lifecycle dashboards

7. **Integration with External Systems**
   - Import from Collibra, Alation, etc.
   - Sync with enterprise taxonomies
   - Publish to external catalogs

---

## Summary

### Phase 0 Deliverables (Immediate)
✅ Clean, read-only ontology browsing UI
✅ Updated terminology (ontologies vs. glossaries)
✅ Removed incomplete custom term UI
✅ Stable baseline for Phase 1

### Phase 1 Deliverables (Next)
📋 Custom term CRUD with versioning
📋 Review workflow with sidebar
📋 RDF graph integration
📋 Git export capability
📋 Permissions and role-based access
📋 Unified search (custom + ontology)

### Success Metrics

**Phase 0:**
- Zero UI errors related to removed components
- All ontology features working correctly
- User feedback positive on terminology clarity

**Phase 1:**
- Users can create, review, and publish custom terms
- Custom terms appear in knowledge graph and search
- Review workflow reduces time-to-publish by 50%
- 80% of published terms linked to ontology concepts

---

## Questions & Decisions Log

### Open Questions
1. Should we support glossary-level access control (some glossaries only visible to certain teams)?
2. How to handle term conflicts across different glossaries?
3. Should deprecated terms still appear in search/tree?

### Decisions Made
1. **Review process**: Similar to data contracts (comment sidebar, approval workflow)
2. **Uniqueness**: Use RDF quads/contexts to allow same IRI from different sources
3. **Git sync**: Export each glossary as separate RDFS files
4. **Versioning**: Semantic versioning with full history tracking
5. **Permissions**: Reviewer role required for approval; owner cannot self-approve

---

**Document Version:** 1.0
**Last Updated:** 2025-01-09
**Status:** Draft - Awaiting Review
