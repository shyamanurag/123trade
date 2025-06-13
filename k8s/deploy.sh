#!/bin/bash

set -e

# Load environment variables
if [ -f .env ]; then
    source .env
fi

# Check if kubectl is installed
if ! command -v kubectl &> /dev/null; then
    echo "Error: kubectl is not installed"
    exit 1
fi

# Function to check if a namespace exists
namespace_exists() {
    kubectl get namespace "$1" &> /dev/null
}

# Function to check if a deployment is ready
deployment_ready() {
    local namespace=$1
    local deployment=$2
    kubectl rollout status deployment/$deployment -n $namespace
}

# Function to backup data
backup_data() {
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_dir="backups/$timestamp"
    
    echo "Creating backup at $backup_dir"
    mkdir -p "$backup_dir"
    
    # Backup PostgreSQL data
    kubectl exec -n trading-system deploy/trading-db -- pg_dump -U $DB_USER $DB_NAME > "$backup_dir/db_backup.sql"
    
    # Backup Redis data
    kubectl exec -n trading-system deploy/trading-redis -- redis-cli SAVE
    kubectl cp trading-system/trading-redis:/data/dump.rdb "$backup_dir/redis_backup.rdb"
    
    echo "Backup completed successfully"
}

# Function to restore data
restore_data() {
    local backup_dir=$1
    
    if [ ! -d "$backup_dir" ]; then
        echo "Error: Backup directory $backup_dir does not exist"
        exit 1
    }
    
    echo "Restoring data from $backup_dir"
    
    # Restore PostgreSQL data
    kubectl cp "$backup_dir/db_backup.sql" trading-system/trading-db:/tmp/
    kubectl exec -n trading-system deploy/trading-db -- psql -U $DB_USER $DB_NAME -f /tmp/db_backup.sql
    
    # Restore Redis data
    kubectl cp "$backup_dir/redis_backup.rdb" trading-system/trading-redis:/data/
    kubectl exec -n trading-system deploy/trading-redis -- redis-cli BGREWRITEAOF
    
    echo "Restore completed successfully"
}

# Function to deploy the application
deploy() {
    echo "Deploying trading system to Kubernetes..."
    
    # Create namespace if it doesn't exist
    if ! namespace_exists trading-system; then
        echo "Creating trading-system namespace..."
        kubectl apply -f namespace.yaml
    fi
    
    # Apply configurations in order
    echo "Applying configurations..."
    kubectl apply -f configmap.yaml
    kubectl apply -f secrets.yaml
    kubectl apply -f pvc.yaml
    kubectl apply -f services.yaml
    kubectl apply -f deployment.yaml
    kubectl apply -f ingress.yaml
    
    # Wait for deployments to be ready
    echo "Waiting for deployments to be ready..."
    deployment_ready trading-system trading-system
    deployment_ready trading-system trading-db
    deployment_ready trading-system trading-redis
    deployment_ready trading-system prometheus
    deployment_ready trading-system grafana
    
    echo "Deployment completed successfully"
}

# Function to rollback to a previous version
rollback() {
    local version=$1
    
    echo "Rolling back to version $version..."
    kubectl rollout undo deployment/trading-system -n trading-system --to-revision=$version
    
    echo "Rollback completed successfully"
}

# Main script
case "$1" in
    "deploy")
        deploy
        ;;
    "rollback")
        if [ -z "$2" ]; then
            echo "Error: Version number required for rollback"
            exit 1
        fi
        rollback "$2"
        ;;
    "backup")
        backup_data
        ;;
    "restore")
        if [ -z "$2" ]; then
            echo "Error: Backup directory required for restore"
            exit 1
        fi
        restore_data "$2"
        ;;
    *)
        echo "Usage: $0 {deploy|rollback|backup|restore}"
        exit 1
        ;;
esac 