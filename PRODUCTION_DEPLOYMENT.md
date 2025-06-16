# 123trade Production Deployment Guide

## Table of Contents
1. [Introduction](#introduction)
2. [System Architecture](#system-architecture)
3. [Infrastructure Requirements](#infrastructure-requirements)
4. [Environment Setup](#environment-setup)
5. [Security Configuration](#security-configuration)
6. [Deployment Process](#deployment-process)
7. [Database Management](#database-management)
8. [Monitoring and Observability](#monitoring-and-observability)
9. [Backup and Disaster Recovery](#backup-and-disaster-recovery)
10. [Performance Optimization](#performance-optimization)
11. [Maintenance Procedures](#maintenance-procedures)
12. [Scaling Strategies](#scaling-strategies)
13. [Troubleshooting](#troubleshooting)
14. [Compliance and Auditing](#compliance-and-auditing)
15. [Appendices](#appendices)

## Introduction

This document provides comprehensive guidance for deploying and maintaining the 123trade application in a production environment. 123trade is a trading system that requires high reliability, security, and performance.

### Purpose and Scope
- Guide administrators through the deployment and operation of 123trade
- Establish best practices for security, reliability, and performance
- Provide reference for troubleshooting and maintenance procedures

### Important Considerations
- 123trade handles financial transactions and potentially sensitive user data
- Application requires real-time data processing and high availability
- Compliance with financial regulations may be required depending on deployment region

## System Architecture

### Component Overview

The 123trade system consists of the following core components:

- **Web API Backend**: FastAPI-based REST API service that handles client requests
- **Database Layer**: PostgreSQL database for persistent storage
- **Redis Cache**: For session management, rate limiting, and real-time data
- **Data Provider Integration**: Connects to TrueData and other market data sources
- **Trading Engine**: Core logic for executing trades and managing positions
- **Authentication Service**: Handles user authentication and authorization
- **Frontend Application**: React-based web interface for users

### Architecture Diagram

```
┌────────────┐     ┌─────────────┐     ┌───────────────┐
│  Frontend  │◄────┤ Load        │◄────┤ Web API       │
│  (React)   │     │ Balancer    │     │ (FastAPI)     │
└────────────┘     └─────────────┘     └───────┬───────┘
                                               │
                   ┌─────────────┐     ┌──────▼──────┐     ┌────────────┐
                   │ Redis Cache │◄────┤ Trading     │◄────┤ Data       │
                   │             │     │ Engine      │     │ Providers  │
                   └─────────────┘     └──────┬──────┘     └────────────┘
                                              │
                                        ┌─────▼─────┐
                                        │ PostgreSQL │
                                        │ Database   │
                                        └───────────┘
```

### Data Flow

1. Client requests come through the load balancer to the Web API
2. Authentication and rate limiting is applied at the API layer
3. Business logic is handled by the Trading Engine
4. Real-time market data flows from Data Providers to the Trading Engine
5. Persistent data is stored in PostgreSQL
6. Redis is used for caching, session management, and real-time communication

## Infrastructure Requirements

### Hardware Recommendations

#### Production Environment

| Component | Minimum Specs | Recommended Specs |
|-----------|---------------|-------------------|
| API Server | 4 vCPUs, 8GB RAM | 8+ vCPUs, 16GB RAM |
| Database Server | 4 vCPUs, 16GB RAM | 8+ vCPUs, 32GB RAM |
| Redis Server | 2 vCPUs, 4GB RAM | 4 vCPUs, 8GB RAM |
| Storage | 100GB SSD | 500GB+ SSD |

#### High Availability Configuration

- Minimum of 2 API server instances behind a load balancer
- Database with replication (primary and at least one standby)
- Redis in cluster mode with persistence

### Cloud Provider Recommendations

123trade can be deployed on any major cloud provider:

- **AWS**: EC2 or ECS for application, RDS for PostgreSQL, ElastiCache for Redis
- **Azure**: App Service or AKS for application, Azure Database for PostgreSQL, Azure Cache for Redis
- **GCP**: GCE or GKE for application, Cloud SQL for PostgreSQL, Memorystore for Redis
- **DigitalOcean**: Droplets or App Platform, managed PostgreSQL and Redis

### Network Requirements

- All internal communication should be on private networks
- API endpoints exposed via HTTPS only
- Database access restricted to application servers only
- Redis configured with authentication and TLS

## Environment Setup

### Environment Variables

The application uses environment variables for configuration. Create a proper `.env` file based on the provided `.env.example`:

```bash
# Core application settings
APP_VERSION=1.0.0
ENVIRONMENT=production
DEBUG=False
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE=/var/log/123trade/app.log

# API settings
HOST=0.0.0.0
PORT=8000
DOMAIN=api.example.com
ALLOWED_ORIGINS=https://app.example.com,https://admin.example.com
API_WORKERS=4

# Security settings
SECRET_KEY=generate_a_secure_random_key_here
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7
PASSWORD_SALT=generate_another_secure_random_string
ENABLE_HTTPS=true
CORS_ALLOW_ORIGINS=https://app.example.com

# Database settings
DATABASE_URL=postgresql://username:password@db-host:5432/dbname?sslmode=require
DATABASE_MAX_CONNECTIONS=50
DB_MIN_CONNECTIONS=5
DB_MAX_CONNECTIONS=20
DB_COMMAND_TIMEOUT=15
DB_CONNECT_TIMEOUT=10
DB_MAX_RETRIES=5
DB_RETRY_DELAY=5

# Redis settings
REDIS_HOST=redis-host
REDIS_PORT=6379
REDIS_PASSWORD=secure_redis_password
REDIS_DB=0
REDIS_USE_SSL=true

# Rate limiting
RATE_LIMIT=120
RATE_LIMIT_PERIOD=60
RATE_LIMIT_BURST_MULTIPLIER=2.0
RATE_LIMIT_BLOCK_DURATION=300

# TrueData API credentials
TRUEDATA_USERNAME=your_username
TRUEDATA_PASSWORD=your_password
TRUEDATA_API_URL=https://api.truedata.in/

# Zerodha credentials
ZERODHA_API_KEY=your_zerodha_api_key
ZERODHA_API_SECRET=your_zerodha_api_secret
```

### Directory Structure and Permissions

```
/opt/123trade/            # Application root directory
  ├── app/                # Application code
  ├── logs/               # Application logs
  ├── data/               # Data files
  ├── static/             # Static files
  └── .env                # Environment configuration
  
/etc/123trade/           # Configuration files
/var/log/123trade/       # Log files
/var/lib/123trade/       # Data files
```

**File Permissions:**

```bash
# Directory ownership
chown -R 123trade:123trade /opt/123trade
chown -R 123trade:123trade /var/log/123trade
chown -R 123trade:123trade /var/lib/123trade

# Set restrictive permissions
chmod 750 /opt/123trade
chmod 640 /opt/123trade/.env
chmod -R 640 /etc/123trade/*
```

### Operating System Recommendations

- Linux-based OS (Ubuntu Server 22.04 LTS or later recommended)
- Keep OS up to date with security patches
- Minimal installation with only required packages
- Configured firewall (UFW or iptables)
- SSH with key-based authentication only

## Security Configuration

### API Security

1. **Authentication & Authorization**
   - JWT-based authentication with proper expiration
   - Role-based access control
   - OAuth2 implementation for third-party integrations

2. **API Protection**
   - Implement rate limiting to prevent abuse
   - Use HTTPS only (TLS 1.3 preferred)
   - API key authentication for internal services
   - Apply input validation for all endpoints

3. **Headers & Cookies**
   - Set secure headers:
     ```
     X-Content-Type-Options: nosniff
     X-Frame-Options: DENY
     X-XSS-Protection: 1; mode=block
     Content-Security-Policy: default-src 'self'
     Strict-Transport-Security: max-age=31536000; includeSubDomains
     ```
   - Use secure cookies:
     ```
     Set-Cookie: session=123; Secure; HttpOnly; SameSite=Strict
     ```

### Database Security

1. **Connection Security**
   - Use TLS for all database connections
   - Implement connection pooling with proper sizing
   - Restrict database user permissions (least privilege)

2. **Data Protection**
   - Encrypt sensitive data at rest
   - Use parameterized queries to prevent SQL injection
   - Implement proper error handling to prevent information leakage

3. **Access Control**
   - Separate database accounts for different roles
   - Regular auditing of database access
   - Network-level restrictions (firewall, security groups)

### Redis Security

1. **Protection Measures**
   - Enable Redis authentication
   - Configure TLS for Redis connections
   - Disable dangerous commands in production
   - Bind to localhost or private network only

### Networking Security

1. **Firewall Rules**
   ```
   # Sample UFW rules
   ufw default deny incoming
   ufw default allow outgoing
   ufw allow ssh
   ufw allow 80/tcp
   ufw allow 443/tcp
   ufw enable
   ```

2. **TLS Configuration**
   - Use minimum TLS 1.2, preferably TLS 1.3
   - Strong cipher suites only
   - Regular certificate rotation
   - Use Let's Encrypt for free certificates

## Deployment Process

### Containerization with Docker

1. **Building Images**

   ```bash
   # Build the application image
   docker build -t 123trade-api:$(git rev-parse --short HEAD) -f Dockerfile .
   
   # Tag as latest
   docker tag 123trade-api:$(git rev-parse --short HEAD) 123trade-api:latest
   ```

2. **Docker Compose Setup**

   Create a `docker-compose.yml` file:

   ```yaml
   version: '3.8'
   
   services:
     api:
       image: 123trade-api:latest
       restart: always
       depends_on:
         - db
         - redis
       env_file: .env
       ports:
         - "8000:8000"
       volumes:
         - ./logs:/app/logs
       networks:
         - app_network
       deploy:
         replicas: 2
         update_config:
           parallelism: 1
           delay: 10s
         restart_policy:
           condition: on-failure
   
     db:
       image: postgres:14-alpine
       restart: always
       environment:
         - POSTGRES_USER=${DB_USER}
         - POSTGRES_PASSWORD=${DB_PASSWORD}
         - POSTGRES_DB=${DB_NAME}
       volumes:
         - postgres_data:/var/lib/postgresql/data
       networks:
         - app_network
       ports:
         - "5432:5432"
   
     redis:
       image: redis:7-alpine
       command: redis-server --requirepass ${REDIS_PASSWORD}
       restart: always
       volumes:
         - redis_data:/data
       networks:
         - app_network
       ports:
         - "6379:6379"
   
   volumes:
     postgres_data:
     redis_data:
   
   networks:
     app_network:
       driver: bridge
   ```

3. **Deployment Scripts**

   Create a deployment script `deploy.sh`:

   ```bash
   #!/bin/bash
   set -e
   
   # Pull latest code
   git pull origin main
   
   # Build new image
   docker build -t 123trade-api:$(git rev-parse --short HEAD) .
   docker tag 123trade-api:$(git rev-parse --short HEAD) 123trade-api:latest
   
   # Stop and remove existing containers
   docker-compose down
   
   # Start new containers
   docker-compose up -d
   
   # Verify deployment
   docker-compose ps
   curl -s http://localhost:8000/health | grep -q '"status":"healthy"' && echo "Deployment successful" || echo "Deployment failed"
   ```

### Kubernetes Deployment

For larger deployments, Kubernetes is recommended:

1. **Kubernetes Manifests**

   Create namespace:
   ```yaml
   apiVersion: v1
   kind: Namespace
   metadata:
     name: 123trade
   ```

   API deployment:
   ```yaml
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: api
     namespace: 123trade
   spec:
     replicas: 3
     selector:
       matchLabels:
         app: api
     template:
       metadata:
         labels:
           app: api
       spec:
         containers:
         - name: api
           image: 123trade-api:latest
           ports:
           - containerPort: 8000
           envFrom:
           - secretRef:
               name: api-secrets
           - configMapRef:
               name: api-config
           livenessProbe:
             httpGet:
               path: /health/liveness
               port: 8000
             initialDelaySeconds: 30
             periodSeconds: 10
           readinessProbe:
             httpGet:
               path: /health/readiness
               port: 8000
             initialDelaySeconds: 5
             periodSeconds: 10
           resources:
             limits:
               cpu: "1"
               memory: "1Gi"
             requests:
               cpu: "500m"
               memory: "512Mi"
   ```

2. **Continuous Deployment with GitOps**

   Using tools like ArgoCD or Flux:
   - Store Kubernetes manifests in Git
   - ArgoCD watches repository for changes
   - Changes are automatically applied to the cluster

## Database Management

### Initialization and Migrations

1. **Database Setup**

   ```bash
   # Create database if it doesn't exist
   psql -U postgres -c "CREATE DATABASE tradingdb;"
   psql -U postgres -c "CREATE USER trading_user WITH ENCRYPTED PASSWORD 'secure_password';"
   psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE tradingdb TO trading_user;"
   ```

2. **Migration Process**

   The application uses Alembic for migrations:

   ```bash
   # Generate new migration
   alembic revision --autogenerate -m "description"
   
   # Apply migrations
   alembic upgrade head
   ```

3. **Database Backup**

   Scheduled backup script:

   ```bash
   #!/bin/bash
   # Set variables
   DB_NAME="tradingdb"
   BACKUP_DIR="/var/backups/postgres"
   TIMESTAMP=$(date +%Y%m%d_%H%M%S)
   BACKUP_FILE="${BACKUP_DIR}/${DB_NAME}_${TIMESTAMP}.sql"
   
   # Create backup directory if it doesn't exist
   mkdir -p $BACKUP_DIR
   
   # Create backup
   pg_dump -U postgres -d $DB_NAME -f $BACKUP_FILE
   
   # Compress the backup
   gzip $BACKUP_FILE
   
   # Remove backups older than 30 days
   find $BACKUP_DIR -name "*.sql.gz" -type f -mtime +30 -delete
   ```

### Performance Tuning

1. **PostgreSQL Configuration**

   Key settings for `postgresql.conf`:

   ```
   # Memory Configuration
   shared_buffers = 4GB                   # 25% of RAM for dedicated server
   effective_cache_size = 12GB            # 75% of RAM for dedicated server
   work_mem = 64MB                        # Depends on max_connections
   maintenance_work_mem = 512MB           # For maintenance operations
   
   # Write Ahead Log
   wal_buffers = 16MB
   checkpoint_timeout = 15min
   checkpoint_completion_target = 0.9
   
   # Query Optimization
   random_page_cost = 1.1                 # For SSD storage
   effective_io_concurrency = 200         # For SSD storage
   parallel_workers_per_gather = 4        # Based on CPU cores
   
   # Monitoring
   track_activities = on
   track_counts = on
   track_io_timing = on
   track_functions = all
   log_min_duration_statement = 100       # Log slow queries (>100ms)
   ```

2. **Connection Pooling**

   Configure PgBouncer for connection pooling:

   ```ini
   # pgbouncer.ini
   [databases]
   tradingdb = host=127.0.0.1 port=5432 dbname=tradingdb
   
   [pgbouncer]
   listen_addr = *
   listen_port = 6432
   auth_type = md5
   auth_file = /etc/pgbouncer/userlist.txt
   pool_mode = transaction
   max_client_conn = 1000
   default_pool_size = 20
   min_pool_size = 10
   reserve_pool_size = 5
   reserve_pool_timeout = 3
   log_connections = 1
   log_disconnections = 1
   ```

## Monitoring and Observability

### Logging Configuration

1. **Application Logging**

   Configure structured JSON logging:

   ```python
   # Configure logging in main.py
   setup_logging(
       level="INFO" if not config.debug else "DEBUG",
       log_format="json" if config.environment == "production" else "text",
       log_file=config.log_file
   )
   ```

2. **Log Rotation**

   Configure logrotate:

   ```
   # /etc/logrotate.d/123trade
   /var/log/123trade/*.log {
       daily
       missingok
       rotate 14
       compress
       delaycompress
       notifempty
       create 0640 123trade 123trade
       sharedscripts
       postrotate
           systemctl kill -s USR1 123trade.service
       endscript
   }
   ```

### Metrics Collection

1. **Prometheus Integration**

   The application exposes metrics at the `/health/metrics` endpoint in Prometheus format.

   Sample Prometheus configuration:

   ```yaml
   # prometheus.yml
   scrape_configs:
     - job_name: '123trade'
       scrape_interval: 10s
       metrics_path: '/health/metrics'
       static_configs:
         - targets: ['api:8000']
   ```

2. **Key Metrics to Monitor**

   - Application metrics:
     - Request rate, latency, and error rate
     - Endpoint-specific metrics
     - Authentication success/failure rate
     - Trading operation metrics

   - System metrics:
     - CPU, memory, disk usage
     - Network I/O
     - Connection counts

   - Database metrics:
     - Query performance
     - Connection pool utilization
     - Transaction rate
     - Table and index sizes

### Alerting Setup

1. **Alertmanager Configuration**

   ```yaml
   # alertmanager.yml
   route:
     group_by: ['job', 'severity']
     group_wait: 30s
     group_interval: 5m
     repeat_interval: 4h
     receiver: 'email-alerts'
   receivers:
     - name: 'email-alerts'
       email_configs:
         - to: 'alerts@example.com'
           from: 'prometheus@example.com'
           smarthost: 'smtp.example.com:587'
           auth_username: 'prometheus@example.com'
           auth_password: 'password'
           send_resolved: true
   ```

2. **Alert Rules**

   ```yaml
   # alerts.yml
   groups:
     - name: 123trade-alerts
       rules:
       # High error rate
       - alert: HighErrorRate
         expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.05
         for: 5m
         labels:
           severity: critical
         annotations:
           summary: "High error rate detected"
           description: "Error rate is {{ $value | humanizePercentage }} for the past 5 minutes"
       
       # API latency alert
       - alert: HighAPILatency
         expr: http_request_duration_seconds{quantile="0.95"} > 1
         for: 5m
         labels:
           severity: warning
         annotations:
           summary: "High API latency detected"
           description: "95th percentile latency is {{ $value }}s for endpoint {{ $labels.endpoint }}"
       
       # Database connection pool alert
       - alert: DatabaseConnectionPoolSaturation
         expr: database_connection_pool_usage > 0.9
         for: 5m
         labels:
           severity: warning
         annotations:
           summary: "Database connection pool nearly full"
           description: "Connection pool usage at {{ $value | humanizePercentage }}"
   ```

### Dashboards

Configure Grafana dashboards for visualization:

1. **System Overview Dashboard**
   - CPU, memory, disk usage over time
   - Network I/O
   - Request rate and error rate

2. **API Performance Dashboard**
   - Request latency by endpoint
   - Error rate by endpoint
   - Authentication success/failure
   - Rate limiting metrics

3. **Database Performance Dashboard**
   - Query execution time
   - Connection pool utilization
   - Transaction rate
   - Replication lag (for replicated setups)

## Backup and Disaster Recovery

### Backup Strategy

1. **Database Backups**
   - Full daily backups using `pg_dump`
   - Point-in-time recovery using WAL archiving
   - Retention policy: 30 daily, 12 monthly, 2 yearly

2. **Application Data**
   - Regular backups of application data directory
   - Configuration file backups
   - Secrets backup (encrypted)

3. **Backup Storage**
   - Off-site storage (cloud storage bucket)
   - Encrypted backup files
   - Regular backup testing

### Disaster Recovery Plan

1. **Recovery Procedures**

   Database restore:
   ```bash
   # Restore from backup
   gunzip -c /path/to/backup.sql.gz | psql -U postgres -d tradingdb
   
   # Apply any missing WAL files
   pg_wal_replay_resume()
   ```

2. **Failover Procedures**

   For replicated setups:
   ```bash
   # Promote standby to primary
   pg_ctl promote -D /path/to/data_directory
   
   # Update connection strings in application config
   sed -i 's/old-primary/new-primary/' /opt/123trade/.env
   
   # Restart application services
   systemctl restart 123trade
   ```

3. **Recovery Time Objectives (RTO)**
   - Database recovery: < 1 hour
   - Full application recovery: < 4 hours
   - Complete infrastructure rebuild: < 24 hours

## Performance Optimization

### Application Tuning

1. **FastAPI Performance**
   - Use appropriate worker count (2 × CPU cores + 1)
   - Enable Uvicorn workers for better performance
   - Configure connection keep-alive

2. **Caching Strategy**
   - Use Redis for frequent queries
   - Cache market data for specified periods
   - Implement cache invalidation strategy

3. **Database Query Optimization**
   - Create proper indexes for common queries
   - Regular ANALYZE and VACUUM
   - Partition large tables

## Maintenance Procedures

### Routine Maintenance

1. **System Updates**

   ```bash
   # Update OS packages
   apt update && apt upgrade -y
   
   # Restart services if needed
   systemctl restart 123trade
   ```

2. **Database Maintenance**

   ```bash
   # Run VACUUM ANALYZE
   psql -U postgres -d tradingdb -c "VACUUM ANALYZE;"
   
   # Check for bloated tables
   psql -U postgres -d tradingdb -f /opt/123trade/scripts/check_bloat.sql
   ```

3. **Log Management**

   ```bash
   # Check log sizes
   du -sh /var/log/123trade/
   
   # Manually rotate logs if needed
   logrotate -f /etc/logrotate.d/123trade
   ```

### Upgrade Procedures

1. **Application Upgrade**

   ```bash
   # Pull latest code
   cd /opt/123trade
   git pull
   
   # Create backup
   tar -czf /var/backups/123trade_$(date +%Y%m%d).tar.gz /opt/123trade
   
   # Install dependencies
   pip install -r requirements.txt
   
   # Run database migrations
   alembic upgrade head
   
   # Restart service
   systemctl restart 123trade
   ```

2. **Database Upgrade**

   ```bash
   # Backup current database
   pg_dump -U postgres -d tradingdb -f /var/backups/tradingdb_before_upgrade.sql
   
   # Stop application
   systemctl stop 123trade
   
   # Upgrade PostgreSQL
   # (follow PostgreSQL-specific upgrade procedure)
   
   # Start application
   systemctl start 123trade
   ```

## Scaling Strategies

### Horizontal Scaling

1. **API Layer Scaling**
   - Add more API server instances
   - Distribute traffic with a load balancer
   - Use sticky sessions for WebSocket connections

2. **Database Scaling**
   - Read replicas for read-heavy workloads
   - Sharding for very large datasets
   - Connection pooling to manage connection load

### Vertical Scaling

1. **Resource Allocation**
   - Increase CPU and memory for API servers
   - Optimize database server resources
   - Tune Redis memory settings

## Troubleshooting

### Common Issues

1. **API Server Issues**

   - High response times:
     - Check database query performance
     - Check CPU and memory usage
     - Review application logs for slow operations

   - Connection errors:
     - Check network connectivity
     - Verify firewall rules
     - Check service status

2. **Database Issues**

   - Connection pool exhaustion:
     - Check for connection leaks
     - Adjust pool settings
     - Review long-running transactions

   - Slow queries:
     - Check for missing indexes
     - Review query plans with EXPLAIN ANALYZE
     - Check for table bloat

### Debugging Procedures

1. **Log Analysis**

   ```bash
   # Search for errors
   grep -i error /var/log/123trade/app.log
   
   # Search for specific user or transaction
   grep -i "user_id=123" /var/log/123trade/app.log
   ```

2. **Process Monitoring**

   ```bash
   # Check process status
   systemctl status 123trade
   
   # Check resource usage
   top -c -p $(pgrep -d',' -f "uvicorn")
   ```

3. **Network Diagnostics**

   ```bash
   # Check network connections
   netstat -tunapl | grep 8000
   
   # Check connection to database
   nc -zv db-host 5432
   ```

## Compliance and Auditing

### Security Auditing

1. **Access Logging**
   - Log all administrative actions
   - Maintain authentication logs
   - Record API access patterns

2. **Vulnerability Scanning**
   - Regular security scans
   - Dependency vulnerability checks
   - Code security reviews

### Regulatory Compliance

1. **Data Protection**
   - GDPR compliance checklist
   - Secure data handling procedures
   - Data retention policies

2. **Financial Regulations**
   - Market data usage compliance
   - Trading activity logs for audit
   - Transaction recording

## Appendices

### Reference Documentation

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Redis Documentation](https://redis.io/documentation)
- [Docker Documentation](https://docs.docker.com/)
- [Prometheus Documentation](https://prometheus.io/docs/introduction/overview/)

### Sample Configuration Files

- `nginx.conf` - Web server configuration
- `systemd.service` - Service unit file
- `pgbouncer.ini` - Connection pooling config
- `prometheus.yml` - Monitoring configuration

### Contact Information

- Development Team: dev@example.com
- Operations Team: ops@example.com
- Security Team: security@example.com
- Emergency Contact: +1 (555) 123-4567
