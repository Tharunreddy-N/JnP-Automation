@echo off
REM Start Log Viewer API Server and open UI
cd /d "%~dp0"

echo ================================================================================
echo Starting Log Viewer API Server
echo ================================================================================

REM Activate virtual environment if it exists
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else (
    echo WARNING: Virtual environment not found. Using system Python.
)

REM Start the API server in background
start "Log Viewer API" /min python utils\log_history_api.py

REM Wait a moment for server to start
timeout /t 3 /nobreak >nul

REM Open the UI in default browser
start "" "log_viewer_ui.html"

echo.
echo ================================================================================
echo Log Viewer started!
echo API Server: http://127.0.0.1:5001
echo UI: log_viewer_ui.html
echo ================================================================================
echo.
echo Press any key to stop the server and exit...
pause >nul

REM Kill the API server
taskkill /FI "WINDOWTITLE eq Log Viewer API*" /F >nul 2>&1
