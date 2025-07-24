@echo off
echo.
echo ========================================
echo    Trading System Local Setup (Windows)
echo ========================================
echo.
echo This script will install and configure:
echo - PostgreSQL 15.x
echo - Redis 
echo - Node.js 18.x
echo - Set up the local database
echo.
echo IMPORTANT: This is for LOCAL development only!
echo It will NOT connect to production systems.
echo.
pause

REM Check if running as administrator
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo.
    echo ERROR: This script must be run as Administrator!
    echo Please right-click and select "Run as administrator"
    pause
    exit /b 1
)

echo.
echo [1/6] Checking existing installations...
echo.

REM Check if PostgreSQL is installed
pg_config --version >nul 2>&1
if %errorLevel% equ 0 (
    echo ✓ PostgreSQL is already installed
    set POSTGRES_INSTALLED=1
) else (
    echo - PostgreSQL not found
    set POSTGRES_INSTALLED=0
)

REM Check if Redis is installed
redis-server --version >nul 2>&1
if %errorLevel% equ 0 (
    echo ✓ Redis is already installed
    set REDIS_INSTALLED=1
) else (
    echo - Redis not found
    set REDIS_INSTALLED=0
)

REM Check if Node.js is installed
node --version >nul 2>&1
if %errorLevel% equ 0 (
    echo ✓ Node.js is already installed
    set NODE_INSTALLED=1
) else (
    echo - Node.js not found
    set NODE_INSTALLED=0
)

REM Check if Python is installed
python --version >nul 2>&1
if %errorLevel% equ 0 (
    echo ✓ Python is already installed
    set PYTHON_INSTALLED=1
) else (
    echo - Python not found
    set PYTHON_INSTALLED=0
)

echo.
echo [2/6] Installing missing dependencies...
echo.

REM Install PostgreSQL if not present
if %POSTGRES_INSTALLED% equ 0 (
    echo Installing PostgreSQL 15.x...
    echo Please download and install PostgreSQL from:
    echo https://get.enterprisedb.com/postgresql/postgresql-15.4-1-windows-x64.exe
    echo.
    echo Installation notes:
    echo - Set password for postgres user: postgres
    echo - Keep default port 5432
    echo - Include pgAdmin 4
    echo - Include Stack Builder
    echo.
    echo Press any key after PostgreSQL installation is complete...
    pause
)

REM Install Redis if not present
if %REDIS_INSTALLED% equ 0 (
    echo Installing Redis...
    echo Please download and install Redis from:
    echo Download Redis from official website or use package manager
    echo.
    echo Installation notes:
    echo - Keep default port 6379
    echo - Add Redis to PATH
    echo - Install as Windows service
    echo.
    echo Press any key after Redis installation is complete...
    pause
)

REM Install Node.js if not present
if %NODE_INSTALLED% equ 0 (
    echo Installing Node.js 18.x...
    echo Please download and install Node.js from:
    echo https://nodejs.org/dist/v18.19.0/node-v18.19.0-x64.msi
    echo.
    echo Installation notes:
    echo - Add to PATH
    echo - Install npm package manager
    echo.
    echo Press any key after Node.js installation is complete...
    pause
)

REM Install Python if not present
if %PYTHON_INSTALLED% equ 0 (
    echo Installing Python 3.11...
    echo Please download and install Python from:
    echo https://www.python.org/ftp/python/3.11.2/python-3.11.2-amd64.exe
    echo.
    echo Installation notes:
    echo - Check "Add Python to PATH"
    echo - Install pip
    echo.
    echo Press any key after Python installation is complete...
    pause
)

echo.
echo [3/6] Starting services...
echo.

REM Start PostgreSQL service
echo Starting PostgreSQL service...
net start postgresql-x64-15
if %errorLevel% neq 0 (
    echo Warning: Could not start PostgreSQL service
    echo Please start it manually from Services or pgAdmin
)

REM Start Redis service
echo Starting Redis service...
net start Redis
if %errorLevel% neq 0 (
    echo Warning: Could not start Redis service
    echo Please start it manually from Services
)

echo.
echo [4/6] Creating database and user...
echo.

REM Create database and user
echo Creating database and user...
psql -U postgres -c "CREATE DATABASE trading_system_local;" 2>nul
psql -U postgres -c "CREATE USER trading_user WITH PASSWORD 'trading_password_local';" 2>nul
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE trading_system_local TO trading_user;" 2>nul
psql -U postgres -c "ALTER USER trading_user CREATEDB;" 2>nul

echo.
echo [5/6] Setting up database schema...
echo.

REM Run database setup script
if exist "setup_local_database.sql" (
    echo Running database setup script...
    psql -U postgres -d trading_system_local -f setup_local_database.sql
    if %errorLevel% equ 0 (
        echo ✓ Database setup completed successfully
    ) else (
        echo ✗ Database setup failed
        echo Please check the SQL script and try again
    )
) else (
    echo ✗ Database setup script not found!
    echo Please ensure setup_local_database.sql exists in the current directory
)

echo.
echo [6/6] Setting up environment file...
echo.

REM Copy environment file
if exist "config\local.env" (
    echo Copying environment configuration...
    copy "config\local.env" ".env" >nul
    if %errorLevel% equ 0 (
        echo ✓ Environment file created successfully
    ) else (
        echo ✗ Failed to create environment file
    )
) else (
    echo ✗ Local environment file not found!
    echo Please ensure config\local.env exists
)

echo.
echo ========================================
echo    Setup Complete!
echo ========================================
echo.
echo Services Status:
echo - PostgreSQL: Running on port 5432
echo - Redis: Running on port 6379
echo - Database: trading_system_local
echo - User: trading_user
echo.
echo Next Steps:
echo 1. Install Python dependencies: pip install -r requirements.txt
echo 2. Install Node.js dependencies: cd src\frontend && npm install
echo 3. Start the backend: python run_local.py
echo 4. Start the frontend: cd src\frontend && npm run dev
echo.
echo Access URLs:
echo - Backend API: http://localhost:8000
echo - Frontend: http://localhost:3000
echo - API Documentation: http://localhost:8000/docs
echo - Database: postgresql://trading_user:trading_password_local@localhost:5432/trading_system_local
echo.
echo Press any key to exit...
pause 