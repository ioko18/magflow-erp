#!/bin/bash
# MagFlow ERP Restore Script
# This script restores PostgreSQL and Redis data from backups

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE=${COMPOSE_FILE:-"docker-compose.simple.yml"}
BACKUP_DIR="./backups"

# Function to show usage
show_usage() {
    echo -e "${BLUE}Usage: $0 [OPTIONS] BACKUP_NAME${NC}"
    echo -e "${BLUE}Restore MagFlow ERP data from backup${NC}"
    echo ""
    echo -e "${BLUE}Options:${NC}"
    echo -e "${BLUE}  -h, --help          Show this help message${NC}"
    echo -e "${BLUE}  -l, --list          List available backups${NC}"
    echo -e "${BLUE}  -d, --dry-run       Show what would be restored without doing it${NC}"
    echo -e "${BLUE}  -f, --force         Force restore without confirmation${NC}"
    echo ""
    echo -e "${BLUE}Examples:${NC}"
    echo -e "${BLUE}  $0 magflow_backup_20250121_143000${NC}"
    echo -e "${BLUE}  $0 --list${NC}"
    echo -e "${BLUE}  $0 --dry-run magflow_backup_20250121_143000${NC}"
}

# Function to list available backups
list_backups() {
    echo -e "${GREEN}📋 Available backups:${NC}"

    if ! command -v jq &> /dev/null; then
        echo -e "${RED}❌ 'jq' is not installed. Please install it to parse backup manifests.${NC}"
        exit 1
    fi

    if [[ ! -d "$BACKUP_DIR" ]]; then
        echo -e "${RED}❌ Backup directory not found: $BACKUP_DIR${NC}"
        exit 1
    fi

    # Find manifest files and display backup information
    find "$BACKUP_DIR" -name "manifest_*.json" | sort -r | while read -r manifest_file; do
        backup_name=$(jq -r '.backup_name' "$manifest_file")
        created_at=$(jq -r '.created_at' "$manifest_file")
        
        echo -e "${YELLOW}Backup: $backup_name${NC}"
        echo "  Manifest: $(basename "$manifest_file")"
        echo "  📅 Created: $created_at"

        # Check for backup files
        postgresql_file=$(jq -r '.services.postgresql.file' "$manifest_file")
        redis_file=$(jq -r '.services.redis.file' "$manifest_file")
        volumes_file=$(jq -r '.services.volumes.file' "$manifest_file")

        [[ -f "${BACKUP_DIR}/${postgresql_file}" ]] && echo "  ✅ PostgreSQL: $postgresql_file"
        [[ -f "${BACKUP_DIR}/${redis_file}" ]] && echo "  ✅ Redis: $redis_file"
        [[ -f "${BACKUP_DIR}/${volumes_file}" ]] && echo "  ✅ Volumes: $volumes_file"
        echo ""
    done
}

# Function to restore PostgreSQL
restore_postgresql() {
    local backup_name="$1"
    local dry_run="$2"

    local postgresql_file="${BACKUP_DIR}/postgresql_${backup_name}.dump"

    if [[ ! -f "$postgresql_file" ]]; then
        echo -e "${RED}❌ PostgreSQL backup file not found: $postgresql_file${NC}"
        return 1
    fi

    echo -e "${YELLOW}📦 Restoring PostgreSQL...${NC}"

    if [[ "$dry_run" == "true" ]]; then
        echo -e "${BLUE}📋 Would restore: $postgresql_file${NC}"
        return 0
    fi

    # Stop the database container
    echo -e "${YELLOW}🛑 Stopping database container...${NC}"
    docker compose -f "${COMPOSE_FILE}" stop db

    # Drop and recreate database
    echo -e "${YELLOW}🗑️  Dropping existing database...${NC}"
    docker compose -f "${COMPOSE_FILE}" exec -T db dropdb -U app --if-exists magflow
    docker compose -f "${COMPOSE_FILE}" exec -T db createdb -U app magflow

    # Restore the database using pg_restore
    echo -e "${YELLOW}🔄 Restoring database...${NC}"
    cat "$postgresql_file" | docker compose -f "${COMPOSE_FILE}" exec -T db pg_restore -U app -d magflow --clean --if-exists

    # Start the database container
    echo -e "${YELLOW}▶️  Starting database container...${NC}"
    docker compose -f "${COMPOSE_FILE}" start db

    echo -e "${GREEN}✅ PostgreSQL restored successfully${NC}"
}

# Function to restore Redis
restore_redis() {
    local backup_name="$1"
    local dry_run="$2"

    local redis_file="${BACKUP_DIR}/redis_${backup_name}.rdb.gz"

    if [[ ! -f "$redis_file" ]]; then
        echo -e "${RED}❌ Redis backup file not found: $redis_file${NC}"
        return 1
    fi

    echo -e "${YELLOW}📦 Restoring Redis...${NC}"

    if [[ "$dry_run" == "true" ]]; then
        echo -e "${BLUE}📋 Would restore: $redis_file${NC}"
        return 0
    fi

    # Stop Redis container
    echo -e "${YELLOW}🛑 Stopping Redis container...${NC}"
    docker compose -f "${COMPOSE_FILE}" stop redis

    # Remove existing RDB file
    docker compose -f "${COMPOSE_FILE}" exec -T redis rm -f /data/dump.rdb

    # Uncompress backup to Redis data directory
    gunzip -c "$redis_file" | docker cp - /$(docker compose -f "${COMPOSE_FILE}" ps -q redis):/data/dump.rdb

    # Start Redis container
    echo -e "${YELLOW}▶️  Starting Redis container...${NC}"
    docker compose -f "${COMPOSE_FILE}" start redis

    echo -e "${GREEN}✅ Redis restored successfully${NC}"
}

