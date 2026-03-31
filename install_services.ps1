# FlySafair Price Tracker - Linux Service Installer
# Run this from PowerShell on your Windows PC.

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
if (-not $ScriptDir) { $ScriptDir = Get-Location }
Set-Location $ScriptDir

$LINUX_IP = "192.168.10.173"
$LINUX_USER = "andre"

Write-Host "`n============================================"
Write-Host "   ⚙️ Installing Linux System Services"
Write-Host "   Target: ${LINUX_USER}@${LINUX_IP}"
Write-Host "============================================`n"

# 1. Send Service Files
Write-Host "--- Step 1: Sending Service Files ---"
scp flysafair-dashboard.service flysafair-scraper.service "${LINUX_USER}@${LINUX_IP}:~/flysafair-scraper/"

# 2. Register and Start Services
Write-Host "`n--- Step 2: Registering and Starting Services (Requires Sudo) ---"
# Note: This will ask for your password (Andre@58078)
$RemoteCmd = "sudo mv ~/flysafair-scraper/flysafair-*.service /etc/systemd/system/; " +
             "sudo systemctl daemon-reload; " +
             "sudo systemctl enable flysafair-dashboard flysafair-scraper; " +
             "sudo systemctl restart flysafair-dashboard flysafair-scraper; " +
             "systemctl status flysafair-scraper --no-pager"

ssh -t "${LINUX_USER}@${LINUX_IP}" $RemoteCmd

Write-Host "`n============================================"
Write-Host "   ✅ Services are Installed & Active!"
Write-Host "   The tracker will now start on every boot."
Write-Host "============================================"
