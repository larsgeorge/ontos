from uuid import uuid4
from sqlalchemy import Column, String, Text, Integer, Date, Index
from sqlalchemy.sql import func
from sqlalchemy import TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from src.common.database import Base


class CostItemDb(Base):
    __tablename__ = "cost_items"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Generic entity scoping
    entity_type = Column(String, nullable=False, index=True)  # data_domain | data_product | data_contract
    entity_id = Column(String, nullable=False, index=True)

    # Descriptive fields
    title = Column(String, nullable=True)
    description = Column(Text, nullable=True)

    # Cost classification
    cost_center = Column(String, nullable=False)  # Enum stored as string
    custom_center_name = Column(String, nullable=True)

    # Money and currency
    amount_cents = Column(Integer, nullable=False)  # per-month recurring amount in minor units
    currency = Column(String, nullable=False, default="USD")  # ISO 4217 code

    # Month window for recurrence (inclusive)
    start_month = Column(Date, nullable=False)
    end_month = Column(Date, nullable=True)

    # Audit
    created_by = Column(String, nullable=True)
    updated_by = Column(String, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_cost_items_entity", "entity_type", "entity_id"),
        Index("ix_cost_items_entity_start", "entity_type", "entity_id", "start_month"),
        Index("ix_cost_items_month_window", "start_month", "end_month"),
    )


