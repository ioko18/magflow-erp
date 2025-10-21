# Supplier Products Data Persistence Guide

## Problem Overview

**Issue**: Supplier products displayed in the frontend (page "Produse Furnizori") disappear after running `make down` and `make up`.

**Root Cause**: The `make down` command executes `docker compose down -v`, which **deletes all Docker volumes**, including the PostgreSQL database volume (`postgres_data`). This results in complete data loss.

## Understanding the Data Flow

### Database Tables

The system uses **two** supplier-related tables:

1. **`product_supplier_sheets`** (Primary for frontend display)
   - Stores supplier mappings imported from Google Sheets
   - Contains: SKU, supplier name, price (CNY), contact info, URLs
   - Used by: Low Stock Suppliers page, Purchase Orders
   - Model: `ProductSupplierSheet`

2. **`supplier_products`** (Relational design)
   - Newer table with proper foreign keys to suppliers and products
   - Used for: 1688.com integration, supplier matching
   - Model: `SupplierProduct`

### Why Data Disappears

```bash
make down
  ↓
docker compose down -v
  ↓
Deletes postgres_data volume
  ↓
All data lost (including supplier products)
  ↓
make up
  ↓
Creates fresh database
  ↓
Runs migrations (creates empty tables)
  ↓
No seed data → Empty supplier products
```

## Solutions Implemented

### 1. Safe Down Command

**New command**: `make down-keep-data`

```bash
# Old (DANGEROUS - deletes all data)
make down

# New (SAFE - keeps data)
make down-keep-data
```

The `make down` command now shows a warning and requires confirmation:

```bash
$ make down
⚠️  WARNING: This will DELETE ALL DATA (volumes will be removed)!
⚠️  Use 'make down-keep-data' to keep your data.
Are you sure? [y/N]
```

### 2. Seed Data Script

**Script**: `scripts/seed_supplier_products.py`

Automatically seeds demo supplier products data.

**Usage**:

```bash
# Seed supplier products only
make seed-suppliers

# Seed all demo data
make seed-all
```

**Manual execution**:

```bash
# Inside Docker container
docker compose exec app python scripts/seed_supplier_products.py

# Or locally
python3 scripts/seed_supplier_products.py
```

### 3. Database Backup & Restore

**Backup database**:

```bash
make db-backup
```

Creates: `backups/magflow_YYYYMMDD_HHMMSS.sql.gz`

**Restore database**:

```bash
make db-restore
```

Restores from the latest backup in `backups/` directory.

**Important**: This command will:
1. Show a confirmation prompt
2. **DROP the entire database**
3. Recreate it fresh
4. Restore all data from backup

For automated scripts, use:
```bash
make db-restore-force  # No confirmation
```

## Recommended Workflow

### Development Workflow

```bash
# 1. Start containers (first time)
make up

# 2. Seed demo data
make seed-all

# 3. Work on your features...

# 4. Stop containers (KEEPS DATA)
make down-keep-data

# 5. Restart later
make up
# Data is still there! ✅
```

### When You Need Fresh Database

```bash
# 1. Backup current data (optional but recommended)
make db-backup

# 2. Stop and remove volumes
make down  # Confirms deletion

# 3. Start fresh
make up

# 4. Seed demo data
make seed-all

# Or restore from backup
make db-restore
```

### Production Deployment

```bash
# NEVER use 'make down' in production!
# Always use:
make down-keep-data

# Or for production:
docker compose -f docker-compose.production.yml down
```

## Available Make Commands

### Docker Operations

| Command | Description | Data Loss Risk |
|---------|-------------|----------------|
| `make up` | Start containers | ❌ No |
| `make down` | Stop + delete volumes | ⚠️ **YES - DELETES ALL DATA** |
| `make down-keep-data` | Stop containers only | ✅ No |
| `make restart` | Restart app container | ❌ No |
| `make logs` | View app logs | ❌ No |

### Database Operations

| Command | Description |
|---------|-------------|
| `make seed-suppliers` | Seed supplier products |
| `make seed-all` | Seed all demo data |
| `make db-backup` | Backup database |
| `make db-restore` | Restore from backup (with confirmation) |
| `make db-restore-force` | Force restore without confirmation |
| `make migrate-compose` | Run migrations |
| `make db-shell` | Open PostgreSQL shell |

### Development

| Command | Description |
|---------|-------------|
| `make start` | Start local server |
| `make test` | Run tests |
| `make lint` | Run linters |
| `make format` | Format code |

## Troubleshooting

### Supplier Products Not Showing

**Symptoms**: Frontend shows empty supplier products list

**Solution**:

```bash
# Check if data exists
make db-shell
# Then in psql:
SELECT COUNT(*) FROM app.product_supplier_sheets;

# If count is 0, seed data:
make seed-suppliers
```

### After `make down` Data is Gone

**This is expected behavior!** `make down` deletes volumes.

**Solution**:

```bash
# Restore from backup
make db-restore

# Or seed fresh data
make seed-all
```

### Want to Keep Data Between Restarts

**Always use**:

```bash
make down-keep-data  # Instead of 'make down'
```

## Technical Details

### Database Volume

- **Volume name**: `postgres_data`
- **Location**: Managed by Docker
- **Persistence**: Survives container restarts unless explicitly deleted

### Seed Data Included

The seed script creates sample data for:

- Arduino UNO R3 (3 suppliers)
- ESP32 DevKit (2 suppliers)
- NodeMCU ESP8266 (1 supplier)
- Raspberry Pi Pico (2 suppliers)
- 37-in-1 Sensor Kit (1 supplier)

### Migration Files

- `86f7456767fd_initial_database_schema_with_users_.py` - Creates all tables
- `20251010_add_auxiliary_tables.py` - Auxiliary tables
- `20251013_fix_all_timezone_columns.py` - Timezone fixes

All migrations now use `logger` instead of `print()` for cleaner output.

## Best Practices

1. **Never use `make down` unless you want to delete all data**
2. **Always backup before major changes**: `make db-backup`
3. **Use `make down-keep-data` for normal stops**
4. **Seed data after fresh database**: `make seed-all`
5. **Keep backups in version control** (add to `.gitignore` if sensitive)

## Additional Resources

- **API Documentation**: http://localhost:8000/docs
- **Database Schema**: See `app/models/` directory
- **Seed Script**: `scripts/seed_supplier_products.py`
- **Makefile**: See all available commands with `make help`

---

**Last Updated**: 2025-10-14
**Version**: 1.0
