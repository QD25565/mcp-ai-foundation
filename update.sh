#!/bin/bash

echo "========================================"
echo "MCP AI Foundation - v1.0.0 Updater"
echo "========================================"
echo ""
echo "This will update your MCP tools to the latest version."
echo "Your data and settings will be preserved."
echo ""

# Detect Python command
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "[ERROR] Python not found!"
    exit 1
fi

echo "Running updater..."
$PYTHON_CMD update.py

if [ $? -eq 0 ]; then
    echo ""
    echo "Update successful!"
else
    echo ""
    echo "[ERROR] Update failed!"
    echo "Please check the error messages above."
fi

echo ""
echo "Press Enter to continue..."
read