#!/bin/bash

echo "========================================"
echo "MCP AI Foundation - v1.0.0 Installer"
echo "========================================"
echo ""

# Detect Python command
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "[ERROR] Python not found!"
    echo "Please install Python 3.8+ first"
    echo "  Mac: brew install python3"
    echo "  Linux: sudo apt install python3"
    exit 1
fi

echo "Found Python: $($PYTHON_CMD --version)"
echo ""

echo "Installing dependencies..."
$PYTHON_CMD -m pip install requests --quiet
if [ $? -ne 0 ]; then
    echo "[WARNING] Failed to install dependencies"
    echo "You may need to run: pip install requests"
fi

echo ""
echo "Running installer..."
$PYTHON_CMD install.py

if [ $? -eq 0 ]; then
    echo ""
    echo "Installation successful!"
else
    echo ""
    echo "[ERROR] Installation failed!"
    echo "Please check the error messages above."
fi

echo ""
echo "Press Enter to continue..."
read