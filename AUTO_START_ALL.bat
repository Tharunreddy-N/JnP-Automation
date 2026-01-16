@echo off
echo Starting Test Server System...
echo.
echo This will start:
echo   1. Helper Server (port 8767) - Auto-starts main server
echo   2. Main Test Server (port 8766) - Runs tests
echo.
echo Keep this window minimized. Close it to stop all servers.
echo.
cd /d "%~dp0"

REM Start helper server in background
start "Helper Server" /min python utils\server_helper.py

REM Wait a moment
timeout /t 2 /nobreak >nul

REM Start main server in background  
start "Test Server" /min python utils\always_on_server.py

echo.
echo ✅ All servers started!
echo.
echo Servers are running in background windows.
echo You can now use the dashboard to run tests.
echo.
pause
