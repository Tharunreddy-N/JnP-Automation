@echo off
REM ================================================================================
REM Log Viewer API Server - 24/7 Auto-Restart Version
REM This script keeps the API server running continuously with auto-restart
REM ================================================================================

cd /d "%~dp0"

REM Activate virtual environment if it exists
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else (
    echo WARNING: Virtual environment not found. Using system Python.
)

echo ================================================================================
echo Starting Log Viewer API Server (24/7 Mode with Auto-Restart)
echo ================================================================================
echo.
echo Server will automatically restart if it crashes.
echo Press Ctrl+C to stop the server.
echo.

:restart_loop
echo [%date% %time%] Starting API Server...
echo.

REM Check if port 5001 is already in use
netstat -an | findstr ":5001" >nul
if %errorlevel% == 0 (
    echo [%date% %time%] Port 5001 is already in use. Checking if server is running...
    python -c "import requests; r = requests.get('http://127.0.0.1:5001/api/health', timeout=2); print('Server is already running!')" 2>nul
    if %errorlevel% == 0 (
        echo [%date% %time%] Server is already running. Exiting...
        goto :end
    ) else (
        echo [%date% %time%] Port is in use but server not responding. Killing process...
        for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5001" ^| findstr "LISTENING"') do (
            taskkill /F /PID %%a >nul 2>&1
        )
        timeout /t 2 /nobreak >nul
    )
)

REM Start the API server
python utils\log_history_api.py

REM If we reach here, the server crashed or was stopped
if %errorlevel% == 0 (
    echo [%date% %time%] Server stopped normally.
    goto :end
) else (
    echo [%date% %time%] Server crashed or encountered an error. Restarting in 5 seconds...
    echo.
    timeout /t 5 /nobreak >nul
    goto :restart_loop
)

:end
echo.
echo [%date% %time%] API Server stopped.
echo ================================================================================
pause
