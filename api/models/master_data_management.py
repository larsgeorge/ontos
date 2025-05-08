from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict, Field


class MasterDataManagementDataset(BaseModel):
    model_config = ConfigDict(
        alias_generator=lambda x: ''.join(word.capitalize() for word in x.split('_')),
        populate_by_name=True
    )

    id: str
    name: str
    catalog: str
    db_schema: str = Field(..., alias="schema")
    table: str
    entity_column: str = Field(alias="entityColumn")
    type: str = Field(..., description="Type of entity: customer, product, supplier, or location")
    total_records: int = Field(alias="totalRecords")
    created_at: datetime = Field(default_factory=datetime.now, alias="createdAt")
    updated_at: datetime = Field(default_factory=datetime.now, alias="updatedAt")

class MasterDataManagementColumnStat(BaseModel):
    model_config = ConfigDict(
        alias_generator=lambda x: ''.join(word.capitalize() for word in x.split('_')),
        populate_by_name=True
    )

    column: str
    match_rate: float = Field(alias="matchRate")
    null_rate: float = Field(alias="nullRate")

class MasterDataManagementSampleMatch(BaseModel):
    model_config = ConfigDict(
        alias_generator=lambda x: ''.join(word.capitalize() for word in x.split('_')),
        populate_by_name=True
    )

    entity_a: str = Field(alias="entityA")
    entity_b: str = Field(alias="entityB")
    confidence: float

class MasterDataManagementComparisonResult(BaseModel):
    model_config = ConfigDict(
        alias_generator=lambda x: ''.join(word.capitalize() for word in x.split('_')),
        populate_by_name=True
    )

    dataset_a: str = Field(alias="datasetA")
    dataset_b: str = Field(alias="datasetB")
    matching_entities: int = Field(alias="matchingEntities")
    unique_to_a: int = Field(alias="uniqueToA")
    unique_to_b: int = Field(alias="uniqueToB")
    match_score: float = Field(alias="matchScore")
    common_columns: List[str] = Field(alias="commonColumns")
    sample_matches: List[MasterDataManagementSampleMatch] = Field(alias="sampleMatches")
    column_stats: List[MasterDataManagementColumnStat] = Field(alias="columnStats")
    created_at: datetime = Field(default_factory=datetime.now, alias="createdAt")

class MasterDataManagementResponse(BaseModel):
    datasets: List[MasterDataManagementDataset]
    comparisons: List[MasterDataManagementComparisonResult]
