@echo off
echo Starting Dashboard Launcher...
echo.
echo This will:
echo   1. Auto-start test servers
echo   2. Open dashboard in your browser
echo   3. Everything works automatically!
echo.
cd /d "%~dp0"
start "Dashboard Launcher" /min python utils\dashboard_launcher.py
timeout /t 3 /nobreak >nul
echo.
echo ✅ Dashboard is opening in your browser...
echo.
echo The dashboard will be available at: http://localhost:8888
echo.
echo Keep this window minimized. Close it to stop the server.
echo.
pause
