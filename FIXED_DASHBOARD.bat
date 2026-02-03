@echo off
echo ========================================
echo FIXED DASHBOARD - All Issues Resolved
echo ========================================
echo.

cd /d "%~dp0"

REM Force update history
echo [1/4] Updating history from JSON...
python force_fix_history.py
echo.

REM Kill all API servers
echo [2/4] Cleaning up old API servers...
Get-Process python -ErrorAction SilentlyContinue | Where-Object { (Get-NetTCPConnection -OwningProcess $_.Id -ErrorAction SilentlyContinue | Where-Object LocalPort -eq 5001) } | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
echo.

REM Start fresh API server
echo [3/4] Starting fresh API server...
Start-Process python -ArgumentList "-m", "utils.log_history_api" -WindowStyle Hidden
Start-Sleep -Seconds 4
echo.

REM Check HTTP server
echo [4/4] Checking HTTP server...
netstat -ano | findstr ":8888" | findstr "LISTENING" >nul
if %errorlevel% neq 0 (
    echo Starting HTTP server...
    start "HTTP Server" /min python -m http.server 8888 --bind 127.0.0.1
    timeout /t 2 /nobreak >nul
) else (
    echo HTTP server is running
)
echo.

REM Verify everything
echo Verifying...
python check_everything.py
echo.

echo ========================================
echo Opening Dashboard...
echo ========================================
echo.
echo IMPORTANT: 
echo 1. Dashboard URL: http://127.0.0.1:8888/log_viewer_ui.html?module=jobseeker
echo 2. Press Ctrl+F5 to hard refresh (clear cache)
echo 3. Click on test_t1_09_db_solr_sync_verification
echo 4. You should see: Status FAIL, Failures: 1,625, Total Jobs: 23,483
echo.
start http://127.0.0.1:8888/log_viewer_ui.html?module=jobseeker
echo.
pause
