from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from src.db_models.data_contracts import DataProfilingRunDb
from src.common.repository import CRUDBase


class DataProfilingRunsRepository(CRUDBase[DataProfilingRunDb, Dict[str, Any], Dict[str, Any]]):
    pass
    
    def get_by_contract_id(self, db: Session, contract_id: str) -> List[DataProfilingRunDb]:
        """Get all profiling runs for a contract, ordered by most recent first."""
        return (
            db.query(DataProfilingRunDb)
            .filter(DataProfilingRunDb.contract_id == contract_id)
            .order_by(desc(DataProfilingRunDb.started_at))
            .all()
        )
    
    def get_latest_for_contract(self, db: Session, contract_id: str) -> Optional[DataProfilingRunDb]:
        """Get the most recent profiling run for a contract."""
        return (
            db.query(DataProfilingRunDb)
            .filter(DataProfilingRunDb.contract_id == contract_id)
            .order_by(desc(DataProfilingRunDb.started_at))
            .first()
        )


# Singleton instance
data_profiling_runs_repo = DataProfilingRunsRepository(DataProfilingRunDb)

