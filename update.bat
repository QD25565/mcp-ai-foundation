@echo off
echo MCP AI Foundation - Update Tool
echo ================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)

echo Checking for updates...
python update.py

echo.
echo Press any key to exit...
pause >nul