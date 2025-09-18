@echo off
echo MCP AI Foundation - Windows Installer
echo =====================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

echo Installing dependencies...
pip install requests >nul 2>&1

echo Running installer...
python install.py

echo.
echo Press any key to exit...
pause >nul