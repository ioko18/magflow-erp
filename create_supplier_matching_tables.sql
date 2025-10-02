-- Create supplier matching tables for MagFlow ERP

-- Create product_matching_groups table
CREATE TABLE IF NOT EXISTS app.product_matching_groups (
    id SERIAL PRIMARY KEY,
    group_name VARCHAR(1000) NOT NULL,
    group_name_en VARCHAR(1000),
    description TEXT,
    representative_image_url VARCHAR(2000),
    representative_image_hash VARCHAR(64),
    confidence_score FLOAT NOT NULL DEFAULT 0.0,
    matching_method VARCHAR(20) NOT NULL DEFAULT 'text',
    status VARCHAR(20) NOT NULL DEFAULT 'auto_matched',
    verified_by INTEGER,
    verified_at TIMESTAMP,
    min_price_cny FLOAT,
    max_price_cny FLOAT,
    avg_price_cny FLOAT,
    best_supplier_id INTEGER,
    product_count INTEGER NOT NULL DEFAULT 0,
    local_product_id INTEGER,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    tags JSON,
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create supplier_raw_products table
CREATE TABLE IF NOT EXISTS app.supplier_raw_products (
    id SERIAL PRIMARY KEY,
    supplier_id INTEGER NOT NULL REFERENCES app.suppliers(id),
    chinese_name VARCHAR(1000) NOT NULL,
    price_cny FLOAT NOT NULL,
    product_url VARCHAR(2000) NOT NULL,
    image_url VARCHAR(2000) NOT NULL,
    english_name VARCHAR(1000),
    normalized_name VARCHAR(1000),
    image_hash VARCHAR(64),
    image_features JSON,
    image_downloaded BOOLEAN DEFAULT FALSE,
    image_local_path VARCHAR(500),
    matching_status VARCHAR(20) DEFAULT 'pending',
    product_group_id INTEGER REFERENCES app.product_matching_groups(id),
    import_batch_id VARCHAR(50),
    import_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_price_check TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    notes TEXT,
    specifications JSON,
    supplier_sku VARCHAR(100),
    moq INTEGER,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for product_matching_groups
CREATE INDEX IF NOT EXISTS idx_product_matching_groups_status ON app.product_matching_groups(status);
CREATE INDEX IF NOT EXISTS idx_product_matching_groups_active ON app.product_matching_groups(is_active);
CREATE INDEX IF NOT EXISTS idx_product_matching_groups_confidence ON app.product_matching_groups(confidence_score);
CREATE INDEX IF NOT EXISTS idx_product_matching_groups_created ON app.product_matching_groups(created_at);

-- Create indexes for supplier_raw_products
CREATE INDEX IF NOT EXISTS idx_supplier_raw_name ON app.supplier_raw_products(chinese_name);
CREATE INDEX IF NOT EXISTS idx_supplier_raw_supplier ON app.supplier_raw_products(supplier_id);
CREATE INDEX IF NOT EXISTS idx_supplier_raw_status ON app.supplier_raw_products(matching_status);
CREATE INDEX IF NOT EXISTS idx_supplier_raw_active ON app.supplier_raw_products(is_active);
CREATE INDEX IF NOT EXISTS idx_supplier_raw_group ON app.supplier_raw_products(product_group_id);
CREATE INDEX IF NOT EXISTS idx_supplier_raw_batch ON app.supplier_raw_products(import_batch_id);

-- Create product_matching_scores table
CREATE TABLE IF NOT EXISTS app.product_matching_scores (
    id SERIAL PRIMARY KEY,
    product_a_id INTEGER NOT NULL REFERENCES app.supplier_raw_products(id),
    product_b_id INTEGER NOT NULL REFERENCES app.supplier_raw_products(id),
    text_similarity FLOAT NOT NULL DEFAULT 0.0,
    image_similarity FLOAT,
    price_similarity FLOAT,
    total_score FLOAT NOT NULL DEFAULT 0.0,
    matching_algorithm VARCHAR(50) NOT NULL,
    matching_features JSON,
    is_match BOOLEAN NOT NULL DEFAULT FALSE,
    threshold_used FLOAT NOT NULL DEFAULT 0.7,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_product_pair UNIQUE (product_a_id, product_b_id)
);

-- Create supplier_price_history table
CREATE TABLE IF NOT EXISTS app.supplier_price_history (
    id SERIAL PRIMARY KEY,
    raw_product_id INTEGER NOT NULL REFERENCES app.supplier_raw_products(id),
    price_cny FLOAT NOT NULL,
    price_change FLOAT,
    price_change_percent FLOAT,
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    source VARCHAR(50) NOT NULL DEFAULT 'scraping',
    notes VARCHAR(500),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for product_matching_scores
CREATE INDEX IF NOT EXISTS idx_matching_products ON app.product_matching_scores(product_a_id, product_b_id);
CREATE INDEX IF NOT EXISTS idx_matching_score ON app.product_matching_scores(total_score);

-- Create indexes for supplier_price_history
CREATE INDEX IF NOT EXISTS idx_price_history_product ON app.supplier_price_history(raw_product_id);
CREATE INDEX IF NOT EXISTS idx_price_history_date ON app.supplier_price_history(recorded_at);

-- Grant permissions
GRANT ALL ON app.product_matching_groups TO magflow_user;
GRANT ALL ON app.supplier_raw_products TO magflow_user;
GRANT ALL ON app.product_matching_scores TO magflow_user;
GRANT ALL ON app.supplier_price_history TO magflow_user;
GRANT USAGE, SELECT ON SEQUENCE app.product_matching_groups_id_seq TO magflow_user;
GRANT USAGE, SELECT ON SEQUENCE app.supplier_raw_products_id_seq TO magflow_user;
GRANT USAGE, SELECT ON SEQUENCE app.product_matching_scores_id_seq TO magflow_user;
GRANT USAGE, SELECT ON SEQUENCE app.supplier_price_history_id_seq TO magflow_user;
