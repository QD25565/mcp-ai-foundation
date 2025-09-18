#!/bin/bash

echo "MCP AI Foundation - Unix Uninstaller"
echo "====================================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    exit 1
fi

echo "Running uninstaller..."
python3 uninstall.py || python uninstall.py

echo ""
read -p "Press Enter to continue..."