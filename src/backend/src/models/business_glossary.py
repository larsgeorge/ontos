from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel


class TaggedAsset(BaseModel):
    id: str
    name: str
    type: str  # 'table' | 'view' | 'column'
    path: str

@dataclass
class Domain:
    id: str
    name: str
    description: Optional[str] = None

@dataclass
class GlossaryTerm:
    id: str
    name: str
    definition: str
    domain: str
    abbreviation: Optional[str] = None
    synonyms: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    owner: str = ""
    status: str = "draft"
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    source_glossary_id: str = ""
    taggedAssets: List[Dict] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'name': self.name,
            'definition': self.definition,
            'domain': self.domain,
            'abbreviation': self.abbreviation,
            'synonyms': self.synonyms,
            'examples': self.examples,
            'tags': self.tags,
            'owner': self.owner,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'source_glossary_id': self.source_glossary_id,
            'taggedAssets': self.taggedAssets
        }

@dataclass
class BusinessGlossary:
    id: str
    name: str
    description: str
    scope: str  # e.g., "company", "division", "department", "team"
    org_unit: str  # Organizational unit this glossary belongs to
    domain: str
    parent_glossary_ids: List[str] = field(default_factory=list)
    terms: Dict[str, GlossaryTerm] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    owner: str = ""
    status: str = "active"
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
