@echo off
echo ========================================
echo Opening Dashboard - Clean Data Ready
echo ========================================
echo.
cd /d "%~dp0"

REM Check and start API server if needed
netstat -ano | findstr ":5001" | findstr "LISTENING" >nul
if %errorlevel% neq 0 (
    echo Starting API server...
    start "API Server" /min python -m utils.log_history_api
    timeout /t 3 /nobreak >nul
)

REM Check and start HTTP server if needed
netstat -ano | findstr ":8888" | findstr "LISTENING" >nul
if %errorlevel% neq 0 (
    echo Starting HTTP server...
    start "HTTP Server" /min python -m http.server 8888 --bind 127.0.0.1
    timeout /t 2 /nobreak >nul
)

echo.
echo Opening dashboard in browser...
echo URL: http://127.0.0.1:8888/log_viewer_ui.html?module=jobseeker
echo.
start http://127.0.0.1:8888/log_viewer_ui.html?module=jobseeker
echo.
echo Dashboard opened! Click on test_t1_09_db_solr_sync_verification to see clean data.
echo.
pause
