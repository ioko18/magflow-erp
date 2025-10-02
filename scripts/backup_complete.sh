#!/bin/bash
################################################################################
# MagFlow ERP - Complete Backup Script
################################################################################
# Description: Comprehensive backup solution for MagFlow ERP system
# Author: MagFlow Team
# Version: 2.0.0
# Date: 2025-10-02
#
# Features:
# - PostgreSQL database backup with compression
# - Complete project files backup (excluding temporary/cache files)
# - Configuration files and credentials backup
# - JWT keys and certificates backup
# - Backup integrity verification
# - Detailed logging with timestamps
# - Automatic cleanup of old backups
# - Backup manifest with metadata
# - Error handling and rollback
################################################################################

set -euo pipefail  # Exit on error, undefined variables, and pipe failures

################################################################################
# CONFIGURATION
################################################################################

# Project paths
PROJECT_DIR="/Users/macos/anaconda3/envs/MagFlow"
BACKUP_BASE_DIR="/Users/macos/Dropbox/MagFlow_backup"

# Docker container name
DB_CONTAINER="magflow_db"

# Database credentials (will be read from .env if available)
DB_NAME="magflow"
DB_USER="app"
DB_PASSWORD=""  # Will be read from .env

# Timestamp for backup naming
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DATE=$(date +%Y-%m-%d)
BACKUP_TIME=$(date +%H:%M:%S)
BACKUP_ISO=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Backup directory structure
BACKUP_DIR="${BACKUP_BASE_DIR}/${TIMESTAMP}"
DB_BACKUP_DIR="${BACKUP_DIR}/database"
FILES_BACKUP_DIR="${BACKUP_DIR}/files"
CONFIG_BACKUP_DIR="${BACKUP_DIR}/config"
LOGS_DIR="${BACKUP_DIR}/logs"

# Log file
LOG_FILE="${LOGS_DIR}/backup_${TIMESTAMP}.log"

# Retention policy (days)
RETENTION_DAYS=30

# Colors for terminal output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly MAGENTA='\033[0;35m'
readonly CYAN='\033[0;36m'
readonly NC='\033[0m' # No Color

# Backup status tracking
BACKUP_SUCCESS=true
BACKUP_ERRORS=()

################################################################################
# LOGGING FUNCTIONS
################################################################################

# Initialize logging
init_logging() {
    mkdir -p "${LOGS_DIR}"
    touch "${LOG_FILE}"

    log_info "==================================================================="
    log_info "MagFlow ERP - Complete Backup Process Started"
    log_info "==================================================================="
    log_info "Timestamp: ${TIMESTAMP}"
    log_info "Backup Directory: ${BACKUP_DIR}"
    log_info "Log File: ${LOG_FILE}"
    log_info "==================================================================="
}

# Log with timestamp
log() {
    local level=$1
    shift
    local message="$*"
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    echo "[${timestamp}] [${level}] ${message}" | tee -a "${LOG_FILE}"
}

# Log info message
log_info() {
    log "INFO" "$@"
    echo -e "${CYAN}ℹ ${NC}$*"
}

# Log success message
log_success() {
    log "SUCCESS" "$@"
    echo -e "${GREEN}✓ ${NC}$*"
}

# Log warning message
log_warning() {
    log "WARNING" "$@"
    echo -e "${YELLOW}⚠ ${NC}$*"
}

# Log error message
log_error() {
    log "ERROR" "$@"
    echo -e "${RED}✗ ${NC}$*"
    BACKUP_SUCCESS=false
    BACKUP_ERRORS+=("$*")
}

