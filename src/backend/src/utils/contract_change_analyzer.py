"""
Contract Change Analyzer for Semantic Versioning
Analyzes changes between two data contract versions to determine version bump type.
"""

from enum import Enum
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass


class ChangeType(Enum):
    """Type of change detected"""
    BREAKING = "breaking"  # Requires major version bump
    FEATURE = "feature"    # Requires minor version bump
    FIX = "fix"           # Requires patch version bump
    NONE = "none"         # No significant changes


class ChangeSeverity(Enum):
    """Severity classification for changes"""
    CRITICAL = "critical"  # Breaking changes
    MODERATE = "moderate"  # New features
    MINOR = "minor"        # Bug fixes, improvements


@dataclass
class SchemaChange:
    """Represents a change in schema"""
    change_type: str  # "added", "removed", "modified", "type_changed"
    schema_name: str
    field_name: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    severity: ChangeSeverity = ChangeSeverity.MINOR


@dataclass
class ChangeAnalysisResult:
    """Result of change analysis"""
    change_type: ChangeType
    version_bump: str  # "major", "minor", "patch", "none"
    schema_changes: List[SchemaChange]
    quality_rule_changes: List[Dict]
    summary: str
    breaking_changes: List[str]
    new_features: List[str]
    fixes: List[str]


