# Elite Trading System - PC2 Setup Script
# Run this on PC2 (ProfitTrader) as Administrator to enable remote management
# This script configures PowerShell remoting and firewall rules

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host ""
    Write-Host "  ERROR: This script must be run as Administrator" -ForegroundColor Red
    Write-Host ""
    Write-Host "  Right-click PowerShell and select 'Run as Administrator', then run:" -ForegroundColor Yellow
    Write-Host "    cd $PSScriptRoot" -ForegroundColor Yellow
    Write-Host "    .\setup-pc2.ps1" -ForegroundColor Yellow
    Write-Host ""
    pause
    exit 1
}

Write-Host ""
Write-Host "  ============================================" -ForegroundColor Magenta
Write-Host "   PC2 (ProfitTrader) Setup" -ForegroundColor Magenta
Write-Host "   Configuring for Elite Trading System" -ForegroundColor Magenta
Write-Host "  ============================================" -ForegroundColor Magenta
Write-Host ""

function Log($msg, $color) {
    if ($color) { Write-Host "  $msg" -ForegroundColor $color }
    else { Write-Host "  $msg" }
}

# Step 1: Set network profile to Private
Log "1. Checking network profile..." Cyan
$profiles = Get-NetConnectionProfile
foreach ($profile in $profiles) {
    if ($profile.NetworkCategory -ne "Private") {
        Log "  Setting '$($profile.Name)' to Private..." Yellow
        Set-NetConnectionProfile -Name $profile.Name -NetworkCategory Private
        Log "  Network profile set to Private" Green
    } else {
        Log "  Network profile is already Private" Green
    }
}

# Step 2: Enable PowerShell Remoting
Log ""
Log "2. Enabling PowerShell Remoting..." Cyan
try {
    Enable-PSRemoting -Force -SkipNetworkProfileCheck | Out-Null
    Log "  PowerShell Remoting enabled" Green
} catch {
    Log "  Error enabling PowerShell Remoting: $($_.Exception.Message)" Red
}

# Step 3: Configure WinRM to allow connections from PC1
Log ""
Log "3. Configuring WinRM trusted hosts..." Cyan
$currentTrustedHosts = (Get-Item WSMan:\localhost\Client\TrustedHosts).Value
if ($currentTrustedHosts -eq "" -or $currentTrustedHosts -eq $null) {
    Set-Item WSMan:\localhost\Client\TrustedHosts -Value "*" -Force
    Log "  TrustedHosts set to * (allow all)" Yellow
    Log "  For better security, set this to PC1's IP: 192.168.1.105" DarkGray
} else {
    Log "  TrustedHosts already configured: $currentTrustedHosts" Green
}

# Step 4: Create firewall rules for services
Log ""
Log "4. Configuring Windows Firewall rules..." Cyan

# Ollama API (port 11434)
$ollamaRule = Get-NetFirewallRule -DisplayName "Ollama API" -ErrorAction SilentlyContinue
if (-not $ollamaRule) {
    New-NetFirewallRule -DisplayName "Ollama API" -Direction Inbound -Protocol TCP -LocalPort 11434 -Action Allow -Profile Private | Out-Null
    Log "  Created firewall rule: Ollama API (port 11434)" Green
} else {
    Log "  Firewall rule already exists: Ollama API" DarkGray
}

# Brain gRPC Service (port 50051)
$brainRule = Get-NetFirewallRule -DisplayName "Brain gRPC" -ErrorAction SilentlyContinue
if (-not $brainRule) {
    New-NetFirewallRule -DisplayName "Brain gRPC" -Direction Inbound -Protocol TCP -LocalPort 50051 -Action Allow -Profile Private | Out-Null
    Log "  Created firewall rule: Brain gRPC (port 50051)" Green
} else {
    Log "  Firewall rule already exists: Brain gRPC" DarkGray
}

# WinRM (PowerShell Remoting) - should be auto-created by Enable-PSRemoting, but verify
$winrmRule = Get-NetFirewallRule -DisplayName "Windows Remote Management (HTTP-In)" -ErrorAction SilentlyContinue
if ($winrmRule) {
    Log "  Firewall rule already exists: WinRM (PowerShell Remoting)" DarkGray
} else {
    Log "  WARNING: WinRM firewall rule not found. Enable-PSRemoting should have created it." Yellow
}

# Step 5: Verify WinRM service
Log ""
Log "5. Verifying WinRM service..." Cyan
$winrmService = Get-Service -Name "WinRM"
if ($winrmService.Status -eq "Running") {
    Log "  WinRM service is running" Green
} else {
    Log "  Starting WinRM service..." Yellow
    Start-Service -Name "WinRM"
    Log "  WinRM service started" Green
}

# Step 6: Display network information
Log ""
Log "6. Network information:" Cyan
$ipAddresses = Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.254.*" }
foreach ($ip in $ipAddresses) {
    Log "  IP Address: $($ip.IPAddress) (Interface: $($ip.InterfaceAlias))" Green
}

# Step 7: Test from PC1
Write-Host ""
Write-Host "  ============================================" -ForegroundColor Green
Write-Host "   PC2 Setup Complete!" -ForegroundColor Green
Write-Host "  ============================================" -ForegroundColor Green
Write-Host ""
Log "Next steps:" Yellow
Log "  1. Note your PC2 IP address above" Yellow
Log "  2. On PC1, set CLUSTER_PC2_HOST in backend/.env to this IP" Yellow
Log "  3. Test connectivity from PC1:" Yellow
Write-Host ""
Write-Host "     # On PC1 PowerShell:" -ForegroundColor DarkGray
Write-Host "     Test-Connection -ComputerName <PC2_IP> -Count 2" -ForegroundColor DarkGray
Write-Host "     Invoke-Command -ComputerName <PC2_IP> -ScriptBlock { `$env:COMPUTERNAME }" -ForegroundColor DarkGray
Write-Host ""
Log "  4. Run the dual-PC launcher from PC1:" Yellow
Write-Host "     cd C:\Users\Espen\elite-trading-system" -ForegroundColor DarkGray
Write-Host "     .\start-dual-pc.ps1" -ForegroundColor DarkGray
Write-Host ""
pause
