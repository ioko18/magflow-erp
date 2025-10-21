#!/usr/bin/env python3
"""
Manual migration script to create missing tables for MagFlow ERP
"""

import os

import psycopg2
from dotenv import load_dotenv

load_dotenv()

def create_missing_tables():
    """Create all missing tables manually."""

    try:
        conn = psycopg2.connect(
            host='localhost',
            port='5432',
            database='magflow',
            user='app',
            password=os.getenv('DB_PASS', 'password')
        )

        cursor = conn.cursor()

        print("🔧 Creating missing tables...")

        # Create enum types
        enum_queries = [
            (
                "CREATE TYPE IF NOT EXISTS mappingstatus AS ENUM "
                "('active', 'inactive', 'pending', 'deprecated')"
            ),
            (
                "CREATE TYPE IF NOT EXISTS mappingtype AS ENUM "
                "('product_id', 'category_id', 'brand_id', 'characteristic_id')"
            ),
            (
                "CREATE TYPE IF NOT EXISTS returnstatus AS ENUM "
                "('pending', 'approved', 'rejected', 'processing', 'completed', 'cancelled')"
            ),
            (
                "CREATE TYPE IF NOT EXISTS returnreason AS ENUM "
                "('defective_product', 'wrong_item', 'damaged_in_transit', "
                "'customer_dissatisfaction', 'late_delivery', 'other')"
            ),
            (
                "CREATE TYPE IF NOT EXISTS refundmethod AS ENUM "
                "('original_payment', 'store_credit', 'bank_transfer', 'cash')"
            ),
            (
                "CREATE TYPE IF NOT EXISTS emagreturnstatus AS ENUM "
                "('new', 'in_progress', 'approved', 'rejected', 'completed', 'cancelled')"
            ),
            (
                "CREATE TYPE IF NOT EXISTS cancellationstatus AS ENUM "
                "('pending', 'approved', 'rejected', 'processing', 'completed', 'cancelled')"
            ),
            (
                "CREATE TYPE IF NOT EXISTS cancellationreason AS ENUM "
                "('customer_request', 'payment_failed', 'inventory_unavailable', "
                "'shipping_delay', 'fraud_suspected', 'administrative', 'other')"
            ),
            (
                "CREATE TYPE IF NOT EXISTS refundstatus AS ENUM "
                "('pending', 'processing', 'completed', 'failed', 'partial')"
            ),
            (
                "CREATE TYPE IF NOT EXISTS invoicestatus AS ENUM "
                "('draft', 'issued', 'sent', 'paid', 'overdue', 'cancelled', 'refunded')"
            ),
            (
                "CREATE TYPE IF NOT EXISTS invoicetype AS ENUM "
                "('sales_invoice', 'credit_note', 'proforma_invoice', 'corrected_invoice')"
            ),
            (
                "CREATE TYPE IF NOT EXISTS paymentmethod AS ENUM "
                "('cash', 'bank_transfer', 'card', 'online_payment', 'check', 'other')"
            ),
            (
                "CREATE TYPE IF NOT EXISTS taxcategory AS ENUM "
                "('standard', 'reduced', 'super_reduced', 'zero', 'exempt')"
            )
        ]

        for query in enum_queries:
            cursor.execute(query)
            print(f"  ✅ Created enum: {query.split()[-1]}")

        # Create roles table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS app.roles (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL UNIQUE,
                description VARCHAR(255),
                is_system_role BOOLEAN NOT NULL DEFAULT false,
                created_at TIMESTAMP NOT NULL DEFAULT now(),
                updated_at TIMESTAMP NOT NULL DEFAULT now()
            )
        ''')
        print("  ✅ Created roles table")

        # Create permissions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS app.permissions (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL UNIQUE,
                description VARCHAR(255),
                resource VARCHAR(100) NOT NULL,
                action VARCHAR(50) NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT now(),
                updated_at TIMESTAMP NOT NULL DEFAULT now()
            )
        ''')
        print("  ✅ Created permissions table")

        # Create refresh_tokens table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS app.refresh_tokens (
                id SERIAL PRIMARY KEY,
                token VARCHAR(512) NOT NULL UNIQUE,
                expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
                is_revoked BOOLEAN NOT NULL DEFAULT false,
                user_agent VARCHAR(255),
                ip_address VARCHAR(45),
                user_id INTEGER NOT NULL REFERENCES app.users(id) ON DELETE CASCADE,
                created_at TIMESTAMP NOT NULL DEFAULT now(),
                updated_at TIMESTAMP NOT NULL DEFAULT now()
            )
        ''')
        print("  ✅ Created refresh_tokens table")

        # Create audit_logs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS app.audit_logs (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES app.users(id) ON DELETE SET NULL,
                action VARCHAR(100) NOT NULL,
                resource VARCHAR(100) NOT NULL,
                resource_id VARCHAR(100),
                details TEXT,
                ip_address VARCHAR(45),
                user_agent VARCHAR(500),
                timestamp TIMESTAMP NOT NULL DEFAULT now(),
                success BOOLEAN NOT NULL DEFAULT true,
                error_message TEXT
            )
        ''')
        print("  ✅ Created audit_logs table")

        # Create user_sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS app.user_sessions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES app.users(id) ON DELETE CASCADE,
                session_token VARCHAR(255) NOT NULL UNIQUE,
                refresh_token VARCHAR(255) UNIQUE,
                ip_address VARCHAR(45),
                user_agent VARCHAR(500),
                created_at TIMESTAMP NOT NULL DEFAULT now(),
                expires_at TIMESTAMP NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT true,
                last_activity TIMESTAMP NOT NULL DEFAULT now()
            )
        ''')
        print("  ✅ Created user_sessions table")

        # Create categories table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS app.categories (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL UNIQUE,
                description TEXT,
                parent_id INTEGER REFERENCES app.categories(id) ON DELETE CASCADE,
                is_active BOOLEAN NOT NULL DEFAULT true,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
            )
        ''')
        print("  ✅ Created categories table")

        # Create products table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS app.products (
                id SERIAL PRIMARY KEY,
                sku VARCHAR(100) NOT NULL UNIQUE,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                price DECIMAL(10,2) NOT NULL,
                cost DECIMAL(10,2),
                stock_quantity INTEGER NOT NULL DEFAULT 0,
                min_stock_level INTEGER NOT NULL DEFAULT 0,
                category_id INTEGER REFERENCES app.categories(id) ON DELETE SET NULL,
                supplier_id INTEGER,
                is_active BOOLEAN NOT NULL DEFAULT true,
                weight DECIMAL(8,3),
                dimensions JSON DEFAULT '{}',
                barcode VARCHAR(100),
                image_url VARCHAR(500),
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
            )
        ''')
        print("  ✅ Created products table")

        # Create suppliers table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS app.suppliers (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL UNIQUE,
                contact_email VARCHAR(255),
                contact_phone VARCHAR(50),
                address TEXT,
                is_active BOOLEAN NOT NULL DEFAULT true,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
            )
        ''')
        print("  ✅ Created suppliers table")

        # Create association tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS app.user_roles (
                user_id INTEGER NOT NULL REFERENCES app.users(id) ON DELETE CASCADE,
                role_id INTEGER NOT NULL REFERENCES app.roles(id) ON DELETE CASCADE,
                created_at TIMESTAMP NOT NULL DEFAULT now(),
                PRIMARY KEY (user_id, role_id)
            )
        ''')
        print("  ✅ Created user_roles table")

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS app.role_permissions (
                role_id INTEGER NOT NULL REFERENCES app.roles(id) ON DELETE CASCADE,
                permission_id INTEGER NOT NULL REFERENCES app.permissions(id) ON DELETE CASCADE,
                PRIMARY KEY (role_id, permission_id)
            )
        ''')
        print("  ✅ Created role_permissions table")

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS app.product_categories (
                product_id INTEGER NOT NULL REFERENCES app.products(id) ON DELETE CASCADE,
                category_id INTEGER NOT NULL REFERENCES app.categories(id) ON DELETE CASCADE,
                PRIMARY KEY (product_id, category_id)
            )
        ''')
        print("  ✅ Created product_categories table")

        # Create indexes
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_roles_name ON app.roles(name)",
            "CREATE INDEX IF NOT EXISTS idx_permissions_name ON app.permissions(name)",
            "CREATE INDEX IF NOT EXISTS idx_permissions_resource ON app.permissions(resource)",
            "CREATE INDEX IF NOT EXISTS idx_permissions_action ON app.permissions(action)",
            "CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user_id ON app.refresh_tokens(user_id)",
            (
                "CREATE INDEX IF NOT EXISTS idx_refresh_tokens_expires_at ON "
                "app.refresh_tokens(expires_at)"
            ),
            "CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON app.audit_logs(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON app.audit_logs(action)",
            "CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON app.audit_logs(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON app.user_sessions(user_id)",
            (
                "CREATE INDEX IF NOT EXISTS idx_user_sessions_expires_at ON "
                "app.user_sessions(expires_at)"
            ),
            (
                "CREATE INDEX IF NOT EXISTS idx_categories_parent_id ON "
                "app.categories(parent_id)"
            ),
            "CREATE INDEX IF NOT EXISTS idx_products_sku ON app.products(sku)",
            "CREATE INDEX IF NOT EXISTS idx_products_category_id ON app.products(category_id)",
            "CREATE INDEX IF NOT EXISTS idx_products_is_active ON app.products(is_active)",
            "CREATE INDEX IF NOT EXISTS idx_suppliers_is_active ON app.suppliers(is_active)"
        ]

        for index_sql in indexes:
            cursor.execute(index_sql)
            print(f"  ✅ Created index: {index_sql.split()[-1]}")

        # Insert default roles and permissions
        cursor.execute('''
            INSERT INTO app.roles (name, description, is_system_role, created_at, updated_at)
            VALUES
                ('admin', 'System Administrator', true, now(), now()),
                ('user', 'Regular User', false, now(), now()),
                ('manager', 'Department Manager', false, now(), now())
            ON CONFLICT (name) DO NOTHING
        ''')
        print("  ✅ Inserted default roles")

        cursor.execute('''
            INSERT INTO app.permissions (
                name,
                description,
                resource,
                action,
                created_at,
                updated_at
            )
            VALUES
                ('user_read', 'View user information', 'users', 'read', now(), now()),
                ('user_write', 'Create and edit users', 'users', 'write', now(), now()),
                ('user_delete', 'Delete users', 'users', 'delete', now(), now()),
                ('product_read', 'View products', 'products', 'read', now(), now()),
                ('product_write', 'Create and edit products', 'products', 'write', now(), now()),
                ('product_delete', 'Delete products', 'products', 'delete', now(), now()),
                ('admin_access', 'Full system access', 'system', 'admin', now(), now())
            ON CONFLICT (name) DO NOTHING
        ''')
        print("  ✅ Inserted default permissions")

        # Assign permissions to admin role
        cursor.execute('''
            INSERT INTO app.role_permissions (role_id, permission_id)
            SELECT r.id, p.id
            FROM app.roles r, app.permissions p
            WHERE r.name = 'admin'
            ON CONFLICT DO NOTHING
        ''')
        print("  ✅ Assigned permissions to admin role")

        conn.commit()
        cursor.close()
        conn.close()

        print("\n🎉 All missing tables created successfully!")

        return True

    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False

if __name__ == "__main__":
    success = create_missing_tables()
    if success:
        print("✅ Migration completed successfully!")
    else:
        print("❌ Migration failed!")
        exit(1)
