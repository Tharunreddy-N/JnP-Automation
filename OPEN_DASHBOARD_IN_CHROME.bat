@echo off
REM Quick launcher to open BenchSale Dashboard in Chrome
title BenchSale Dashboard - Chrome

cd /d "%~dp0"

REM Refresh dashboard to latest
python refresh_dashboard.py >nul 2>&1

REM Try to find and open with Chrome
set "CHROME="
for %%p in (
    "%ProgramFiles%\Google\Chrome\Application\chrome.exe"
    "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
    "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"
) do (
    if exist %%p (
        set "CHROME=%%p"
        goto :found
    )
)

:found
if defined CHROME (
    "%CHROME%" "%~dp0logs\index.html"
) else (
    echo Chrome not found. Opening with default browser...
    start "" "%~dp0logs\index.html"
)
