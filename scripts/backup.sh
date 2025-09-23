#!/bin/bash
# MagFlow ERP Database Backup Script
# This script creates backups of PostgreSQL and Redis data volumes

set -e

# Configuration
COMPOSE_FILE=${COMPOSE_FILE:-"docker-compose.simple.yml"}
BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="magflow_backup_${TIMESTAMP}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting MagFlow ERP Backup Process${NC}"
echo -e "${YELLOW}Timestamp: ${TIMESTAMP}${NC}"

# Create backup directory if it doesn't exist
mkdir -p "${BACKUP_DIR}"

# Function to create PostgreSQL backup
backup_postgresql() {
    echo -e "${YELLOW}📦 Creating PostgreSQL backup...${NC}"

    # Create database dump in custom format
    docker compose -f "${COMPOSE_FILE}" exec db pg_dump -U app -d magflow -Fc > "${BACKUP_DIR}/postgresql_${TIMESTAMP}.dump"
    echo -e "${GREEN}✅ PostgreSQL backup created: postgresql_${TIMESTAMP}.dump${NC}"
}

# Function to create Redis backup
backup_redis() {
    echo -e "${YELLOW}📦 Creating Redis backup...${NC}"

    # Get the timestamp of the last successful save
    local last_save_before
    last_save_before=$(docker compose -f "${COMPOSE_FILE}" exec redis redis-cli LASTSAVE)

    # Trigger a background save
    echo "  -> Triggering Redis BGSAVE..."
    docker compose -f "${COMPOSE_FILE}" exec redis redis-cli BGSAVE

    # Wait for the BGSAVE to complete by polling LASTSAVE
    echo "  -> Waiting for BGSAVE to complete..."
    while true; do
        local last_save_after
        last_save_after=$(docker compose -f "${COMPOSE_FILE}" exec redis redis-cli LASTSAVE)
        if [[ "$last_save_after" -gt "$last_save_before" ]]; then
            echo -e "  -> BGSAVE completed at timestamp ${last_save_after}"
            break
        fi
        echo "     ... still waiting"
        sleep 1
    done

    # Copy the RDB file from container
    docker cp "$(docker compose -f "${COMPOSE_FILE}" ps -q redis)":/data/dump.rdb "${BACKUP_DIR}/redis_${TIMESTAMP}.rdb"

    # Compress the backup
    gzip "${BACKUP_DIR}/redis_${TIMESTAMP}.rdb"
    echo -e "${GREEN}✅ Redis backup created: redis_${TIMESTAMP}.rdb.gz${NC}"
}

# Function to create volume backups
backup_volumes() {
    echo -e "${YELLOW}📦 Creating volume backups...${NC}"

    # Create tar archive of volumes
    docker run --rm \
        -v magflow_postgres_data:/postgres \
        -v magflow_redis_data:/redis \
        -v "${BACKUP_DIR}:/backup" \
        alpine tar czf "/backup/volumes_${TIMESTAMP}.tar.gz" -C / postgres redis

    echo -e "${GREEN}✅ Volume backup created: volumes_${TIMESTAMP}.tar.gz${NC}"
}

# Function to create backup manifest
create_manifest() {
    echo -e "${YELLOW}📝 Creating backup manifest...${NC}"

    cat > "${BACKUP_DIR}/manifest_${TIMESTAMP}.json" << EOF
{
    "backup_name": "${BACKUP_NAME}",
    "timestamp": "${TIMESTAMP}",
    "created_at": "$(date -Iseconds)",
    "version": "1.0.0",
    "services": {
        "postgresql": {
            "image": "postgres:16.4-alpine",
            "file": "postgresql_${TIMESTAMP}.dump",
            "size": "$(stat -f%z \"${BACKUP_DIR}/postgresql_${TIMESTAMP}.dump\" 2>/dev/null || echo '0')"
        },
        "redis": {
            "image": "redis:7.2.5-alpine",
            "file": "redis_${TIMESTAMP}.rdb.gz",
            "size": "$(stat -f%z "${BACKUP_DIR}/redis_${TIMESTAMP}.rdb.gz" 2>/dev/null || echo '0')"
        },
        "volumes": {
            "file": "volumes_${TIMESTAMP}.tar.gz",
            "size": "$(stat -f%z "${BACKUP_DIR}/volumes_${TIMESTAMP}.tar.gz" 2>/dev/null || echo '0')"
        }
    },
    "backup_script": "backup.sh",
    "notes": "Automated backup of MagFlow ERP data"
}
EOF

    echo -e "${GREEN}✅ Backup manifest created: manifest_${TIMESTAMP}.json${NC}"
}

# Function to cleanup old backups
cleanup_old_backups() {
    echo -e "${YELLOW}🧹 Cleaning up old backups (older than 7 days)...${NC}"

    # Find and delete files older than 7 days
    find "${BACKUP_DIR}" -type f \( -name "*.gz" -o -name "*.tar.gz" -o -name "*.json" \) -mtime +7 -print -delete

    echo -e "${GREEN}✅ Cleanup completed${NC}"
}

# Main backup process
main() {
    echo -e "${GREEN}🎯 Starting backup process...${NC}"

    # Check if containers are running
    if ! docker compose -f "${COMPOSE_FILE}" ps | grep -q "Up"; then
        echo -e "${RED}❌ Error: Docker containers are not running${NC}"
        exit 1
    fi

    # Create backups
    backup_postgresql
    backup_redis
    backup_volumes
    create_manifest

    # Cleanup old backups
    cleanup_old_backups

    # Calculate total backup size
    TOTAL_SIZE=$(du -sh "${BACKUP_DIR}" | cut -f1)
    echo -e "${GREEN}✅ Backup completed successfully!${NC}"
    echo -e "${GREEN}📊 Total backup size: ${TOTAL_SIZE}${NC}"
    echo -e "${GREEN}📁 Backup location: ${BACKUP_DIR}${NC}"
    echo -e "${GREEN}🎉 Backup process finished at $(date)${NC}"
}

# Run main function
main "$@"
