@echo off
echo Checking if test servers are running...
echo.

cd /d "%~dp0"

REM Check if ports are in use
netstat -an | findstr "8766" >nul
if %errorlevel% == 0 (
    echo ✅ Main test server (port 8766) is running
) else (
    echo ❌ Main test server not running - starting...
    start "Test Server" /min python utils\always_on_server.py
    timeout /t 2 /nobreak >nul
)

netstat -an | findstr "8767" >nul
if %errorlevel% == 0 (
    echo ✅ Helper server (port 8767) is running
) else (
    echo ❌ Helper server not running - starting...
    start "Helper Server" /min python utils\server_helper.py
    timeout /t 2 /nobreak >nul
)

echo.
echo ✅ All servers are now running!
echo.
timeout /t 2 /nobreak >nul
