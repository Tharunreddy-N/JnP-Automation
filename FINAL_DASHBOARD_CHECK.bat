@echo off
echo ========================================
echo FINAL DASHBOARD CHECK
echo ========================================
echo.

cd /d "%~dp0"

REM Force update history
echo [1/4] Updating history from JSON...
python force_fix_history.py
echo.

REM Check API server
echo [2/4] Checking API server...
netstat -ano | findstr ":5001" | findstr "LISTENING" >nul
if %errorlevel% neq 0 (
    echo Starting API server...
    start "API Server" /min python -m utils.log_history_api
    timeout /t 3 /nobreak >nul
) else (
    echo API server is running
)
echo.

REM Check HTTP server
echo [3/4] Checking HTTP server...
netstat -ano | findstr ":8888" | findstr "LISTENING" >nul
if %errorlevel% neq 0 (
    echo Starting HTTP server...
    start "HTTP Server" /min python -m http.server 8888 --bind 127.0.0.1
    timeout /t 2 /nobreak >nul
) else (
    echo HTTP server is running
)
echo.

REM Test API
echo [4/4] Testing API...
python test_browser_api.py
echo.

echo ========================================
echo Opening Dashboard...
echo ========================================
echo.
echo IMPORTANT: 
echo 1. Open this URL in browser: http://127.0.0.1:8888/log_viewer_ui.html?module=jobseeker
echo 2. Press Ctrl+F5 to hard refresh (clear cache)
echo 3. Click on test_t1_09_db_solr_sync_verification
echo 4. You should see: Status FAIL, Failures: 1,625, Total Jobs: 23,483
echo.
start http://127.0.0.1:8888/log_viewer_ui.html?module=jobseeker
echo.
pause
