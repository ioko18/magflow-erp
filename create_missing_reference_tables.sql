-- Create missing eMAG reference data tables
-- These should have been created by add_section8_fields migration but failed

-- Create emag_categories table
CREATE TABLE IF NOT EXISTS app.emag_categories (
    id INTEGER PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    is_allowed INTEGER NOT NULL DEFAULT 0,
    parent_id INTEGER,
    is_ean_mandatory INTEGER NOT NULL DEFAULT 0,
    is_warranty_mandatory INTEGER NOT NULL DEFAULT 0,
    characteristics JSONB,
    family_types JSONB,
    language VARCHAR(5) NOT NULL DEFAULT 'ro',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_synced_at TIMESTAMP
);

-- Create indexes for emag_categories
CREATE INDEX IF NOT EXISTS idx_emag_categories_parent ON app.emag_categories(parent_id);
CREATE INDEX IF NOT EXISTS idx_emag_categories_allowed ON app.emag_categories(is_allowed);
CREATE INDEX IF NOT EXISTS idx_emag_categories_name ON app.emag_categories(name);
CREATE INDEX IF NOT EXISTS idx_emag_categories_language ON app.emag_categories(language);

-- Add comments
COMMENT ON TABLE app.emag_categories IS 'eMAG product categories cache';
COMMENT ON COLUMN app.emag_categories.id IS 'eMAG category ID';
COMMENT ON COLUMN app.emag_categories.is_allowed IS '1 if seller can post in this category';
COMMENT ON COLUMN app.emag_categories.parent_id IS 'Parent category ID';
COMMENT ON COLUMN app.emag_categories.characteristics IS 'Category characteristics with mandatory flags';
COMMENT ON COLUMN app.emag_categories.family_types IS 'Family types for product variants';
COMMENT ON COLUMN app.emag_categories.language IS 'Language code: en, ro, hu, bg, pl, gr, de';
COMMENT ON COLUMN app.emag_categories.last_synced_at IS 'Last time synced from eMAG API';

-- Create emag_vat_rates table
CREATE TABLE IF NOT EXISTS app.emag_vat_rates (
    id INTEGER PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    rate FLOAT NOT NULL,
    country VARCHAR(2) NOT NULL DEFAULT 'RO',
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_synced_at TIMESTAMP
);

-- Create indexes for emag_vat_rates
CREATE INDEX IF NOT EXISTS idx_emag_vat_country ON app.emag_vat_rates(country);
CREATE INDEX IF NOT EXISTS idx_emag_vat_active ON app.emag_vat_rates(is_active);

-- Add comments
COMMENT ON TABLE app.emag_vat_rates IS 'eMAG VAT rates cache';
COMMENT ON COLUMN app.emag_vat_rates.id IS 'eMAG VAT rate ID';
COMMENT ON COLUMN app.emag_vat_rates.name IS 'VAT rate name (e.g., ''Standard Rate 19%'')';
COMMENT ON COLUMN app.emag_vat_rates.rate IS 'VAT rate as decimal (e.g., 0.19 for 19%)';
COMMENT ON COLUMN app.emag_vat_rates.country IS 'Country code';
COMMENT ON COLUMN app.emag_vat_rates.last_synced_at IS 'Last time synced from eMAG API';

-- Create emag_handling_times table
CREATE TABLE IF NOT EXISTS app.emag_handling_times (
    id INTEGER PRIMARY KEY,
    value INTEGER NOT NULL,
    name VARCHAR(100) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_synced_at TIMESTAMP
);

-- Create indexes for emag_handling_times
CREATE INDEX IF NOT EXISTS idx_emag_handling_time_value ON app.emag_handling_times(value);
CREATE INDEX IF NOT EXISTS idx_emag_handling_time_active ON app.emag_handling_times(is_active);

-- Add comments
COMMENT ON TABLE app.emag_handling_times IS 'eMAG handling times cache';
COMMENT ON COLUMN app.emag_handling_times.id IS 'eMAG handling time ID';
COMMENT ON COLUMN app.emag_handling_times.value IS 'Number of days from order to dispatch';
COMMENT ON COLUMN app.emag_handling_times.name IS 'Handling time name';
COMMENT ON COLUMN app.emag_handling_times.last_synced_at IS 'Last time synced from eMAG API';

-- Verify tables were created
SELECT 'emag_categories' as table_name, COUNT(*) as row_count FROM app.emag_categories
UNION ALL
SELECT 'emag_vat_rates', COUNT(*) FROM app.emag_vat_rates
UNION ALL
SELECT 'emag_handling_times', COUNT(*) FROM app.emag_handling_times;
