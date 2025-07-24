@echo off
echo.
echo ===============================================================================
echo  QUANTUM CRYPTO TRADING SYSTEM - LOCAL PRODUCTION DEPLOYMENT
echo ===============================================================================
echo.
echo Starting full production-like environment locally...
echo This includes: PostgreSQL, Redis, Monitoring, and all production features
echo.

REM Check if Docker is available
echo [1/6] Checking Docker availability...
docker --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker is not installed or not in PATH
    echo Please install Docker Desktop from: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)
echo ✅ Docker is available

REM Check if .env file exists, create if not
echo.
echo [2/6] Setting up environment configuration...
if not exist ".env" (
    echo Creating .env file from local production template...
    copy "local-production.env" ".env" >nul
    echo ✅ Environment file created: .env
    echo.
    echo ⚠️  IMPORTANT: Edit .env file to add your broker API keys:
    echo    - ZERODHA_API_KEY=your_actual_api_key
    echo    - ZERODHA_API_SECRET=your_actual_api_secret
    echo.
) else (
    echo ✅ Environment file already exists: .env
)

REM Create required directories
echo.
echo [3/6] Creating required directories...
if not exist "logs" mkdir logs
if not exist "data" mkdir data
if not exist "backups" mkdir backups
echo ✅ Directories created

REM Stop any existing containers
echo.
echo [4/6] Stopping any existing containers...
docker-compose -f docker-compose.local-production.yml down >nul 2>&1
echo ✅ Existing containers stopped

REM Start the complete production environment
echo.
echo [5/6] Starting local production environment...
echo This may take a few minutes for the first run (downloading images)...
docker-compose -f docker-compose.local-production.yml up -d

REM Check if services started successfully
echo.
echo [6/6] Verifying services...
timeout /t 10 /nobreak >nul

echo.
echo Checking service health...
docker ps --filter "name=trading_" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo.
echo ===============================================================================
echo  🚀 LOCAL PRODUCTION ENVIRONMENT STARTED SUCCESSFULLY!
echo ===============================================================================
echo.
echo 📊 AVAILABLE SERVICES:
echo.
echo   🏛️  Trading API (Production Mode): http://localhost:8000
echo   📖 API Documentation:              http://localhost:8000/docs
echo   🩺 Health Check:                   http://localhost:8000/health
echo   💻 Frontend Dashboard:             http://localhost:3000
echo   📈 Grafana Monitoring:             http://localhost:3001 (admin/admin_secure_2024)
echo   🔥 Prometheus Metrics:             http://localhost:9090
echo   🗄️  PostgreSQL Database:           localhost:5432 (trading_admin/secure_trading_password_2024)
echo   🔴 Redis Cache:                    localhost:6379 (password: secure_redis_password_2024)
echo.
echo 🔐 SECURITY FEATURES:
echo   • Production-grade authentication with JWT
echo   • Encrypted password storage with bcrypt
echo   • Account lockout protection
echo   • Role-based access control
echo.
echo 📈 TRADING FEATURES:
echo   • Real-time market data integration
echo   • Autonomous trading capabilities
echo   • Advanced risk management
echo   • 6 sophisticated trading strategies
echo   • Comprehensive monitoring and alerts
echo.
echo 💾 DATA PERSISTENCE:
echo   • PostgreSQL with optimized performance settings
echo   • Redis for high-speed caching
echo   • Automated backups and data retention
echo.
echo ⚠️  IMPORTANT NOTES:
echo   • This is a PRODUCTION-LIKE environment running locally
echo   • All features are enabled (no mock data)
echo   • Paper trading is enabled by default for safety
echo   • Edit .env file to configure broker credentials
echo   • Check logs/ directory for application logs
echo.
echo 📋 NEXT STEPS:
echo   1. Open http://localhost:8000/docs to explore the API
echo   2. Configure your broker credentials in .env file
echo   3. Access the dashboard at http://localhost:3000
echo   4. Monitor system health at http://localhost:3001
echo.
echo 🛑 TO STOP ALL SERVICES:
echo   docker-compose -f docker-compose.local-production.yml down
echo.
echo ===============================================================================

REM Open key URLs in browser
start http://localhost:8000/docs
start http://localhost:3000

echo.
echo Press any key to exit...
pause >nul 