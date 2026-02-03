@echo off
REM ================================================================================
REM Install Log Viewer API Server as Windows Service (Auto-start on Boot)
REM Run this script as Administrator to install the service
REM ================================================================================

cd /d "%~dp0"

echo ================================================================================
echo Installing Log Viewer API Server as Windows Scheduled Task
echo ================================================================================
echo.

REM Check for admin privileges
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: This script must be run as Administrator!
    echo Right-click and select "Run as administrator"
    pause
    exit /b 1
)

set SCRIPT_PATH=%~dp0START_LOG_VIEWER_API_24x7.bat
set TASK_NAME=LogViewerAPIServer
set TASK_DESCRIPTION=Log Viewer API Server - Runs 24/7 with auto-restart

echo Creating scheduled task...
echo Task Name: %TASK_NAME%
echo Script: %SCRIPT_PATH%
echo.

REM Delete existing task if it exists
schtasks /Delete /TN "%TASK_NAME%" /F >nul 2>&1

REM Create new scheduled task to run at startup
schtasks /Create /TN "%TASK_NAME%" /TR "\"%SCRIPT_PATH%\"" /SC ONSTART /RU SYSTEM /RL HIGHEST /F

if %errorlevel% == 0 (
    echo.
    echo ================================================================================
    echo SUCCESS! API Server service installed successfully!
    echo ================================================================================
    echo.
    echo The API server will now:
    echo   - Start automatically when Windows boots
    echo   - Restart automatically if it crashes
    echo   - Run continuously in the background
    echo.
    echo To start the service now, run:
    echo   schtasks /Run /TN "%TASK_NAME%"
    echo.
    echo To stop the service, run:
    echo   schtasks /End /TN "%TASK_NAME%"
    echo.
    echo To uninstall the service, run:
    echo   schtasks /Delete /TN "%TASK_NAME%" /F
    echo.
) else (
    echo.
    echo ERROR: Failed to create scheduled task!
    echo Please check the error message above.
    echo.
)

pause
