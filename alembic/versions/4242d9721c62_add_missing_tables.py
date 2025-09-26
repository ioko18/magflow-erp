"""add missing tables

Revision ID: 4242d9721c62
Revises: f8a938c16fd8
Create Date: 2025-09-25 16:05:27.860298

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4242d9721c62'
down_revision: Union[str, Sequence[str], None] = 'f8a938c16fd8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('resource', sa.String(length=100), nullable=False),
        sa.Column('resource_id', sa.String(length=100), nullable=True),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['app.users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        schema='app'
    )
    op.create_index(op.f('ix_app_audit_logs_id'), 'audit_logs', ['id'], unique=False, schema='app')


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_app_audit_logs_id'), table_name='audit_logs', schema='app')
    op.drop_table('audit_logs', schema='app')
