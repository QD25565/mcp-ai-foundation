# MCP AI Foundation - PowerShell Installer
# Run with: .\install.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "MCP AI Foundation - v1.0.0 Installer" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Python is available
Write-Host "Checking Python installation..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✓ Found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Python not found in PATH" -ForegroundColor Red
    Write-Host "  Please install Python 3.8+ first" -ForegroundColor Yellow
    Exit 1
}

# Install dependencies
Write-Host ""
Write-Host "Installing dependencies..." -ForegroundColor Yellow
python -m pip install requests --quiet
Write-Host "✓ Dependencies installed" -ForegroundColor Green

# Run the installer
Write-Host ""
Write-Host "Running installer..." -ForegroundColor Yellow
python install.py

# Pause for user to read output
Write-Host ""
Write-Host "Press any key to continue..." -ForegroundColor Cyan
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")