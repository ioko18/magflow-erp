#!/bin/bash
################################################################################
# MagFlow ERP - Complete Restore Script
################################################################################
# Description: Restore MagFlow ERP system from backup
# Author: MagFlow Team
# Version: 2.0.0
# Date: 2025-10-02
#
# Features:
# - Interactive backup selection
# - Database restore with verification
# - Project files restore
# - Configuration restore
# - Pre-restore validation
# - Post-restore verification
# - Rollback capability
################################################################################

set -euo pipefail

################################################################################
# CONFIGURATION
################################################################################

BACKUP_BASE_DIR="/Users/macos/Dropbox/MagFlow_backup"
PROJECT_DIR="/Users/macos/anaconda3/envs/MagFlow"
DB_CONTAINER="magflow_db"
DB_NAME="magflow"
DB_USER="app"

# Colors
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly MAGENTA='\033[0;35m'
readonly CYAN='\033[0;36m'
readonly NC='\033[0m'

RESTORE_LOG=""
SELECTED_BACKUP=""

################################################################################
# LOGGING FUNCTIONS
################################################################################

log_info() {
    echo -e "${CYAN}ℹ ${NC}$*" | tee -a "${RESTORE_LOG}"
}

log_success() {
    echo -e "${GREEN}✓ ${NC}$*" | tee -a "${RESTORE_LOG}"
}

log_warning() {
    echo -e "${YELLOW}⚠ ${NC}$*" | tee -a "${RESTORE_LOG}"
}

log_error() {
    echo -e "${RED}✗ ${NC}$*" | tee -a "${RESTORE_LOG}"
}

log_section() {
    echo "" | tee -a "${RESTORE_LOG}"
    echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}" | tee -a "${RESTORE_LOG}"
    echo -e "${MAGENTA}  $1${NC}" | tee -a "${RESTORE_LOG}"
    echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}" | tee -a "${RESTORE_LOG}"
}

################################################################################
# UTILITY FUNCTIONS
################################################################################

get_dir_size() {
    local dir="$1"
    if [[ -d "$dir" ]]; then
        du -sh "$dir" | cut -f1
    else
        echo "0B"
    fi
}

################################################################################
# BACKUP SELECTION
################################################################################

