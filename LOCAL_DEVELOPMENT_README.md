# 🏠 Local Development Environment Setup

**Complete guide to run the Trading System locally for development and testing**

## ⚡ Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.local.txt

# 2. Run setup (creates database, config, etc.)
python setup_local_development.py

# 3. Start local development server
python run_local_development.py
```

**🌐 Your app will be available at: http://localhost:8000**

---

## 🛡️ Safety Features

### **COMPLETELY ISOLATED FROM PRODUCTION**
- ✅ Uses local SQLite database (not production PostgreSQL)
- ✅ Uses local Redis or in-memory fallback (not production Redis)
- ✅ All trading is SIMULATED (paper trading mode)
- ✅ Mock market data (no real API calls)
- ✅ Different ports from production
- ✅ Separate configuration files

### **NO RISK TO DEPLOYED APP**
- 🔒 Cannot access production database
- 🔒 Cannot place real trades
- 🔒 Cannot affect live trading
- 🔒 Uses test API keys only

---

## 📋 Prerequisites

### Required Software
- **Python 3.8+** (Check: `python --version`)
- **Git** (for cloning/updates)
- **Optional**: Redis (for caching, falls back to in-memory)

### Installation Steps

#### 1. **Clone to New Directory** (if not done already)
```bash
# Clone to a new directory
git clone https://github.com/your-username/trading-system-new.git trading-system-local
cd trading-system-local
```

#### 2. **Create Virtual Environment** (Recommended)
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate
```

#### 3. **Install Dependencies**
```bash
# Install local development dependencies
pip install -r requirements.local.txt

# OR install main requirements if local file not available
pip install -r requirements.txt
```

#### 4. **Run Setup Script**
```bash
python setup_local_development.py
```

This will:
- ✅ Verify Python version
- ✅ Install missing packages
- ✅ Create local SQLite database
- ✅ Create necessary directories
- ✅ Set up configuration files
- ✅ Test all components

---

## 🚀 Running the Local Server

### Basic Usage
```bash
python run_local_development.py
```

### Advanced Options
```bash
# Custom port
python run_local_development.py --port 8080

# Disable auto-reload
python run_local_development.py --no-reload

# Enable mock market data
python run_local_development.py --mock-data
```

### What Happens When You Start
1. **Environment Setup**: Local development mode activated
2. **Database**: SQLite database created/connected
3. **Configuration**: Local settings loaded
4. **Server Start**: FastAPI server starts with hot-reload
5. **Safety Checks**: All production-blocking measures activated

---

## 🌐 Access Points

Once running, you can access:

### **Main Application**
- **URL**: http://localhost:8000
- **Description**: Main trading system interface

### **API Documentation**
- **URL**: http://localhost:8000/docs
- **Description**: Interactive API documentation (Swagger UI)

### **Alternative API Docs**
- **URL**: http://localhost:8000/redoc
- **Description**: Alternative API documentation

### **Health Check**
- **URL**: http://localhost:8000/health
- **Description**: System health status

### **Trading Dashboard**
- **URL**: http://localhost:8000/dashboard
- **Description**: Trading dashboard (if frontend is integrated)

---

## 🗂️ File Structure

### Configuration Files
```
config/
├── local.env                 # Local environment variables
├── config.local.yaml         # Local YAML configuration
├── config.yaml              # Base configuration
└── production.env.example   # Production template (DO NOT USE)
```

### Local Development Files
```
run_local_development.py      # Main local server script
setup_local_development.py    # One-time setup script
requirements.local.txt        # Local development dependencies
.env.local                   # Auto-generated environment file
local_trading.db             # Local SQLite database (auto-created)
local_development.log        # Local development logs
```

### Data Files (Auto-created)
```
data/local/                  # Local data directory
logs/                       # Log files
backups/local/              # Local backups
temp/                       # Temporary files
```

---

## 🧪 Testing and Debugging

