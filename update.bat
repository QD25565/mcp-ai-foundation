@echo off
echo ========================================
echo MCP AI Foundation - v1.0.0 Updater
echo ========================================
echo.
echo This will update your MCP tools to the latest version.
echo Your data and settings will be preserved.
echo.

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found!
    echo Please install Python 3.8+ and add it to PATH
    pause
    exit /b 1
)

echo Running updater...
python update.py
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Update failed!
    echo Please check the error messages above.
) else (
    echo.
    echo Update successful!
)

echo.
pause