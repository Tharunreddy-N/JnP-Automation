@echo off
echo ========================================
echo Verifying Server and Dashboard Setup
echo ========================================
echo.

cd /d "%~dp0"

echo [1/4] Checking if server is running...
echo.
python test_server_connection.py
if errorlevel 1 (
    echo.
    echo ❌ Server is NOT running!
    echo.
    echo Please start the server:
    echo   1. Run START_ALWAYS_ON_SERVER.bat
    echo   2. Wait for "SERVER IS READY" message
    echo   3. Keep that window open
    echo.
) else (
    echo.
    echo ✓ Server is running correctly!
    echo.
)

echo.
echo [2/4] Checking server process...
echo.
tasklist /FI "IMAGENAME eq python.exe" /FO TABLE | findstr /I "python"
echo.

echo [3/4] Checking port 8766...
echo.
netstat -ano | findstr :8766
if errorlevel 1 (
    echo ⚠ Port 8766 is not in use - server may not be running
) else (
    echo ✓ Port 8766 is active
)
echo.

echo [4/4] Verifying dashboard files...
echo.
if exist "logs\index.html" (
    echo ✓ Dashboard HTML file exists: logs\index.html
    for %%A in ("logs\index.html") do echo   File size: %%~zA bytes
    echo   Last modified: %%~tA
) else (
    echo ❌ Dashboard HTML file NOT found: logs\index.html
    echo   Run: python refresh_dashboard.py
)
echo.

echo ========================================
echo Verification Complete
echo ========================================
echo.
echo Next steps:
echo   1. If server is not running: START_ALWAYS_ON_SERVER.bat
echo   2. Open dashboard: logs\index.html
echo   3. Click a test case to run
echo   4. Watch server console for test execution
echo.
pause
