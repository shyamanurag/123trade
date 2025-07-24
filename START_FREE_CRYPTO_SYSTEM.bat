@echo off
title Quantum Crypto Trading System - FREE TIER

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                                                              ║
echo ║        🚀 QUANTUM CRYPTO TRADING SYSTEM - FREE TIER 🚀       ║
echo ║                                                              ║
echo ║              The Smartest Crypto Algorithm                   ║
echo ║                   🆓 100% FREE VERSION 🆓                     ║
echo ║                                                              ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.
echo 💡 WHAT THIS SYSTEM INCLUDES:
echo    ✅ $10,000 virtual trading balance
echo    ✅ 6 professional trading strategies  
echo    ✅ 4-model AI prediction ensemble
echo    ✅ Professional risk management
echo    ✅ Real-time market simulation
echo    ✅ Complete performance tracking
echo    ✅ NO API KEYS REQUIRED!
echo.
echo 🎯 MODE: Paper Trading (No Real Money Risk)
echo 💰 STARTING BALANCE: $10,000 Virtual Money
echo 📊 STRATEGIES: All 6 Enhanced Strategies Active
echo 🧠 AI MODELS: 4-Model Ensemble (CPU Optimized)
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ❌ ERROR: Python is not installed or not in PATH
    echo.
    echo 💡 SOLUTION:
    echo    1. Install Python 3.9+ from https://python.org
    echo    2. Make sure to check "Add Python to PATH" during installation
    echo    3. Restart this script
    echo.
    pause
    exit /b 1
)

REM Check if we're in the right directory
if not exist "start_free_crypto_trading.py" (
    echo ❌ ERROR: Cannot find start_free_crypto_trading.py
    echo.
    echo 💡 SOLUTION:
    echo    Make sure you're running this from the trading-system-working-copy directory
    echo    Current directory: %CD%
    echo.
    pause
    exit /b 1
)

REM Create logs directory if it doesn't exist
if not exist "logs" mkdir logs

REM Check if config files exist
if not exist "config\quantum_trading_config.yaml" (
    echo ❌ ERROR: Missing configuration file: config\quantum_trading_config.yaml
    echo.
    echo 💡 SOLUTION:
    echo    The configuration files should have been created during setup.
    echo    Please check the config\ directory.
    echo.
    pause
    exit /b 1
)

echo ⚡ SYSTEM STARTING...
echo.
echo 🔍 Checking Python dependencies...

REM Install required packages if needed
pip install pyyaml asyncio >nul 2>&1

echo ✅ Dependencies checked
echo.
echo 🚀 Starting Quantum Crypto Trading System...
echo.
echo 💡 INSTRUCTIONS:
echo    • Watch the console for trade updates
echo    • System displays status every 5 minutes
echo    • Press Ctrl+C to stop the system gracefully
echo    • Check logs\ directory for detailed logs
echo.
echo 📊 System will start trading with virtual money...
echo ⏰ Please wait for AI models to load (may take 1-2 minutes)...
echo.

REM Start the trading system
python start_free_crypto_trading.py

echo.
echo 👋 Quantum Crypto Trading System stopped.
echo.
echo 📊 PERFORMANCE SUMMARY:
echo    Check logs\quantum_crypto_free.log for complete trading history
echo.
pause 