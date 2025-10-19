from typing import Any, Dict, List
from sqlalchemy.orm import Session
from sqlalchemy import desc

from src.db_models.data_contracts import SuggestedQualityCheckDb
from src.common.repository import CRUDBase


class SuggestedQualityChecksRepository(CRUDBase[SuggestedQualityCheckDb, Dict[str, Any], Dict[str, Any]]):
    pass
    
    def get_by_profile_run_id(self, db: Session, profile_run_id: str) -> List[SuggestedQualityCheckDb]:
        """Get all suggestions for a profile run."""
        return (
            db.query(SuggestedQualityCheckDb)
            .filter(SuggestedQualityCheckDb.profile_run_id == profile_run_id)
            .order_by(SuggestedQualityCheckDb.schema_name, SuggestedQualityCheckDb.property_name)
            .all()
        )
    
    def get_pending_for_contract(self, db: Session, contract_id: str) -> List[SuggestedQualityCheckDb]:
        """Get all pending suggestions for a contract."""
        return (
            db.query(SuggestedQualityCheckDb)
            .filter(
                SuggestedQualityCheckDb.contract_id == contract_id,
                SuggestedQualityCheckDb.status == 'pending'
            )
            .order_by(desc(SuggestedQualityCheckDb.created_at))
            .all()
        )
    
    def bulk_accept(self, db: Session, suggestion_ids: List[str]) -> int:
        """Mark multiple suggestions as accepted. Returns count of updated records."""
        count = (
            db.query(SuggestedQualityCheckDb)
            .filter(SuggestedQualityCheckDb.id.in_(suggestion_ids))
            .update({"status": "accepted"}, synchronize_session=False)
        )
        db.commit()
        return count
    
    def bulk_reject(self, db: Session, suggestion_ids: List[str]) -> int:
        """Mark multiple suggestions as rejected. Returns count of updated records."""
        count = (
            db.query(SuggestedQualityCheckDb)
            .filter(SuggestedQualityCheckDb.id.in_(suggestion_ids))
            .update({"status": "rejected"}, synchronize_session=False)
        )
        db.commit()
        return count


# Singleton instance
suggested_quality_checks_repo = SuggestedQualityChecksRepository(SuggestedQualityCheckDb)

