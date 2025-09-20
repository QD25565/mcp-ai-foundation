@echo off
echo ========================================
echo MCP AI Foundation - v1.0.0 Installer
echo ========================================
echo.
echo Installing dependencies...
python -m pip install requests --quiet
echo.
echo Running installer...
python install.py
echo.
pause