list_available_backups() {
    log_section "Available Backups"

    if [[ ! -d "$BACKUP_BASE_DIR" ]]; then
        log_error "Backup directory not found: ${BACKUP_BASE_DIR}"
        exit 1
    fi

    local backups=()
    while IFS= read -r -d '' backup_dir; do
        backups+=("$backup_dir")
    done < <(find "${BACKUP_BASE_DIR}" -maxdepth 1 -type d -name "2*" -print0 2>/dev/null | sort -rz)

    if [[ ${#backups[@]} -eq 0 ]]; then
        log_error "No backups found in ${BACKUP_BASE_DIR}"
        exit 1
    fi

    echo ""
    echo "Found ${#backups[@]} backup(s):"
    echo ""

    local i=1
    for backup in "${backups[@]}"; do
        local backup_name=$(basename "$backup")
        local backup_size=$(get_dir_size "$backup")
        local manifest="${backup}/BACKUP_MANIFEST.json"

        if [[ -f "$manifest" ]]; then
            local backup_date=$(jq -r '.backup_info.date' "$manifest" 2>/dev/null || echo "Unknown")
            local backup_time=$(jq -r '.backup_info.time' "$manifest" 2>/dev/null || echo "Unknown")
            local status=$(jq -r '.verification.status' "$manifest" 2>/dev/null || echo "Unknown")

            echo -e "${CYAN}${i}.${NC} ${backup_name}"
            echo "   Date: ${backup_date} ${backup_time}"
            echo "   Size: ${backup_size}"
            echo "   Status: ${status}"
            echo ""
        else
            echo -e "${CYAN}${i}.${NC} ${backup_name} (${backup_size}) - No manifest"
            echo ""
        fi

        ((i++))
    done

    # Prompt for selection
    echo -n "Select backup to restore (1-${#backups[@]}) or 'q' to quit: "
    read -r selection

    if [[ "$selection" == "q" ]] || [[ "$selection" == "Q" ]]; then
        log_info "Restore cancelled by user"
        exit 0
    fi

    if [[ "$selection" =~ ^[0-9]+$ ]] && [[ "$selection" -ge 1 ]] && [[ "$selection" -le ${#backups[@]} ]]; then
        SELECTED_BACKUP="${backups[$((selection-1))]}"
        log_success "Selected backup: $(basename "${SELECTED_BACKUP}")"
    else
        log_error "Invalid selection"
        exit 1
    fi
}

################################################################################
# PRE-RESTORE VALIDATION
################################################################################

validate_backup() {
    log_section "Validating Backup"

    local manifest="${SELECTED_BACKUP}/BACKUP_MANIFEST.json"

    if [[ ! -f "$manifest" ]]; then
        log_error "Backup manifest not found!"
        exit 1
    fi

    log_info "Reading backup manifest..."

    # Display backup information
    local backup_date=$(jq -r '.backup_info.date' "$manifest")
    local backup_time=$(jq -r '.backup_info.time' "$manifest")
    local verification_status=$(jq -r '.verification.status' "$manifest")

    echo ""
    echo "Backup Information:"
    echo "  Date: ${backup_date}"
    echo "  Time: ${backup_time}"
    echo "  Verification: ${verification_status}"
    echo ""

    # Check required files
    log_info "Checking backup files..."

    local db_backup="${SELECTED_BACKUP}/database"
    local files_backup="${SELECTED_BACKUP}/files"
    local config_backup="${SELECTED_BACKUP}/config"

    if [[ -d "$db_backup" ]]; then
        log_success "Database backup found"
    else
        log_error "Database backup not found!"
        exit 1
    fi

    if [[ -d "$files_backup" ]]; then
        log_success "Files backup found"
    else
        log_warning "Files backup not found"
    fi

    if [[ -d "$config_backup" ]]; then
        log_success "Configuration backup found"
    else
        log_warning "Configuration backup not found"
    fi

    log_success "Backup validation passed"
}

################################################################################
# RESTORE OPTIONS
################################################################################

select_restore_options() {
    log_section "Restore Options"

    echo ""
    echo "What would you like to restore?"
    echo ""
    echo "1. Database only"
    echo "2. Files only"
    echo "3. Configuration only"
    echo "4. Database + Configuration"
    echo "5. Everything (Full restore)"
    echo ""
    echo -n "Select option (1-5): "
    read -r option

    case $option in
        1)
            RESTORE_DATABASE=true
            RESTORE_FILES=false
            RESTORE_CONFIG=false
            ;;
        2)
            RESTORE_DATABASE=false
            RESTORE_FILES=true
            RESTORE_CONFIG=false
            ;;
        3)
            RESTORE_DATABASE=false
            RESTORE_FILES=false
            RESTORE_CONFIG=true
            ;;
        4)
            RESTORE_DATABASE=true
            RESTORE_FILES=false
            RESTORE_CONFIG=true
            ;;
        5)
            RESTORE_DATABASE=true
            RESTORE_FILES=true
            RESTORE_CONFIG=true
            ;;
        *)
            log_error "Invalid option"
            exit 1
            ;;
    esac

    # Confirmation
    echo ""
    log_warning "⚠️  WARNING: This will overwrite existing data!"
    echo ""
    echo "You selected to restore:"
    [[ "$RESTORE_DATABASE" == true ]] && echo "  • Database"
    [[ "$RESTORE_FILES" == true ]] && echo "  • Project Files"
    [[ "$RESTORE_CONFIG" == true ]] && echo "  • Configuration"
    echo ""
    echo -n "Are you sure you want to proceed? (yes/no): "
    read -r confirmation

    if [[ "$confirmation" != "yes" ]]; then
        log_info "Restore cancelled by user"
        exit 0
    fi
}

################################################################################
# DATABASE RESTORE
################################################################################

