@echo off
echo Starting Test Queue Watcher...
echo.
echo This will watch for test execution requests from the dashboard.
echo Keep this window open while using the dashboard.
echo.
echo Press Ctrl+C to stop the watcher.
echo.
cd /d "%~dp0"
python utils\test_queue_watcher.py
pause