### Check System Status
```bash
# Test basic imports
python -c "import fastapi, uvicorn, sqlalchemy; print('✅ All imports working')"

# Test database connection
python -c "
import sqlite3
conn = sqlite3.connect('local_trading.db')
cursor = conn.cursor()
cursor.execute('SELECT * FROM test_table')
print('✅ Database working:', cursor.fetchall())
conn.close()
"
```

### View Logs
```bash
# Real-time logs
tail -f local_development.log

# Or view in Python
python -c "
with open('local_development.log', 'r') as f:
    print(f.read())
"
```

### Test API Endpoints
```bash
# Test health endpoint
curl http://localhost:8000/health

# Test market status
curl http://localhost:8000/api/market/market-status

# Test autonomous trading status
curl http://localhost:8000/api/v1/autonomous/status
```

---

## 🔧 Troubleshooting

### Common Issues

#### **Port Already in Use**
```bash
# Find what's using port 8000
lsof -i :8000  # Mac/Linux
netstat -ano | findstr :8000  # Windows

# Use different port
python run_local_development.py --port 8080
```

#### **Import Errors**
```bash
# Reinstall dependencies
pip install -r requirements.local.txt --force-reinstall

# Or try main requirements
pip install -r requirements.txt
```

#### **Database Issues**
```bash
# Delete and recreate database
rm local_trading.db
python setup_local_development.py
```

#### **Permission Issues**
```bash
# On Windows, run as administrator
# On Linux/Mac, check file permissions
chmod +x run_local_development.py
chmod +x setup_local_development.py
```

### Getting Help

1. **Check Logs**: Look at `local_development.log`
2. **Restart Setup**: Run `python setup_local_development.py` again
3. **Clean Start**: Delete all auto-generated files and re-run setup
4. **Check Dependencies**: Ensure all packages in `requirements.local.txt` are installed

---

## 🚀 Development Workflow

### Typical Development Session

1. **Start Development**
   ```bash
   # Activate virtual environment (if using)
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   
   # Start server
   python run_local_development.py
   ```

2. **Make Changes**
   - Edit code files
   - Server auto-reloads on changes (hot-reload enabled)
   - Check http://localhost:8000 for updates

3. **Test Changes**
   - Use http://localhost:8000/docs for API testing
   - Check logs in terminal or `local_development.log`
   - Test endpoints with curl or browser

4. **Debug Issues**
   - Check terminal output for errors
   - Use debug mode (enabled by default)
   - Check database with SQLite browser tools

5. **Stop Development**
   ```bash
   # Stop server: Ctrl+C in terminal
   # Deactivate virtual environment (if using)
   deactivate
   ```

### Code Changes & Hot Reload

The development server automatically reloads when you change:
- ✅ Python files (`.py`)
- ✅ Configuration files (`.yaml`, `.env`)
- ✅ Templates and static files

No restart needed for most changes!

---

## 📊 Local vs Production Differences

| Feature | Local Development | Production |
|---------|-------------------|------------|
| Database | SQLite (file) | PostgreSQL (cloud) |
| Redis | Local/In-memory | Cloud Redis |
| Trading | Paper/Simulation | Real (if enabled) |
| Market Data | Mock/Simulated | Real ShareKhan |
| Broker API | Mock/Sandbox | Real ShareKhan |
| Ports | 8000 (local) | 8000 (cloud) |
| SSL | Disabled | Enabled |
| Authentication | Local secrets | Production secrets |
| Logging | Debug level | Info level |
| Hot Reload | Enabled | Disabled |

---

## 🔒 Security Notes

- 🔐 Local environment uses test secrets only
- 🔐 No production credentials are exposed
- 🔐 All trading operations are simulated
- 🔐 Local database is isolated
- 🔐 No access to production APIs

---

## 🎯 Next Steps

1. **Complete Setup**: Follow the quick start guide above
2. **Explore API**: Use http://localhost:8000/docs
3. **Test Features**: Try different trading endpoints
4. **Debug Issues**: Use the troubleshooting guide
5. **Develop Features**: Make changes and test locally
6. **Deploy Changes**: When ready, commit and push to production

---

**🎉 Happy Local Development!**

*This environment is completely safe for testing and development without any risk to your production trading system.* 