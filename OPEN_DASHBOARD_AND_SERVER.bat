@echo off
setlocal

echo Checking Test Server status...

:: Check if always_on_server is running
tasklist /FI "IMAGENAME eq python.exe" /FI "WINDOWTITLE eq Always-On Test Server" 2>NUL | find /I "python.exe" >NUL
if "%ERRORLEVEL%"=="0" (
    echo Server is already running.
) else (
    echo Server not running. Starting it now...
    :: Start server minized
    start "Always-On Test Server" /min python utils\always_on_server.py
    echo Server started.
)

:: Wait a moment for server to initialize
timeout /t 2 /nobreak >nul

echo Opening Dashboard...
start "" "dashboard_home.html"

echo Done.
endlocal
exit
