@echo off
echo Adding Dashboard Launcher to Windows Startup...
echo.

REM Get the current directory
set "SCRIPT_DIR=%~dp0"
set "BATCH_FILE=%SCRIPT_DIR%OPEN_DASHBOARD.bat"

REM Get the startup folder path
set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"

REM Create VBScript to create shortcut
set "VBS_SCRIPT=%TEMP%\create_dashboard_shortcut.vbs"
echo Set oWS = WScript.CreateObject("WScript.Shell") > "%VBS_SCRIPT%"
echo sLinkFile = "%STARTUP_FOLDER%\Auto Start Dashboard.lnk" >> "%VBS_SCRIPT%"
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> "%VBS_SCRIPT%"
echo oLink.TargetPath = "%BATCH_FILE%" >> "%VBS_SCRIPT%"
echo oLink.WorkingDirectory = "%SCRIPT_DIR%" >> "%VBS_SCRIPT%"
echo oLink.Description = "Auto-start Dashboard with Test Servers" >> "%VBS_SCRIPT%"
echo oLink.WindowStyle = 7 >> "%VBS_SCRIPT%"
echo oLink.Save >> "%VBS_SCRIPT%"

REM Run VBScript
cscript //nologo "%VBS_SCRIPT%"

REM Cleanup
del "%VBS_SCRIPT%"

echo.
echo ✅ Successfully added to Windows Startup!
echo.
echo The dashboard will now start automatically when you log in.
echo You can access it at: http://localhost:8888
echo.
echo You can remove it from: %STARTUP_FOLDER%
echo.
pause
