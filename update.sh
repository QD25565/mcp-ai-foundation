#!/bin/bash

echo "MCP AI Foundation - Update Tool"
echo "================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    exit 1
fi

echo "Checking for updates..."
python3 update.py || python update.py

echo ""
read -p "Press Enter to continue..."