class ContractChangeAnalyzer:
    """
    Analyzes changes between two data contract versions.

    Rules for semantic versioning:
    - MAJOR (X.0.0): Breaking changes
      - Removed schemas
      - Removed required fields
      - Changed field types (incompatible)
      - Stricter quality rules
    - MINOR (0.X.0): New features (backward compatible)
      - New schemas
      - New optional fields
      - New quality rules (not stricter)
    - PATCH (0.0.X): Bug fixes, documentation
      - Description changes
      - Relaxed quality rules
      - Metadata updates
    """

    def __init__(self):
        self.breaking_changes: List[str] = []
        self.new_features: List[str] = []
        self.fixes: List[str] = []
        self.schema_changes: List[SchemaChange] = []
        self.quality_rule_changes: List[Dict] = []

    def analyze(self, old_contract: Dict, new_contract: Dict) -> ChangeAnalysisResult:
        """
        Analyze changes between two contracts.

        Args:
            old_contract: Previous version (dict representation)
            new_contract: New version (dict representation)

        Returns:
            ChangeAnalysisResult with detected changes and recommended version bump
        """
        self._reset()

        # Only analyze schema changes if 'schema' is provided in the update
        # (avoid false positives when field is not included in partial updates)
        if 'schema' in new_contract:
            self._analyze_schema_changes(
                old_contract.get('schema', []),
                new_contract.get('schema', [])
            )

        # Only analyze quality rule changes if 'qualityRules' is provided in the update
        if 'qualityRules' in new_contract:
            self._analyze_quality_rule_changes(
                old_contract.get('qualityRules', []),
                new_contract.get('qualityRules', [])
            )

        # Determine change type and version bump
        change_type, version_bump = self._determine_change_type()

        # Generate summary
        summary = self._generate_summary()

        return ChangeAnalysisResult(
            change_type=change_type,
            version_bump=version_bump,
            schema_changes=self.schema_changes,
            quality_rule_changes=self.quality_rule_changes,
            summary=summary,
            breaking_changes=self.breaking_changes,
            new_features=self.new_features,
            fixes=self.fixes
        )

    def _reset(self):
        """Reset internal state"""
        self.breaking_changes = []
        self.new_features = []
        self.fixes = []
        self.schema_changes = []
        self.quality_rule_changes = []

    def _analyze_schema_changes(self, old_schemas: List[Dict], new_schemas: List[Dict]):
        """Analyze changes in schema definitions"""
        old_schema_map = {s.get('name'): s for s in old_schemas}
        new_schema_map = {s.get('name'): s for s in new_schemas}

        old_names = set(old_schema_map.keys())
        new_names = set(new_schema_map.keys())

        # Removed schemas (BREAKING)
        for removed_name in old_names - new_names:
            self.breaking_changes.append(f"Removed schema: {removed_name}")
            self.schema_changes.append(SchemaChange(
                change_type="removed",
                schema_name=removed_name,
                severity=ChangeSeverity.CRITICAL
            ))

        # Added schemas (FEATURE)
        for added_name in new_names - old_names:
            self.new_features.append(f"Added schema: {added_name}")
            self.schema_changes.append(SchemaChange(
                change_type="added",
                schema_name=added_name,
                severity=ChangeSeverity.MODERATE
            ))

        # Modified schemas
        for schema_name in old_names & new_names:
            self._analyze_schema_properties(
                schema_name,
                old_schema_map[schema_name].get('properties', []),
                new_schema_map[schema_name].get('properties', [])
            )

    def _analyze_schema_properties(self, schema_name: str, old_props: List[Dict], new_props: List[Dict]):
        """Analyze changes in schema properties"""
        old_prop_map = {p.get('name'): p for p in old_props}
        new_prop_map = {p.get('name'): p for p in new_props}

        old_prop_names = set(old_prop_map.keys())
        new_prop_names = set(new_prop_map.keys())

        # Removed properties
        for removed_prop in old_prop_names - new_prop_names:
            old_prop = old_prop_map[removed_prop]
            if old_prop.get('required', False):
                # Removing required field is BREAKING
                self.breaking_changes.append(f"Removed required field: {schema_name}.{removed_prop}")
                severity = ChangeSeverity.CRITICAL
            else:
                # Removing optional field is MINOR
                self.fixes.append(f"Removed optional field: {schema_name}.{removed_prop}")
                severity = ChangeSeverity.MINOR

            self.schema_changes.append(SchemaChange(
                change_type="removed",
                schema_name=schema_name,
                field_name=removed_prop,
                severity=severity
            ))

        # Added properties
        for added_prop in new_prop_names - old_prop_names:
            new_prop = new_prop_map[added_prop]
            if new_prop.get('required', False):
                # Adding required field is BREAKING
                self.breaking_changes.append(f"Added required field: {schema_name}.{added_prop}")
                severity = ChangeSeverity.CRITICAL
            else:
                # Adding optional field is FEATURE
                self.new_features.append(f"Added optional field: {schema_name}.{added_prop}")
                severity = ChangeSeverity.MODERATE

            self.schema_changes.append(SchemaChange(
                change_type="added",
                schema_name=schema_name,
                field_name=added_prop,
                severity=severity
            ))

        # Modified properties
        for prop_name in old_prop_names & new_prop_names:
            old_prop = old_prop_map[prop_name]
            new_prop = new_prop_map[prop_name]

            # Check type changes
            old_type = old_prop.get('logicalType') or old_prop.get('logical_type')
            new_type = new_prop.get('logicalType') or new_prop.get('logical_type')

            if old_type and new_type and old_type != new_type:
                # Type change is potentially BREAKING
                if self._is_compatible_type_change(old_type, new_type):
                    self.fixes.append(f"Compatible type change: {schema_name}.{prop_name} ({old_type} → {new_type})")
                    severity = ChangeSeverity.MINOR
                else:
                    self.breaking_changes.append(f"Incompatible type change: {schema_name}.{prop_name} ({old_type} → {new_type})")
                    severity = ChangeSeverity.CRITICAL

                self.schema_changes.append(SchemaChange(
                    change_type="type_changed",
                    schema_name=schema_name,
                    field_name=prop_name,
                    old_value=old_type,
                    new_value=new_type,
                    severity=severity
                ))

            # Check required flag changes
            old_required = old_prop.get('required', False)
            new_required = new_prop.get('required', False)

            if old_required != new_required:
                if new_required:
                    # Making field required is BREAKING
                    self.breaking_changes.append(f"Field became required: {schema_name}.{prop_name}")
                    severity = ChangeSeverity.CRITICAL
                else:
                    # Making field optional is FIX
                    self.fixes.append(f"Field became optional: {schema_name}.{prop_name}")
                    severity = ChangeSeverity.MINOR

                self.schema_changes.append(SchemaChange(
                    change_type="modified",
                    schema_name=schema_name,
                    field_name=prop_name,
                    old_value=f"required={old_required}",
                    new_value=f"required={new_required}",
                    severity=severity
                ))

    def _is_compatible_type_change(self, old_type: str, new_type: str) -> bool:
        """
        Check if type change is backward compatible.
        Compatible changes: narrowing precision is usually safe (e.g., double → float)
        Incompatible: changing fundamental type (string → int)
        """
        # Define compatible type transitions
        compatible_transitions = {
            ('double', 'float'),
            ('long', 'int'),
            ('timestamp', 'date'),
        }

        return (old_type, new_type) in compatible_transitions

    def _analyze_quality_rule_changes(self, old_rules: List[Dict], new_rules: List[Dict]):
        """Analyze changes in quality rules"""
        old_rule_map = {r.get('name', r.get('id')): r for r in old_rules}
        new_rule_map = {r.get('name', r.get('id')): r for r in new_rules}

        old_rule_ids = set(old_rule_map.keys())
        new_rule_ids = set(new_rule_map.keys())

        # Removed rules (FIX - less strict)
        for removed_id in old_rule_ids - new_rule_ids:
            self.fixes.append(f"Removed quality rule: {removed_id}")
            self.quality_rule_changes.append({
                'type': 'removed',
                'rule_id': removed_id,
                'severity': 'minor'
            })

        # Added rules (potentially BREAKING if stricter)
        for added_id in new_rule_ids - old_rule_ids:
            rule = new_rule_map[added_id]
            # Assume new rules are BREAKING if they add constraints
            self.breaking_changes.append(f"Added quality rule: {added_id}")
            self.quality_rule_changes.append({
                'type': 'added',
                'rule_id': added_id,
                'severity': 'critical'
            })

    def _determine_change_type(self) -> Tuple[ChangeType, str]:
        """Determine change type and recommended version bump"""
        if self.breaking_changes:
            return ChangeType.BREAKING, "major"
        elif self.new_features:
            return ChangeType.FEATURE, "minor"
        elif self.fixes:
            return ChangeType.FIX, "patch"
        else:
            return ChangeType.NONE, "none"

    def _generate_summary(self) -> str:
        """Generate human-readable summary of changes"""
        parts = []

        if self.breaking_changes:
            parts.append(f"**Breaking Changes ({len(self.breaking_changes)}):**\n" +
                        "\n".join(f"- {c}" for c in self.breaking_changes))

        if self.new_features:
            parts.append(f"**New Features ({len(self.new_features)}):**\n" +
                        "\n".join(f"- {f}" for f in self.new_features))

        if self.fixes:
            parts.append(f"**Improvements ({len(self.fixes)}):**\n" +
                        "\n".join(f"- {f}" for f in self.fixes))

        if not parts:
            return "No significant changes detected"

        return "\n\n".join(parts)
