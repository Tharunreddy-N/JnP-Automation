@echo off
REM Start Log Viewer API Server only (for background service)
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

REM Start the API server
python utils\log_history_api.py
