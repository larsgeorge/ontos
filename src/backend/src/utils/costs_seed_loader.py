from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

import yaml
from sqlalchemy.orm import Session

from src.common.logging import get_logger
from src.models.costs import CostItemCreate
from src.controller.costs_manager import CostsManager

logger = get_logger(__name__)


def _load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _resolve_entity_id(db: Session, entity_type: str, entity_name: str) -> Optional[str]:
    try:
        if entity_type == "data_domain":
            from src.db_models.data_domains import DataDomain
            obj = db.query(DataDomain).filter(DataDomain.name == entity_name).first()
            return str(obj.id) if obj else None
        if entity_type == "data_product":
            from src.db_models.data_products import DataProductDb
            # ODPS v1.0.0: Query data products by name field (not info.title)
            product = db.query(DataProductDb).filter(DataProductDb.name == entity_name).first()
            return str(product.id) if product else None
        if entity_type == "data_contract":
            from src.db_models.data_contracts import DataContractDb
            obj = db.query(DataContractDb).filter(DataContractDb.name == entity_name).first()
            return str(obj.id) if obj else None
    except Exception as e:
        logger.warning(f"Failed resolving entity id for {entity_type}:{entity_name}: {e!s}")
        return None
    return None


def seed_costs_from_yaml(db: Session, yaml_path: Path, *, user_email: str = "system@startup.ucapp") -> None:
    """Seed cost items from a YAML file.

    Expected YAML structure:
    costs:
      - entity_type: data_product|data_domain|data_contract
        entity_name: <string>
        items:
          - title: Databricks Infra Cost
            description: Optional
            cost_center: INFRASTRUCTURE|HR|STORAGE|MAINTENANCE|OTHER
            custom_center_name: Optional for OTHER
            amount_cents: 1438200
            currency: USD
            start_month: 2025-09-01
            end_month: 2025-09-01
    """
    if not yaml_path.exists():
        logger.info(f"Costs seed YAML not found: {yaml_path}")
        return

    config = _load_yaml(yaml_path)
    blocks: List[Dict[str, Any]] = config.get("costs", []) or []
    if not blocks:
        logger.info("No 'costs' entries found in YAML; skipping.")
        return

    manager = CostsManager()

    for block in blocks:
        try:
            entity_type = block.get("entity_type")
            entity_name = block.get("entity_name")
            if not entity_type or not entity_name:
                logger.warning(f"Skipping invalid costs block without entity_type/name: {block}")
                continue

            entity_id = _resolve_entity_id(db, entity_type, entity_name)
            if not entity_id:
                logger.warning(f"Target entity not found for {entity_type}:{entity_name}; skipping block")
                continue

            for item in block.get("items", []) or []:
                try:
                    # Normalize fields from YAML
                    cost_center_value = item.get("cost_center")
                    raw_custom = item.get("custom_center_name")
                    custom_str = (str(raw_custom).strip() if raw_custom is not None else None)
                    if cost_center_value == "OTHER" and not custom_str:
                        logger.warning(
                            f"Missing custom_center_name for OTHER cost_center on {entity_type}:{entity_name} item '{item.get('title')}'"
                        )

                    create = CostItemCreate(
                        entity_type=entity_type,
                        entity_id=entity_id,
                        title=item.get("title"),
                        description=item.get("description"),
                        cost_center=cost_center_value,
                        custom_center_name=(custom_str if cost_center_value == "OTHER" and custom_str else None),
                        amount_cents=int(item.get("amount_cents", 0)),
                        currency=item.get("currency", "USD").upper(),
                        start_month=datetime.strptime(str(item.get("start_month")), "%Y-%m-%d").date(),
                        end_month=(datetime.strptime(str(item.get("end_month")), "%Y-%m-%d").date() if item.get("end_month") else None),
                    )
                    manager.create(db, data=create, user_email=user_email)
                except Exception as e:
                    logger.error(f"Failed creating cost item for {entity_type}:{entity_name}: {e!s}")
        except Exception as e:
            logger.error(f"Error processing costs block {block}: {e!s}")


