from datetime import datetime
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field


class DataContractBase(BaseModel):
    name: str
    version: str = Field('v1.0')
    status: str = Field('draft')
    owner: str
    kind: Optional[str] = Field('DataContract')
    apiVersion: Optional[str] = Field('v3.0.1', alias='api_version')
    domainId: Optional[str] = Field(None, alias='domain_id')
    tenant: Optional[str] = None
    dataProduct: Optional[str] = Field(None, alias='data_product')
    descriptionUsage: Optional[str] = Field(None, alias='description_usage')
    descriptionPurpose: Optional[str] = Field(None, alias='description_purpose')
    descriptionLimitations: Optional[str] = Field(None, alias='description_limitations')


class DataContractCreate(DataContractBase):
    format: str = Field('json')
    contract_text: str


class DataContractUpdate(BaseModel):
    name: Optional[str] = None
    version: Optional[str] = None
    status: Optional[str] = None
    owner: Optional[str] = None
    kind: Optional[str] = None
    apiVersion: Optional[str] = Field(None, alias='api_version')
    domainId: Optional[str] = Field(None, alias='domain_id')
    tenant: Optional[str] = None
    dataProduct: Optional[str] = Field(None, alias='data_product')
    descriptionUsage: Optional[str] = Field(None, alias='description_usage')
    descriptionPurpose: Optional[str] = Field(None, alias='description_purpose')
    descriptionLimitations: Optional[str] = Field(None, alias='description_limitations')
    format: Optional[str] = None
    contract_text: Optional[str] = None


class DataContractRead(BaseModel):
    id: str
    name: str
    version: str
    status: str
    owner: str
    format: Optional[str] = None
    created: Optional[str] = None
    updated: Optional[str] = None
    contract_text: Optional[str] = None


class DataContractCommentCreate(BaseModel):
    message: str


class DataContractCommentRead(BaseModel):
    id: str
    author: str
    message: str
    created_at: Optional[str] = None


