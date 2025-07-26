@echo off
REM Batch file for common trading system commands
REM This avoids PowerShell syntax issues

if "%1"=="" goto :help

if "%1"=="commit" goto :commit
if "%1"=="push" goto :push
if "%1"=="deploy" goto :deploy
if "%1"=="test" goto :test
if "%1"=="local" goto :local
if "%1"=="status" goto :status
goto :help

:commit
echo Adding all files...
git add -A
if errorlevel 1 goto :error
echo Committing with message: %2 %3 %4 %5 %6 %7 %8 %9
git commit -m "%2 %3 %4 %5 %6 %7 %8 %9"
if errorlevel 1 goto :error
echo Commit successful!
goto :end

:push
echo Pushing to origin main...
git push origin main
if errorlevel 1 goto :error
echo Push successful!
goto :end

:deploy
echo Checking deployment...
node check_deployment.js
goto :end

:test
echo Running tests...
python test_deployment_status.py
goto :end

:local
echo Starting local server...
python run_local.py
goto :end

:status
echo Git status:
git status
echo.
echo Deployment URL: https://trade123-l3zp7.ondigitalocean.app
goto :end

:help
echo.
echo Trading System Command Helper
echo =============================
echo.
echo Usage: commands.bat [command] [args]
echo.
echo Commands:
echo   commit "message"  - Add all files and commit with message
echo   push             - Push to origin main
echo   deploy           - Check deployment status
echo   test             - Run test suite
echo   local            - Start local server
echo   status           - Show git status
echo.
echo Examples:
echo   commands.bat commit "Fixed API endpoints"
echo   commands.bat push
echo   commands.bat deploy
echo.
goto :end

:error
echo.
echo ERROR: Command failed!
echo.

:end 