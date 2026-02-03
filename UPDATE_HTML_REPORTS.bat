@echo off
REM Update all HTML reports with new UI and 7-day history links
cd /d "%~dp0"

echo ================================================================================
echo Updating HTML Reports with 7-Day History Viewer Links
echo ================================================================================

REM Activate virtual environment if it exists
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else (
    echo WARNING: Virtual environment not found. Using system Python.
)

REM Regenerate all HTML log viewers
python -c "from utils.log_viewer import generate_all_log_viewers; generate_all_log_viewers()"

echo.
echo ================================================================================
echo HTML Reports Updated!
echo Each report now has a link to the 7-Day History Viewer
echo ================================================================================
pause
