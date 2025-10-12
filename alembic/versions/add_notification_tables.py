"""add notification tables

Revision ID: add_notification_tables_v2
Revises: 3a4be43d04f7
Create Date: 2025-01-04 16:30:00.000000

"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = 'add_notification_tables_v2'
down_revision = '3a4be43d04f7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create notifications table
    op.create_table(
        'notifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('type', sa.Enum('success', 'info', 'warning', 'error', name='notificationtype'), nullable=False),
        sa.Column('category', sa.Enum('system', 'emag', 'orders', 'users', 'inventory', 'sync', 'payment', 'shipping', name='notificationcategory'), nullable=False),
        sa.Column('priority', sa.Enum('low', 'medium', 'high', 'critical', name='notificationpriority'), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('action_url', sa.String(length=500), nullable=True),
        sa.Column('action_label', sa.String(length=100), nullable=True),
        sa.Column('read', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('read_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['app.users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        schema='app'
    )

    # Create indexes for notifications
    op.create_index('ix_notifications_id', 'notifications', ['id'], schema='app')
    op.create_index('ix_notifications_user_id', 'notifications', ['user_id'], schema='app')
    op.create_index('ix_notifications_read', 'notifications', ['read'], schema='app')
    op.create_index('ix_notifications_created_at', 'notifications', ['created_at'], schema='app')
    op.create_index('idx_user_read_created', 'notifications', ['user_id', 'read', 'created_at'], schema='app')
    op.create_index('idx_user_category', 'notifications', ['user_id', 'category'], schema='app')
    op.create_index('idx_user_priority', 'notifications', ['user_id', 'priority'], schema='app')

    # Create notification_settings table
    op.create_table(
        'notification_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('email_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('push_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('sms_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('category_preferences', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('min_priority', sa.Enum('low', 'medium', 'high', 'critical', name='notificationpriority'), nullable=False, server_default='low'),
        sa.Column('quiet_hours_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('quiet_hours_start', sa.String(length=5), nullable=True),
        sa.Column('quiet_hours_end', sa.String(length=5), nullable=True),
        sa.Column('auto_delete_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('auto_delete_days', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('digest_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('digest_frequency', sa.String(length=20), nullable=False, server_default='daily'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['app.users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
        schema='app'
    )

    # Create indexes for notification_settings
    op.create_index('ix_notification_settings_id', 'notification_settings', ['id'], schema='app')
    op.create_index('ix_notification_settings_user_id', 'notification_settings', ['user_id'], unique=True, schema='app')


def downgrade() -> None:
    # Drop notification_settings table
    op.drop_index('ix_notification_settings_user_id', table_name='notification_settings', schema='app')
    op.drop_index('ix_notification_settings_id', table_name='notification_settings', schema='app')
    op.drop_table('notification_settings', schema='app')

    # Drop notifications table
    op.drop_index('idx_user_priority', table_name='notifications', schema='app')
    op.drop_index('idx_user_category', table_name='notifications', schema='app')
    op.drop_index('idx_user_read_created', table_name='notifications', schema='app')
    op.drop_index('ix_notifications_created_at', table_name='notifications', schema='app')
    op.drop_index('ix_notifications_read', table_name='notifications', schema='app')
    op.drop_index('ix_notifications_user_id', table_name='notifications', schema='app')
    op.drop_index('ix_notifications_id', table_name='notifications', schema='app')
    op.drop_table('notifications', schema='app')

    # Drop enums
    op.execute('DROP TYPE IF EXISTS notificationtype')
    op.execute('DROP TYPE IF EXISTS notificationcategory')
    op.execute('DROP TYPE IF EXISTS notificationpriority')
