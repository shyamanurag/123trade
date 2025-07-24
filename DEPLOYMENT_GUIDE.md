# 🚀 Production Deployment Guide
## Quantum Crypto Trading System v2.0

This guide provides step-by-step instructions for deploying the enhanced trading system to production.

## 📋 Pre-Deployment Checklist

### ✅ System Requirements
- **OS**: Linux (Ubuntu 20.04+ recommended) or Windows 10/11
- **CPU**: Minimum 2 cores (4+ recommended)
- **RAM**: Minimum 4GB (8GB+ recommended)  
- **Storage**: Minimum 20GB (50GB+ recommended)
- **Python**: 3.8+ (3.11 recommended)
- **Database**: PostgreSQL 12+
- **Cache**: Redis 6+

### ✅ Dependencies Installation

1. **Install Python Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Install Database (PostgreSQL)**
   ```bash
   # Ubuntu/Debian
   sudo apt update
   sudo apt install postgresql postgresql-contrib
   
   # Windows (using Chocolatey)
   choco install postgresql
   ```

3. **Install Redis**
   ```bash
   # Ubuntu/Debian
   sudo apt install redis-server
   
   # Windows (using Chocolatey)
   choco install redis-64
   ```

4. **Install Docker (Optional)**
   ```bash
   # Ubuntu/Debian
   curl -fsSL https://get.docker.com -o get-docker.sh
   sh get-docker.sh
   
   # Windows
   # Download Docker Desktop from docker.com
   ```

## 🔐 Security Configuration

### 1. Environment Variables Setup

Copy the production environment template:
```bash
cp production.env.template .env
```

**CRITICAL**: Edit `.env` and change these values:

```bash
# Generate secure random keys (32+ characters each)
JWT_SECRET=your-super-secure-jwt-secret-key-minimum-32-characters-long
ENCRYPTION_KEY=your-super-secure-encryption-key-32chars-minimum  
SECRET_KEY=your-super-secure-secret-key-for-sessions-change-this

# Database connection
DATABASE_URL=postgresql+asyncpg://trading_user:secure_password@localhost:5432/trading_db
REDIS_URL=redis://localhost:6379/0

# Exchange API Keys (for live trading)
BINANCE_API_KEY=your_actual_binance_api_key
BINANCE_API_SECRET=your_actual_binance_api_secret
```

### 2. Generate Secure Keys
```bash
# Generate JWT secret (Linux/macOS)
openssl rand -hex 32

# Generate JWT secret (Windows PowerShell)
[System.Web.Security.Membership]::GeneratePassword(64, 0)
```

### 3. File Permissions (Linux only)
```bash
chmod 600 .env
chmod 644 *.py
chmod +x deployment_check.py
```

## 🗄️ Database Setup

### 1. Create Database and User
```sql
-- Connect as postgres user
sudo -u postgres psql

-- Create database and user
CREATE DATABASE trading_db;
CREATE USER trading_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE trading_db TO trading_user;
ALTER USER trading_user CREATEDB;  -- For migrations
\q
```

### 2. Run Database Migrations
```bash
# Apply database schema
cd database/migrations
python -c "
import sys
sys.path.append('../../')
from database.migrations.env import run_migrations
run_migrations()
"
```

## 🔄 Redis Setup

### 1. Configure Redis
```bash
# Edit Redis configuration (Linux)
sudo nano /etc/redis/redis.conf

# Key settings for production:
# maxmemory 1gb
# maxmemory-policy allkeys-lru
# save 900 1  # Save every 15 minutes if at least 1 key changed
```

### 2. Start Redis Service
```bash
# Linux
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Windows (if installed as service)
net start Redis
```

## 🧪 Pre-Deployment Testing

### 1. Run Deployment Check
```bash
python deployment_check.py
```

**Expected Output**: `✅ READY FOR DEPLOYMENT` or `⚠️ DEPLOYMENT WITH WARNINGS`

### 2. Fix Critical Issues
If deployment check fails, address these common issues:

- **Missing Environment Variables**: Ensure all required vars in `.env`
- **Database Connection**: Verify PostgreSQL is running and accessible
- **Redis Connection**: Ensure Redis service is started  
- **Dependencies**: Install missing packages from requirements.txt

### 3. Test Application Startup
```bash
# Test in development mode first
python main.py --mode development

# Test production mode
python main.py --mode production
```

## 🚀 Production Deployment Options

### Option 1: Direct Python Deployment

1. **Start Application**
   ```bash
   # Production mode with Gunicorn
   gunicorn -w 4 -k uvicorn.workers.UvicornWorker app:app --bind 0.0.0.0:8000
   
   # Or using the unified launcher
   python main.py --mode production
   ```

2. **Setup Process Manager (Linux)**
   ```bash
   # Install PM2
   npm install -g pm2
   
   # Create ecosystem file
   cat > ecosystem.config.js << EOF
   module.exports = {
     apps: [{
       name: 'crypto-trading-system',
       script: 'main.py',
       args: '--mode production',
       interpreter: 'python3',
       instances: 1,
       autorestart: true,
       watch: false,
       max_memory_restart: '1G',
       env: {
         NODE_ENV: 'production'
       }
     }]
   }
   EOF
   
   # Start with PM2
   pm2 start ecosystem.config.js
   pm2 save
   pm2 startup
   ```

### Option 2: Docker Deployment

1. **Build Docker Image**
   ```bash
   docker build -t crypto-trading-system:latest .
   ```

