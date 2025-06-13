#!/bin/bash

# Restore script for the trading system
# This script restores the system from a backup

set -e

# Configuration
BACKUP_DIR="backups"
RESTORE_DIR="restore_temp"
VERIFY=true

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to verify backup file
verify_backup() {
    local backup_file=$1
    echo "Verifying backup file..."
    
    if [ ! -f "$backup_file" ]; then
        echo -e "${RED}Backup file not found: $backup_file${NC}"
        return 1
    fi
    
    if ! tar -tzf "$backup_file" >/dev/null; then
        echo -e "${RED}Invalid backup file${NC}"
        return 1
    fi
    
    echo -e "${GREEN}Backup file verified${NC}"
    return 0
}

# Function to extract backup
extract_backup() {
    local backup_file=$1
    echo "Extracting backup..."
    
    mkdir -p "$RESTORE_DIR"
    if ! tar -xzf "$backup_file" -C "$RESTORE_DIR"; then
        echo -e "${RED}Failed to extract backup${NC}"
        return 1
    fi
    
    echo -e "${GREEN}Backup extracted to: $RESTORE_DIR${NC}"
    return 0
}

# Function to restore database
restore_database() {
    echo "Restoring database..."
    
    if ! command_exists pg_restore; then
        echo -e "${RED}PostgreSQL client not found${NC}"
        return 1
    fi
    
    local db_backup_file="$RESTORE_DIR/database.sql"
    if [ ! -f "$db_backup_file" ]; then
        echo -e "${RED}Database backup file not found${NC}"
        return 1
    fi
    
    # Drop existing database and create new one
    PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -c "DROP DATABASE IF EXISTS $DB_NAME;"
    PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -c "CREATE DATABASE $DB_NAME;"
    
    # Restore database
    if PGPASSWORD=$DB_PASSWORD pg_restore -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME "$db_backup_file"; then
        echo -e "${GREEN}Database restored successfully${NC}"
    else
        echo -e "${RED}Database restore failed${NC}"
        return 1
    fi
}

# Function to restore Redis data
restore_redis() {
    echo "Restoring Redis data..."
    
    if ! command_exists redis-cli; then
        echo -e "${RED}Redis client not found${NC}"
        return 1
    fi
    
    local redis_backup_file="$RESTORE_DIR/redis.rdb"
    if [ ! -f "$redis_backup_file" ]; then
        echo -e "${RED}Redis backup file not found${NC}"
        return 1
    fi
    
    # Stop Redis server
    redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD SHUTDOWN SAVE
    
    # Copy backup file to Redis data directory
    if cp "$redis_backup_file" "$REDIS_DATA_DIR/dump.rdb"; then
        echo -e "${GREEN}Redis data restored successfully${NC}"
    else
        echo -e "${RED}Redis data restore failed${NC}"
        return 1
    fi
    
    # Start Redis server
    systemctl start redis
}

# Function to restore configuration files
restore_config() {
    echo "Restoring configuration files..."
    
    local config_dir="$RESTORE_DIR/config"
    if [ ! -d "$config_dir" ]; then
        echo -e "${RED}Configuration backup directory not found${NC}"
        return 1
    fi
    
    # Restore environment files
    if [ -f "$config_dir/.env" ]; then
        cp "$config_dir/.env" .
        echo -e "${GREEN}Environment file restored${NC}"
    fi
    
    # Restore Kubernetes configurations
    if [ -d "$config_dir/k8s" ]; then
        cp -r "$config_dir/k8s" .
        echo -e "${GREEN}Kubernetes configurations restored${NC}"
    fi
    
    # Restore Docker configurations
    if [ -d "$config_dir/docker" ]; then
        cp -r "$config_dir/docker" .
        echo -e "${GREEN}Docker configurations restored${NC}"
    fi
}

# Function to restore logs
restore_logs() {
    echo "Restoring logs..."
    
    local logs_dir="$RESTORE_DIR/logs"
    if [ ! -d "$logs_dir" ]; then
        echo -e "${YELLOW}Logs backup directory not found${NC}"
        return 0
    fi
    
    mkdir -p logs
    cp -r "$logs_dir"/* logs/
    echo -e "${GREEN}Logs restored${NC}"
}

# Function to verify restore
verify_restore() {
    echo "Verifying restore..."
    
    # Verify database
    if ! PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "SELECT 1" >/dev/null 2>&1; then
        echo -e "${RED}Database verification failed${NC}"
        return 1
    fi
    
    # Verify Redis
    if ! redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD ping >/dev/null 2>&1; then
        echo -e "${RED}Redis verification failed${NC}"
        return 1
    fi
    
    echo -e "${GREEN}Restore verification successful${NC}"
    return 0
}

# Function to cleanup
cleanup() {
    echo "Cleaning up..."
    rm -rf "$RESTORE_DIR"
    echo -e "${GREEN}Cleanup completed${NC}"
}

# Main function
main() {
    if [ $# -ne 1 ]; then
        echo "Usage: $0 <backup_file>"
        exit 1
    fi
    
    local backup_file=$1
    
    echo "Starting restore process..."
    
    # Check if required environment variables are set
    if [ -z "$DB_USER" ] || [ -z "$DB_PASSWORD" ] || [ -z "$DB_NAME" ] || [ -z "$REDIS_PASSWORD" ] || [ -z "$REDIS_DATA_DIR" ]; then
        echo -e "${RED}Required environment variables are not set${NC}"
        exit 1
    fi
    
    # Verify backup
    if [ "$VERIFY" = true ]; then
        verify_backup "$backup_file" || exit 1
    fi
    
    # Extract backup
    extract_backup "$backup_file" || exit 1
    
    # Perform restore
    restore_database || exit 1
    restore_redis || exit 1
    restore_config || exit 1
    restore_logs || exit 1
    
    # Verify restore
    if [ "$VERIFY" = true ]; then
        verify_restore || exit 1
    fi
    
    # Cleanup
    cleanup
    
    echo "Restore process completed successfully"
}

# Run main function
main "$@" 