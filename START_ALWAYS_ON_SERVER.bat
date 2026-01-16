@echo off
echo Starting Always-On Test Server...
echo.
echo This server will run in the background and process test requests automatically.
echo Keep this window open, or minimize it.
echo.
echo Press Ctrl+C to stop the server.
echo.
cd /d "%~dp0"
python utils\always_on_server.py
pause
