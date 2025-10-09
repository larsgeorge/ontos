from enum import Enum
from typing import List, Dict, Type

class FeatureAccessLevel(str, Enum):
    NONE = "None"           # No access
    READ_ONLY = "Read-only" # Can view data, cannot modify
    READ_WRITE = "Read/Write" # Can view and modify data within the feature
    FILTERED = "Filtered"   # Read/Write access, but only to a subset of data (e.g., based on domain) - Requires specific implementation per feature
    FULL = "Full"           # Full access within the feature scope (potentially includes config)
    ADMIN = "Admin"         # Full access + administrative actions (e.g., delete glossary, manage feature settings)

# Define the order of access levels from lowest to highest
ACCESS_LEVEL_ORDER: Dict[FeatureAccessLevel, int] = {
    FeatureAccessLevel.NONE: 0,
    FeatureAccessLevel.READ_ONLY: 1,
    FeatureAccessLevel.FILTERED: 2, # Filtered is higher than read-only
    FeatureAccessLevel.READ_WRITE: 3,
    FeatureAccessLevel.FULL: 4,
    FeatureAccessLevel.ADMIN: 5,
}

# Define which levels are generally applicable. Specific features might restrict further.
ALL_ACCESS_LEVELS = list(FeatureAccessLevel)
READ_WRITE_ADMIN_LEVELS = [
    FeatureAccessLevel.NONE,
    FeatureAccessLevel.READ_ONLY,
    FeatureAccessLevel.READ_WRITE,
    FeatureAccessLevel.ADMIN,
]
READ_ONLY_FULL_LEVELS = [
    FeatureAccessLevel.NONE,
    FeatureAccessLevel.READ_ONLY,
    FeatureAccessLevel.FULL,
    FeatureAccessLevel.ADMIN,
]
ADMIN_ONLY_LEVELS = [
    FeatureAccessLevel.NONE,
    FeatureAccessLevel.ADMIN,
]


# Mirroring src/config/features.ts (simplified for now)
# Key: Feature ID, Value: Dict with 'name' and 'allowed_levels'
APP_FEATURES: Dict[str, Dict[str, str | List[FeatureAccessLevel]]] = {
    # Data Management
    'data-domains': {
        'name': 'Data Domains',
        'allowed_levels': READ_WRITE_ADMIN_LEVELS # Standard CRUD + Admin delete
    },
    'data-products': {
        'name': 'Data Products',
        'allowed_levels': READ_WRITE_ADMIN_LEVELS + [FeatureAccessLevel.FILTERED] # Allow filtering
    },
    'data-contracts': {
        'name': 'Data Contracts',
        'allowed_levels': READ_WRITE_ADMIN_LEVELS
    },
    'teams': {
        'name': 'Teams',
        'allowed_levels': READ_WRITE_ADMIN_LEVELS
    },
    'projects': {
        'name': 'Projects',
        'allowed_levels': READ_WRITE_ADMIN_LEVELS
    },
    'compliance': {
        'name': 'Compliance',
        'allowed_levels': READ_WRITE_ADMIN_LEVELS
    },
    'estate-manager': {
        'name': 'Estate Manager',
        'allowed_levels': READ_ONLY_FULL_LEVELS # Now includes ADMIN
    },
    'master-data': {
        'name': 'Master Data Management',
        'allowed_levels': READ_WRITE_ADMIN_LEVELS # Requires admin for setup?
    },
    # Security
    'security': {
        'name': 'Security Features',
        'allowed_levels': ADMIN_ONLY_LEVELS # Likely admin only
    },
    'entitlements': {
        'name': 'Entitlements',
        'allowed_levels': ADMIN_ONLY_LEVELS # Admin manages personas/groups
    },
    'entitlements-sync': {
        'name': 'Entitlements Sync',
        'allowed_levels': ADMIN_ONLY_LEVELS # Admin manages sync jobs
    },
    'data-asset-reviews': {
        'name': 'Data Asset Review',
        'allowed_levels': READ_WRITE_ADMIN_LEVELS # Stewards review, admins manage
    },
    # Observability / Logs
    'audit': {
        'name': 'Audit & Change Logs',
        # Allow read-only, full (if used), and admin; write requires at least READ_WRITE but routes use explicit checks
        'allowed_levels': [
            FeatureAccessLevel.NONE,
            FeatureAccessLevel.READ_ONLY,
            FeatureAccessLevel.READ_WRITE,
            FeatureAccessLevel.FULL,
            FeatureAccessLevel.ADMIN,
        ]
    },
    # Tools
    'catalog-commander': {
        'name': 'Catalog Commander',
        'allowed_levels': [FeatureAccessLevel.NONE, FeatureAccessLevel.READ_ONLY, FeatureAccessLevel.FULL, FeatureAccessLevel.ADMIN]
    },
    # System (Settings is special, About is always visible)
    'settings': {
        'name': 'Settings',
        'allowed_levels': ADMIN_ONLY_LEVELS # Only Admins change settings
    },
    'semantic-models': {
        'name': 'Semantic Models',
        'allowed_levels': READ_WRITE_ADMIN_LEVELS
    },
    'tags': {
        'name': 'Tags',
        'allowed_levels': ADMIN_ONLY_LEVELS # Only admins can manage the tag taxonomy
    },
    # 'about': { ... } # About page doesn't need explicit permissions here

}

def get_feature_config() -> Dict[str, Dict[str, str | List[FeatureAccessLevel]]]:
    """Returns the application feature configuration."""
    return APP_FEATURES

def get_all_access_levels() -> List[FeatureAccessLevel]:
    """Returns all possible access levels."""
    return ALL_ACCESS_LEVELS 