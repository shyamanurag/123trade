# PowerShell script to restart the trading system server
# Usage: .\scripts\restart-server.ps1

Write-Host "Restarting Trading System Server..." -ForegroundColor Yellow

# Kill existing Python processes (if any)
Write-Host "Stopping existing processes..." -ForegroundColor Gray
try {
    Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.ProcessName -eq "python" } | Stop-Process -Force
    Write-Host "Existing processes stopped" -ForegroundColor Green
}
catch {
    Write-Host "No existing processes found" -ForegroundColor Blue
}

# Wait a moment for cleanup
Start-Sleep -Seconds 2

# Start the server
Write-Host "Starting Trading System on port 8001..." -ForegroundColor Cyan
try {
    # Change to the correct directory
    Set-Location $PSScriptRoot\..
    
    # Start the Python application
    python main.py
}
catch {
    Write-Host "Failed to start server: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host "Server restart completed!" -ForegroundColor Green 