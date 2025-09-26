# SKU Semantics Documentation - MagFlow ERP

## Overview

SKU semantics in MagFlow ERP are clearly defined to prevent confusion between different product identifiers across systems. This document outlines the semantic meaning of each SKU-related field and their usage across the codebase, database, and eMAG integration.

## SKU Field Definitions

### 1. Seller SKU (`sku`)

- **Definition**: Internal product identifier used by the seller/merchant
- **Field name in code**: `sku`
- **Database column**: `sku` (VARCHAR(100), UNIQUE, NOT NULL)
- **eMAG API field**: `part_number` (when sending data to eMAG)
- **Usage**: Internal inventory management, order processing, reporting
- **Constraints**: Must be unique across all products, seller-defined format

### 2. eMAG Product Key (`emag_part_number_key`)

- **Definition**: eMAG's unique product identifier (part_number_key)
- **Field name in code**: `emag_part_number_key`
- **Database column**: `emag_part_number_key` (VARCHAR(50), UNIQUE, NULLABLE)
- **eMAG API field**: `part_number_key` (when reading data from eMAG)
- **Usage**: eMAG marketplace integration, product synchronization
- **Constraints**: Unique within eMAG, assigned by eMAG system

### 3. EAN (`ean`)

- **Definition**: European Article Number (EAN/UPC barcode)
- **Field name in code**: `ean`
- **Database column**: `ean` (VARCHAR(18), INDEXED, NULLABLE)
- **eMAG API field**: `ean` (array of EAN codes)
- **Usage**: Product identification, barcode scanning, alternative to part_number_key
- **Constraints**: Valid EAN format (6-18 numeric digits)

## Database Schema

### products table

```sql
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    sku VARCHAR(100) UNIQUE NOT NULL COMMENT 'Seller internal SKU (part_number in eMAG API)',
    emag_part_number_key VARCHAR(50) UNIQUE NULL COMMENT 'eMAG unique identifier (part_number_key in eMAG API)',
    ean VARCHAR(18) NULL COMMENT 'European Article Number - alternative identifier',
    -- ... other fields
);
```

### Key Constraints

- `sku`: UNIQUE, NOT NULL - Required for all products
- `emag_part_number_key`: UNIQUE, NULLABLE - Only for eMAG-integrated products
- `ean`: INDEXED, NULLABLE - Optional barcode identifier

## Code Usage Patterns

### 1. Product Creation

```python
# Creating a new product with seller SKU
product = Product(
    sku="ABC-123",  # Seller's internal SKU
    name="Sample Product",
    # ... other fields
)

# eMAG integration adds marketplace identifiers
product.emag_part_number_key = "EMAG-XYZ-789"  # Assigned by eMAG
product.ean = "1234567890123"  # Barcode
```

### 2. SKU Retrieval Methods

```python
# Get seller SKU (always available)
seller_sku = product.get_seller_sku()  # Returns product.sku

# Get eMAG identifier (may be None)
emag_key = product.get_emag_identifier()  # Returns emag_part_number_key or ean

# Check if product is mapped to eMAG
is_mapped = product.is_mapped_to_emag()  # True if emag_part_number_key or ean exists

# Get display SKU (eMAG key if available, otherwise seller SKU)
display_sku = product.get_display_sku()  # For UI display
```

### 3. eMAG Integration

```python
# Mapping between internal and eMAG fields
mapping_config = MappingConfiguration(
    product_field_mapping=ProductFieldMapping(
        part_number_mapping=FieldMappingRule(
            internal_field="sku",        # Our internal SKU
            emag_field="part_number",    # eMAG's part_number field
            required=False
        )
        # ... other mappings
    )
)
```

## API Integration Semantics

### Sending Data to eMAG

```python
# When creating/updating offers in eMAG
emag_data = {
    "part_number": product.sku,           # Our seller SKU goes to eMAG's part_number
    "name": product.name,
    # ... other fields
}
```

### Receiving Data from eMAG

```python
# When reading offers from eMAG API
emag_response = {
    "id": 12345,
    "part_number_key": "EMAG-KEY-123",    # eMAG's unique identifier
    "name": "Product Name",
    # ... other fields
}

# Map to our database
product.emag_part_number_key = emag_response["part_number_key"]
```

## Validation Rules

### 1. Product Creation

