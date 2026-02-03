@echo off
REM Start Log Viewer API Server in background
cd /d "%~dp0"

echo ================================================================================
echo Starting Log Viewer API Server (Background)
echo ================================================================================

REM Activate virtual environment if it exists
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else (
    echo WARNING: Virtual environment not found. Using system Python.
)

REM Start the API server in minimized window
start "Log Viewer API" /min python utils\log_history_api.py

echo.
echo API Server starting in background...
echo Server will be available at: http://127.0.0.1:5001
echo.
echo You can now open log_viewer_ui.html in your browser.
echo ================================================================================
