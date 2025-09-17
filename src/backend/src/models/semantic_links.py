from pydantic import BaseModel
from typing import Optional, Literal


EntityType = Literal['data_domain', 'data_product', 'data_contract', 'data_contract_schema', 'data_contract_property']


class EntitySemanticLink(BaseModel):
    id: str
    entity_id: str
    entity_type: EntityType
    iri: str
    label: Optional[str] = None


class EntitySemanticLinkCreate(BaseModel):
    entity_id: str
    entity_type: EntityType
    iri: str
    label: Optional[str] = None