2. **Run with Docker Compose**
   ```bash
   # Create docker-compose.prod.yml
   cat > docker-compose.prod.yml << EOF
   version: '3.8'
   services:
     trading-app:
       build: .
       ports:
         - "8000:8000"
       environment:
         - ENVIRONMENT=production
       env_file:
         - .env
       depends_on:
         - postgres
         - redis
       restart: unless-stopped
       
     postgres:
       image: postgres:15
       environment:
         POSTGRES_DB: trading_db
         POSTGRES_USER: trading_user
         POSTGRES_PASSWORD: secure_password
       volumes:
         - postgres_data:/var/lib/postgresql/data
       restart: unless-stopped
       
     redis:
       image: redis:7-alpine
       restart: unless-stopped
       
   volumes:
     postgres_data:
   EOF
   
   # Deploy
   docker-compose -f docker-compose.prod.yml up -d
   ```

## 📊 Monitoring Setup

### 1. Health Checks
```bash
# Application health
curl http://localhost:8000/health

# Database health  
curl http://localhost:8000/api/v1/system/health/database

# System status
curl http://localhost:8000/api/v1/system/status
```

### 2. Metrics Collection
```bash
# Prometheus metrics
curl http://localhost:8000/metrics

# System metrics
curl http://localhost:8000/api/v1/monitoring/metrics
```

### 3. Alerting Setup
Configure alerts in `deployment_config.yaml`:
```yaml
monitoring:
  alerting:
    enabled: true
    rules:
      - name: "high_cpu_usage"
        threshold: 80
        duration: 300
      - name: "high_error_rate"  
        threshold: 0.05
        duration: 180
```

## 🔒 Security Hardening

### 1. Firewall Configuration
```bash
# Ubuntu/Debian
sudo ufw allow 22    # SSH
sudo ufw allow 8000  # Application
sudo ufw enable
```

### 2. SSL/TLS Setup
```bash
# Install Certbot (Let's Encrypt)
sudo apt install certbot nginx

# Configure Nginx reverse proxy
sudo nano /etc/nginx/sites-available/trading-system
```

### 3. Rate Limiting
The application includes built-in rate limiting:
- 1000 requests/minute per IP
- 1500 burst limit
- Configurable in `deployment_config.yaml`

## 🗂️ Backup & Recovery

### 1. Database Backups
```bash
# Create backup script
cat > backup_database.sh << EOF
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump -h localhost -U trading_user trading_db > backup_\${DATE}.sql
gzip backup_\${DATE}.sql
aws s3 cp backup_\${DATE}.sql.gz s3://your-backup-bucket/
rm backup_\${DATE}.sql.gz
EOF

chmod +x backup_database.sh

# Schedule daily backups
echo "0 2 * * * /path/to/backup_database.sh" | crontab -
```

### 2. Configuration Backups
```bash
# Backup configuration files
tar -czf config_backup_$(date +%Y%m%d).tar.gz \
  .env deployment_config.yaml config/
```

## 🎯 Go-Live Checklist

### Final Pre-Launch Steps

- [ ] ✅ Deployment check passes
- [ ] 🔐 All security keys changed from defaults
- [ ] 🗄️ Database properly configured and accessible
- [ ] 🔴 Redis running and connected
- [ ] 📊 Monitoring and alerts configured  
- [ ] 💾 Backup procedures in place
- [ ] 🔒 SSL/TLS certificates installed
- [ ] 🚫 Debug mode disabled (`DEBUG=false`)
- [ ] 📈 Trading mode set appropriately (`TRADING_MODE=paper` for testing)
- [ ] 🔑 Exchange API keys configured (for live trading)
- [ ] 🌐 DNS and domain configured
- [ ] 📝 Documentation updated

### Launch Commands

1. **Final deployment check**:
   ```bash
   python deployment_check.py
   ```

2. **Start production system**:
   ```bash
   python main.py --mode production
   ```

3. **Verify system health**:
   ```bash
   curl http://localhost:8000/health
   curl http://localhost:8000/api/v1/system/health
   ```

## 🚨 Troubleshooting

### Common Issues

1. **"ImportError: No module named 'psycopg2'"**
   ```bash
   pip install psycopg2-binary
   ```

2. **"ConnectionError: Redis connection failed"**
   ```bash
   sudo systemctl status redis-server
   sudo systemctl start redis-server
   ```

3. **"ValidationError: Extra inputs are not permitted"**
   - Remove extra configuration variables from `.env`
   - Use only variables listed in `production.env.template`

4. **"Permission denied" errors**
   ```bash
   chmod 600 .env
   chmod -R 755 logs/ data/ backups/
   ```

### Performance Tuning

1. **Increase worker processes**:
   ```bash
   API_WORKERS=8  # Set in .env
   ```

2. **Optimize database connections**:
   ```bash
   POOL_SIZE=20
   MAX_OVERFLOW=30
   ```

3. **Enable caching**:
   ```bash
   ENABLE_REDIS_CACHE=true
   CACHE_TTL=300
   ```

## 📞 Support

- **System Health**: Monitor `/health` endpoint
- **Logs**: Check `logs/` directory
- **Metrics**: View `/metrics` endpoint  
- **API Documentation**: Visit `/docs` (disable in production)

## 🎉 Success Indicators

Your deployment is successful when:

- ✅ Deployment check reports "READY FOR DEPLOYMENT"
- ✅ Application starts without errors
- ✅ Health checks return 200 OK
- ✅ Database connections working
- ✅ Redis cache operational
- ✅ Trading strategies loading correctly
- ✅ Monitoring metrics being collected
- ✅ No security warnings in logs

**Congratulations! Your Quantum Crypto Trading System is now live! 🚀** 