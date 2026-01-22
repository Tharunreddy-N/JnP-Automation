@echo off
REM Continuous Test Runner - Runs ALL test suites (Employer, JobSeeker, BenchSale) without stopping
REM This script is designed to work with Windows Task Scheduler
REM Set working directory to script location
cd /d "%~dp0"

echo ================================================================================
echo CONTINUOUS TEST RUNNER - ALL TEST SUITES
echo Started at: %date% %time%
echo ================================================================================
echo.
echo This will run ALL test suites continuously:
echo   1. BENCHSALE ADMIN Tests
echo   2. BENCHSALE RECRUITER Tests
echo   3. EMPLOYER Tests
echo   4. JOBSEEKER Tests
echo.
echo Tests will continue even if failures occur!
echo ================================================================================
echo.

REM Activate virtual environment if it exists
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else (
    echo WARNING: Virtual environment not found. Using system Python.
)

REM Run the Python script with full path
python run_all_test_suites_continuous.py

REM Log completion
echo.
echo ================================================================================
echo Test execution completed at: %date% %time%
echo ================================================================================

REM Only pause if running interactively (not from Task Scheduler)
REM Check if running in a visible window (not minimized/hidden)
if "%SESSIONNAME%"=="Console" (
    pause
)