- `sku` must be unique and not empty
- `sku` can contain letters, numbers, hyphens, underscores
- `emag_part_number_key` must be unique if provided
- `ean` must be valid EAN format if provided

### 2. eMAG Integration

- Products can exist without eMAG mapping (internal only)
- Once mapped to eMAG, `emag_part_number_key` should not change
- `part_number_key` and `ean` are mutually exclusive in eMAG API
- Only one identifier should be used for eMAG product attachment

## Best Practices

### 1. Always Use Semantic Methods

```python
# ✅ Good - Use semantic methods
seller_sku = product.get_seller_sku()
emag_identifier = product.get_emag_identifier()

# ❌ Bad - Direct field access
seller_sku = product.sku  # Less clear intent
```

### 2. Validate Before eMAG Operations

```python
# Check if product can be sent to eMAG
if not product.is_mapped_to_emag():
    # Cannot sync - missing eMAG identifier
    raise ValidationError("Product not mapped to eMAG")
```

### 3. Handle Missing Identifiers Gracefully

```python
# Provide fallback when eMAG key is missing
display_identifier = product.get_emag_identifier() or product.get_seller_sku()
```

## Migration from Legacy Systems

### 1. Data Migration Script

```python
# When migrating from systems without clear SKU semantics
def migrate_product_skus():
    for product in legacy_products:
        # Assume legacy SKU becomes our seller SKU
        new_product = Product(
            sku=product.legacy_sku,
            name=product.name,
            # ... other fields
        )

        # If there's an eMAG mapping, set the eMAG identifier
        if product.emag_key:
            new_product.emag_part_number_key = product.emag_key
```

### 2. Validation During Migration

```python
# Ensure no duplicate SKUs after migration
existing_skus = {p.sku for p in Product.query.all()}
for legacy_product in legacy_products:
    if legacy_product.legacy_sku in existing_skus:
        # Handle duplicate - perhaps add suffix
        legacy_product.legacy_sku += "_MIGRATED"
```

## Testing

### 1. Unit Tests

```python
def test_sku_semantics():
    """Test that SKU semantics are properly implemented."""
    product = Product(sku="TEST-123", name="Test Product")

    # Test seller SKU access
    assert product.get_seller_sku() == "TEST-123"
    assert product.sku == "TEST-123"

    # Test eMAG identifier access (should be None initially)
    assert product.get_emag_identifier() is None
    assert not product.is_mapped_to_emag()

    # Test display SKU (falls back to seller SKU)
    assert product.get_display_sku() == "TEST-123"
```

### 2. Integration Tests

```python
def test_emag_integration():
    """Test eMAG integration with proper SKU mapping."""
    product = Product(sku="SELLER-123", name="Integration Test Product")

    # Simulate eMAG assignment
    product.emag_part_number_key = "EMAG-KEY-456"

    # Verify mapping works correctly
    assert product.is_mapped_to_emag()
    assert product.get_emag_identifier() == "EMAG-KEY-456"
    assert product.get_display_sku() == "EMAG-KEY-456"  # Prefers eMAG key
```

## Troubleshooting

### Common Issues

#### 1. "Product not found in eMAG"

```python
# Check if product has eMAG identifier
if not product.emag_part_number_key and not product.ean:
    print("Product not mapped to eMAG - cannot search by ID")
```

#### 2. "Duplicate SKU error"

```python
# Check for conflicting identifiers
if product.emag_part_number_key and product.ean:
    print("Warning: Both part_number_key and EAN set - eMAG allows only one")
```

#### 3. "Invalid part_number format"

```python
# Validate seller SKU format
if ',' in product.sku or ' ' in product.sku:
    print("Seller SKU contains invalid characters for eMAG")
```

## Summary

The SKU semantics in MagFlow ERP are clearly defined as follows:

1. **Seller SKU** (`sku`): Internal identifier, always required, unique
1. **eMAG Key** (`emag_part_number_key`): eMAG's identifier, optional, unique
1. **EAN** (`ean`): Barcode identifier, optional, indexed

This clear separation ensures:

- ✅ No confusion between different identifier types
- ✅ Proper mapping to eMAG API fields
- ✅ Flexible product management (internal vs marketplace)
- ✅ Data integrity and validation
- ✅ Clear upgrade path for existing systems

All code should use the semantic methods (`get_seller_sku()`, `get_emag_identifier()`, etc.) rather than direct field access to maintain clarity and prevent bugs.
