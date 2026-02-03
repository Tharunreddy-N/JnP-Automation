@echo off
echo ========================================
echo Opening Dashboard via HTTP Server
echo ========================================
echo.
echo This will open the dashboard at:
echo   http://127.0.0.1:8888/log_viewer_ui.html?module=jobseeker
echo.
echo IMPORTANT: Use HTTP URL, NOT file:// protocol
echo This fixes CORS issues with API connections
echo.
cd /d "%~dp0"

REM Check if HTTP server is running on port 8888
netstat -ano | findstr ":8888" >nul
if %errorlevel% neq 0 (
    echo Starting HTTP server on port 8888...
    start "HTTP Server" /min python -m http.server 8888 --bind 127.0.0.1
    timeout /t 2 /nobreak >nul
)

REM Check if API server is running on port 5001
netstat -ano | findstr ":5001" >nul
if %errorlevel% neq 0 (
    echo Starting API server on port 5001...
    start "API Server" /min python -m utils.log_history_api
    timeout /t 3 /nobreak >nul
)

echo Opening dashboard in browser...
start http://127.0.0.1:8888/log_viewer_ui.html?module=jobseeker
echo.
echo Dashboard opened! If you see API errors, wait 5 seconds and refresh.
echo.
pause
