"""
Unit tests for semantic helpers utility functions.

Tests the shared semantic processing utilities to ensure consistent
handling of ODCS authoritativeDefinitions across all routes.
"""

import pytest
from unittest.mock import Mock, patch
from typing import Dict, Any, List

from src.utils.semantic_helpers import (
    process_contract_semantic_links,
    process_schema_semantic_links,
    process_property_semantic_links,
    process_all_semantic_links_from_odcs,
    get_semantic_assignment_type,
    SEMANTIC_ASSIGNMENT_TYPE
)
from src.models.semantic_links import EntitySemanticLinkCreate


class TestSemanticHelpers:
    """Test suite for semantic helpers utility functions."""

    @pytest.fixture
    def mock_semantic_manager(self):
        """Mock SemanticLinksManager for testing."""
        manager = Mock()
        manager.add = Mock()
        return manager

    def test_get_semantic_assignment_type(self):
        """Test that the semantic assignment type constant is correct."""
        expected = "http://databricks.com/ontology/uc/semanticAssignment"
        assert get_semantic_assignment_type() == expected
        assert SEMANTIC_ASSIGNMENT_TYPE == expected

    def test_process_contract_semantic_links_success(self, mock_semantic_manager):
        """Test successful processing of contract-level semantic links."""
        authoritative_definitions = [
            {
                "type": "http://databricks.com/ontology/uc/semanticAssignment",
                "url": "https://example.com/business-concept/customer"
            },
            {
                "type": "http://databricks.com/ontology/uc/semanticAssignment",
                "url": "https://example.com/business-concept/revenue"
            },
            {
                "type": "http://other.com/ontology/different",
                "url": "https://example.com/should-be-ignored"
            }
        ]

        result = process_contract_semantic_links(
            semantic_manager=mock_semantic_manager,
            contract_id="contract-123",
            authoritative_definitions=authoritative_definitions,
            created_by="test-user"
        )

        assert result == 2  # Only semantic assignment types should be processed
        assert mock_semantic_manager.add.call_count == 2

        # Check the semantic links that were created
        calls = mock_semantic_manager.add.call_args_list
        first_link = calls[0][0][0]  # First argument of first call
        assert first_link.entity_id == "contract-123"
        assert first_link.entity_type == "data_contract"
        assert first_link.iri == "https://example.com/business-concept/customer"

        second_link = calls[1][0][0]  # First argument of second call
        assert second_link.iri == "https://example.com/business-concept/revenue"

    def test_process_contract_semantic_links_empty(self, mock_semantic_manager):
        """Test processing with empty authoritative definitions."""
        result = process_contract_semantic_links(
            semantic_manager=mock_semantic_manager,
            contract_id="contract-123",
            authoritative_definitions=[],
            created_by="test-user"
        )

        assert result == 0
        mock_semantic_manager.add.assert_not_called()

    def test_process_contract_semantic_links_wrong_type(self, mock_semantic_manager):
        """Test processing with non-semantic assignment types."""
        authoritative_definitions = [
            {
                "type": "http://other.com/ontology/different",
                "url": "https://example.com/should-be-ignored"
            }
        ]

        result = process_contract_semantic_links(
            semantic_manager=mock_semantic_manager,
            contract_id="contract-123",
            authoritative_definitions=authoritative_definitions,
            created_by="test-user"
        )

        assert result == 0
        mock_semantic_manager.add.assert_not_called()

    def test_process_schema_semantic_links_success(self, mock_semantic_manager):
        """Test successful processing of schema-level semantic links."""
        authoritative_definitions = [
            {
                "type": "http://databricks.com/ontology/uc/semanticAssignment",
                "url": "https://example.com/business-concept/customer-table"
            }
        ]

        result = process_schema_semantic_links(
            semantic_manager=mock_semantic_manager,
            contract_id="contract-123",
            schema_name="customers",
            authoritative_definitions=authoritative_definitions,
            created_by="test-user"
        )

        assert result == 1
        mock_semantic_manager.add.assert_called_once()

        # Check the semantic link that was created
        call_args = mock_semantic_manager.add.call_args[0][0]
        assert call_args.entity_id == "contract-123#customers"
        assert call_args.entity_type == "data_contract_schema"
        assert call_args.iri == "https://example.com/business-concept/customer-table"

    def test_process_property_semantic_links_success(self, mock_semantic_manager):
        """Test successful processing of property-level semantic links."""
        authoritative_definitions = [
            {
                "type": "http://databricks.com/ontology/uc/semanticAssignment",
                "url": "https://example.com/business-concept/customer-id"
            }
        ]

        result = process_property_semantic_links(
            semantic_manager=mock_semantic_manager,
            contract_id="contract-123",
            schema_name="customers",
            property_name="customer_id",
            authoritative_definitions=authoritative_definitions,
            created_by="test-user"
        )

        assert result == 1
        mock_semantic_manager.add.assert_called_once()

        # Check the semantic link that was created
        call_args = mock_semantic_manager.add.call_args[0][0]
        assert call_args.entity_id == "contract-123#customers#customer_id"
        assert call_args.entity_type == "data_contract_property"
        assert call_args.iri == "https://example.com/business-concept/customer-id"

    def test_process_all_semantic_links_from_odcs_success(self, mock_semantic_manager):
        """Test processing all semantic links from a complete ODCS contract."""
        parsed_odcs = {
            "name": "customer-contract",
            "authoritativeDefinitions": [
                {
                    "type": "http://databricks.com/ontology/uc/semanticAssignment",
                    "url": "https://example.com/business-concept/customer-contract"
                }
            ],
            "schema": [
                {
                    "name": "customers",
                    "authoritativeDefinitions": [
                        {
                            "type": "http://databricks.com/ontology/uc/semanticAssignment",
                            "url": "https://example.com/business-concept/customer-table"
                        }
                    ],
                    "properties": [
                        {
                            "name": "customer_id",
                            "authoritativeDefinitions": [
                                {
                                    "type": "http://databricks.com/ontology/uc/semanticAssignment",
                                    "url": "https://example.com/business-concept/customer-id"
                                }
                            ]
                        },
                        {
                            "name": "customer_name",
                            "authoritativeDefinitions": [
                                {
                                    "type": "http://databricks.com/ontology/uc/semanticAssignment",
                                    "url": "https://example.com/business-concept/customer-name"
                                }
                            ]
                        }
                    ]
                },
                {
                    "name": "orders",
                    "properties": [
                        {
                            "name": "order_id",
                            "authoritativeDefinitions": [
                                {
                                    "type": "http://databricks.com/ontology/uc/semanticAssignment",
                                    "url": "https://example.com/business-concept/order-id"
                                }
                            ]
                        }
                    ]
                }
            ]
        }

        result = process_all_semantic_links_from_odcs(
            semantic_manager=mock_semantic_manager,
            contract_id="contract-123",
            parsed_odcs=parsed_odcs,
            created_by="test-user"
        )

        # Expected: 1 contract + 1 schema + 3 properties = 5 total
        assert result == 5
        assert mock_semantic_manager.add.call_count == 5

    def test_process_all_semantic_links_handles_missing_sections(self, mock_semantic_manager):
        """Test processing ODCS with missing sections."""
        parsed_odcs = {
            "name": "minimal-contract"
            # No authoritativeDefinitions, no schema
        }

        result = process_all_semantic_links_from_odcs(
            semantic_manager=mock_semantic_manager,
            contract_id="contract-123",
            parsed_odcs=parsed_odcs,
            created_by="test-user"
        )

        assert result == 0
        mock_semantic_manager.add.assert_not_called()

    def test_process_all_semantic_links_handles_malformed_data(self, mock_semantic_manager):
        """Test processing with malformed ODCS data."""
        parsed_odcs = {
            "name": "malformed-contract",
            "schema": [
                "invalid-schema-as-string",
                {
                    "name": "valid-schema",
                    "properties": [
                        "invalid-property-as-string",
                        {
                            "name": "valid-property",
                            "authoritativeDefinitions": [
                                {
                                    "type": "http://databricks.com/ontology/uc/semanticAssignment",
                                    "url": "https://example.com/business-concept/valid-property"
                                }
                            ]
                        }
                    ]
                }
            ]
        }

        result = process_all_semantic_links_from_odcs(
            semantic_manager=mock_semantic_manager,
            contract_id="contract-123",
            parsed_odcs=parsed_odcs,
            created_by="test-user"
        )

        # Should only process the one valid property
        assert result == 1
        mock_semantic_manager.add.assert_called_once()

    def test_semantic_manager_exception_handling(self, mock_semantic_manager):
        """Test that exceptions in semantic manager are logged but don't break processing."""
        # Make the first call succeed, second call fail
        mock_semantic_manager.add.side_effect = [None, Exception("Database error")]

        authoritative_definitions = [
            {
                "type": "http://databricks.com/ontology/uc/semanticAssignment",
                "url": "https://example.com/business-concept/success"
            },
            {
                "type": "http://databricks.com/ontology/uc/semanticAssignment",
                "url": "https://example.com/business-concept/failure"
            }
        ]

        with patch('src.utils.semantic_helpers.logger') as mock_logger:
            result = process_contract_semantic_links(
                semantic_manager=mock_semantic_manager,
                contract_id="contract-123",
                authoritative_definitions=authoritative_definitions,
                created_by="test-user"
            )

            # Should successfully process the first link, log warning for the second
            assert result == 1
            assert mock_semantic_manager.add.call_count == 2
            mock_logger.warning.assert_called_once()

    def test_missing_url_handling(self, mock_semantic_manager):
        """Test that definitions without URLs are skipped."""
        authoritative_definitions = [
            {
                "type": "http://databricks.com/ontology/uc/semanticAssignment",
                # Missing URL
            },
            {
                "type": "http://databricks.com/ontology/uc/semanticAssignment",
                "url": ""  # Empty URL
            },
            {
                "type": "http://databricks.com/ontology/uc/semanticAssignment",
                "url": "https://example.com/business-concept/valid"
            }
        ]

        result = process_contract_semantic_links(
            semantic_manager=mock_semantic_manager,
            contract_id="contract-123",
            authoritative_definitions=authoritative_definitions,
            created_by="test-user"
        )

        # Should only process the one with a valid URL
        assert result == 1
        mock_semantic_manager.add.assert_called_once()