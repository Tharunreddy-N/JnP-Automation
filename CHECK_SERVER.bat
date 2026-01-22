@echo off
echo ========================================
echo Checking Always-On Server Status
echo ========================================
echo.

cd /d "%~dp0"

echo Testing server connection...
python test_server_connection.py

echo.
echo ========================================
echo Checking if server process is running...
echo ========================================
echo.

tasklist /FI "IMAGENAME eq python.exe" /FO TABLE | findstr /I "python"

echo.
echo Checking port 8766...
netstat -ano | findstr :8766

echo.
echo ========================================
echo Server Status Check Complete
echo ========================================
pause
