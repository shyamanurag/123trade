#!/bin/bash

# Health check script for the trading system
# This script checks the health of all components and services

set -e

# Configuration
API_URL="http://localhost:8000"
METRICS_URL="http://localhost:8001"
DB_HOST="localhost"
DB_PORT="5432"
REDIS_HOST="localhost"
REDIS_PORT="6379"
TIMEOUT=5
RETRIES=3

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if a port is open
check_port() {
    local host=$1
    local port=$2
    timeout $TIMEOUT bash -c "cat < /dev/null > /dev/tcp/$host/$port" 2>/dev/null
    return $?
}

# Function to check API health
check_api() {
    echo "Checking API health..."
    local response
    local status
    
    for ((i=1; i<=RETRIES; i++)); do
        response=$(curl -s -w "\n%{http_code}" "$API_URL/health")
        status=$(echo "$response" | tail -n1)
        
        if [ "$status" -eq 200 ]; then
            echo -e "${GREEN}API is healthy${NC}"
            return 0
        fi
        
        echo -e "${YELLOW}API check attempt $i failed, retrying...${NC}"
        sleep 1
    done
    
    echo -e "${RED}API is unhealthy${NC}"
    return 1
}

# Function to check metrics endpoint
check_metrics() {
    echo "Checking metrics endpoint..."
    local response
    local status
    
    for ((i=1; i<=RETRIES; i++)); do
        response=$(curl -s -w "\n%{http_code}" "$METRICS_URL/metrics")
        status=$(echo "$response" | tail -n1)
        
        if [ "$status" -eq 200 ]; then
            echo -e "${GREEN}Metrics endpoint is healthy${NC}"
            return 0
        fi
        
        echo -e "${YELLOW}Metrics check attempt $i failed, retrying...${NC}"
        sleep 1
    done
    
    echo -e "${RED}Metrics endpoint is unhealthy${NC}"
    return 1
}

# Function to check database connection
check_database() {
    echo "Checking database connection..."
    
    if ! command_exists psql; then
        echo -e "${RED}PostgreSQL client not found${NC}"
        return 1
    fi
    
    for ((i=1; i<=RETRIES; i++)); do
        if PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "SELECT 1" >/dev/null 2>&1; then
            echo -e "${GREEN}Database connection is healthy${NC}"
            return 0
        fi
        
        echo -e "${YELLOW}Database check attempt $i failed, retrying...${NC}"
        sleep 1
    done
    
    echo -e "${RED}Database connection is unhealthy${NC}"
    return 1
}

# Function to check Redis connection
check_redis() {
    echo "Checking Redis connection..."
    
    if ! command_exists redis-cli; then
        echo -e "${RED}Redis client not found${NC}"
        return 1
    fi
    
    for ((i=1; i<=RETRIES; i++)); do
        if redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD ping >/dev/null 2>&1; then
            echo -e "${GREEN}Redis connection is healthy${NC}"
            return 0
        fi
        
        echo -e "${YELLOW}Redis check attempt $i failed, retrying...${NC}"
        sleep 1
    done
    
    echo -e "${RED}Redis connection is unhealthy${NC}"
    return 1
}

# Function to check system resources
check_resources() {
    echo "Checking system resources..."
    
    # Check CPU usage
    local cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}')
    if (( $(echo "$cpu_usage > 80" | bc -l) )); then
        echo -e "${RED}High CPU usage: ${cpu_usage}%${NC}"
    else
        echo -e "${GREEN}CPU usage: ${cpu_usage}%${NC}"
    fi
    
    # Check memory usage
    local memory_usage=$(free | grep Mem | awk '{print $3/$2 * 100.0}')
    if (( $(echo "$memory_usage > 80" | bc -l) )); then
        echo -e "${RED}High memory usage: ${memory_usage}%${NC}"
    else
        echo -e "${GREEN}Memory usage: ${memory_usage}%${NC}"
    fi
    
    # Check disk usage
    local disk_usage=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
    if [ "$disk_usage" -gt 80 ]; then
        echo -e "${RED}High disk usage: ${disk_usage}%${NC}"
    else
        echo -e "${GREEN}Disk usage: ${disk_usage}%${NC}"
    fi
}

# Function to check log files
check_logs() {
    echo "Checking log files..."
    
    local log_dir="logs"
    if [ ! -d "$log_dir" ]; then
        echo -e "${RED}Log directory not found${NC}"
        return 1
    fi
    
    # Check for error logs in the last hour
    local error_count=$(find "$log_dir" -type f -name "*.log" -mmin -60 -exec grep -l "ERROR" {} \; | wc -l)
    if [ "$error_count" -gt 0 ]; then
        echo -e "${RED}Found $error_count log files with errors in the last hour${NC}"
    else
        echo -e "${GREEN}No recent errors found in logs${NC}"
    fi
}

# Main function
main() {
    echo "Starting health check..."
    
    # Check if required environment variables are set
    if [ -z "$DB_USER" ] || [ -z "$DB_PASSWORD" ] || [ -z "$DB_NAME" ] || [ -z "$REDIS_PASSWORD" ]; then
        echo -e "${RED}Required environment variables are not set${NC}"
        exit 1
    fi
    
    # Run all checks
    check_api
    check_metrics
    check_database
    check_redis
    check_resources
    check_logs
    
    echo "Health check completed"
}

# Run main function
main 