@echo off
echo ========================================
echo Run Tests and Verify Dashboard Updates
echo ========================================
echo.
echo This script will:
echo   1. Run tests one by one (Employer, Job Seeker, Bench Sale)
echo   2. After each test, verify if dashboard is updated
echo   3. Show summary of results
echo.
echo ========================================
echo.

cd /d "%~dp0"

echo Checking Python...
python --version
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH!
    pause
    exit /b 1
)
echo.

echo Starting test execution and dashboard verification...
echo.

python run_tests_and_verify_dashboard.py

if errorlevel 1 (
    echo.
    echo ========================================
    echo ERROR: Script execution failed!
    echo ========================================
    echo.
) else (
    echo.
    echo ========================================
    echo Test execution completed!
    echo ========================================
    echo.
    echo Check test_verification_results.json for detailed results.
    echo.
)

pause
