@echo off
echo ========================================
echo MCP AI Foundation - Uninstaller
echo ========================================
echo.
echo This will remove MCP tools from Claude Desktop.
echo.

REM Confirm uninstall
set /p confirm="Continue with uninstall? (y/N): "
if /i not "%confirm%"=="y" (
    echo Uninstall cancelled.
    pause
    exit /b 0
)

echo.
echo Running uninstaller...
python uninstall.py
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Uninstall failed!
    echo You may need to manually remove the tools.
) else (
    echo.
    echo Uninstall complete!
)

echo.
pause