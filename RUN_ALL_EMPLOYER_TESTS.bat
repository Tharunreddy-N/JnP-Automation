@echo off
echo ========================================
echo Running All Employer Tests Sequentially
echo ========================================
echo.
echo This will run all test cases in test_employer_test_cases.py
echo Tests will run one by one without stopping.
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

echo Starting test execution...
echo.

REM Run all employer tests sequentially using Python script
python run_all_employer_tests.py

echo.
echo ========================================
echo Test Execution Complete!
echo ========================================
echo.
echo Check logs\employer.log for detailed results
echo Check logs\index.html for dashboard
echo.
pause
