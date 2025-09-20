@echo off
echo ========================================
echo MCP AI Foundation - v1.0.0 Installer
echo ========================================
echo.

REM Check if Python is available
echo Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found!
    echo Please install Python 3.8+ and add it to PATH
    echo Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo.
echo Installing dependencies...
python -m pip install requests --quiet
if %errorlevel% neq 0 (
    echo [WARNING] Failed to install dependencies
    echo Continuing anyway...
)

echo.
echo Running installer...
python install.py
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Installation failed!
    echo Please check the error messages above.
) else (
    echo.
    echo Installation successful!
)

echo.
pause