#!/bin/bash

echo "MCP AI Foundation - Unix Installer"
echo "==================================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python 3.8+ first"
    exit 1
fi

echo "Installing dependencies..."
pip3 install requests &> /dev/null || pip install requests &> /dev/null

echo "Running installer..."
python3 install.py || python install.py

echo ""
echo "Installation complete!"
read -p "Press Enter to continue..."