@echo off
REM ================================================================================
REM Quick Start - Log Viewer API Server (24/7 Mode)
REM This starts the server immediately with auto-restart
REM ================================================================================

cd /d "%~dp0"

echo Starting API Server in 24/7 mode...
start "Log Viewer API - 24/7" /min cmd /c "START_LOG_VIEWER_API_24x7.bat"

timeout /t 3 /nobreak >nul

REM Check if server started
python -c "import requests; r = requests.get('http://127.0.0.1:5001/api/health', timeout=3); print('✅ API Server is running!')" 2>nul
if %errorlevel% == 0 (
    echo.
    echo ✅ API Server started successfully!
    echo Server URL: http://127.0.0.1:5001
    echo.
) else (
    echo.
    echo ⚠️  Server may still be starting. Please wait a few seconds and check again.
    echo.
)

pause
