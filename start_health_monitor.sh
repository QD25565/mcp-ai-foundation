#!/bin/bash
# Teambook Health Monitor Startup Script (Mac/Linux)

echo "============================================================"
echo "TEAMBOOK HEALTH MONITOR"
echo "============================================================"
echo ""
echo "Starting health monitoring server..."
echo ""
echo "Once started, open: http://localhost:8765"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""
echo "============================================================"
echo ""

cd "$(dirname "$0")"
python3 web/health_server.py
