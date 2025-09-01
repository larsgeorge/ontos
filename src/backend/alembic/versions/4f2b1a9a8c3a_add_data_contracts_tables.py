"""Add data contracts tables

Revision ID: 4f2b1a9a8c3a
Revises: d347bdebec4d
Create Date: 2025-08-26 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4f2b1a9a8c3a'
down_revision: Union[str, None] = 'd347bdebec4d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'data_contracts',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('kind', sa.String(), nullable=False),
        sa.Column('api_version', sa.String(), nullable=False),
        sa.Column('version', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('owner', sa.String(), nullable=False),
        sa.Column('tenant', sa.String(), nullable=True),
        sa.Column('data_product', sa.String(), nullable=True),
        sa.Column('domain_id', sa.String(), nullable=True),
        sa.Column('description_usage', sa.Text(), nullable=True),
        sa.Column('description_purpose', sa.Text(), nullable=True),
        sa.Column('description_limitations', sa.Text(), nullable=True),
        sa.Column('raw_format', sa.String(), nullable=True),
        sa.Column('raw_text', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('created_by', sa.String(), nullable=True),
        sa.Column('updated_by', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_data_contracts_name'), 'data_contracts', ['name'], unique=False)
    op.create_index(op.f('ix_data_contracts_version'), 'data_contracts', ['version'], unique=False)
    op.create_index(op.f('ix_data_contracts_status'), 'data_contracts', ['status'], unique=False)
    op.create_index(op.f('ix_data_contracts_owner'), 'data_contracts', ['owner'], unique=False)
    op.create_index(op.f('ix_data_contracts_domain_id'), 'data_contracts', ['domain_id'], unique=False)

    op.create_table(
        'data_contract_tags',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('contract_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['contract_id'], ['data_contracts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('contract_id', 'name', name='uq_contract_tag')
    )
    op.create_index(op.f('ix_data_contract_tags_contract_id'), 'data_contract_tags', ['contract_id'], unique=False)

    op.create_table(
        'data_contract_servers',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('contract_id', sa.String(), nullable=False),
        sa.Column('server', sa.String(), nullable=True),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('environment', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['contract_id'], ['data_contracts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_data_contract_servers_contract_id'), 'data_contract_servers', ['contract_id'], unique=False)

    op.create_table(
        'data_contract_server_properties',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('server_id', sa.String(), nullable=False),
        sa.Column('key', sa.String(), nullable=False),
        sa.Column('value', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['server_id'], ['data_contract_servers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_data_contract_server_properties_server_id'), 'data_contract_server_properties', ['server_id'], unique=False)

    op.create_table(
        'data_contract_roles',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('contract_id', sa.String(), nullable=False),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('access', sa.String(), nullable=True),
        sa.Column('first_level_approvers', sa.String(), nullable=True),
        sa.Column('second_level_approvers', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['contract_id'], ['data_contracts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_data_contract_roles_contract_id'), 'data_contract_roles', ['contract_id'], unique=False)

    op.create_table(
        'data_contract_role_properties',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('role_id', sa.String(), nullable=False),
        sa.Column('property', sa.String(), nullable=False),
        sa.Column('value', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['role_id'], ['data_contract_roles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_data_contract_role_properties_role_id'), 'data_contract_role_properties', ['role_id'], unique=False)

    op.create_table(
        'data_contract_team',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('contract_id', sa.String(), nullable=False),
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('role', sa.String(), nullable=True),
        sa.Column('date_in', sa.String(), nullable=True),
        sa.Column('date_out', sa.String(), nullable=True),
        sa.Column('replaced_by_username', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['contract_id'], ['data_contracts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_data_contract_team_contract_id'), 'data_contract_team', ['contract_id'], unique=False)

    op.create_table(
        'data_contract_support',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('contract_id', sa.String(), nullable=False),
        sa.Column('channel', sa.String(), nullable=False),
        sa.Column('url', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('tool', sa.String(), nullable=True),
        sa.Column('scope', sa.String(), nullable=True),
        sa.Column('invitation_url', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['contract_id'], ['data_contracts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_data_contract_support_contract_id'), 'data_contract_support', ['contract_id'], unique=False)

    op.create_table(
        'data_contract_pricing',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('contract_id', sa.String(), nullable=False),
        sa.Column('price_amount', sa.String(), nullable=True),
        sa.Column('price_currency', sa.String(), nullable=True),
        sa.Column('price_unit', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['contract_id'], ['data_contracts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_data_contract_pricing_contract_id'), 'data_contract_pricing', ['contract_id'], unique=False)

    op.create_table(
        'data_contract_authorities',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('contract_id', sa.String(), nullable=False),
        sa.Column('url', sa.String(), nullable=False),
        sa.Column('type', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['contract_id'], ['data_contracts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_data_contract_authorities_contract_id'), 'data_contract_authorities', ['contract_id'], unique=False)

    op.create_table(
        'data_contract_custom_properties',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('contract_id', sa.String(), nullable=False),
        sa.Column('property', sa.String(), nullable=False),
        sa.Column('value', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['contract_id'], ['data_contracts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_data_contract_custom_properties_contract_id'), 'data_contract_custom_properties', ['contract_id'], unique=False)

    op.create_table(
        'data_contract_sla_properties',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('contract_id', sa.String(), nullable=False),
        sa.Column('property', sa.String(), nullable=False),
        sa.Column('value', sa.String(), nullable=True),
        sa.Column('value_ext', sa.String(), nullable=True),
        sa.Column('unit', sa.String(), nullable=True),
        sa.Column('element', sa.String(), nullable=True),
        sa.Column('driver', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['contract_id'], ['data_contracts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_data_contract_sla_properties_contract_id'), 'data_contract_sla_properties', ['contract_id'], unique=False)

    op.create_table(
        'data_contract_schema_objects',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('contract_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('logical_type', sa.String(), nullable=False),
        sa.Column('physical_name', sa.String(), nullable=True),
        sa.Column('data_granularity_description', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['contract_id'], ['data_contracts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_data_contract_schema_objects_contract_id'), 'data_contract_schema_objects', ['contract_id'], unique=False)

    op.create_table(
        'data_contract_schema_properties',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('object_id', sa.String(), nullable=False),
        sa.Column('parent_property_id', sa.String(), nullable=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('logical_type', sa.String(), nullable=True),
        sa.Column('physical_type', sa.String(), nullable=True),
        sa.Column('required', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('unique', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('partitioned', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('classification', sa.String(), nullable=True),
        sa.Column('encrypted_name', sa.String(), nullable=True),
        sa.Column('transform_source_objects', sa.Text(), nullable=True),
        sa.Column('transform_logic', sa.Text(), nullable=True),
        sa.Column('transform_description', sa.Text(), nullable=True),
        sa.Column('examples', sa.Text(), nullable=True),
        sa.Column('critical_data_element', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('logical_type_options_json', sa.Text(), nullable=True),
        sa.Column('items_logical_type', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['object_id'], ['data_contract_schema_objects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_property_id'], ['data_contract_schema_properties.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_data_contract_schema_properties_object_id'), 'data_contract_schema_properties', ['object_id'], unique=False)
    op.create_index(op.f('ix_data_contract_schema_properties_parent_property_id'), 'data_contract_schema_properties', ['parent_property_id'], unique=False)

    op.create_table(
        'data_contract_quality_checks',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('object_id', sa.String(), nullable=False),
        sa.Column('level', sa.String(), nullable=True),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('dimension', sa.String(), nullable=True),
        sa.Column('method', sa.String(), nullable=True),
        sa.Column('schedule', sa.String(), nullable=True),
        sa.Column('scheduler', sa.String(), nullable=True),
        sa.Column('severity', sa.String(), nullable=True),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('unit', sa.String(), nullable=True),
        sa.Column('tags', sa.Text(), nullable=True),
        sa.Column('rule', sa.String(), nullable=True),
        sa.Column('query', sa.Text(), nullable=True),
        sa.Column('engine', sa.String(), nullable=True),
        sa.Column('implementation', sa.Text(), nullable=True),
        sa.Column('must_be', sa.String(), nullable=True),
        sa.Column('must_not_be', sa.String(), nullable=True),
        sa.Column('must_be_gt', sa.String(), nullable=True),
        sa.Column('must_be_ge', sa.String(), nullable=True),
        sa.Column('must_be_lt', sa.String(), nullable=True),
        sa.Column('must_be_le', sa.String(), nullable=True),
        sa.Column('must_be_between_min', sa.String(), nullable=True),
        sa.Column('must_be_between_max', sa.String(), nullable=True),
        sa.Column('must_not_between_min', sa.String(), nullable=True),
        sa.Column('must_not_between_max', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['object_id'], ['data_contract_schema_objects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_data_contract_quality_checks_object_id'), 'data_contract_quality_checks', ['object_id'], unique=False)

    op.create_table(
        'data_contract_comments',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('contract_id', sa.String(), nullable=False),
        sa.Column('author', sa.String(), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['contract_id'], ['data_contracts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_data_contract_comments_contract_id'), 'data_contract_comments', ['contract_id'], unique=False)

    op.create_table(
        'entity_change_log',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('entity_type', sa.String(), nullable=False),
        sa.Column('entity_id', sa.String(), nullable=False),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('username', sa.String(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('details_json', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_entity_change_log_entity_type'), 'entity_change_log', ['entity_type'], unique=False)
    op.create_index(op.f('ix_entity_change_log_entity_id'), 'entity_change_log', ['entity_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_entity_change_log_entity_id'), table_name='entity_change_log')
    op.drop_index(op.f('ix_entity_change_log_entity_type'), table_name='entity_change_log')
    op.drop_table('entity_change_log')

    op.drop_index(op.f('ix_data_contract_comments_contract_id'), table_name='data_contract_comments')
    op.drop_table('data_contract_comments')

    op.drop_index(op.f('ix_data_contract_quality_checks_object_id'), table_name='data_contract_quality_checks')
    op.drop_table('data_contract_quality_checks')

    op.drop_index(op.f('ix_data_contract_schema_properties_parent_property_id'), table_name='data_contract_schema_properties')
    op.drop_index(op.f('ix_data_contract_schema_properties_object_id'), table_name='data_contract_schema_properties')
    op.drop_table('data_contract_schema_properties')

    op.drop_index(op.f('ix_data_contract_schema_objects_contract_id'), table_name='data_contract_schema_objects')
    op.drop_table('data_contract_schema_objects')

    op.drop_index(op.f('ix_data_contract_sla_properties_contract_id'), table_name='data_contract_sla_properties')
    op.drop_table('data_contract_sla_properties')

    op.drop_index(op.f('ix_data_contract_custom_properties_contract_id'), table_name='data_contract_custom_properties')
    op.drop_table('data_contract_custom_properties')

    op.drop_index(op.f('ix_data_contract_authorities_contract_id'), table_name='data_contract_authorities')
    op.drop_table('data_contract_authorities')

    op.drop_index(op.f('ix_data_contract_pricing_contract_id'), table_name='data_contract_pricing')
    op.drop_table('data_contract_pricing')

    op.drop_index(op.f('ix_data_contract_support_contract_id'), table_name='data_contract_support')
    op.drop_table('data_contract_support')

    op.drop_index(op.f('ix_data_contract_team_contract_id'), table_name='data_contract_team')
    op.drop_table('data_contract_team')

    op.drop_index(op.f('ix_data_contract_role_properties_role_id'), table_name='data_contract_role_properties')
    op.drop_table('data_contract_role_properties')

    op.drop_index(op.f('ix_data_contract_roles_contract_id'), table_name='data_contract_roles')
    op.drop_table('data_contract_roles')

    op.drop_index(op.f('ix_data_contract_server_properties_server_id'), table_name='data_contract_server_properties')
    op.drop_table('data_contract_server_properties')

    op.drop_index(op.f('ix_data_contract_servers_contract_id'), table_name='data_contract_servers')
    op.drop_table('data_contract_servers')

    op.drop_index(op.f('ix_data_contract_tags_contract_id'), table_name='data_contract_tags')
    op.drop_table('data_contract_tags')

    op.drop_index(op.f('ix_data_contracts_domain_id'), table_name='data_contracts')
    op.drop_index(op.f('ix_data_contracts_owner'), table_name='data_contracts')
    op.drop_index(op.f('ix_data_contracts_status'), table_name='data_contracts')
    op.drop_index(op.f('ix_data_contracts_version'), table_name='data_contracts')
    op.drop_index(op.f('ix_data_contracts_name'), table_name='data_contracts')
    op.drop_table('data_contracts')


