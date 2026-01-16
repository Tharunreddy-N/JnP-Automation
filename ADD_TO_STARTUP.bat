@echo off
echo Adding Test Servers to Windows Startup...
echo.

REM Get the current directory
set "SCRIPT_DIR=%~dp0"
set "BATCH_FILE=%SCRIPT_DIR%AUTO_START_ALL.bat"

REM Get the startup folder path
set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"

REM Create shortcut in startup folder
echo Creating shortcut in startup folder...
echo Startup folder: %STARTUP_FOLDER%
echo.

REM Create VBScript to create shortcut
set "VBS_SCRIPT=%TEMP%\create_shortcut.vbs"
echo Set oWS = WScript.CreateObject("WScript.Shell") > "%VBS_SCRIPT%"
echo sLinkFile = "%STARTUP_FOLDER%\Auto Start Test Servers.lnk" >> "%VBS_SCRIPT%"
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> "%VBS_SCRIPT%"
echo oLink.TargetPath = "%BATCH_FILE%" >> "%VBS_SCRIPT%"
echo oLink.WorkingDirectory = "%SCRIPT_DIR%" >> "%VBS_SCRIPT%"
echo oLink.Description = "Auto-start Test Servers for Dashboard" >> "%VBS_SCRIPT%"
echo oLink.WindowStyle = 7 >> "%VBS_SCRIPT%"
echo oLink.Save >> "%VBS_SCRIPT%"

REM Run VBScript
cscript //nologo "%VBS_SCRIPT%"

REM Cleanup
del "%VBS_SCRIPT%"

echo.
echo ✅ Successfully added to Windows Startup!
echo.
echo The test servers will now start automatically when you log in.
echo You can remove it from: %STARTUP_FOLDER%
echo.
pause
