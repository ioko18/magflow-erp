"""Complete migration to fix the database schema

Revision ID: complete_migration_fix
Revises:
Create Date: 2025-09-23 11:45:00.000000

This migration creates all the necessary tables for the MagFlow ERP system
including users, roles, permissions, audit logs, and all ERP tables.

"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'complete_migration_fix'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all necessary tables for MagFlow ERP system."""

    # Create enum types
    mapping_status = sa.Enum('active', 'inactive', 'pending', 'deprecated', name='mappingstatus')
    mapping_type = sa.Enum('product_id', 'category_id', 'brand_id', 'characteristic_id', name='mappingtype')

    # Create enums for RMA system
    return_status = sa.Enum('pending', 'approved', 'rejected', 'processing', 'completed', 'cancelled', name='returnstatus')
    return_reason = sa.Enum('defective_product', 'wrong_item', 'damaged_in_transit', 'customer_dissatisfaction', 'late_delivery', 'other', name='returnreason')
    refund_method = sa.Enum('original_payment', 'store_credit', 'bank_transfer', 'cash', name='refundmethod')
    emag_return_status = sa.Enum('new', 'in_progress', 'approved', 'rejected', 'completed', 'cancelled', name='emagreturnstatus')

    # Create enums for Cancellation system
    cancellation_status = sa.Enum('pending', 'approved', 'rejected', 'processing', 'completed', 'cancelled', name='cancellationstatus')
    cancellation_reason = sa.Enum('customer_request', 'payment_failed', 'inventory_unavailable', 'shipping_delay', 'fraud_suspected', 'administrative', 'other', name='cancellationreason')
    refund_status = sa.Enum('pending', 'processing', 'completed', 'failed', 'partial', name='refundstatus')

    # Create enums for Invoice system
    invoice_status = sa.Enum('draft', 'issued', 'sent', 'paid', 'overdue', 'cancelled', 'refunded', name='invoicestatus')
    invoice_type = sa.Enum('sales_invoice', 'credit_note', 'proforma_invoice', 'corrected_invoice', name='invoicetype')
    payment_method = sa.Enum('cash', 'bank_transfer', 'card', 'online_payment', 'check', 'other', name='paymentmethod')
    tax_category = sa.Enum('standard', 'reduced', 'super_reduced', 'zero', 'exempt', name='taxcategory')

    # Create all enums
    for enum_type in [mapping_status, mapping_type, return_status, return_reason,
                      refund_method, emag_return_status, cancellation_status,
                      cancellation_reason, refund_status, invoice_status,
                      invoice_type, payment_method, tax_category]:
        enum_type.create(op.get_bind(), checkfirst=True)

    # Create roles table
    op.create_table(
        'roles',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('is_system_role', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.Index('idx_roles_name', 'name'),
        schema='app'
    )

    # Create permissions table
    op.create_table(
        'permissions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('resource', sa.String(length=100), nullable=False),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.Index('idx_permissions_name', 'name'),
        sa.Index('idx_permissions_resource', 'resource'),
        sa.Index('idx_permissions_action', 'action'),
        schema='app'
    )

    # Create user_sessions table
    op.create_table(
        'user_sessions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('session_token', sa.String(length=255), nullable=False),
        sa.Column('refresh_token', sa.String(length=255), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_activity', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['app.users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('session_token'),
        sa.UniqueConstraint('refresh_token'),
        sa.Index('idx_user_sessions_user_id', 'user_id'),
        sa.Index('idx_user_sessions_session_token', 'session_token'),
        sa.Index('idx_user_sessions_refresh_token', 'refresh_token'),
        sa.Index('idx_user_sessions_expires_at', 'expires_at'),
        schema='app'
    )

    # Create refresh_tokens table
    op.create_table(
        'refresh_tokens',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('token', sa.String(length=512), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_revoked', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('user_agent', sa.String(length=255), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['app.users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('token'),
        sa.Index('idx_refresh_tokens_user_id', 'user_id'),
        sa.Index('idx_refresh_tokens_token', 'token'),
        sa.Index('idx_refresh_tokens_expires_at', 'expires_at'),
        schema='app'
    )

    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('resource', sa.String(length=100), nullable=False),
        sa.Column('resource_id', sa.String(length=100), nullable=True),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('timestamp', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('success', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['app.users.id'], ondelete='SET NULL'),
        sa.Index('idx_audit_logs_user_id', 'user_id'),
        sa.Index('idx_audit_logs_action', 'action'),
        sa.Index('idx_audit_logs_resource', 'resource'),
        sa.Index('idx_audit_logs_timestamp', 'timestamp'),
        schema='app'
    )

    # Create categories table
    op.create_table(
        'categories',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('parent_id', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.ForeignKeyConstraint(['parent_id'], ['app.categories.id'], ondelete='CASCADE'),
        sa.Index('idx_categories_name', 'name'),
        sa.Index('idx_categories_parent_id', 'parent_id'),
        schema='app'
    )

    # Create products table
    op.create_table(
        'products',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('sku', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('cost', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('stock_quantity', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('min_stock_level', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('category_id', sa.Integer(), nullable=True),
        sa.Column('supplier_id', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('weight', sa.Numeric(precision=8, scale=3), nullable=True),
        sa.Column('dimensions', postgresql.JSON(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('barcode', sa.String(length=100), nullable=True),
        sa.Column('image_url', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('sku'),
        sa.ForeignKeyConstraint(['category_id'], ['app.categories.id'], ondelete='SET NULL'),
        sa.Index('idx_products_sku', 'sku'),
        sa.Index('idx_products_name', 'name'),
        sa.Index('idx_products_category_id', 'category_id'),
        sa.Index('idx_products_is_active', 'is_active'),
        schema='app'
    )

    # Create suppliers table
    op.create_table(
        'suppliers',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('contact_email', sa.String(length=255), nullable=True),
        sa.Column('contact_phone', sa.String(length=50), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.Index('idx_suppliers_name', 'name'),
        sa.Index('idx_suppliers_is_active', 'is_active'),
        schema='app'
    )

    # Create association tables
    op.create_table(
        'user_roles',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['app.users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['app.roles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'role_id'),
        schema='app'
    )

    op.create_table(
        'role_permissions',
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('permission_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['role_id'], ['app.roles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['permission_id'], ['app.permissions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('role_id', 'permission_id'),
        schema='app'
    )

    op.create_table(
        'product_categories',
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['product_id'], ['app.products.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['category_id'], ['app.categories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('product_id', 'category_id'),
        schema='app'
    )

    # Create indexes for association tables
    op.create_index('idx_user_roles_user_id', 'user_roles', ['user_id'], schema='app')
    op.create_index('idx_user_roles_role_id', 'user_roles', ['role_id'], schema='app')

    op.create_index('idx_role_permissions_role_id', 'role_permissions', ['role_id'], schema='app')
    op.create_index('idx_role_permissions_permission_id', 'role_permissions', ['permission_id'], schema='app')

    op.create_index('idx_product_categories_product_id', 'product_categories', ['product_id'], schema='app')
    op.create_index('idx_product_categories_category_id', 'product_categories', ['category_id'], schema='app')

    # Create default roles and permissions
    op.execute(sa.text("""
        INSERT INTO app.roles (name, description, is_system_role, created_at, updated_at)
        VALUES
            ('admin', 'System Administrator', true, now(), now()),
            ('user', 'Regular User', false, now(), now()),
            ('manager', 'Department Manager', false, now(), now())
        ON CONFLICT (name) DO NOTHING
    """))

    op.execute(sa.text("""
        INSERT INTO app.permissions (name, description, resource, action, created_at, updated_at)
        VALUES
            ('user_read', 'View user information', 'users', 'read', now(), now()),
            ('user_write', 'Create and edit users', 'users', 'write', now(), now()),
            ('user_delete', 'Delete users', 'users', 'delete', now(), now()),
            ('product_read', 'View products', 'products', 'read', now(), now()),
            ('product_write', 'Create and edit products', 'products', 'write', now(), now()),
            ('product_delete', 'Delete products', 'products', 'delete', now(), now()),
            ('admin_access', 'Full system access', 'system', 'admin', now(), now())
        ON CONFLICT (name) DO NOTHING
    """))

    # Assign permissions to admin role
    op.execute(sa.text("""
        INSERT INTO app.role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM app.roles r, app.permissions p
        WHERE r.name = 'admin'
        ON CONFLICT DO NOTHING
    """))

    print("✅ Complete migration applied successfully!")


def downgrade() -> None:
    """Drop all tables created in this migration."""

    # Drop tables in reverse order (respecting foreign keys)
    op.drop_table('product_categories', schema='app')
    op.drop_table('role_permissions', schema='app')
    op.drop_table('user_roles', schema='app')

    op.drop_table('user_sessions', schema='app')
    op.drop_table('refresh_tokens', schema='app')
    op.drop_table('audit_logs', schema='app')

    op.drop_table('suppliers', schema='app')
    op.drop_table('products', schema='app')
    op.drop_table('categories', schema='app')

    op.drop_table('permissions', schema='app')
    op.drop_table('roles', schema='app')

    # Drop enum types
    op.execute('DROP TYPE IF EXISTS mappingstatus CASCADE')
    op.execute('DROP TYPE IF EXISTS mappingtype CASCADE')
    op.execute('DROP TYPE IF EXISTS returnstatus CASCADE')
    op.execute('DROP TYPE IF EXISTS returnreason CASCADE')
    op.execute('DROP TYPE IF EXISTS refundmethod CASCADE')
    op.execute('DROP TYPE IF EXISTS emagreturnstatus CASCADE')
    op.execute('DROP TYPE IF EXISTS cancellationstatus CASCADE')
    op.execute('DROP TYPE IF EXISTS cancellationreason CASCADE')
    op.execute('DROP TYPE IF EXISTS refundstatus CASCADE')
    op.execute('DROP TYPE IF EXISTS invoicestatus CASCADE')
    op.execute('DROP TYPE IF EXISTS invoicetype CASCADE')
    op.execute('DROP TYPE IF EXISTS paymentmethod CASCADE')
    op.execute('DROP TYPE IF EXISTS taxcategory CASCADE')

    print("✅ Complete migration downgraded successfully!")
