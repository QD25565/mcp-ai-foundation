@echo off
REM Teambook Health Monitor Startup Script (Windows)

echo ============================================================
echo TEAMBOOK HEALTH MONITOR
echo ============================================================
echo.
echo Starting health monitoring server...
echo.
echo Once started, open: http://localhost:8765
echo.
echo Press Ctrl+C to stop the server
echo.
echo ============================================================
echo.

cd /d "%~dp0"
python web\health_server.py

pause
