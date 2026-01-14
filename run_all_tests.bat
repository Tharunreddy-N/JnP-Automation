@echo off
REM Sequential Test Runner - Runs Admin tests first, then Recruiter tests
echo ================================================================================
echo BenchSale Sequential Test Runner
echo ================================================================================
echo.
echo This will run:
echo   1. Admin tests first
echo   2. Recruiter tests second
echo.
echo ================================================================================
echo.

python run_all_tests.py

pause
