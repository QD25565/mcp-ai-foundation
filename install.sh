#!/bin/bash
echo "========================================"
echo "MCP AI Foundation - v1.0.0 Installer"
echo "========================================"
echo ""
echo "Installing dependencies..."
python3 -m pip install requests --quiet
echo ""
echo "Running installer..."
python3 install.py
echo ""
echo "Press any key to continue..."
read -n 1