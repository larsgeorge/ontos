"""rename_data_product_tables_with_prefix

Revision ID: 3f322c53b3c7
Revises: 4a7b3c2d1e0f
Create Date: 2025-11-19 17:34:46.189694

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3f322c53b3c7'
down_revision: Union[str, None] = '4a7b3c2d1e0f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rename data product tables to use consistent data_product_ prefix."""

    # Rename child tables first (those with foreign keys to other renamed tables)
    # Team members (child of product_teams)
    op.rename_table('product_team_members', 'data_product_team_members')

    # Output port children (children of output_ports)
    op.rename_table('output_port_sbom', 'data_product_output_port_sbom')
    op.rename_table('output_port_input_contracts', 'data_product_output_port_input_contracts')

    # Direct children of data_products (parent table remains unchanged)
    op.rename_table('product_descriptions', 'data_product_descriptions')
    op.rename_table('product_authoritative_definitions', 'data_product_authoritative_definitions')
    op.rename_table('product_custom_properties', 'data_product_custom_properties')
    op.rename_table('input_ports', 'data_product_input_ports')
    op.rename_table('output_ports', 'data_product_output_ports')
    op.rename_table('management_ports', 'data_product_management_ports')
    op.rename_table('product_support_channels', 'data_product_support_channels')
    op.rename_table('product_teams', 'data_product_teams')


def downgrade() -> None:
    """Revert table names to original naming scheme."""

    # Reverse order - parent tables first, then children
    # Direct children of data_products
    op.rename_table('data_product_teams', 'product_teams')
    op.rename_table('data_product_support_channels', 'product_support_channels')
    op.rename_table('data_product_management_ports', 'management_ports')
    op.rename_table('data_product_output_ports', 'output_ports')
    op.rename_table('data_product_input_ports', 'input_ports')
    op.rename_table('data_product_custom_properties', 'product_custom_properties')
    op.rename_table('data_product_authoritative_definitions', 'product_authoritative_definitions')
    op.rename_table('data_product_descriptions', 'product_descriptions')

    # Output port children (must be renamed after output_ports is reverted)
    op.rename_table('data_product_output_port_input_contracts', 'output_port_input_contracts')
    op.rename_table('data_product_output_port_sbom', 'output_port_sbom')

    # Team members (must be renamed after product_teams is reverted)
    op.rename_table('data_product_team_members', 'product_team_members')
