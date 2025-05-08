import logging
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from api.models.security_features import SecurityFeature

from api.common.logging import get_logger

logger = get_logger(__name__)

class SecurityFeaturesManager:
    def __init__(self):
        self.features: Dict[str, SecurityFeature] = {}

    def create_feature(self, feature: SecurityFeature) -> SecurityFeature:
        self.features[feature.id] = feature
        return feature

    def get_feature(self, feature_id: str) -> Optional[SecurityFeature]:
        feature = self.features.get(feature_id)
        return feature

    def list_features(self) -> List[SecurityFeature]:
        try:
            features = list(self.features.values())
            for feature in features:
                try:
                    # Verify the feature can be converted to dict
                    feature_dict = feature.to_dict()
                except Exception as e:
                    logger.error(f"Error processing feature {feature.id if hasattr(feature, 'id') else 'unknown'}")
                    logger.error(f"Error: {e!s}")
                    import traceback
                    logger.error(f"Stack trace: {traceback.format_exc()}")
                    raise
            return features
        except Exception as e:
            logger.error(f"Error in list_features: {e!s}")
            logger.error(f"Error type: {type(e)}")
            import traceback
            logger.error(f"Stack trace: {traceback.format_exc()}")
            raise

    def update_feature(self, feature_id: str, feature: SecurityFeature) -> Optional[SecurityFeature]:
        if feature_id not in self.features:
            logging.warning(f"Security feature not found: {feature_id}")
            return None
        self.features[feature_id] = feature
        return feature

    def delete_feature(self, feature_id: str) -> bool:
        if feature_id not in self.features:
            logging.warning(f"Security feature not found: {feature_id}")
            return False
        del self.features[feature_id]
        return True

    def load_from_yaml(self, yaml_path: Path) -> None:
        try:
            if not yaml_path.exists():
                logger.warning(f"YAML file not found at {yaml_path}")
                return
            with open(yaml_path) as f:
                data = yaml.safe_load(f)
                if not data or 'features' not in data:
                    logger.warning("No features found in YAML data")
                    return
                for feature_data in data['features']:
                    try:
                        feature = SecurityFeature.from_dict(feature_data)
                        self.features[feature.id] = feature
                    except Exception as e:
                        logger.error(f"Error processing feature data: {feature_data}")
                        logger.error(f"Error: {e!s}")
                        import traceback
                        logger.error(f"Stack trace: {traceback.format_exc()}")
                        raise
                logger.info(f"Successfully loaded {len(self.features)} security features")
        except Exception as e:
            logger.error(f"Error loading security features from YAML: {e!s}")
            logger.error(f"Error type: {type(e)}")
            import traceback
            logger.error(f"Stack trace: {traceback.format_exc()}")
            raise

    def save_to_yaml(self, yaml_path: Path) -> None:
        try:
            data = {'features': [feature.to_dict() for feature in self.features.values()]}
            with open(yaml_path, 'w') as f:
                yaml.dump(data, f)
        except Exception as e:
            logging.exception(f"Error saving security features to YAML: {e!s}")
            raise