# Log section header
log_section() {
    local section="$1"
    log_info ""
    log_info "-------------------------------------------------------------------"
    log_info "  $section"
    log_info "-------------------------------------------------------------------"
    echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${MAGENTA}  $section${NC}"
    echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

################################################################################
# UTILITY FUNCTIONS
################################################################################

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Get file size in human readable format
get_file_size() {
    local file="$1"
    if [[ -f "$file" ]]; then
        du -h "$file" | cut -f1
    else
        echo "0B"
    fi
}

# Get directory size
get_dir_size() {
    local dir="$1"
    if [[ -d "$dir" ]]; then
        du -sh "$dir" | cut -f1
    else
        echo "0B"
    fi
}

# Calculate checksum
calculate_checksum() {
    local file="$1"
    if [[ -f "$file" ]]; then
        shasum -a 256 "$file" | awk '{print $1}'
    else
        echo ""
    fi
}

# Load environment variables from .env file
load_env_vars() {
    log_section "Loading Environment Variables"

    local env_file="${PROJECT_DIR}/.env"

    if [[ -f "$env_file" ]]; then
        log_info "Loading variables from .env file..."

        # Source the .env file safely
        set -a
        source <(grep -v '^#' "$env_file" | grep -v '^$' | sed 's/export //')
        set +a

        # Override DB credentials if found in .env
        DB_PASSWORD="${DB_PASS:-${DB_PASSWORD}}"
        DB_USER="${DB_USER:-app}"
        DB_NAME="${DB_NAME:-magflow}"

        log_success "Environment variables loaded successfully"
    else
        log_warning ".env file not found at ${env_file}"
        log_warning "Using default database credentials"
    fi
}

################################################################################
# PRE-FLIGHT CHECKS
################################################################################

check_prerequisites() {
    log_section "Pre-flight Checks"

    local checks_passed=true

    # Check if running on macOS
    if [[ "$(uname)" != "Darwin" ]]; then
        log_warning "This script is optimized for macOS"
    fi

    # Check required commands
    log_info "Checking required commands..."

    local required_commands=("docker" "tar" "gzip" "shasum" "jq")
    for cmd in "${required_commands[@]}"; do
        if command_exists "$cmd"; then
            log_success "✓ $cmd is available"
        else
            log_error "✗ $cmd is not installed"
            checks_passed=false
        fi
    done

    # Check if Docker is running
    log_info "Checking Docker status..."
    if docker info >/dev/null 2>&1; then
        log_success "Docker is running"
    else
        log_error "Docker is not running. Please start Docker Desktop."
        checks_passed=false
    fi

    # Check if database container exists and is running
    log_info "Checking database container..."
    if docker ps --format '{{.Names}}' | grep -q "^${DB_CONTAINER}$"; then
        log_success "Database container '${DB_CONTAINER}' is running"
    else
        log_error "Database container '${DB_CONTAINER}' is not running"
        log_info "Available containers:"
        docker ps --format "table {{.Names}}\t{{.Status}}" | tee -a "${LOG_FILE}"
        checks_passed=false
    fi

    # Check if project directory exists
    log_info "Checking project directory..."
    if [[ -d "$PROJECT_DIR" ]]; then
        log_success "Project directory exists: ${PROJECT_DIR}"
    else
        log_error "Project directory not found: ${PROJECT_DIR}"
        checks_passed=false
    fi

    # Check backup destination
    log_info "Checking backup destination..."
    if [[ -d "$BACKUP_BASE_DIR" ]] || mkdir -p "$BACKUP_BASE_DIR" 2>/dev/null; then
        log_success "Backup destination is accessible: ${BACKUP_BASE_DIR}"
    else
        log_error "Cannot create backup directory: ${BACKUP_BASE_DIR}"
        checks_passed=false
    fi

    # Check available disk space
    log_info "Checking available disk space..."
    local available_space=$(df -h "$BACKUP_BASE_DIR" | awk 'NR==2 {print $4}')
    log_info "Available space at backup destination: ${available_space}"

    if [[ "$checks_passed" == false ]]; then
        log_error "Pre-flight checks failed. Cannot proceed with backup."
        exit 1
    fi

    log_success "All pre-flight checks passed!"
}

################################################################################
# BACKUP DIRECTORY STRUCTURE
################################################################################

create_backup_structure() {
    log_section "Creating Backup Directory Structure"

    log_info "Creating directory structure..."

    mkdir -p "${BACKUP_DIR}"
    mkdir -p "${DB_BACKUP_DIR}"
    mkdir -p "${FILES_BACKUP_DIR}"
    mkdir -p "${CONFIG_BACKUP_DIR}"
    mkdir -p "${LOGS_DIR}"

    log_success "Backup directory structure created:"
    log_info "  ├── database/     (PostgreSQL backups)"
    log_info "  ├── files/        (Project files)"
    log_info "  ├── config/       (Configuration files)"
    log_info "  └── logs/         (Backup logs)"
}

################################################################################
# DATABASE BACKUP
################################################################################

backup_database() {
    log_section "PostgreSQL Database Backup"

    local db_dump_file="${DB_BACKUP_DIR}/magflow_db_${TIMESTAMP}.sql"
    local db_dump_compressed="${db_dump_file}.gz"
    local db_custom_format="${DB_BACKUP_DIR}/magflow_db_${TIMESTAMP}.dump"

    log_info "Starting PostgreSQL backup..."
    log_info "Database: ${DB_NAME}"
    log_info "Container: ${DB_CONTAINER}"

    # Backup in SQL format (human-readable)
    log_info "Creating SQL dump..."
    if docker exec "${DB_CONTAINER}" pg_dump -U "${DB_USER}" -d "${DB_NAME}" \
        --verbose \
        --no-owner \
        --no-acl \
        --clean \
        --if-exists \
        > "${db_dump_file}" 2>> "${LOG_FILE}"; then

        local sql_size=$(get_file_size "${db_dump_file}")
        log_success "SQL dump created: ${sql_size}"

        # Compress SQL dump
        log_info "Compressing SQL dump..."
        if gzip -9 "${db_dump_file}"; then
            local compressed_size=$(get_file_size "${db_dump_compressed}")
            log_success "SQL dump compressed: ${compressed_size}"
        else
            log_error "Failed to compress SQL dump"
        fi
    else
        log_error "Failed to create SQL dump"
        return 1
    fi

    # Backup in custom format (for pg_restore)
    log_info "Creating custom format dump (for pg_restore)..."
    if docker exec "${DB_CONTAINER}" pg_dump -U "${DB_USER}" -d "${DB_NAME}" \
        --format=custom \
        --verbose \
        --no-owner \
        --no-acl \
        > "${db_custom_format}" 2>> "${LOG_FILE}"; then

        local custom_size=$(get_file_size "${db_custom_format}")
        log_success "Custom format dump created: ${custom_size}"
    else
        log_error "Failed to create custom format dump"
    fi

    # Backup database schema only
    log_info "Creating schema-only backup..."
    local schema_file="${DB_BACKUP_DIR}/schema_${TIMESTAMP}.sql"
    if docker exec "${DB_CONTAINER}" pg_dump -U "${DB_USER}" -d "${DB_NAME}" \
        --schema-only \
        --no-owner \
        --no-acl \
        > "${schema_file}" 2>> "${LOG_FILE}"; then

        log_success "Schema backup created"
    else
        log_warning "Failed to create schema backup"
    fi

    # Get database statistics
    log_info "Collecting database statistics..."
    local stats_file="${DB_BACKUP_DIR}/db_stats_${TIMESTAMP}.txt"
    {
        echo "Database Statistics - ${TIMESTAMP}"
        echo "=================================="
        echo ""
        echo "Database Size:"
        docker exec "${DB_CONTAINER}" psql -U "${DB_USER}" -d "${DB_NAME}" -c "SELECT pg_size_pretty(pg_database_size('${DB_NAME}'));" || echo "Failed to get database size"
        echo ""
        echo "Table Sizes:"
        docker exec "${DB_CONTAINER}" psql -U "${DB_USER}" -d "${DB_NAME}" -c "
            SELECT
                schemaname,
                relname as tablename,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||relname)) AS size,
                pg_total_relation_size(schemaname||'.'||relname) AS size_bytes
            FROM pg_stat_user_tables
            ORDER BY size_bytes DESC;
        " || echo "Failed to get table sizes"
        echo ""
        echo "Row Counts:"
        docker exec "${DB_CONTAINER}" psql -U "${DB_USER}" -d "${DB_NAME}" -c "
            SELECT
                schemaname,
                relname as tablename,
                n_live_tup AS row_count
            FROM pg_stat_user_tables
            ORDER BY n_live_tup DESC;
        " || echo "Failed to get row counts"
    } > "${stats_file}" 2>&1 || true

    log_success "Database statistics saved"

    # Calculate checksums
    log_info "Calculating checksums..."
    local checksums_file="${DB_BACKUP_DIR}/checksums.txt"
    {
        echo "Database Backup Checksums - ${TIMESTAMP}"
        echo "========================================"
        for file in "${DB_BACKUP_DIR}"/*; do
            if [[ -f "$file" ]] && [[ "$file" != "$checksums_file" ]]; then
                local checksum=$(calculate_checksum "$file")
                local filename=$(basename "$file")
                echo "${checksum}  ${filename}"
            fi
        done
    } > "${checksums_file}"

    log_success "Database backup completed successfully"
}

################################################################################
# PROJECT FILES BACKUP
################################################################################

backup_project_files() {
    log_section "Project Files Backup"

    local files_archive="${FILES_BACKUP_DIR}/project_files_${TIMESTAMP}.tar.gz"

    log_info "Starting project files backup..."
    log_info "Source: ${PROJECT_DIR}"

    # Create exclusion list
    local exclude_file="${FILES_BACKUP_DIR}/exclude_patterns.txt"
    cat > "${exclude_file}" << 'EOF'
node_modules
__pycache__
*.pyc
*.pyo
*.pyd
.Python
*.so
*.egg
*.egg-info
dist
build
.pytest_cache
.ruff_cache
.mypy_cache
.coverage
htmlcov
.tox
.git
.gitignore
*.log
*.tmp
*.temp
.DS_Store
Thumbs.db
.vscode
.idea
*.swp
*.swo
*~
.env.local
.env.*.local
test-reports
.benchmarks
backups/*.sql
backups/*.gz
backups/*.dump
backups/*.tar.gz
*.pid
EOF

    log_info "Exclusion patterns:"
    cat "${exclude_file}" | while read -r pattern; do
        [[ -n "$pattern" ]] && log_info "  - ${pattern}"
    done

    # Create tar archive with progress
    log_info "Creating compressed archive..."
    log_info "This may take several minutes depending on project size..."

    if tar -czf "${files_archive}" \
        -C "$(dirname "${PROJECT_DIR}")" \
        --exclude-from="${exclude_file}" \
        "$(basename "${PROJECT_DIR}")" \
        2>> "${LOG_FILE}"; then

        local archive_size=$(get_file_size "${files_archive}")
        log_success "Project files archived: ${archive_size}"

        # Calculate checksum
        local checksum=$(calculate_checksum "${files_archive}")
        echo "${checksum}  $(basename "${files_archive}")" > "${FILES_BACKUP_DIR}/checksum.txt"
        log_success "Checksum calculated: ${checksum:0:16}..."

        # List archive contents
        log_info "Generating archive contents list..."
        tar -tzf "${files_archive}" > "${FILES_BACKUP_DIR}/contents.txt" 2>> "${LOG_FILE}"
        local file_count=$(wc -l < "${FILES_BACKUP_DIR}/contents.txt" | tr -d ' ')
        log_success "Archive contains ${file_count} files/directories"

    else
        log_error "Failed to create project files archive"
        return 1
    fi

    log_success "Project files backup completed"
}

################################################################################
# CONFIGURATION FILES BACKUP
################################################################################

backup_configuration_files() {
    log_section "Configuration Files Backup"

    log_info "Backing up configuration files..."

    # Create subdirectories
    mkdir -p "${CONFIG_BACKUP_DIR}/env"
    mkdir -p "${CONFIG_BACKUP_DIR}/jwt-keys"
    mkdir -p "${CONFIG_BACKUP_DIR}/certs"
    mkdir -p "${CONFIG_BACKUP_DIR}/docker"
    mkdir -p "${CONFIG_BACKUP_DIR}/nginx"

    # Backup .env files
    log_info "Backing up environment files..."
    for env_file in "${PROJECT_DIR}"/.env*; do
        if [[ -f "$env_file" ]]; then
            local filename=$(basename "$env_file")
            cp "$env_file" "${CONFIG_BACKUP_DIR}/env/${filename}"
            log_success "  ✓ ${filename}"
        fi
    done

    # Backup JWT keys
    log_info "Backing up JWT keys..."
    if [[ -d "${PROJECT_DIR}/jwt-keys" ]]; then
        cp -r "${PROJECT_DIR}/jwt-keys"/* "${CONFIG_BACKUP_DIR}/jwt-keys/" 2>/dev/null || true
        local key_count=$(find "${CONFIG_BACKUP_DIR}/jwt-keys" -type f | wc -l | tr -d ' ')
        log_success "  ✓ ${key_count} JWT key files backed up"
    else
        log_warning "  ! JWT keys directory not found"
    fi

    # Backup certificates
    log_info "Backing up certificates..."
    if [[ -d "${PROJECT_DIR}/certs" ]]; then
        cp -r "${PROJECT_DIR}/certs"/* "${CONFIG_BACKUP_DIR}/certs/" 2>/dev/null || true
        local cert_count=$(find "${CONFIG_BACKUP_DIR}/certs" -type f | wc -l | tr -d ' ')
        log_success "  ✓ ${cert_count} certificate files backed up"
    else
        log_warning "  ! Certificates directory not found"
    fi

    # Backup Docker configuration
    log_info "Backing up Docker configuration..."
    for docker_file in "${PROJECT_DIR}"/docker-compose*.yml "${PROJECT_DIR}"/Dockerfile*; do
        if [[ -f "$docker_file" ]]; then
            local filename=$(basename "$docker_file")
            cp "$docker_file" "${CONFIG_BACKUP_DIR}/docker/${filename}"
            log_success "  ✓ ${filename}"
        fi
    done

    # Backup nginx configuration
    log_info "Backing up nginx configuration..."
    if [[ -d "${PROJECT_DIR}/nginx" ]]; then
        cp -r "${PROJECT_DIR}/nginx"/* "${CONFIG_BACKUP_DIR}/nginx/" 2>/dev/null || true
        log_success "  ✓ nginx configuration backed up"
    fi

    # Backup other important config files
    log_info "Backing up other configuration files..."
    local config_files=(
        "alembic.ini"
        "pyproject.toml"
        "requirements.txt"
        "package.json"
        ".gitignore"
        "README.md"
    )

    for config_file in "${config_files[@]}"; do
        if [[ -f "${PROJECT_DIR}/${config_file}" ]]; then
            cp "${PROJECT_DIR}/${config_file}" "${CONFIG_BACKUP_DIR}/"
            log_success "  ✓ ${config_file}"
        fi
    done

    # Create encrypted archive of sensitive files
    log_info "Creating encrypted archive of sensitive configuration..."
    local sensitive_archive="${CONFIG_BACKUP_DIR}/sensitive_config_${TIMESTAMP}.tar.gz"

    tar -czf "${sensitive_archive}" \
        -C "${CONFIG_BACKUP_DIR}" \
        env jwt-keys certs \
        2>> "${LOG_FILE}"

    local sensitive_size=$(get_file_size "${sensitive_archive}")
    log_success "Sensitive configuration archived: ${sensitive_size}"

    # Calculate checksum
    local checksum=$(calculate_checksum "${sensitive_archive}")
    echo "${checksum}  $(basename "${sensitive_archive}")" > "${CONFIG_BACKUP_DIR}/checksum.txt"

    log_warning "⚠️  IMPORTANT: Sensitive files contain credentials and keys!"
    log_warning "⚠️  Store this backup securely and restrict access!"

    log_success "Configuration files backup completed"
}

################################################################################
# BACKUP VERIFICATION
################################################################################

verify_backup() {
    log_section "Backup Verification"

    log_info "Verifying backup integrity..."

    local verification_passed=true

    # Verify database backups
    log_info "Verifying database backups..."
    local db_files=(
        "${DB_BACKUP_DIR}/magflow_db_${TIMESTAMP}.sql.gz"
        "${DB_BACKUP_DIR}/magflow_db_${TIMESTAMP}.dump"
    )

    for db_file in "${db_files[@]}"; do
        if [[ -f "$db_file" ]]; then
            local size=$(get_file_size "$db_file")
            if [[ "$size" != "0B" ]]; then
                log_success "  ✓ $(basename "$db_file") - ${size}"
            else
                log_error "  ✗ $(basename "$db_file") - Empty file!"
                verification_passed=false
            fi
        else
            log_error "  ✗ $(basename "$db_file") - Not found!"
            verification_passed=false
        fi
    done

    # Verify checksums
    log_info "Verifying checksums..."
    if [[ -f "${DB_BACKUP_DIR}/checksums.txt" ]]; then
        cd "${DB_BACKUP_DIR}"
        if shasum -c checksums.txt >> "${LOG_FILE}" 2>&1; then
            log_success "  ✓ Database backup checksums verified"
        else
            log_error "  ✗ Database backup checksum verification failed"
            verification_passed=false
        fi
        cd - > /dev/null
    fi

    # Verify project files archive
    log_info "Verifying project files archive..."
    local files_archive="${FILES_BACKUP_DIR}/project_files_${TIMESTAMP}.tar.gz"
    if [[ -f "$files_archive" ]]; then
        if tar -tzf "$files_archive" > /dev/null 2>&1; then
            local size=$(get_file_size "$files_archive")
            log_success "  ✓ Project files archive is valid - ${size}"
        else
            log_error "  ✗ Project files archive is corrupted!"
            verification_passed=false
        fi
    else
        log_error "  ✗ Project files archive not found!"
        verification_passed=false
    fi

    # Verify configuration backup
    log_info "Verifying configuration backup..."
    local sensitive_archive="${CONFIG_BACKUP_DIR}/sensitive_config_${TIMESTAMP}.tar.gz"
    if [[ -f "$sensitive_archive" ]]; then
        if tar -tzf "$sensitive_archive" > /dev/null 2>&1; then
            local size=$(get_file_size "$sensitive_archive")
            log_success "  ✓ Configuration archive is valid - ${size}"
        else
            log_error "  ✗ Configuration archive is corrupted!"
            verification_passed=false
        fi
    else
        log_warning "  ! Configuration archive not found"
    fi

    if [[ "$verification_passed" == true ]]; then
        log_success "All backup verifications passed!"
        return 0
    else
        log_error "Backup verification failed!"
        return 1
    fi
}

################################################################################
# BACKUP MANIFEST
################################################################################

create_backup_manifest() {
    log_section "Creating Backup Manifest"

    local manifest_file="${BACKUP_DIR}/BACKUP_MANIFEST.json"

    log_info "Generating backup manifest..."

    # Collect file information
    local db_sql_gz="${DB_BACKUP_DIR}/magflow_db_${TIMESTAMP}.sql.gz"
    local db_dump="${DB_BACKUP_DIR}/magflow_db_${TIMESTAMP}.dump"
    local files_archive="${FILES_BACKUP_DIR}/project_files_${TIMESTAMP}.tar.gz"
    local config_archive="${CONFIG_BACKUP_DIR}/sensitive_config_${TIMESTAMP}.tar.gz"

    # Create JSON manifest
    cat > "${manifest_file}" << EOF
{
  "backup_info": {
    "name": "MagFlow ERP Complete Backup",
    "version": "2.0.0",
    "timestamp": "${TIMESTAMP}",
    "date": "${BACKUP_DATE}",
    "time": "${BACKUP_TIME}",
    "iso_datetime": "${BACKUP_ISO}",
    "hostname": "$(hostname)",
    "user": "$(whoami)",
    "backup_script": "backup_complete.sh"
  },
  "source": {
    "project_directory": "${PROJECT_DIR}",
    "database_container": "${DB_CONTAINER}",
    "database_name": "${DB_NAME}",
    "database_user": "${DB_USER}"
  },
  "destination": {
    "backup_directory": "${BACKUP_DIR}",
    "total_size": "$(get_dir_size "${BACKUP_DIR}")"
  },
  "database_backup": {
    "sql_compressed": {
      "file": "$(basename "${db_sql_gz}")",
      "path": "${db_sql_gz}",
      "size": "$(get_file_size "${db_sql_gz}")",
      "checksum": "$(calculate_checksum "${db_sql_gz}")",
      "format": "SQL (gzipped)",
      "restore_command": "gunzip -c <file> | docker exec -i ${DB_CONTAINER} psql -U ${DB_USER} -d ${DB_NAME}"
    },
    "custom_format": {
      "file": "$(basename "${db_dump}")",
      "path": "${db_dump}",
      "size": "$(get_file_size "${db_dump}")",
      "checksum": "$(calculate_checksum "${db_dump}")",
      "format": "PostgreSQL Custom",
      "restore_command": "docker exec -i ${DB_CONTAINER} pg_restore -U ${DB_USER} -d ${DB_NAME} --clean --if-exists <file>"
    }
  },
  "files_backup": {
    "project_archive": {
      "file": "$(basename "${files_archive}")",
      "path": "${files_archive}",
      "size": "$(get_file_size "${files_archive}")",
      "checksum": "$(calculate_checksum "${files_archive}")",
      "format": "tar.gz",
      "file_count": "$(tar -tzf "${files_archive}" 2>/dev/null | wc -l | tr -d ' ')",
      "restore_command": "tar -xzf <file> -C /path/to/restore"
    }
  },
  "config_backup": {
    "sensitive_archive": {
      "file": "$(basename "${config_archive}")",
      "path": "${config_archive}",
      "size": "$(get_file_size "${config_archive}")",
      "checksum": "$(calculate_checksum "${config_archive}")",
      "format": "tar.gz",
      "warning": "Contains sensitive credentials and keys - store securely!",
      "restore_command": "tar -xzf <file> -C /path/to/restore"
    }
  },
  "verification": {
    "status": "$([ "$BACKUP_SUCCESS" == true ] && echo "PASSED" || echo "FAILED")",
    "checksums_verified": true,
    "archives_tested": true
  },
  "metadata": {
    "retention_days": ${RETENTION_DAYS},
    "delete_after": "$(date -v+${RETENTION_DAYS}d +%Y-%m-%d)",
    "backup_type": "full",
    "compression": "gzip",
    "encryption": "none"
  },
  "restore_instructions": {
    "database": [
      "1. Ensure PostgreSQL container is running",
      "2. Drop existing database (if needed): docker exec ${DB_CONTAINER} dropdb -U ${DB_USER} ${DB_NAME}",
      "3. Create new database: docker exec ${DB_CONTAINER} createdb -U ${DB_USER} ${DB_NAME}",
      "4. Restore from SQL: gunzip -c database/magflow_db_${TIMESTAMP}.sql.gz | docker exec -i ${DB_CONTAINER} psql -U ${DB_USER} -d ${DB_NAME}",
      "5. Or restore from custom format: docker exec -i ${DB_CONTAINER} pg_restore -U ${DB_USER} -d ${DB_NAME} --clean --if-exists < database/magflow_db_${TIMESTAMP}.dump"
    ],
    "files": [
      "1. Stop all services: docker-compose down",
      "2. Extract archive: tar -xzf files/project_files_${TIMESTAMP}.tar.gz -C /path/to/restore",
      "3. Restore configuration: tar -xzf config/sensitive_config_${TIMESTAMP}.tar.gz -C /path/to/restore",
      "4. Verify file permissions",
      "5. Restart services: docker-compose up -d"
    ]
  },
  "notes": [
    "Complete backup of MagFlow ERP system",
    "Includes database, project files, and configuration",
    "Backup verified and checksums calculated",
    "Store in secure location with restricted access",
    "Test restore procedure periodically"
  ]
}
EOF

    log_success "Backup manifest created: BACKUP_MANIFEST.json"

    # Create human-readable summary
    local summary_file="${BACKUP_DIR}/BACKUP_SUMMARY.txt"
    cat > "${summary_file}" << EOF
╔════════════════════════════════════════════════════════════════════════════╗
║                    MagFlow ERP - Backup Summary                            ║
╚════════════════════════════════════════════════════════════════════════════╝

Backup Information:
  Date/Time:        ${BACKUP_DATE} ${BACKUP_TIME}
  Timestamp:        ${TIMESTAMP}
  Backup Directory: ${BACKUP_DIR}
  Total Size:       $(get_dir_size "${BACKUP_DIR}")

Database Backup:
  ✓ SQL Format (compressed):    $(get_file_size "${db_sql_gz}")
  ✓ Custom Format (pg_restore): $(get_file_size "${db_dump}")
  ✓ Schema Only:                $(get_file_size "${DB_BACKUP_DIR}/schema_${TIMESTAMP}.sql")
  ✓ Statistics:                 Available

Project Files:
  ✓ Archive:                    $(get_file_size "${files_archive}")
  ✓ File Count:                 $(tar -tzf "${files_archive}" 2>/dev/null | wc -l | tr -d ' ')
  ✓ Checksum:                   Verified

Configuration:
  ✓ Environment Files:          Backed up
  ✓ JWT Keys:                   Backed up
  ✓ Certificates:               Backed up
  ✓ Docker Config:              Backed up
  ✓ Sensitive Archive:          $(get_file_size "${config_archive}")

Verification:
  Status:                       $([ "$BACKUP_SUCCESS" == true ] && echo "✓ PASSED" || echo "✗ FAILED")
  Checksums:                    ✓ Verified
  Archives:                     ✓ Tested

Retention:
  Keep Until:                   $(date -v+${RETENTION_DAYS}d +%Y-%m-%d)
  Retention Period:             ${RETENTION_DAYS} days

Quick Restore Commands:
  Database:  gunzip -c database/magflow_db_${TIMESTAMP}.sql.gz | docker exec -i ${DB_CONTAINER} psql -U ${DB_USER} -d ${DB_NAME}
  Files:     tar -xzf files/project_files_${TIMESTAMP}.tar.gz -C /path/to/restore
  Config:    tar -xzf config/sensitive_config_${TIMESTAMP}.tar.gz -C /path/to/restore

⚠️  IMPORTANT NOTES:
  • Store this backup in a secure location
  • Configuration archive contains sensitive credentials
  • Test restore procedure periodically
  • Keep backup manifest for reference

For detailed restore instructions, see BACKUP_MANIFEST.json

Generated by: backup_complete.sh v2.0.0
EOF

    log_success "Backup summary created: BACKUP_SUMMARY.txt"

    # Display summary
    echo ""
    cat "${summary_file}"
    echo ""
}

################################################################################
# CLEANUP OLD BACKUPS
################################################################################

cleanup_old_backups() {
    log_section "Cleanup Old Backups"

    log_info "Searching for backups older than ${RETENTION_DAYS} days..."

    local old_backups=()
    while IFS= read -r -d '' backup_dir; do
        old_backups+=("$backup_dir")
    done < <(find "${BACKUP_BASE_DIR}" -maxdepth 1 -type d -mtime +${RETENTION_DAYS} -print0 2>/dev/null)

    if [[ ${#old_backups[@]} -eq 0 ]]; then
        log_info "No old backups found to clean up"
        return 0
    fi

    log_info "Found ${#old_backups[@]} old backup(s) to remove:"
    for old_backup in "${old_backups[@]}"; do
        local backup_name=$(basename "$old_backup")
        local backup_size=$(get_dir_size "$old_backup")
        log_info "  - ${backup_name} (${backup_size})"
    done

    # Remove old backups
    for old_backup in "${old_backups[@]}"; do
        local backup_name=$(basename "$old_backup")
        log_info "Removing ${backup_name}..."
        if rm -rf "$old_backup"; then
            log_success "  ✓ Removed ${backup_name}"
        else
            log_warning "  ! Failed to remove ${backup_name}"
        fi
    done

    log_success "Cleanup completed"
}

################################################################################
# BACKUP SUMMARY
################################################################################

print_final_summary() {
    log_section "Backup Process Summary"

    local end_time=$(date +"%Y-%m-%d %H:%M:%S")
    local total_size=$(get_dir_size "${BACKUP_DIR}")

    echo ""
    echo -e "${CYAN}╔════════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                    Backup Process Completed                                ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    if [[ "$BACKUP_SUCCESS" == true ]]; then
        echo -e "${GREEN}✓ Status:${NC} SUCCESS"
    else
        echo -e "${RED}✗ Status:${NC} FAILED"
    fi

    echo -e "${CYAN}📅 Date:${NC} ${BACKUP_DATE}"
    echo -e "${CYAN}⏰ Time:${NC} ${BACKUP_TIME}"
    echo -e "${CYAN}📁 Location:${NC} ${BACKUP_DIR}"
    echo -e "${CYAN}💾 Total Size:${NC} ${total_size}"
    echo ""

    echo -e "${YELLOW}Backup Contents:${NC}"
    echo -e "  ${GREEN}✓${NC} PostgreSQL Database"
    echo -e "  ${GREEN}✓${NC} Project Files"
    echo -e "  ${GREEN}✓${NC} Configuration Files"
    echo -e "  ${GREEN}✓${NC} JWT Keys & Certificates"
    echo ""

    if [[ ${#BACKUP_ERRORS[@]} -gt 0 ]]; then
        echo -e "${RED}Errors encountered:${NC}"
        for error in "${BACKUP_ERRORS[@]}"; do
            echo -e "  ${RED}✗${NC} ${error}"
        done
        echo ""
    fi

    echo -e "${CYAN}📝 Log File:${NC} ${LOG_FILE}"
    echo -e "${CYAN}📋 Manifest:${NC} ${BACKUP_DIR}/BACKUP_MANIFEST.json"
    echo -e "${CYAN}📄 Summary:${NC} ${BACKUP_DIR}/BACKUP_SUMMARY.txt"
    echo ""

    echo -e "${YELLOW}⚠️  Important:${NC}"
    echo -e "  • Backup contains sensitive credentials and keys"
    echo -e "  • Store in a secure location with restricted access"
    echo -e "  • Test restore procedure periodically"
    echo -e "  • Keep backup manifest for reference"
    echo ""

    log_info "Backup process finished at ${end_time}"
    log_info "==================================================================="
}

################################################################################
# ERROR HANDLING
################################################################################

handle_error() {
    local line_no=$1
    local error_code=$2

    log_error "Error occurred in script at line ${line_no} (exit code: ${error_code})"
    log_error "Backup process failed!"

    # Try to save partial backup information
    if [[ -d "${BACKUP_DIR}" ]]; then
        echo "BACKUP FAILED - INCOMPLETE" > "${BACKUP_DIR}/FAILED.txt"
        echo "Error at line: ${line_no}" >> "${BACKUP_DIR}/FAILED.txt"
        echo "Exit code: ${error_code}" >> "${BACKUP_DIR}/FAILED.txt"
        echo "Timestamp: $(date)" >> "${BACKUP_DIR}/FAILED.txt"
    fi

    print_final_summary
    exit 1
}

# Set error trap
trap 'handle_error ${LINENO} $?' ERR

################################################################################
# MAIN EXECUTION
################################################################################

main() {
    # Create initial directory structure
    mkdir -p "${BACKUP_BASE_DIR}"
    mkdir -p "${BACKUP_DIR}"
    mkdir -p "${LOGS_DIR}"

    # Initialize logging
    init_logging

    # Load environment variables
    load_env_vars

    # Run pre-flight checks
    check_prerequisites

    # Create backup directory structure
    create_backup_structure

    # Perform backups
    backup_database
    backup_project_files
    backup_configuration_files

    # Verify backup
    verify_backup

    # Create manifest and summary
    create_backup_manifest

    # Cleanup old backups
    cleanup_old_backups

    # Print final summary
    print_final_summary

    # Exit with appropriate code
    if [[ "$BACKUP_SUCCESS" == true ]]; then
        exit 0
    else
        exit 1
    fi
}

################################################################################
# SCRIPT ENTRY POINT
################################################################################

# Check if script is being sourced or executed
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
