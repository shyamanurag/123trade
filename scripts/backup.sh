#!/bin/bash

# Backup script for the trading system
# This script creates backups of the database, Redis data, and configuration files

set -e

# Configuration
BACKUP_DIR="backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_PATH="$BACKUP_DIR/$TIMESTAMP"
RETENTION_DAYS=7
COMPRESS=true

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to create backup directory
create_backup_dir() {
    echo "Creating backup directory..."
    mkdir -p "$BACKUP_PATH"
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Backup directory created: $BACKUP_PATH${NC}"
    else
        echo -e "${RED}Failed to create backup directory${NC}"
        exit 1
    fi
}

# Function to backup PostgreSQL database
backup_database() {
    echo "Backing up PostgreSQL database..."
    
    if ! command_exists pg_dump; then
        echo -e "${RED}PostgreSQL client not found${NC}"
        return 1
    fi
    
    local db_backup_file="$BACKUP_PATH/database.sql"
    if PGPASSWORD=$DB_PASSWORD pg_dump -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -F c -f "$db_backup_file"; then
        echo -e "${GREEN}Database backup created: $db_backup_file${NC}"
    else
        echo -e "${RED}Database backup failed${NC}"
        return 1
    fi
}

# Function to backup Redis data
backup_redis() {
    echo "Backing up Redis data..."
    
    if ! command_exists redis-cli; then
        echo -e "${RED}Redis client not found${NC}"
        return 1
    fi
    
    local redis_backup_file="$BACKUP_PATH/redis.rdb"
    if redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD SAVE && \
       redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD --rdb "$redis_backup_file"; then
        echo -e "${GREEN}Redis backup created: $redis_backup_file${NC}"
    else
        echo -e "${RED}Redis backup failed${NC}"
        return 1
    fi
}

# Function to backup configuration files
backup_config() {
    echo "Backing up configuration files..."
    
    local config_dir="$BACKUP_PATH/config"
    mkdir -p "$config_dir"
    
    # Backup environment files
    if [ -f ".env" ]; then
        cp .env "$config_dir/"
    fi
    
    # Backup Kubernetes configurations
    if [ -d "k8s" ]; then
        cp -r k8s "$config_dir/"
    fi
    
    # Backup Docker configurations
    if [ -d "docker" ]; then
        cp -r docker "$config_dir/"
    fi
    
    echo -e "${GREEN}Configuration files backed up to: $config_dir${NC}"
}

# Function to backup logs
backup_logs() {
    echo "Backing up logs..."
    
    local logs_dir="$BACKUP_PATH/logs"
    mkdir -p "$logs_dir"
    
    if [ -d "logs" ]; then
        cp -r logs/* "$logs_dir/"
        echo -e "${GREEN}Logs backed up to: $logs_dir${NC}"
    else
        echo -e "${YELLOW}No logs directory found${NC}"
    fi
}

# Function to compress backup
compress_backup() {
    if [ "$COMPRESS" = true ]; then
        echo "Compressing backup..."
        local archive_name="$BACKUP_PATH.tar.gz"
        if tar -czf "$archive_name" -C "$BACKUP_DIR" "$TIMESTAMP"; then
            echo -e "${GREEN}Backup compressed: $archive_name${NC}"
            rm -rf "$BACKUP_PATH"
        else
            echo -e "${RED}Backup compression failed${NC}"
            return 1
        fi
    fi
}

# Function to clean up old backups
cleanup_old_backups() {
    echo "Cleaning up old backups..."
    
    if [ -d "$BACKUP_DIR" ]; then
        find "$BACKUP_DIR" -type f -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete
        find "$BACKUP_DIR" -type d -mtime +$RETENTION_DAYS -delete
        echo -e "${GREEN}Old backups cleaned up${NC}"
    fi
}

# Function to verify backup
verify_backup() {
    echo "Verifying backup..."
    
    local backup_file="$BACKUP_PATH.tar.gz"
    if [ -f "$backup_file" ]; then
        if tar -tzf "$backup_file" >/dev/null; then
            echo -e "${GREEN}Backup verification successful${NC}"
        else
            echo -e "${RED}Backup verification failed${NC}"
            return 1
        fi
    else
        echo -e "${RED}Backup file not found${NC}"
        return 1
    fi
}

# Main function
main() {
    echo "Starting backup process..."
    
    # Check if required environment variables are set
    if [ -z "$DB_USER" ] || [ -z "$DB_PASSWORD" ] || [ -z "$DB_NAME" ] || [ -z "$REDIS_PASSWORD" ]; then
        echo -e "${RED}Required environment variables are not set${NC}"
        exit 1
    fi
    
    # Create backup directory
    create_backup_dir
    
    # Perform backups
    backup_database
    backup_redis
    backup_config
    backup_logs
    
    # Compress backup
    compress_backup
    
    # Verify backup
    verify_backup
    
    # Clean up old backups
    cleanup_old_backups
    
    echo "Backup process completed successfully"
}

# Run main function
main 