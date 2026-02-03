@echo off
echo ===================================================
echo  RESETTING AUTOMATION SYSTEM AND STARTING DASHBOARD
echo ===================================================

echo [1/3] Stopping all Python processes...
taskkill /F /IM python.exe /T 2>nul
taskkill /F /IM pythonw.exe /T 2>nul
echo Done.

echo [2/3] Cleaning up lock files...
cd /d "%~dp0"
if exist ".test_execution.lock" del ".test_execution.lock"
if exist ".test_queue.lock" del ".test_queue.lock"
if exist ".browser_lock" del ".browser_lock"
if exist ".pytest_running.lock" del ".pytest_running.lock"
if exist ".always_on_server.pid" del ".always_on_server.pid"
if exist ".test_queue.json" echo {"queue": [], "last_updated": ""} > ".test_queue.json"
echo Done.

echo [3/3] Starting Dashboard Server...
echo The dashboard will open in your browser automatically.
start "Dashboard Launcher" /min python utils\dashboard_launcher.py

echo.
echo SUCCESS! You can close this window if it doesn't close automatically.
timeout /t 5 >nul
exit