# Function to restore volumes
restore_volumes() {
    local backup_name="$1"
    local dry_run="$2"

    local volumes_file="${BACKUP_DIR}/volumes_${backup_name}.tar.gz"

    if [[ ! -f "$volumes_file" ]]; then
        echo -e "${RED}❌ Volumes backup file not found: $volumes_file${NC}"
        return 1
    fi

    echo -e "${YELLOW}📦 Restoring volumes...${NC}"

    if [[ "$dry_run" == "true" ]]; then
        echo -e "${BLUE}📋 Would restore: $volumes_file${NC}"
        return 0
    fi

    # Stop all containers
    echo -e "${YELLOW}🛑 Stopping all containers...${NC}"
    docker compose -f "${COMPOSE_FILE}" down

    # Remove existing volumes
    echo -e "${YELLOW}🗑️  Removing existing volumes...${NC}"
    docker volume rm magflow_postgres_data magflow_redis_data || true

    # Recreate volumes
    docker volume create magflow_postgres_data
    docker volume create magflow_redis_data

    # Extract backup to volumes
    echo -e "${YELLOW}🔄 Extracting volumes backup...${NC}"
    docker run --rm \
        -v magflow_postgres_data:/restore/postgres \
        -v magflow_redis_data:/restore/redis \
        -v "$volumes_file:/backup.tar.gz" \
        alpine sh -c "tar xzf /backup.tar.gz -C /restore"

    # Start all containers
    echo -e "${YELLOW}▶️  Starting all containers...${NC}"
    docker compose -f "${COMPOSE_FILE}" up -d

    echo -e "${GREEN}✅ Volumes restored successfully${NC}"
}

# Function to confirm restore
confirm_restore() {
    local backup_name="$1"
    local force="$2"

    if [[ "$force" == "true" ]]; then
        return 0
    fi

    echo -e "${RED}⚠️  WARNING: This will overwrite existing data!${NC}"
    echo -e "${RED}All current data in PostgreSQL and Redis will be lost.${NC}"
    echo -e "${YELLOW}Backup to restore: $backup_name${NC}"
    echo ""
    read -p "Are you sure you want to continue? (yes/no): " -r
    echo ""

    if [[ ! "$REPLY" =~ ^[Yy][Ee][Ss]$ ]]; then
        echo -e "${GREEN}✅ Restore cancelled${NC}"
        exit 0
    fi
}

# Main restore process
main() {
    # Parse arguments
    local dry_run="false"
    local force="false"
    local list_only="false"

    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            -l|--list)
                list_only="true"
                shift
                ;;
            -d|--dry-run)
                dry_run="true"
                shift
                ;;
            -f|--force)
                force="true"
                shift
                ;;
            -*)
                echo -e "${RED}❌ Unknown option: $1${NC}"
                show_usage
                exit 1
                ;;
            *)
                break
                ;;
        esac
    done

    # List backups if requested
    if [[ "$list_only" == "true" ]]; then
        list_backups
        exit 0
    fi

    # Check if backup name is provided
    if [[ $# -eq 0 ]]; then
        echo -e "${RED}❌ Error: Backup name is required${NC}"
        show_usage
        exit 1
    fi

    local backup_name="$1"

    # Check if backup exists
    local manifest_file="${BACKUP_DIR}/manifest_${backup_name}.json"
    if [[ ! -f "$manifest_file" ]]; then
        echo -e "${RED}❌ Error: Backup not found: $backup_name${NC}"
        echo -e "${YELLOW}Use --list to see available backups${NC}"
        exit 1
    fi

    # Show dry run info
    if [[ "$dry_run" == "true" ]]; then
        echo -e "${BLUE}🔍 DRY RUN MODE - No changes will be made${NC}"
    fi

    # Confirm restore unless forced
    confirm_restore "$backup_name" "$force"

    echo -e "${GREEN}🚀 Starting restore process for: $backup_name${NC}"

    # Perform restores
    restore_postgresql "$backup_name" "$dry_run"
    restore_redis "$backup_name" "$dry_run"
    restore_volumes "$backup_name" "$dry_run"

    if [[ "$dry_run" == "true" ]]; then
        echo -e "${BLUE}📋 Dry run completed. Use without --dry-run to perform actual restore.${NC}"
    else
        echo -e "${GREEN}✅ Restore completed successfully!${NC}"
        echo -e "${GREEN}🎉 MagFlow ERP data has been restored from backup: $backup_name${NC}"
    fi
}

# Run main function
main "$@"
