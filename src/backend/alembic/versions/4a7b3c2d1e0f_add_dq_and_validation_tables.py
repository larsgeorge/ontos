"""Add DQ and validation tables

Revision ID: 4a7b3c2d1e0f
Revises: 3135632d55e1
Create Date: 2025-11-14 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4a7b3c2d1e0f'
down_revision: Union[str, None] = '3135632d55e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add data quality check and contract validation tables."""

    # Create data_quality_check_runs table
    op.create_table(
        'data_quality_check_runs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('contract_id', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('checks_passed', sa.Integer(), nullable=False),
        sa.Column('checks_failed', sa.Integer(), nullable=False),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['contract_id'], ['data_contracts.id']),
    )
    op.create_index(op.f('ix_data_quality_check_runs_contract_id'), 'data_quality_check_runs', ['contract_id'], unique=False)
    op.create_index(op.f('ix_data_quality_check_runs_status'), 'data_quality_check_runs', ['status'], unique=False)

    # Create data_quality_check_results table
    op.create_table(
        'data_quality_check_results',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('run_id', sa.String(), nullable=False),
        sa.Column('contract_id', sa.String(), nullable=False),
        sa.Column('object_name', sa.String(), nullable=False),
        sa.Column('check_type', sa.String(), nullable=False),
        sa.Column('column_name', sa.String(), nullable=True),
        sa.Column('passed', sa.Boolean(), nullable=False),
        sa.Column('violations_count', sa.Integer(), nullable=False),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['run_id'], ['data_quality_check_runs.id']),
    )
    op.create_index(op.f('ix_data_quality_check_results_run_id'), 'data_quality_check_results', ['run_id'], unique=False)
    op.create_index(op.f('ix_data_quality_check_results_contract_id'), 'data_quality_check_results', ['contract_id'], unique=False)

    # Create data_contract_validation_runs table
    op.create_table(
        'data_contract_validation_runs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('contract_id', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('checks_passed', sa.Integer(), nullable=False),
        sa.Column('checks_failed', sa.Integer(), nullable=False),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['contract_id'], ['data_contracts.id']),
    )
    op.create_index(op.f('ix_data_contract_validation_runs_contract_id'), 'data_contract_validation_runs', ['contract_id'], unique=False)
    op.create_index(op.f('ix_data_contract_validation_runs_status'), 'data_contract_validation_runs', ['status'], unique=False)

    # Create data_contract_validation_results table
    op.create_table(
        'data_contract_validation_results',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('run_id', sa.String(), nullable=False),
        sa.Column('contract_id', sa.String(), nullable=False),
        sa.Column('check_type', sa.String(), nullable=False),
        sa.Column('passed', sa.Boolean(), nullable=False),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('details_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['run_id'], ['data_contract_validation_runs.id']),
    )
    op.create_index(op.f('ix_data_contract_validation_results_run_id'), 'data_contract_validation_results', ['run_id'], unique=False)
    op.create_index(op.f('ix_data_contract_validation_results_contract_id'), 'data_contract_validation_results', ['contract_id'], unique=False)


def downgrade() -> None:
    """Remove data quality check and contract validation tables."""

    # Drop tables in reverse order (children first due to foreign keys)
    op.drop_index(op.f('ix_data_contract_validation_results_contract_id'), table_name='data_contract_validation_results')
    op.drop_index(op.f('ix_data_contract_validation_results_run_id'), table_name='data_contract_validation_results')
    op.drop_table('data_contract_validation_results')

    op.drop_index(op.f('ix_data_contract_validation_runs_status'), table_name='data_contract_validation_runs')
    op.drop_index(op.f('ix_data_contract_validation_runs_contract_id'), table_name='data_contract_validation_runs')
    op.drop_table('data_contract_validation_runs')

    op.drop_index(op.f('ix_data_quality_check_results_contract_id'), table_name='data_quality_check_results')
    op.drop_index(op.f('ix_data_quality_check_results_run_id'), table_name='data_quality_check_results')
    op.drop_table('data_quality_check_results')

    op.drop_index(op.f('ix_data_quality_check_runs_status'), table_name='data_quality_check_runs')
    op.drop_index(op.f('ix_data_quality_check_runs_contract_id'), table_name='data_quality_check_runs')
    op.drop_table('data_quality_check_runs')
