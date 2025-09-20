#!/bin/bash

echo "========================================"
echo "MCP AI Foundation - Uninstaller"
echo "========================================"
echo ""
echo "This will remove MCP tools from Claude Desktop."
echo ""

# Confirm uninstall
read -p "Continue with uninstall? (y/N): " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "Uninstall cancelled."
    exit 0
fi

# Detect Python command
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "[ERROR] Python not found!"
    exit 1
fi

echo ""
echo "Running uninstaller..."
$PYTHON_CMD uninstall.py

if [ $? -eq 0 ]; then
    echo ""
    echo "Uninstall complete!"
else
    echo ""
    echo "[ERROR] Uninstall failed!"
    echo "You may need to manually remove the tools."
fi

echo ""
echo "Press Enter to continue..."
read