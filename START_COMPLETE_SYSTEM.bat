@echo off
setlocal enabledelayedexpansion

:: Complete Trading System Launcher for Windows
:: Starts both backend API and frontend dashboard

echo ================================================================================
echo                    COMPLETE CRYPTO TRADING SYSTEM
echo ================================================================================
echo.
echo Starting complete trading system with:
echo   - Backend Trading API (FastAPI + Python)
echo   - Frontend Dashboard (React + Vite)
echo   - Real-time market data
echo   - All production features enabled
echo.

:: Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found! Please install Python 3.8+ first.
    echo Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Check if Node.js is available
node --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Node.js not found! Please install Node.js 16+ first.
    echo Download from: https://nodejs.org/
    pause
    exit /b 1
)

:: Check if npm is available
npm --version >nul 2>&1
if errorlevel 1 (
    echo ❌ npm not found! Please install Node.js which includes npm.
    pause
    exit /b 1
)

echo ✅ Python available: 
python --version
echo ✅ Node.js available: 
node --version
echo ✅ npm available: 
npm --version
echo.

:: Install Python dependencies if needed
echo 📦 Checking Python dependencies...
python -c "import fastapi, uvicorn, redis, psycopg2" >nul 2>&1
if errorlevel 1 (
    echo Installing Python dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ❌ Failed to install Python dependencies
        pause
        exit /b 1
    )
)
echo ✅ Python dependencies ready

:: Check frontend dependencies
if not exist "src\frontend\node_modules" (
    echo 📦 Installing frontend dependencies...
    cd src\frontend
    npm install
    if errorlevel 1 (
        echo ❌ Failed to install frontend dependencies
        pause
        exit /b 1
    )
    cd ..\..
)
echo ✅ Frontend dependencies ready

echo.
echo 🚀 Launching complete trading system...
echo.
echo This will open:
echo   - Backend API in a new console window
echo   - Frontend dashboard in another console window
echo   - Browser tabs for both interfaces
echo.
echo Press any key to continue...
pause >nul

:: Start the complete system
python run_complete_system.py

echo.
echo Complete trading system has been stopped.
pause 