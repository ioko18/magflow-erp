# MagFlow ERP - Database Schema Documentation

[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-blue.svg)](https://www.postgresql.org/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0+-green.svg)](https://www.sqlalchemy.org/)

Comprehensive database schema documentation for MagFlow ERP system.

## 📋 Table of Contents

- [Database Overview](#database-overview)
- [Schema Design](#schema-design)
- [Core Tables](#core-tables)
- [Relationships](#relationships)
- [Indexes & Constraints](#indexes--constraints)
- [Database Migrations](#database-migrations)
- [Data Types](#data-types)
- [Audit & Logging](#audit--logging)
- [Performance Considerations](#performance-considerations)

## 🗄️ Database Overview

### Database Configuration
```python
# app/core/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql+asyncpg://user:password@localhost/magflow"

engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False
)

async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)
```

### Database Specifications
- **Database**: PostgreSQL 15+
- **ORM**: SQLAlchemy 2.0+
- **Async Support**: asyncpg driver
- **Connection Pooling**: Configurable pool size
- **Migrations**: Alembic for schema versioning
- **Encoding**: UTF-8
- **Timezone**: UTC

## 🏗️ Schema Design

### Design Principles

#### 1. Normalized Structure
- **1NF**: Atomic values in each column
- **2NF**: No partial dependencies
- **3NF**: No transitive dependencies
- **BCNF**: Every determinant is a candidate key

#### 2. Audit Trail
- All tables have `created_at` and `updated_at` columns
- Soft deletes using `is_active` flag
- User tracking with `created_by` and `updated_by`

#### 3. Extensibility
- Generic foreign key relationships
- Flexible attribute storage
- Plugin architecture support

### Naming Conventions

#### Tables
```sql
-- Core business tables (singular)
users, customers, orders, products

-- Junction tables (plural)
user_roles, order_items, product_categories

-- System tables (prefixed)
sys_settings, sys_logs, sys_jobs
```

#### Columns
```sql
-- Primary keys
id (SERIAL PRIMARY KEY)

-- Foreign keys
user_id, customer_id, order_id (INTEGER REFERENCES)

-- Timestamps
created_at, updated_at (TIMESTAMP WITH TIME ZONE)

-- Status fields
status, is_active, is_deleted (VARCHAR/BOOLEAN)

-- Monetary values
price, amount, total (DECIMAL(10,2))

-- Text fields
name, description, notes (VARCHAR/TEXT)
```

## 📊 Core Tables

### Users & Authentication

#### users table
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    phone VARCHAR(20),
    is_active BOOLEAN DEFAULT true,
    is_superuser BOOLEAN DEFAULT false,
    last_login_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_is_active ON users(is_active);
```

#### user_roles table
```sql
CREATE TABLE user_roles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    role_id INTEGER REFERENCES roles(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, role_id)
);
```

#### roles table
```sql
CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert default roles
INSERT INTO roles (name, description) VALUES
('admin', 'System administrator with full access'),
('manager', 'Manager with elevated permissions'),
('user', 'Regular user with standard permissions');
```

#### permissions table
```sql
CREATE TABLE permissions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    module VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert default permissions
INSERT INTO permissions (name, description, module) VALUES
('user.create', 'Create users', 'user_management'),
('user.read', 'View users', 'user_management'),
('user.update', 'Update users', 'user_management'),
('user.delete', 'Delete users', 'user_management'),
('inventory.manage', 'Manage inventory', 'inventory');
```

### Inventory Management

#### categories table
```sql
CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    parent_id INTEGER REFERENCES categories(id),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_categories_name ON categories(name);
CREATE INDEX idx_categories_parent_id ON categories(parent_id);
```

#### inventory_items table
```sql
CREATE TABLE inventory_items (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    sku VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    category_id INTEGER REFERENCES categories(id),
    unit_cost DECIMAL(10,2) NOT NULL,
    stock_quantity INTEGER DEFAULT 0,
    min_stock_level INTEGER DEFAULT 0,
    max_stock_level INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_inventory_items_sku ON inventory_items(sku);
CREATE INDEX idx_inventory_items_category_id ON inventory_items(category_id);
CREATE INDEX idx_inventory_items_is_active ON inventory_items(is_active);
```

#### warehouses table
```sql
CREATE TABLE warehouses (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    location VARCHAR(255),
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_warehouses_name ON warehouses(name);
```

#### stock_movements table
```sql
CREATE TABLE stock_movements (
    id SERIAL PRIMARY KEY,
    item_id INTEGER REFERENCES inventory_items(id) ON DELETE CASCADE,
    warehouse_id INTEGER REFERENCES warehouses(id) ON DELETE CASCADE,
    quantity INTEGER NOT NULL,
    movement_type VARCHAR(20) NOT NULL CHECK (movement_type IN ('IN', 'OUT', 'TRANSFER')),
    reason VARCHAR(255),
    reference_id INTEGER, -- References sales_order, purchase_order, etc.
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_stock_movements_item_id ON stock_movements(item_id);
CREATE INDEX idx_stock_movements_warehouse_id ON stock_movements(warehouse_id);
CREATE INDEX idx_stock_movements_created_at ON stock_movements(created_at);
```

### Sales Management

#### customers table
```sql
CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(20),
    address TEXT,
    tax_id VARCHAR(50),
    payment_terms VARCHAR(100),
    credit_limit DECIMAL(10,2),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_customers_email ON customers(email);
CREATE INDEX idx_customers_is_active ON customers(is_active);
```

#### sales_orders table
```sql
CREATE TABLE sales_orders (
    id SERIAL PRIMARY KEY,
    order_number VARCHAR(50) UNIQUE NOT NULL,
    customer_id INTEGER REFERENCES customers(id) ON DELETE SET NULL,
    order_date DATE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'confirmed', 'processing', 'shipped', 'delivered', 'cancelled')),
    subtotal DECIMAL(10,2) NOT NULL DEFAULT 0,
    tax_amount DECIMAL(10,2) NOT NULL DEFAULT 0,
    total_amount DECIMAL(10,2) NOT NULL DEFAULT 0,
    notes TEXT,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_sales_orders_order_number ON sales_orders(order_number);
CREATE INDEX idx_sales_orders_customer_id ON sales_orders(customer_id);
CREATE INDEX idx_sales_orders_status ON sales_orders(status);
CREATE INDEX idx_sales_orders_order_date ON sales_orders(order_date);
```

#### sales_order_items table
```sql
CREATE TABLE sales_order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES sales_orders(id) ON DELETE CASCADE,
    inventory_item_id INTEGER REFERENCES inventory_items(id) ON DELETE SET NULL,
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL,
    line_total DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_sales_order_items_order_id ON sales_order_items(order_id);
CREATE INDEX idx_sales_order_items_inventory_item_id ON sales_order_items(inventory_item_id);
```

#### invoices table
```sql
CREATE TABLE invoices (
    id SERIAL PRIMARY KEY,
    invoice_number VARCHAR(50) UNIQUE NOT NULL,
    order_id INTEGER REFERENCES sales_orders(id) ON DELETE SET NULL,
    customer_id INTEGER REFERENCES customers(id) ON DELETE SET NULL,
    invoice_date DATE NOT NULL,
    due_date DATE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'unpaid'
        CHECK (status IN ('unpaid', 'paid', 'overdue', 'cancelled')),
    subtotal DECIMAL(10,2) NOT NULL DEFAULT 0,
    tax_amount DECIMAL(10,2) NOT NULL DEFAULT 0,
    total_amount DECIMAL(10,2) NOT NULL DEFAULT 0,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_invoices_invoice_number ON invoices(invoice_number);
CREATE INDEX idx_invoices_order_id ON invoices(order_id);
CREATE INDEX idx_invoices_status ON invoices(status);
```

### Purchase Management

#### suppliers table
```sql
CREATE TABLE suppliers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(20),
    address TEXT,
    tax_id VARCHAR(50),
    payment_terms VARCHAR(100),
    lead_time_days INTEGER DEFAULT 7,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_suppliers_name ON suppliers(name);
CREATE INDEX idx_suppliers_is_active ON suppliers(is_active);
```

#### purchase_orders table
```sql
CREATE TABLE purchase_orders (
    id SERIAL PRIMARY KEY,
    order_number VARCHAR(50) UNIQUE NOT NULL,
    supplier_id INTEGER REFERENCES suppliers(id) ON DELETE SET NULL,
    order_date DATE NOT NULL,
    expected_delivery DATE,
    status VARCHAR(20) NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'sent', 'confirmed', 'received', 'cancelled')),
    subtotal DECIMAL(10,2) NOT NULL DEFAULT 0,
    tax_amount DECIMAL(10,2) NOT NULL DEFAULT 0,
    total_amount DECIMAL(10,2) NOT NULL DEFAULT 0,
    notes TEXT,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_purchase_orders_order_number ON purchase_orders(order_number);
CREATE INDEX idx_purchase_orders_supplier_id ON purchase_orders(supplier_id);
CREATE INDEX idx_purchase_orders_status ON purchase_orders(status);
```

#### purchase_order_items table
```sql
CREATE TABLE purchase_order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES purchase_orders(id) ON DELETE CASCADE,
    inventory_item_id INTEGER REFERENCES inventory_items(id) ON DELETE SET NULL,
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL,
    line_total DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_purchase_order_items_order_id ON purchase_order_items(order_id);
CREATE INDEX idx_purchase_order_items_inventory_item_id ON purchase_order_items(inventory_item_id);
```

#### purchase_receipts table
```sql
CREATE TABLE purchase_receipts (
    id SERIAL PRIMARY KEY,
    receipt_number VARCHAR(50) UNIQUE NOT NULL,
    order_id INTEGER REFERENCES purchase_orders(id) ON DELETE SET NULL,
    supplier_id INTEGER REFERENCES suppliers(id) ON DELETE SET NULL,
    receipt_date DATE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'partial', 'received', 'cancelled')),
    notes TEXT,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_purchase_receipts_receipt_number ON purchase_receipts(receipt_number);
CREATE INDEX idx_purchase_receipts_order_id ON purchase_receipts(order_id);
```

## 🔗 Relationships

### Entity Relationship Diagram

#### User Management
```
users (1:N) user_roles (N:1) roles
users (1:N) sales_orders (created_by)
users (1:N) purchase_orders (created_by)
```

#### Inventory Management
```
categories (1:N) inventory_items
warehouses (1:N) stock_movements
inventory_items (1:N) stock_movements
inventory_items (1:N) sales_order_items
inventory_items (1:N) purchase_order_items
```

#### Sales Management
```
customers (1:N) sales_orders
sales_orders (1:N) sales_order_items
sales_orders (1:1) invoices
```

#### Purchase Management
```
suppliers (1:N) purchase_orders
purchase_orders (1:N) purchase_order_items
purchase_orders (1:N) purchase_receipts
```

### Foreign Key Constraints

#### Cascade Operations
```sql
-- Sales orders cascade delete items
ALTER TABLE sales_order_items
ADD CONSTRAINT fk_sales_order_items_order_id
FOREIGN KEY (order_id) REFERENCES sales_orders(id) ON DELETE CASCADE;

-- Stock movements cascade delete
ALTER TABLE stock_movements
ADD CONSTRAINT fk_stock_movements_item_id
FOREIGN KEY (item_id) REFERENCES inventory_items(id) ON DELETE CASCADE;
```

#### Set Null Operations
```sql
-- Orders set customer to null if customer deleted
ALTER TABLE sales_orders
ADD CONSTRAINT fk_sales_orders_customer_id
FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE SET NULL;
```

## 📈 Indexes & Constraints

### Performance Indexes

#### Composite Indexes
```sql
-- Sales orders by customer and date
CREATE INDEX idx_sales_orders_customer_date ON sales_orders(customer_id, order_date);

-- Inventory items by category and active status
CREATE INDEX idx_inventory_items_category_active ON inventory_items(category_id, is_active);

-- Stock movements by item and date
CREATE INDEX idx_stock_movements_item_date ON stock_movements(item_id, created_at);
```

#### Partial Indexes
```sql
-- Active users only
CREATE INDEX idx_users_active_email ON users(email) WHERE is_active = true;

-- Active inventory items only
CREATE INDEX idx_inventory_items_active_sku ON inventory_items(sku) WHERE is_active = true;

-- Pending orders only
CREATE INDEX idx_sales_orders_pending ON sales_orders(created_at) WHERE status = 'pending';
```

#### Unique Constraints
```sql
-- User email uniqueness
ALTER TABLE users ADD CONSTRAINT uk_users_email UNIQUE (email);

-- SKU uniqueness
ALTER TABLE inventory_items ADD CONSTRAINT uk_inventory_items_sku UNIQUE (sku);

-- Order number uniqueness
ALTER TABLE sales_orders ADD CONSTRAINT uk_sales_orders_order_number UNIQUE (order_number);
```

### Check Constraints

#### Business Rules
```sql
-- Positive quantities
ALTER TABLE sales_order_items ADD CONSTRAINT chk_positive_quantity CHECK (quantity > 0);
ALTER TABLE purchase_order_items ADD CONSTRAINT chk_positive_quantity CHECK (quantity > 0);

-- Valid order status
ALTER TABLE sales_orders ADD CONSTRAINT chk_valid_status CHECK (status IN ('draft', 'confirmed', 'processing', 'shipped', 'delivered', 'cancelled'));

-- Valid monetary values
ALTER TABLE sales_orders ADD CONSTRAINT chk_positive_amount CHECK (total_amount >= 0);
ALTER TABLE purchase_orders ADD CONSTRAINT chk_positive_amount CHECK (total_amount >= 0);
```

#### Data Integrity
```sql
-- Min/max stock levels
ALTER TABLE inventory_items ADD CONSTRAINT chk_stock_levels CHECK (min_stock_level >= 0 AND max_stock_level >= min_stock_level);

-- Credit limit
ALTER TABLE customers ADD CONSTRAINT chk_credit_limit CHECK (credit_limit >= 0);
```

## 🔄 Database Migrations

### Migration Structure
```
alembic/
├── versions/
│   ├── 0001_initial_migration_manual.py
│   ├── 35118b1f034f_initial_migration_with_all_models.py
│   └── 199dbdac42a3_add_emag_offer_models_for_importing_.py
├── env.py
├── script.py.mako
└── README
```

### Migration Commands
```bash
# Create new migration
alembic revision --autogenerate -m "add_user_preferences"

# Run migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Check current revision
alembic current

# Show migration history
alembic history
```

### Migration Example
```python
# alembic/versions/xxxx_add_user_preferences.py
"""Add user preferences

Revision ID: xxxx
Revises: yyyy
Create Date: 2024-01-15 10:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = 'xxxx'
down_revision = 'yyyy'
branch_labels = None
depends_on = None

def upgrade():
    # Create user_preferences table
    op.create_table('user_preferences',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('preference_key', sa.String(length=100), nullable=False),
        sa.Column('preference_value', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_user_preferences_user_id', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'preference_key', name='uk_user_preferences_user_key')
    )

    # Create indexes
    op.create_index('idx_user_preferences_user_id', 'user_preferences', ['user_id'], unique=False)
    op.create_index('idx_user_preferences_key', 'user_preferences', ['preference_key'], unique=False)

def downgrade():
    # Drop table and indexes
    op.drop_index('idx_user_preferences_key', table_name='user_preferences')
    op.drop_index('idx_user_preferences_user_id', table_name='user_preferences')
    op.drop_table('user_preferences')
```

## 📊 Data Types

### PostgreSQL Data Types Used

#### Numeric Types
```sql
-- Integer types
id SERIAL PRIMARY KEY           -- Auto-incrementing integer
quantity INTEGER NOT NULL       -- Whole numbers
stock_level INTEGER DEFAULT 0   -- Stock quantities

-- Decimal types (for money)
price DECIMAL(10,2) NOT NULL    -- Currency values
tax_amount DECIMAL(10,2)        -- Tax calculations
total_amount DECIMAL(12,2)      -- Order totals
```

#### Character Types
```sql
-- Variable length strings
name VARCHAR(255) NOT NULL      -- Product names
description TEXT                -- Long descriptions
email VARCHAR(255) UNIQUE       -- Email addresses

-- Fixed length strings
sku VARCHAR(100) UNIQUE         -- Stock keeping units
status VARCHAR(20) NOT NULL     -- Status values
```

#### Date/Time Types
```sql
-- Timestamp with timezone
created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()

-- Date only
order_date DATE NOT NULL
due_date DATE NOT NULL

-- Time intervals
lead_time_days INTEGER DEFAULT 7  -- Days for delivery
```

#### Boolean Types
```sql
-- Boolean flags
is_active BOOLEAN DEFAULT true
is_superuser BOOLEAN DEFAULT false
is_deleted BOOLEAN DEFAULT false
```

#### JSON Types
```sql
-- Flexible data storage
metadata JSONB                  -- Additional data
settings JSONB                  -- User preferences
characteristics JSONB           -- Product attributes
```

### Data Type Best Practices

#### Use Appropriate Types
```sql
-- Good: Specific types
price DECIMAL(10,2) NOT NULL    -- Exact decimal places
email VARCHAR(255) NOT NULL     -- Reasonable length limit
description TEXT                -- Unlimited length

-- Bad: Generic types
data TEXT                       -- No type safety
info VARCHAR(1000)              -- Arbitrary limit
```

#### NULL vs Empty Strings
```sql
-- Prefer NULL for optional data
description TEXT                -- NULL when no description
phone VARCHAR(20)               -- NULL when no phone

-- Use empty strings for required data
name VARCHAR(255) NOT NULL      -- Empty string not allowed
sku VARCHAR(100) UNIQUE NOT NULL -- Must have value
```

#### Enum vs VARCHAR
```sql
-- Use VARCHAR with CHECK constraints for status
status VARCHAR(20) NOT NULL CHECK (status IN ('draft', 'confirmed', 'cancelled'))

-- Or create ENUM types for better performance
CREATE TYPE order_status AS ENUM ('draft', 'confirmed', 'cancelled');
ALTER TABLE sales_orders ALTER COLUMN status TYPE order_status;
```

## 📝 Audit & Logging

### Audit Tables

#### audit_log table
```sql
CREATE TABLE audit_log (
    id SERIAL PRIMARY KEY,
    table_name VARCHAR(100) NOT NULL,
    record_id INTEGER NOT NULL,
    action VARCHAR(20) NOT NULL,
    old_values JSONB,
    new_values JSONB,
    changed_by INTEGER REFERENCES users(id),
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_audit_log_table_record ON audit_log(table_name, record_id);
CREATE INDEX idx_audit_log_changed_at ON audit_log(changed_at);
CREATE INDEX idx_audit_log_changed_by ON audit_log(changed_by);
```

#### system_logs table
```sql
CREATE TABLE system_logs (
    id SERIAL PRIMARY KEY,
    level VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    module VARCHAR(100),
    function VARCHAR(100),
    line_number INTEGER,
    user_id INTEGER REFERENCES users(id),
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_system_logs_level ON system_logs(level);
CREATE INDEX idx_system_logs_created_at ON system_logs(created_at);
CREATE INDEX idx_system_logs_user_id ON system_logs(user_id);
```

### Audit Triggers

#### Automatic Audit Logging
```sql
-- Function to log changes
CREATE OR REPLACE FUNCTION audit_trigger_function()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        INSERT INTO audit_log (table_name, record_id, action, old_values, changed_by)
        VALUES (TG_TABLE_NAME, OLD.id, TG_OP, row_to_json(OLD), NULL);
        RETURN OLD;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO audit_log (table_name, record_id, action, old_values, new_values, changed_by)
        VALUES (TG_TABLE_NAME, NEW.id, TG_OP, row_to_json(OLD), row_to_json(NEW), NULL);
        RETURN NEW;
    ELSIF TG_OP = 'INSERT' THEN
        INSERT INTO audit_log (table_name, record_id, action, new_values, changed_by)
        VALUES (TG_TABLE_NAME, NEW.id, TG_OP, row_to_json(NEW), NULL);
        RETURN NEW;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Apply to tables
CREATE TRIGGER audit_users_trigger
    AFTER INSERT OR UPDATE OR DELETE ON users
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();

CREATE TRIGGER audit_inventory_items_trigger
    AFTER INSERT OR UPDATE OR DELETE ON inventory_items
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();
```

## ⚡ Performance Considerations

### Query Optimization

#### Use Proper Indexing
```sql
-- Index for common queries
CREATE INDEX CONCURRENTLY idx_inventory_items_low_stock ON inventory_items(stock_quantity) WHERE stock_quantity <= min_stock_level;

-- Composite index for complex queries
CREATE INDEX CONCURRENTLY idx_sales_orders_customer_status ON sales_orders(customer_id, status, order_date);

-- Partial index for active records
CREATE INDEX CONCURRENTLY idx_users_active ON users(id) WHERE is_active = true;
```

#### Optimize Queries
```sql
-- Good: Uses indexes
SELECT * FROM sales_orders
WHERE customer_id = ? AND status = 'confirmed'
ORDER BY order_date DESC
LIMIT 10;

-- Bad: Full table scan
SELECT * FROM sales_orders
WHERE EXTRACT(YEAR FROM order_date) = 2024;

-- Good: Use date range
SELECT * FROM sales_orders
WHERE order_date >= '2024-01-01' AND order_date < '2025-01-01';
```

### Connection Pooling

#### SQLAlchemy Configuration
```python
engine = create_async_engine(
    DATABASE_URL,
    # Connection pool settings
    pool_size=20,           # Base number of connections
    max_overflow=30,        # Additional connections when needed
    pool_pre_ping=True,     # Verify connections before use
    pool_recycle=3600,      # Recycle connections after 1 hour
    # Performance settings
    echo=False,             # Disable SQL logging in production
    future=True             # Use SQLAlchemy 2.0 style
)
```

#### Connection Pool Monitoring
```python
# app/services/database_monitoring.py
from sqlalchemy import text
from app.core.database import engine

async def get_pool_status():
    """Get database connection pool status."""
    async with engine.begin() as conn:
        result = await conn.execute(text("""
            SELECT
                COUNT(*) as total_connections,
                COUNT(*) FILTER (WHERE state = 'active') as active_connections,
                COUNT(*) FILTER (WHERE state = 'idle') as idle_connections
            FROM pg_stat_activity
            WHERE datname = current_database()
        """))
        row = result.fetchone()
        return {
            "total_connections": row.total_connections,
            "active_connections": row.active_connections,
            "idle_connections": row.idle_connections
        }
```

### Partitioning Strategy

#### Date-based Partitioning
```sql
-- Create partitioned table
CREATE TABLE sales_orders_partitioned (
    id SERIAL NOT NULL,
    order_number VARCHAR(50) NOT NULL,
    customer_id INTEGER,
    order_date DATE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    total_amount DECIMAL(10,2) NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
) PARTITION BY RANGE (order_date);

-- Create partitions
CREATE TABLE sales_orders_2024 PARTITION OF sales_orders_partitioned
    FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');

CREATE TABLE sales_orders_2025 PARTITION OF sales_orders_partitioned
    FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');
```

#### Automated Partition Management
```sql
-- Function to create new partitions
CREATE OR REPLACE FUNCTION create_monthly_partition(
    partition_date DATE DEFAULT CURRENT_DATE
) RETURNS VOID AS $$
DECLARE
    partition_name TEXT;
    start_date DATE;
    end_date DATE;
BEGIN
    start_date := DATE_TRUNC('month', partition_date);
    end_date := start_date + INTERVAL '1 month';
    partition_name := 'sales_orders_' || TO_CHAR(start_date, 'YYYY_MM');

    EXECUTE format(
        'CREATE TABLE IF NOT EXISTS %I PARTITION OF sales_orders_partitioned
         FOR VALUES FROM (%L) TO (%L)',
        partition_name, start_date, end_date
    );
END;
$$ LANGUAGE plpgsql;
```

---

**MagFlow ERP Database Schema** - Complete Database Documentation 🗄️