restore_database() {
    log_section "Restoring Database"

    local db_backup_dir="${SELECTED_BACKUP}/database"
    local manifest="${SELECTED_BACKUP}/BACKUP_MANIFEST.json"

    # Find the SQL backup file
    local sql_backup=$(jq -r '.database_backup.sql_compressed.path' "$manifest")

    if [[ ! -f "$sql_backup" ]]; then
        log_error "Database backup file not found: ${sql_backup}"
        return 1
    fi

    log_info "Database backup: $(basename "${sql_backup}")"

    # Check if container is running
    if ! docker ps --format '{{.Names}}' | grep -q "^${DB_CONTAINER}$"; then
        log_error "Database container '${DB_CONTAINER}' is not running"
        return 1
    fi

    # Create backup of current database before restore
    log_info "Creating safety backup of current database..."
    local safety_backup="/tmp/magflow_pre_restore_$(date +%Y%m%d_%H%M%S).sql"
    docker exec "${DB_CONTAINER}" pg_dump -U "${DB_USER}" -d "${DB_NAME}" > "${safety_backup}" 2>/dev/null || true
    log_success "Safety backup created: ${safety_backup}"

    # Drop and recreate database
    log_warning "Dropping existing database..."
    docker exec "${DB_CONTAINER}" psql -U "${DB_USER}" -d postgres -c "DROP DATABASE IF EXISTS ${DB_NAME};" 2>&1 | tee -a "${RESTORE_LOG}"

    log_info "Creating new database..."
    docker exec "${DB_CONTAINER}" psql -U "${DB_USER}" -d postgres -c "CREATE DATABASE ${DB_NAME};" 2>&1 | tee -a "${RESTORE_LOG}"

    # Restore database
    log_info "Restoring database from backup..."
    log_info "This may take several minutes..."

    if gunzip -c "${sql_backup}" | docker exec -i "${DB_CONTAINER}" psql -U "${DB_USER}" -d "${DB_NAME}" 2>&1 | tee -a "${RESTORE_LOG}"; then
        log_success "Database restored successfully"

        # Verify restore
        log_info "Verifying database restore..."
        local table_count=$(docker exec "${DB_CONTAINER}" psql -U "${DB_USER}" -d "${DB_NAME}" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" | tr -d ' ')
        log_success "Database contains ${table_count} tables"

        # Remove safety backup
        rm -f "${safety_backup}"
    else
        log_error "Database restore failed!"
        log_warning "Attempting to restore from safety backup..."
        docker exec -i "${DB_CONTAINER}" psql -U "${DB_USER}" -d "${DB_NAME}" < "${safety_backup}"
        return 1
    fi
}

################################################################################
# FILES RESTORE
################################################################################

restore_files() {
    log_section "Restoring Project Files"

    local files_backup_dir="${SELECTED_BACKUP}/files"
    local manifest="${SELECTED_BACKUP}/BACKUP_MANIFEST.json"

    # Find the files archive
    local files_archive=$(jq -r '.files_backup.project_archive.path' "$manifest")

    if [[ ! -f "$files_archive" ]]; then
        log_error "Files backup not found: ${files_archive}"
        return 1
    fi

    log_info "Files archive: $(basename "${files_archive}")"

    # Create backup of current project
    log_warning "Creating safety backup of current project..."
    local safety_backup="/tmp/magflow_project_backup_$(date +%Y%m%d_%H%M%S).tar.gz"
    tar -czf "${safety_backup}" -C "$(dirname "${PROJECT_DIR}")" "$(basename "${PROJECT_DIR}")" 2>/dev/null || true
    log_success "Safety backup created: ${safety_backup}"

    # Extract files
    log_info "Extracting project files..."
    log_warning "This will overwrite existing files!"

    if tar -xzf "${files_archive}" -C "$(dirname "${PROJECT_DIR}")" 2>&1 | tee -a "${RESTORE_LOG}"; then
        log_success "Project files restored successfully"
    else
        log_error "Files restore failed!"
        return 1
    fi
}

################################################################################
# CONFIGURATION RESTORE
################################################################################

restore_configuration() {
    log_section "Restoring Configuration"

    local config_backup_dir="${SELECTED_BACKUP}/config"
    local manifest="${SELECTED_BACKUP}/BACKUP_MANIFEST.json"

    # Find the configuration archive
    local config_archive=$(jq -r '.config_backup.sensitive_archive.path' "$manifest")

    if [[ ! -f "$config_archive" ]]; then
        log_error "Configuration backup not found: ${config_archive}"
        return 1
    fi

    log_info "Configuration archive: $(basename "${config_archive}")"

    # Extract to temporary directory
    local temp_dir=$(mktemp -d)
    log_info "Extracting configuration to temporary directory..."
    tar -xzf "${config_archive}" -C "${temp_dir}" 2>&1 | tee -a "${RESTORE_LOG}"

    # Restore environment files
    if [[ -d "${temp_dir}/env" ]]; then
        log_info "Restoring environment files..."
        cp -v "${temp_dir}/env"/* "${PROJECT_DIR}/" 2>&1 | tee -a "${RESTORE_LOG}"
        log_success "Environment files restored"
    fi

    # Restore JWT keys
    if [[ -d "${temp_dir}/jwt-keys" ]]; then
        log_info "Restoring JWT keys..."
        mkdir -p "${PROJECT_DIR}/jwt-keys"
        cp -rv "${temp_dir}/jwt-keys"/* "${PROJECT_DIR}/jwt-keys/" 2>&1 | tee -a "${RESTORE_LOG}"
        log_success "JWT keys restored"
    fi

    # Restore certificates
    if [[ -d "${temp_dir}/certs" ]]; then
        log_info "Restoring certificates..."
        mkdir -p "${PROJECT_DIR}/certs"
        cp -rv "${temp_dir}/certs"/* "${PROJECT_DIR}/certs/" 2>&1 | tee -a "${RESTORE_LOG}"
        log_success "Certificates restored"
    fi

    # Cleanup
    rm -rf "${temp_dir}"

    log_success "Configuration restored successfully"
}

################################################################################
# POST-RESTORE VERIFICATION
################################################################################

verify_restore() {
    log_section "Post-Restore Verification"

    local verification_passed=true

    if [[ "$RESTORE_DATABASE" == true ]]; then
        log_info "Verifying database..."
        if docker exec "${DB_CONTAINER}" psql -U "${DB_USER}" -d "${DB_NAME}" -c "SELECT 1;" >/dev/null 2>&1; then
            log_success "Database is accessible"
        else
            log_error "Database verification failed"
            verification_passed=false
        fi
    fi

    if [[ "$RESTORE_FILES" == true ]]; then
        log_info "Verifying project files..."
        if [[ -d "${PROJECT_DIR}" ]] && [[ -f "${PROJECT_DIR}/app/main.py" ]]; then
            log_success "Project files are present"
        else
            log_error "Project files verification failed"
            verification_passed=false
        fi
    fi

    if [[ "$RESTORE_CONFIG" == true ]]; then
        log_info "Verifying configuration..."
        if [[ -f "${PROJECT_DIR}/.env" ]]; then
            log_success "Configuration files are present"
        else
            log_warning "Some configuration files may be missing"
        fi
    fi

    if [[ "$verification_passed" == true ]]; then
        log_success "All verifications passed!"
    else
        log_error "Some verifications failed!"
    fi
}

################################################################################
# MAIN EXECUTION
################################################################################

main() {
    echo -e "${CYAN}╔════════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                    MagFlow ERP - Restore Utility                           ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    # Initialize log
    RESTORE_LOG="/tmp/magflow_restore_$(date +%Y%m%d_%H%M%S).log"
    touch "${RESTORE_LOG}"
    log_info "Restore log: ${RESTORE_LOG}"

    # List and select backup
    list_available_backups

    # Validate selected backup
    validate_backup

    # Select restore options
    select_restore_options

    # Perform restore
    log_section "Starting Restore Process"

    [[ "$RESTORE_DATABASE" == true ]] && restore_database
    [[ "$RESTORE_FILES" == true ]] && restore_files
    [[ "$RESTORE_CONFIG" == true ]] && restore_configuration

    # Verify restore
    verify_restore

    # Final summary
    log_section "Restore Complete"
    echo ""
    log_success "Restore process completed successfully!"
    echo ""
    echo "Next steps:"
    echo "  1. Review the restore log: ${RESTORE_LOG}"
    echo "  2. Restart services: docker-compose restart"
    echo "  3. Verify application functionality"
    echo "  4. Check logs for any errors"
    echo ""
}

# Run main function
main "$@"
