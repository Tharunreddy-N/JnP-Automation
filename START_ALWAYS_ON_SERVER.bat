@echo off
echo ========================================
echo Starting Always-On Test Server...
echo ========================================
echo.
echo This server will run in the background and process test requests automatically.
echo Keep this window open, or minimize it.
echo.
echo Press Ctrl+C to stop the server.
echo.
cd /d "%~dp0"
echo Current directory: %CD%
echo.
echo Checking Python...
python --version
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH!
    pause
    exit /b 1
)
echo.
echo Starting server...
echo.
python utils\always_on_server.py
if errorlevel 1 (
    echo.
    echo ========================================
    echo ERROR: Server failed to start!
    echo ========================================
    echo.
    echo Possible causes:
    echo 1. Port 8766 is already in use
    echo 2. Another server instance is running
    echo 3. Python script has errors
    echo.
    echo Try:
    echo - Delete .always_on_server.pid file if it exists
    echo - Check if another server is running
    echo - Check the error messages above
    echo.
) else (
    echo.
    echo Server stopped normally.
)
pause
