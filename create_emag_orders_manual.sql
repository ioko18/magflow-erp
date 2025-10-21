-- Manual creation of emag_orders table
-- This is the SQL equivalent of the Alembic migration

-- Check if table exists
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables 
               WHERE table_schema = 'app' 
               AND table_name = 'emag_orders') THEN
        RAISE NOTICE 'Table emag_orders already exists, skipping creation';
    ELSE
        RAISE NOTICE 'Creating emag_orders table...';
        
        -- Create the table
        CREATE TABLE app.emag_orders (
            -- Primary identification
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            emag_order_id BIGINT NOT NULL,
            account_type VARCHAR(10) NOT NULL DEFAULT 'main',
            
            -- Order status and type
            status INTEGER NOT NULL,
            status_name VARCHAR(50),
            type INTEGER,
            is_complete BOOLEAN NOT NULL DEFAULT FALSE,
            
            -- Customer information
            customer_id BIGINT,
            customer_name VARCHAR(200),
            customer_email VARCHAR(200),
            customer_phone VARCHAR(50),
            
            -- Financial information
            total_amount FLOAT NOT NULL DEFAULT 0.0,
            currency VARCHAR(3) NOT NULL DEFAULT 'RON',
            
            -- Payment information
            payment_method VARCHAR(50),
            payment_mode_id INTEGER,
            detailed_payment_method VARCHAR(100),
            payment_status INTEGER,
            cashed_co FLOAT,
            cashed_cod FLOAT,
            
            -- Shipping information
            delivery_mode VARCHAR(50),
            shipping_tax FLOAT,
            shipping_tax_voucher_split JSONB,
            shipping_address JSONB,
            billing_address JSONB,
            
            -- Delivery details
            locker_id VARCHAR(50),
            locker_name VARCHAR(200),
            
            -- AWB and tracking
            awb_number VARCHAR(100),
            courier_name VARCHAR(100),
            
            -- Documents
            invoice_url TEXT,
            invoice_uploaded_at TIMESTAMP,
            
            -- Order items and vouchers - CRITICAL FOR SOLD QUANTITY
            products JSONB,
            vouchers JSONB,
            attachments JSONB,
            
            -- Special flags
            is_storno BOOLEAN NOT NULL DEFAULT FALSE,
            
            -- Order lifecycle timestamps
            acknowledged_at TIMESTAMP,
            finalized_at TIMESTAMP,
            
            -- Sync tracking
            sync_status VARCHAR(50) NOT NULL DEFAULT 'pending',
            last_synced_at TIMESTAMP,
            sync_error TEXT,
            sync_attempts INTEGER NOT NULL DEFAULT 0,
            
            -- Timestamps
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
            order_date TIMESTAMP,
            emag_created_at TIMESTAMP,
            emag_modified_at TIMESTAMP,
            
            -- Raw eMAG data
            raw_emag_data JSONB
        );
        
        -- Create indexes
        CREATE INDEX idx_emag_orders_emag_id_account ON app.emag_orders(emag_order_id, account_type);
        CREATE INDEX idx_emag_orders_account ON app.emag_orders(account_type);
        CREATE INDEX idx_emag_orders_status ON app.emag_orders(status);
        CREATE INDEX idx_emag_orders_sync_status ON app.emag_orders(sync_status);
        CREATE INDEX idx_emag_orders_order_date ON app.emag_orders(order_date);
        CREATE INDEX idx_emag_orders_customer_email ON app.emag_orders(customer_email);
        
        -- Create unique constraint
        ALTER TABLE app.emag_orders 
        ADD CONSTRAINT uq_emag_orders_id_account 
        UNIQUE (emag_order_id, account_type);
        
        -- Create check constraints
        ALTER TABLE app.emag_orders 
        ADD CONSTRAINT ck_emag_orders_account_type 
        CHECK (account_type IN ('main', 'fbe'));
        
        ALTER TABLE app.emag_orders 
        ADD CONSTRAINT ck_emag_orders_status 
        CHECK (status IN (0,1,2,3,4,5));
        
        ALTER TABLE app.emag_orders 
        ADD CONSTRAINT ck_emag_orders_type 
        CHECK (type IN (2,3));
        
        RAISE NOTICE '✅ Successfully created emag_orders table with all indexes and constraints';
    END IF;
END $$;

-- Verify table creation
SELECT 
    table_name,
    (SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = 'app' AND table_name = 'emag_orders') as column_count,
    (SELECT COUNT(*) FROM pg_indexes WHERE schemaname = 'app' AND tablename = 'emag_orders') as index_count
FROM information_schema.tables
WHERE table_schema = 'app' AND table_name = 'emag_orders';
