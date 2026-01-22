@echo off
REM Simple script to run ALL tests from all suites in one go
echo ================================================================================
echo RUNNING ALL TEST SUITES - EMPLOYER, JOBSEEKER, BENCHSALE
echo ================================================================================
echo.
echo This will run ALL tests from:
echo   - Employer tests
echo   - JobSeeker tests  
echo   - BenchSale Admin tests
echo   - BenchSale Recruiter tests
echo.
echo Tests will continue even if failures occur!
echo ================================================================================
echo.

REM Kill any stuck browser or python processes before running
echo Cleaning up previous test processes...
taskkill /F /IM python.exe 2>nul
taskkill /F /IM chrome.exe 2>nul
taskkill /F /IM msedgedriver.exe 2>nul
timeout /t 2 /nobreak

REM Activate virtual environment if it exists
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

REM Run all tests in one command
pytest tests/ -v --maxfail=0 --continue-on-collection-errors

REM Keep window open to see results
echo.
echo ================================================================================
echo Test execution completed!
echo ================================================================================
pause
    