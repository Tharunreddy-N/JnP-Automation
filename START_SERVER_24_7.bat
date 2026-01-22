@echo off
REM ========================================
REM Start Server 24/7 with Keep-Alive Monitor
REM ========================================
REM This script starts the server and keeps it running 24/7
REM It will automatically restart the server if it stops

cd /d "%~dp0"
echo ========================================
echo Starting Server 24/7 Monitor
echo ========================================
echo.
echo This will:
echo 1. Start the test server if not running
echo 2. Monitor the server continuously
echo 3. Auto-restart if server stops
echo.
echo Keep this window open for monitoring.
echo Press Ctrl+C to stop.
echo.
echo ========================================
echo.

python utils\server_keep_alive.py

if errorlevel 1 (
    echo.
    echo ========================================
    echo ERROR: Keep-alive monitor failed!
    echo ========================================
    echo.
    pause
)
