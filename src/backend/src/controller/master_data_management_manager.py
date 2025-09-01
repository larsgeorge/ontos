import os
from typing import List, Optional

import yaml

from ..models.master_data_management import (
    MasterDataManagementComparisonResult,
    MasterDataManagementDataset,
)


class MasterDataManagementManager:
    def __init__(self):
        self.datasets: List[MasterDataManagementDataset] = []
        self.comparisons: List[MasterDataManagementComparisonResult] = []
        self.load_sample_data()

    def load_sample_data(self):
        """Load sample data from YAML file"""
        data_file = os.path.join(os.path.dirname(__file__), '../data/master_data_management.yaml')
        if os.path.exists(data_file):
            with open(data_file) as f:
                data = yaml.safe_load(f)
                self.datasets = [MasterDataManagementDataset(**dataset) for dataset in data.get('datasets', [])]
                self.comparisons = [MasterDataManagementComparisonResult(**comp) for comp in data.get('comparisons', [])]

    def get_datasets(self, entity_type: Optional[str] = None) -> List[MasterDataManagementDataset]:
        """Get all datasets, optionally filtered by entity type"""
        if entity_type:
            return [d for d in self.datasets if d.type == entity_type]
        return self.datasets

    def get_dataset_by_id(self, dataset_id: str) -> Optional[MasterDataManagementDataset]:
        """Get a specific dataset by ID"""
        return next((d for d in self.datasets if d.id == dataset_id), None)

    def create_dataset(self, dataset: MasterDataManagementDataset) -> MasterDataManagementDataset:
        """Create a new dataset"""
        self.datasets.append(dataset)
        return dataset

    def update_dataset(self, dataset_id: str, dataset: MasterDataManagementDataset) -> Optional[MasterDataManagementDataset]:
        """Update an existing dataset"""
        for i, d in enumerate(self.datasets):
            if d.id == dataset_id:
                self.datasets[i] = dataset
                return dataset
        return None

    def delete_dataset(self, dataset_id: str) -> bool:
        """Delete a dataset"""
        initial_length = len(self.datasets)
        self.datasets = [d for d in self.datasets if d.id != dataset_id]
        return len(self.datasets) < initial_length

    def compare_datasets(self, dataset_ids: List[str]) -> List[MasterDataManagementComparisonResult]:
        """Compare selected datasets and generate comparison results"""
        if len(dataset_ids) < 2:
            return []

        new_comparisons = []
        for i in range(len(dataset_ids)):
            for j in range(i + 1, len(dataset_ids)):
                dataset_a = self.get_dataset_by_id(dataset_ids[i])
                dataset_b = self.get_dataset_by_id(dataset_ids[j])

                if not dataset_a or not dataset_b:
                    continue

                # Generate mock comparison results
                comparison = MasterDataManagementComparisonResult(
                    dataset_a=dataset_a.name,
                    dataset_b=dataset_b.name,
                    matching_entities=min(dataset_a.total_records, dataset_b.total_records) // 2,
                    unique_to_a=dataset_a.total_records // 3,
                    unique_to_b=dataset_b.total_records // 3,
                    match_score=85.5,
                    common_columns=['id', 'name', 'email', 'phone', 'address'],
                    sample_matches=[
                        {"entity_a": "CUST001", "entity_b": "C-001", "confidence": 0.95},
                        {"entity_a": "CUST002", "entity_b": "C-002", "confidence": 0.88},
                        {"entity_a": "CUST003", "entity_b": "C-003", "confidence": 0.92}
                    ],
                    column_stats=[
                        {"column": 'id', "match_rate": 0.95, "null_rate": 0.01},
                        {"column": 'name', "match_rate": 0.85, "null_rate": 0.05},
                        {"column": 'email', "match_rate": 0.75, "null_rate": 0.15},
                        {"column": 'phone', "match_rate": 0.65, "null_rate": 0.25}
                    ]
                )
                new_comparisons.append(comparison)

        self.comparisons.extend(new_comparisons)
        return new_comparisons

    def get_comparison_results(self) -> List[MasterDataManagementComparisonResult]:
        """Get all comparison results"""
        return self.comparisons

    def get_comparison_by_datasets(self, dataset_a: str, dataset_b: str) -> Optional[MasterDataManagementComparisonResult]:
        """Get comparison result for specific datasets"""
        return next(
            (c for c in self.comparisons
             if (c.dataset_a == dataset_a and c.dataset_b == dataset_b) or
                (c.dataset_a == dataset_b and c.dataset_b == dataset_a)),
            None
        )
