@echo off
REM ================================================================================
REM Uninstall Log Viewer API Server Windows Service
REM ================================================================================

cd /d "%~dp0"

set TASK_NAME=LogViewerAPIServer

echo ================================================================================
echo Uninstalling Log Viewer API Server Service
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

echo Stopping task if running...
schtasks /End /TN "%TASK_NAME%" >nul 2>&1

echo Deleting scheduled task...
schtasks /Delete /TN "%TASK_NAME%" /F

if %errorlevel% == 0 (
    echo.
    echo ================================================================================
    echo SUCCESS! API Server service uninstalled successfully!
    echo ================================================================================
) else (
    echo.
    echo Task may not exist or was already deleted.
)

echo.
pause
