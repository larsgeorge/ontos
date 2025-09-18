import pytest
import yaml
import json
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session

from src.controller.data_contracts_manager import DataContractsManager
from src.db_models.data_contracts import (
    DataContractDb,
    DataContractTagDb,
    DataContractRoleDb,
    DataContractServerDb,
    DataContractServerPropertyDb,
    DataContractTeamDb,
    DataContractSupportDb,
    DataContractPricingDb,
    DataContractAuthorityDb,
    DataContractCustomPropertyDb,
    DataContractSlaPropertyDb,
    SchemaObjectDb,
    SchemaPropertyDb,
    DataQualityCheckDb,
    SchemaObjectAuthorityDb,
    SchemaObjectCustomPropertyDb,
)


class TestDataContractsManager:
    """Unit tests for DataContractsManager focusing on ODCS functionality."""

    @pytest.fixture
    def temp_data_dir(self):
        """Create a temporary directory for test data files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def manager(self, temp_data_dir):
        """Create a DataContractsManager instance for testing."""
        return DataContractsManager(data_dir=temp_data_dir)

    @pytest.fixture
    def sample_contract_db(self):
        """Create a sample DataContractDb object for testing."""
        contract = DataContractDb(
            id="eb4e9e0a-8929-4fd9-a3e5-4fbd184482f4",
            name="my quantum",
            kind="DataContract",
            api_version="v3.0.2",
            version="1.1.0",
            status="active",
            owner="localdev",
            tenant="ClimateQuantumInc",
            data_product="my quantum",
            sla_default_element="tab1.txn_ref_dt",
            contract_created_ts=datetime(2022, 11, 15, 2, 59, 43),
            description_usage="Predict sales over time",
            description_purpose="Views built on top of the seller tables.",
            description_limitations="Data based on seller perspective, no buyer information"
        )

        # Add domain relationship
        contract.domain_id = "test-domain-id"

        return contract

    @pytest.fixture
    def sample_schema_object(self, sample_contract_db):
        """Create a sample schema object with properties."""
        schema_obj = SchemaObjectDb(
            id="schema-obj-1",
            contract_id=sample_contract_db.id,
            name="tbl",
            physical_name="tbl_1",
            business_name="Core Payment Metrics",
            physical_type="table",
            description="Provides core payment metrics",
            data_granularity_description="Aggregation on columns txn_ref_dt, pmt_txn_id",
            tags='["finance", "payments"]'
        )

        # Add properties
        prop1 = SchemaPropertyDb(
            id="prop-1",
            object_id=schema_obj.id,
            name="transaction_reference_date",
            logical_type="date",
            physical_type="date",
            required=False,
            unique=False,
            partitioned=True,
            partition_key_position=1,
            classification="public",
            transform_logic="sel t1.txn_dt as txn_ref_dt from table_name_1 as t1, table_name_2 as t2, table_name_3 as t3 where t1.txn_dt=date-3",
            transform_source_objects='["table_name_1", "table_name_2", "table_name_3"]',
            transform_description="Reference date for transaction",
            examples='["2022-10-03", "2020-01-28"]',
            critical_data_element=False,
            business_name="transaction reference date"
        )

        prop2 = SchemaPropertyDb(
            id="prop-2",
            object_id=schema_obj.id,
            name="rcvr_id",
            logical_type="string",
            physical_type="varchar(18)",
            required=False,
            unique=False,
            partitioned=False,
            primary_key_position=1,
            classification="restricted",
            transform_description="A description for column rcvr_id.",
            critical_data_element=False,
            business_name="receiver id"
        )

        prop3 = SchemaPropertyDb(
            id="prop-3",
            object_id=schema_obj.id,
            name="rcvr_cntry_code",
            logical_type="string",
            physical_type="varchar(2)",
            required=False,
            unique=False,
            partitioned=False,
            classification="public",
            encrypted_name="rcvr_cntry_code_encrypted",
            transform_description="Country code",
            critical_data_element=False,
            business_name="receiver country code"
        )

        schema_obj.properties = [prop1, prop2, prop3]

        # Add quality checks
        quality1 = DataQualityCheckDb(
            id="quality-1",
            object_id=schema_obj.id,
            rule="nullCheck",
            type="library",
            description="column should not contain null values",
            dimension="completeness",
            business_impact="operational",
            severity="error",
            schedule="0 20 * * *",
            scheduler="cron"
        )

        quality2 = DataQualityCheckDb(
            id="quality-2",
            object_id=schema_obj.id,
            rule="countCheck",
            type="library",
            description="Ensure row count is within expected volume range",
            dimension="completeness",
            business_impact="operational",
            severity="error",
            method="reconciliation",
            schedule="0 20 * * *",
            scheduler="cron"
        )

        schema_obj.quality_checks = [quality1, quality2]

        # Add authoritative definitions
        auth_def1 = SchemaObjectAuthorityDb(
            id="auth-1",
            schema_object_id=schema_obj.id,
            url="https://catalog.data.gov/dataset/air-quality",
            type="businessDefinition"
        )

        auth_def2 = SchemaObjectAuthorityDb(
            id="auth-2",
            schema_object_id=schema_obj.id,
            url="https://youtu.be/jbY1BKFj9ec",
            type="videoTutorial"
        )

        schema_obj.authoritative_definitions = [auth_def1, auth_def2]

        # Add custom properties
        custom_prop = SchemaObjectCustomPropertyDb(
            id="custom-1",
            schema_object_id=schema_obj.id,
            property="business-key",
            value='["txn_ref_dt", "rcvr_id"]'
        )

        schema_obj.custom_properties = [custom_prop]

        return schema_obj

    @pytest.fixture
    def full_contract_db(self, sample_contract_db, sample_schema_object):
        """Create a fully populated contract for comprehensive testing."""
        # Add tags
        tag1 = DataContractTagDb(id="tag-1", contract_id=sample_contract_db.id, name="transactions")
        sample_contract_db.tags = [tag1]

        # Add team members
        team1 = DataContractTeamDb(
            id="team-1",
            contract_id=sample_contract_db.id,
            username="ceastwood",
            role="Data Scientist",
            date_in="2022-08-02",
            date_out="2022-10-01",
            replaced_by_username="mhopper"
        )
        team2 = DataContractTeamDb(
            id="team-2",
            contract_id=sample_contract_db.id,
            username="mhopper",
            role="Data Scientist",
            date_in="2022-10-01"
        )
        team3 = DataContractTeamDb(
            id="team-3",
            contract_id=sample_contract_db.id,
            username="daustin",
            role="Owner",
            date_in="2022-10-01"
        )
        sample_contract_db.team = [team1, team2, team3]

        # Add roles
        role1 = DataContractRoleDb(
            id="role-1",
            contract_id=sample_contract_db.id,
            role="microstrategy_user_opr",
            access="read",
            first_level_approvers="Reporting Manager",
            second_level_approvers="mandolorian"
        )
        role2 = DataContractRoleDb(
            id="role-2",
            contract_id=sample_contract_db.id,
            role="bq_queryman_user_opr",
            access="read",
            first_level_approvers="Reporting Manager",
            second_level_approvers="na"
        )
        sample_contract_db.roles = [role1, role2]

        # Add servers
        server1 = DataContractServerDb(
            id="server-1",
            contract_id=sample_contract_db.id,
            server="my-postgres",
            type="postgres",
            description=None,
            environment=None
        )

        # Add server properties
        prop1 = DataContractServerPropertyDb(id="sprop-1", server_id=server1.id, key="host", value="localhost")
        prop2 = DataContractServerPropertyDb(id="sprop-2", server_id=server1.id, key="port", value="5432")
        prop3 = DataContractServerPropertyDb(id="sprop-3", server_id=server1.id, key="database", value="pypl-edw")
        prop4 = DataContractServerPropertyDb(id="sprop-4", server_id=server1.id, key="schema", value="pp_access_views")
        server1.properties = [prop1, prop2, prop3, prop4]

        sample_contract_db.servers = [server1]

        # Add support
        support1 = DataContractSupportDb(
            id="support-1",
            contract_id=sample_contract_db.id,
            channel="#product-help",
            url="https://aidaug.slack.com/archives/C05UZRSBKLY",
            tool="slack"
        )
        support2 = DataContractSupportDb(
            id="support-2",
            contract_id=sample_contract_db.id,
            channel="datacontract-ann",
            url="mailto:datacontract-ann@bitol.io",
            tool="email"
        )
        support3 = DataContractSupportDb(
            id="support-3",
            contract_id=sample_contract_db.id,
            channel="Feedback",
            url="https://product-feedback.com",
            description="General Product Feedback (Public)"
        )
        sample_contract_db.support = [support1, support2, support3]

        # Add pricing
        pricing = DataContractPricingDb(
            id="pricing-1",
            contract_id=sample_contract_db.id,
            price_amount="9.95",
            price_currency="USD",
            price_unit="megabyte"
        )
        sample_contract_db.pricing = pricing

        # Add SLA properties
        sla1 = DataContractSlaPropertyDb(
            id="sla-1",
            contract_id=sample_contract_db.id,
            property="latency",
            value="4",
            unit="d",
            element="tab1.txn_ref_dt"
        )
        sla2 = DataContractSlaPropertyDb(
            id="sla-2",
            contract_id=sample_contract_db.id,
            property="generalAvailability",
            value="2022-05-12T09:30:10-08:00"
        )
        sample_contract_db.sla_properties = [sla1, sla2]

        # Add custom properties
        custom1 = DataContractCustomPropertyDb(
            id="custom-1",
            contract_id=sample_contract_db.id,
            property="refRulesetName",
            value="gcsc.ruleset.name"
        )
        sample_contract_db.custom_properties = [custom1]

        # Add authoritative definitions
        auth1 = DataContractAuthorityDb(
            id="auth-1",
            contract_id=sample_contract_db.id,
            url="https://example.com/gdpr.pdf",
            type="privacy-statement"
        )
        sample_contract_db.authoritative_defs = [auth1]

        # Add schema objects
        sample_contract_db.schema_objects = [sample_schema_object]

        return sample_contract_db

    def test_build_odcs_from_db_basic_fields(self, manager, sample_contract_db):
        """Test basic ODCS field mapping from database object."""
        # Mock the domain resolution
        with patch('src.repositories.data_domain_repository.data_domain_repo') as mock_domain_repo:
            mock_domain = Mock()
            mock_domain.name = "seller"
            mock_domain_repo.get.return_value = mock_domain

            mock_db_session = Mock(spec=Session)

            odcs = manager.build_odcs_from_db(sample_contract_db, mock_db_session)

            # Test basic fields
            assert odcs['id'] == sample_contract_db.id
            assert odcs['kind'] == "DataContract"
            assert odcs['apiVersion'] == "v3.0.2"
            assert odcs['version'] == "1.1.0"
            assert odcs['status'] == "active"
            assert odcs['name'] == "my quantum"
            assert odcs['owner'] == "localdev"
            assert odcs['tenant'] == "ClimateQuantumInc"
            assert odcs['dataProduct'] == "my quantum"
            assert odcs['slaDefaultElement'] == "tab1.txn_ref_dt"
            assert odcs['domain'] == "seller"

            # Test description object
            assert 'description' in odcs
            assert odcs['description']['usage'] == "Predict sales over time"
            assert odcs['description']['purpose'] == "Views built on top of the seller tables."
            assert odcs['description']['limitations'] == "Data based on seller perspective, no buyer information"

    def test_build_odcs_from_db_without_domain(self, manager, sample_contract_db):
        """Test ODCS build when no domain is set."""
        sample_contract_db.domain_id = None

        odcs = manager.build_odcs_from_db(sample_contract_db, None)

        assert 'domain' not in odcs
        assert odcs['name'] == "my quantum"

    def test_build_odcs_from_db_domain_resolution_failure(self, manager, sample_contract_db):
        """Test graceful handling when domain resolution fails."""
        with patch('src.repositories.data_domain_repository.data_domain_repo') as mock_domain_repo:
            mock_domain_repo.get.side_effect = Exception("Database error")

            mock_db_session = Mock(spec=Session)

            odcs = manager.build_odcs_from_db(sample_contract_db, mock_db_session)

            # Should not have domain field when resolution fails
            assert 'domain' not in odcs
            assert odcs['name'] == "my quantum"

    def test_build_odcs_from_db_schema_properties(self, manager, full_contract_db):
        """Test schema and properties mapping in ODCS export."""
        with patch('src.repositories.data_domain_repository.data_domain_repo') as mock_domain_repo:
            mock_domain = Mock()
            mock_domain.name = "seller"
            mock_domain_repo.get.return_value = mock_domain

            # Mock semantic links manager
            with patch('src.controller.semantic_links_manager.SemanticLinksManager') as mock_semantic_manager:
                mock_semantic_manager.return_value.list_for_entity.return_value = []

                mock_db_session = Mock(spec=Session)

                odcs = manager.build_odcs_from_db(full_contract_db, mock_db_session)

                # Test schema structure
                assert 'schema' in odcs
                assert len(odcs['schema']) == 1

                schema = odcs['schema'][0]
                assert schema['name'] == "tbl"
                assert schema['physicalName'] == "tbl_1"
                assert schema['businessName'] == "Core Payment Metrics"
                assert schema['physicalType'] == "table"
                assert schema['description'] == "Provides core payment metrics"
                assert schema['dataGranularityDescription'] == "Aggregation on columns txn_ref_dt, pmt_txn_id"
                assert schema['tags'] == ["finance", "payments"]

                # Test properties
                assert 'properties' in schema
                assert len(schema['properties']) == 3

                # Test first property (transaction_reference_date)
                prop1 = schema['properties'][0]
                assert prop1['name'] == "transaction_reference_date"
                assert prop1['logicalType'] == "date"
                assert prop1['physicalType'] == "date"
                assert prop1['required'] == False
                assert prop1['unique'] == False
                assert prop1['partitioned'] == True
                assert prop1['primaryKey'] == False  # Should be false for non-primary keys
                assert prop1['primaryKeyPosition'] == -1  # Should be -1 for non-primary keys
                assert prop1['partitionKeyPosition'] == 1  # Should be 1 for partitioned property
                assert prop1['classification'] == "public"
                assert prop1['transformLogic'] == "sel t1.txn_dt as txn_ref_dt from table_name_1 as t1, table_name_2 as t2, table_name_3 as t3 where t1.txn_dt=date-3"
                assert prop1['transformSourceObjects'] == ["table_name_1", "table_name_2", "table_name_3"]
                assert prop1['description'] == "Reference date for transaction"
                assert prop1['examples'] == ["2022-10-03", "2020-01-28"]
                assert prop1['criticalDataElement'] == False
                assert prop1['businessName'] == "transaction reference date"
                assert 'tags' in prop1  # Should always have tags array

                # Test second property (rcvr_id) - primary key
                prop2 = schema['properties'][1]
                assert prop2['name'] == "rcvr_id"
                assert prop2['primaryKey'] == True
                assert prop2['primaryKeyPosition'] == 1
                assert prop2['partitionKeyPosition'] == -1  # Should be -1 for non-partitioned
                assert prop2['classification'] == "restricted"
                assert prop2['businessName'] == "receiver id"
                assert 'tags' in prop2  # Should always have tags array

                # Test third property (rcvr_cntry_code) - encrypted
                prop3 = schema['properties'][2]
                assert prop3['name'] == "rcvr_cntry_code"
                assert prop3['primaryKey'] == False  # Should be false for non-primary keys
                assert prop3['primaryKeyPosition'] == -1  # Should be -1 for non-primary keys
                assert prop3['partitionKeyPosition'] == -1  # Should be -1 for non-partitioned
                assert prop3['encryptedName'] == "rcvr_cntry_code_encrypted"
                assert prop3['classification'] == "public"
                assert prop3['businessName'] == "receiver country code"
                assert 'tags' in prop3  # Should always have tags array

    def test_build_odcs_from_db_quality_checks(self, manager, full_contract_db):
        """Test quality checks mapping in ODCS export."""
        with patch('src.repositories.data_domain_repository.data_domain_repo') as mock_domain_repo:
            mock_domain = Mock()
            mock_domain.name = "seller"
            mock_domain_repo.get.return_value = mock_domain

            # Mock semantic links manager
            with patch('src.controller.semantic_links_manager.SemanticLinksManager') as mock_semantic_manager:
                mock_semantic_manager.return_value.list_for_entity.return_value = []

                mock_db_session = Mock(spec=Session)

                odcs = manager.build_odcs_from_db(full_contract_db, mock_db_session)

                schema = odcs['schema'][0]
                assert 'quality' in schema
                assert len(schema['quality']) == 2

                # Test first quality check
                quality1 = schema['quality'][0]
                assert quality1['rule'] == "nullCheck"
                assert quality1['type'] == "library"
                assert quality1['description'] == "column should not contain null values"
                assert quality1['dimension'] == "completeness"
                assert quality1['businessImpact'] == "operational"
                assert quality1['severity'] == "error"
                assert quality1['schedule'] == "0 20 * * *"
                assert quality1['scheduler'] == "cron"

                # Test second quality check
                quality2 = schema['quality'][1]
                assert quality2['rule'] == "countCheck"
                assert quality2['method'] == "reconciliation"

    def test_build_odcs_from_db_team_members(self, manager, full_contract_db):
        """Test team members mapping in ODCS export."""
        with patch('src.repositories.data_domain_repository.data_domain_repo') as mock_domain_repo:
            mock_domain = Mock()
            mock_domain.name = "seller"
            mock_domain_repo.get.return_value = mock_domain

            # Mock semantic links manager
            with patch('src.controller.semantic_links_manager.SemanticLinksManager') as mock_semantic_manager:
                mock_semantic_manager.return_value.list_for_entity.return_value = []

                mock_db_session = Mock(spec=Session)

                odcs = manager.build_odcs_from_db(full_contract_db, mock_db_session)

                assert 'team' in odcs
                assert len(odcs['team']) == 3

                # Test team member 1
                team1 = odcs['team'][0]
                assert team1['role'] == "Data Scientist"
                assert team1['username'] == "ceastwood"
                assert team1['dateIn'] == "2022-08-02"
                assert team1['dateOut'] == "2022-10-01"

                # Test team member 2
                team2 = odcs['team'][1]
                assert team2['role'] == "Data Scientist"
                assert team2['username'] == "mhopper"
                assert team2['dateIn'] == "2022-10-01"
                assert 'dateOut' not in team2

    def test_build_odcs_from_db_roles(self, manager, full_contract_db):
        """Test roles mapping in ODCS export."""
        with patch('src.repositories.data_domain_repository.data_domain_repo') as mock_domain_repo:
            mock_domain = Mock()
            mock_domain.name = "seller"
            mock_domain_repo.get.return_value = mock_domain

            # Mock semantic links manager
            with patch('src.controller.semantic_links_manager.SemanticLinksManager') as mock_semantic_manager:
                mock_semantic_manager.return_value.list_for_entity.return_value = []

                mock_db_session = Mock(spec=Session)

                odcs = manager.build_odcs_from_db(full_contract_db, mock_db_session)

                assert 'roles' in odcs
                assert len(odcs['roles']) == 2

                # Test first role
                role1 = odcs['roles'][0]
                assert role1['role'] == "microstrategy_user_opr"
                assert role1['access'] == "read"
                assert role1['firstLevelApprovers'] == "Reporting Manager"
                assert role1['secondLevelApprovers'] == "mandolorian"

    def test_build_odcs_from_db_servers(self, manager, full_contract_db):
        """Test servers mapping in ODCS export."""
        with patch('src.repositories.data_domain_repository.data_domain_repo') as mock_domain_repo:
            mock_domain = Mock()
            mock_domain.name = "seller"
            mock_domain_repo.get.return_value = mock_domain

            # Mock semantic links manager
            with patch('src.controller.semantic_links_manager.SemanticLinksManager') as mock_semantic_manager:
                mock_semantic_manager.return_value.list_for_entity.return_value = []

                mock_db_session = Mock(spec=Session)

                odcs = manager.build_odcs_from_db(full_contract_db, mock_db_session)

                assert 'servers' in odcs
                assert len(odcs['servers']) == 1

                server = odcs['servers'][0]
                assert server['server'] == "my-postgres"
                assert server['type'] == "postgres"
                assert server['host'] == "localhost"
                assert server['port'] == 5432  # Should be converted to integer
                assert server['database'] == "pypl-edw"
                assert server['schema'] == "pp_access_views"

    def test_build_odcs_from_db_support_sla_pricing(self, manager, full_contract_db):
        """Test support, SLA, and pricing mapping in ODCS export."""
        with patch('src.repositories.data_domain_repository.data_domain_repo') as mock_domain_repo:
            mock_domain = Mock()
            mock_domain.name = "seller"
            mock_domain_repo.get.return_value = mock_domain

            # Mock semantic links manager
            with patch('src.controller.semantic_links_manager.SemanticLinksManager') as mock_semantic_manager:
                mock_semantic_manager.return_value.list_for_entity.return_value = []

                mock_db_session = Mock(spec=Session)

                odcs = manager.build_odcs_from_db(full_contract_db, mock_db_session)

                # Test support
                assert 'support' in odcs
                assert len(odcs['support']) == 3

                support1 = odcs['support'][0]
                assert support1['channel'] == "#product-help"
                assert support1['url'] == "https://aidaug.slack.com/archives/C05UZRSBKLY"
                assert support1['tool'] == "slack"

                # Test SLA properties
                assert 'slaProperties' in odcs
                assert len(odcs['slaProperties']) == 2

                sla1 = odcs['slaProperties'][0]
                assert sla1['property'] == "latency"
                assert sla1['value'] == 4  # Should be converted to integer
                assert sla1['unit'] == "d"
                assert sla1['element'] == "tab1.txn_ref_dt"

                # Test pricing
                assert 'price' in odcs
                price = odcs['price']
                assert price['priceAmount'] == 9.95  # Should be converted to float
                assert price['priceCurrency'] == "USD"
                assert price['priceUnit'] == "megabyte"

    def test_build_odcs_from_db_tags_and_custom_properties(self, manager, full_contract_db):
        """Test tags and custom properties mapping in ODCS export."""
        with patch('src.repositories.data_domain_repository.data_domain_repo') as mock_domain_repo:
            mock_domain = Mock()
            mock_domain.name = "seller"
            mock_domain_repo.get.return_value = mock_domain

            # Mock semantic links manager
            with patch('src.controller.semantic_links_manager.SemanticLinksManager') as mock_semantic_manager:
                mock_semantic_manager.return_value.list_for_entity.return_value = []

                mock_db_session = Mock(spec=Session)

                odcs = manager.build_odcs_from_db(full_contract_db, mock_db_session)

                # Test tags
                assert 'tags' in odcs
                assert odcs['tags'] == ["transactions"]

                # Test custom properties
                assert 'customProperties' in odcs
                custom_props = odcs['customProperties']
                assert custom_props['refRulesetName'] == "gcsc.ruleset.name"

    def test_build_odcs_from_db_missing_relationships(self, manager, sample_contract_db):
        """Test ODCS build with minimal relationships."""
        # Don't add any relationships to test missing data handling
        with patch('src.repositories.data_domain_repository.data_domain_repo') as mock_domain_repo:
            mock_domain = Mock()
            mock_domain.name = "seller"
            mock_domain_repo.get.return_value = mock_domain

            # Mock semantic links manager
            with patch('src.controller.semantic_links_manager.SemanticLinksManager') as mock_semantic_manager:
                mock_semantic_manager.return_value.list_for_entity.return_value = []

                mock_db_session = Mock(spec=Session)

                odcs = manager.build_odcs_from_db(sample_contract_db, mock_db_session)

                # Should have basic fields but no optional sections
                assert 'schema' not in odcs
                assert 'team' not in odcs
                assert 'roles' not in odcs
                assert 'servers' not in odcs
                assert 'support' not in odcs
                assert 'price' not in odcs
                assert 'tags' not in odcs
                assert 'customProperties' not in odcs

                # But should still have basic required fields
                assert odcs['name'] == "my quantum"
                assert odcs['version'] == "1.1.0"

    def test_build_odcs_from_db_semantic_assignments(self, manager, full_contract_db):
        """Test semantic assignments injection in ODCS export."""
        with patch('src.repositories.data_domain_repository.data_domain_repo') as mock_domain_repo:
            mock_domain = Mock()
            mock_domain.name = "seller"
            mock_domain_repo.get.return_value = mock_domain

            # Mock semantic links manager with some test links
            with patch('src.controller.semantic_links_manager.SemanticLinksManager') as mock_semantic_manager_class:
                mock_semantic_manager = Mock()
                mock_semantic_manager_class.return_value = mock_semantic_manager

                # Mock contract-level semantic links
                mock_contract_link = Mock()
                mock_contract_link.iri = "http://example.com/contract-semantic"
                mock_semantic_manager.list_for_entity.return_value = [mock_contract_link]

                mock_db_session = Mock(spec=Session)

                with patch('src.common.database.get_db_session') as mock_get_db:
                    mock_get_db.return_value.__enter__.return_value = mock_db_session

                    odcs = manager.build_odcs_from_db(full_contract_db, mock_db_session)

                    # Should have semantic assignments in authoritative definitions
                    assert 'authoritativeDefinitions' in odcs

                    # Find the semantic assignment
                    semantic_defs = [
                        auth_def for auth_def in odcs['authoritativeDefinitions']
                        if auth_def['type'] == "http://databricks.com/ontology/uc/semanticAssignment"
                    ]
                    assert len(semantic_defs) >= 1
                    assert semantic_defs[0]['url'] == "http://example.com/contract-semantic"

    def test_create_from_odcs_dict_basic(self, manager):
        """Test creating contract from ODCS dictionary."""
        odcs_data = {
            'name': 'test-contract',
            'version': '1.0.0',
            'status': 'draft',
            'owner': 'test-user',
            'kind': 'DataContract',
            'apiVersion': 'v3.0.2',
            'description': {
                'usage': 'Test usage',
                'purpose': 'Test purpose',
                'limitations': 'Test limitations'
            }
        }

        mock_db = Mock(spec=Session)

        with patch('src.repositories.data_contracts_repository.data_contract_repo') as mock_repo:
            mock_created = Mock()
            mock_created.id = "new-contract-id"
            mock_repo.create.return_value = mock_created

            result = manager.create_from_odcs_dict(mock_db, odcs_data, "test-user")

            assert result.id == "new-contract-id"
            mock_repo.create.assert_called_once()

            # Check the created object
            created_obj = mock_repo.create.call_args[1]['obj_in']
            assert created_obj.name == 'test-contract'
            assert created_obj.version == '1.0.0'
            assert created_obj.description_usage == 'Test usage'
            assert created_obj.description_purpose == 'Test purpose'
            assert created_obj.description_limitations == 'Test limitations'

    def test_create_from_odcs_dict_with_tags_roles_servers(self, manager):
        """Test creating contract from ODCS with tags, roles, and servers."""
        odcs_data = {
            'name': 'test-contract',
            'version': '1.0.0',
            'tags': ['tag1', 'tag2'],
            'roles': [
                {
                    'role': 'reader',
                    'access': 'read',
                    'firstLevelApprovers': 'manager'
                }
            ],
            'servers': [
                {
                    'server': 'test-server',
                    'type': 'postgres',
                    'description': 'Test server'
                }
            ]
        }

        mock_db = Mock(spec=Session)

        with patch('src.repositories.data_contracts_repository.data_contract_repo') as mock_repo:
            mock_created = Mock()
            mock_created.id = "new-contract-id"
            mock_repo.create.return_value = mock_created

            manager.create_from_odcs_dict(mock_db, odcs_data, "test-user")

            # Verify tags were added
            tag_adds = [call for call in mock_db.add.call_args_list
                       if isinstance(call[0][0], DataContractTagDb)]
            assert len(tag_adds) == 2

            # Verify roles were added
            role_adds = [call for call in mock_db.add.call_args_list
                        if isinstance(call[0][0], DataContractRoleDb)]
            assert len(role_adds) == 1

            # Verify servers were added
            server_adds = [call for call in mock_db.add.call_args_list
                          if isinstance(call[0][0], DataContractServerDb)]
            assert len(server_adds) == 1

    def test_validate_odcs_format(self, manager):
        """Test ODCS format validation."""
        # Valid ODCS
        valid_odcs = {
            'name': 'test',
            'version': '1.0.0',
            'datasets': []
        }
        assert manager.validate_odcs_format(valid_odcs) == True

        # Invalid ODCS - missing required fields
        invalid_odcs = {
            'name': 'test'
        }
        assert manager.validate_odcs_format(invalid_odcs) == False

    def test_search_index_items(self, manager):
        """Test search index item generation."""
        # Mock contracts
        contract1 = Mock()
        contract1.id = "contract-1"
        contract1.name = "Test Contract 1"
        contract1.description = "Test description"
        contract1.tags = ["tag1", "tag2"]

        contract2 = Mock()
        contract2.id = "contract-2"
        contract2.name = "Test Contract 2"
        contract2.description = None

        with patch.object(manager, 'list_contracts', return_value=[contract1, contract2]):
            items = manager.get_search_index_items()

            assert len(items) == 2

            assert items[0].id == "contract::contract-1"
            assert items[0].type == "data-contract"
            assert items[0].feature_id == "data-contracts"
            assert items[0].title == "Test Contract 1"
            assert items[0].description == "Test description"
            assert items[0].link == "/data-contracts/contract-1"
            assert items[0].tags == ["tag1", "tag2"]

            assert items[1].id == "contract::contract-2"
            assert items[1].description == ""