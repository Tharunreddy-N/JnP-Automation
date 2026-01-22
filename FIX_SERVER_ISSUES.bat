@echo off
echo ========================================
echo Fixing Server Issues
echo ========================================
echo.

cd /d "%~dp0"

echo [1/5] Removing stale lock files...
if exist ".test_execution.lock" (
    del ".test_execution.lock"
    echo   Removed: .test_execution.lock
) else (
    echo   No .test_execution.lock found
)
if exist ".test_queue.lock" (
    del ".test_queue.lock"
    echo   Removed: .test_queue.lock
) else (
    echo   No .test_queue.lock found
)
if exist ".browser_lock" (
    del ".browser_lock"
    echo   Removed: .browser_lock
) else (
    echo   No .browser_lock found
)
if exist ".pytest_running.lock" (
    del ".pytest_running.lock"
    echo   Removed: .pytest_running.lock
) else (
    echo   No .pytest_running.lock found
)
echo.

echo [2/5] Checking and cleaning PID file...
if exist ".always_on_server.pid" (
    echo   PID file exists: .always_on_server.pid
    for /f "tokens=*" %%A in (.always_on_server.pid) do set PID=%%A
    echo   PID in file: %PID%
    echo   Checking if process is running...
    tasklist /FI "PID eq %PID%" /FO TABLE | findstr /I "%PID%" >nul
    if errorlevel 1 (
        echo   Process %PID% is NOT running - removing stale PID file
        del ".always_on_server.pid"
        echo   OK: Stale PID file removed
    ) else (
        echo   Process %PID% IS running - server may be active
        echo   Keep PID file (server is running)
    )
) else (
    echo   No PID file found
)
echo.

echo [3/5] Clearing test queue...
if exist ".test_queue.json" (
    echo {"queue": [], "last_updated": ""} > ".test_queue.json"
    echo   Queue cleared
) else (
    echo   No queue file found
)
echo.

echo [4/5] Checking for running Python processes...
tasklist /FI "IMAGENAME eq python.exe" /FO TABLE | findstr /I "python"
if errorlevel 1 (
    echo   No Python processes found
) else (
    echo   Python processes detected above
)
echo.

echo [5/5] Checking port 8766 status...
netstat -ano | findstr :8766 >nul
if errorlevel 1 (
    echo   Port 8766 is free
) else (
    echo   WARNING: Port 8766 is in use
    echo   Showing port details:
    netstat -ano | findstr :8766
)
echo.

echo ========================================
echo Cleanup Complete
echo ========================================
echo.
echo Next steps:
echo   1. If server is running, you may need to restart it:
echo      - Close the server window (Ctrl+C)
echo      - Run START_ALWAYS_ON_SERVER.bat again
echo.
echo   2. The server will now:
echo      - Automatically remove stale locks on startup
echo      - Only allow pytest processes to hold test locks
echo      - Process tests from the queue correctly
echo.
echo   3. To verify server is working:
echo      - Run CHECK_SERVER.bat
echo      - Or run VERIFY_SERVER_AND_DASHBOARD.bat
echo.
pause
