@echo off
REM ========================================
REM Add Server Keep-Alive to Windows Startup
REM ========================================
REM This adds the server keep-alive monitor to Windows startup
REM so the server runs automatically when Windows starts

echo ========================================
echo Adding Server Keep-Alive to Windows Startup
echo ========================================
echo.

cd /d "%~dp0"
set SCRIPT_PATH=%~dp0START_SERVER_24_7.bat
set STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup

echo Script path: %SCRIPT_PATH%
echo Startup folder: %STARTUP_FOLDER%
echo.

REM Create shortcut in startup folder
set SHORTCUT_NAME=Test Server Keep-Alive.lnk
set SHORTCUT_PATH=%STARTUP_FOLDER%\%SHORTCUT_NAME%

echo Creating shortcut...
echo.

REM Use PowerShell to create shortcut
powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%SHORTCUT_PATH%'); $Shortcut.TargetPath = '%SCRIPT_PATH%'; $Shortcut.WorkingDirectory = '%~dp0'; $Shortcut.Description = 'Test Server Keep-Alive Monitor - Runs 24/7'; $Shortcut.Save()"

if errorlevel 1 (
    echo.
    echo ========================================
    echo ERROR: Failed to create startup shortcut!
    echo ========================================
    echo.
    echo You can manually add to startup:
    echo 1. Press Win+R
    echo 2. Type: shell:startup
    echo 3. Create shortcut to: %SCRIPT_PATH%
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo SUCCESS: Server Keep-Alive added to startup!
echo ========================================
echo.
echo The server will now start automatically when Windows starts.
echo.
echo To remove from startup:
echo 1. Press Win+R
echo 2. Type: shell:startup
echo 3. Delete: %SHORTCUT_NAME%
echo.
pause
