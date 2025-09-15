from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import select

from src.common.repository import CRUDBase
from src.db_models.compliance import CompliancePolicyDb, ComplianceRunDb, ComplianceResultDb


class CompliancePolicyRepository(CRUDBase[CompliancePolicyDb, Dict[str, Any], Dict[str, Any]]):
    def __init__(self):
        super().__init__(CompliancePolicyDb)

    def list_all(self, db: Session) -> List[CompliancePolicyDb]:
        stmt = select(CompliancePolicyDb).order_by(CompliancePolicyDb.updated_at.desc())
        return list(db.execute(stmt).scalars().all())


class ComplianceRunRepository(CRUDBase[ComplianceRunDb, Dict[str, Any], Dict[str, Any]]):
    def __init__(self):
        super().__init__(ComplianceRunDb)

    def list_for_policy(self, db: Session, *, policy_id: str, limit: int = 50) -> List[ComplianceRunDb]:
        stmt = (
            select(ComplianceRunDb)
            .where(ComplianceRunDb.policy_id == policy_id)
            .order_by(ComplianceRunDb.started_at.desc())
            .limit(limit)
        )
        return list(db.execute(stmt).scalars().all())


class ComplianceResultRepository(CRUDBase[ComplianceResultDb, Dict[str, Any], Dict[str, Any]]):
    def __init__(self):
        super().__init__(ComplianceResultDb)

    def list_for_run(self, db: Session, *, run_id: str, only_failed: bool = False, limit: int = 1000) -> List[ComplianceResultDb]:
        stmt = select(ComplianceResultDb).where(ComplianceResultDb.run_id == run_id)
        if only_failed:
            stmt = stmt.where(ComplianceResultDb.passed == False)  # noqa: E712
        stmt = stmt.order_by(ComplianceResultDb.created_at.desc()).limit(limit)
        return list(db.execute(stmt).scalars().all())


compliance_policy_repo = CompliancePolicyRepository()
compliance_run_repo = ComplianceRunRepository()
compliance_result_repo = ComplianceResultRepository()


