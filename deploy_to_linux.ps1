# FlySafair Price Tracker - Windows to Linux Deployer
# This version is optimized for PowerShell 5.1/7.0

# 1. Automatically Go to the folder where this script is located
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
if (-not $ScriptDir) { $ScriptDir = Get-Location }
Set-Location $ScriptDir

$LINUX_IP = "192.168.10.173"
$LINUX_USER = "andre"

Write-Host "============================================"
Write-Host "   Deploying FlySafair Scraper to Linux"
Write-Host "   Target: ${LINUX_USER}@${LINUX_IP}"
Write-Host "============================================"

# Step 1: Transfer Files
Write-Host "--- Step 1: Sending Files ---"
# Note: Enter your password (Andre@58078) when prompted
# We use -r to copy the folder contents
scp -r * "${LINUX_USER}@${LINUX_IP}:~/flysafair-scraper"

# Step 2: Run Setup
Write-Host "--- Step 2: Running Setup on Linux ---"
# Use semicolons instead of && to avoid PowerShell 5 parsing issues
$RemoteCmd = "cd ~/flysafair-scraper; chmod +x setup_linux.sh start_scraper.sh; ./setup_linux.sh"
ssh "${LINUX_USER}@${LINUX_IP}" $RemoteCmd

Write-Host "============================================"
Write-Host "   Deployment Complete!"
Write-Host "   To start the scraper on Linux, run:"
Write-Host "   ssh ${LINUX_USER}@${LINUX_IP} 'cd ~/flysafair-scraper; ./start_scraper.sh'"
Write-Host "============================================"
