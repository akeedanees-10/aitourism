@echo off
setlocal
title VoyAIge - AI Tourism Recommendation Web Application
echo ======================================================================
echo    Starting VoyAIge - AI Tourism Recommendation Web Application
echo ======================================================================
cd /d "%~dp0"

REM Check for virtual environment Python
if exist "%~dp0\.venv\Scripts\python.exe" (
    "%~dp0\.venv\Scripts\python.exe" run.py %*
) else (
    python run.py %*
)

if %ERRORLEVEL% neq 0 (
    echo.
    echo [Notice] Server exited with error code %ERRORLEVEL%.
    pause
)
