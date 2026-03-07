# ─────────────────────────────────────────────────────────────
# Redis Firewall Setup — Run as Administrator on PC1
# Opens port 6379 (Redis) for Private network traffic so PC2
# can connect to PC1's Redis message broker.
# ─────────────────────────────────────────────────────────────

Write-Host "=== Redis Cluster Firewall Setup ===" -ForegroundColor Cyan

# Check for admin
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "ERROR: Run this script as Administrator!" -ForegroundColor Red
    exit 1
}

# Remove existing rule if present (idempotent)
$existing = Get-NetFirewallRule -DisplayName "Redis Cluster" -ErrorAction SilentlyContinue
if ($existing) {
    Remove-NetFirewallRule -DisplayName "Redis Cluster"
    Write-Host "Removed existing Redis firewall rule" -ForegroundColor Yellow
}

# Create inbound rule for Redis (TCP 6379, Private network only)
New-NetFirewallRule `
    -DisplayName "Redis Cluster" `
    -Direction Inbound `
    -Protocol TCP `
    -LocalPort 6379 `
    -Action Allow `
    -Profile Private `
    -Description "Allow Redis connections from cluster nodes on private LAN"

Write-Host ""
Write-Host "Firewall rule created:" -ForegroundColor Green
Get-NetFirewallRule -DisplayName "Redis*" | Select-Object DisplayName, Enabled, Direction, Profile | Format-Table -AutoSize

Write-Host ""
Write-Host "Verify from PC2 with:" -ForegroundColor Cyan
Write-Host "  Test-NetConnection -ComputerName 192.168.1.105 -Port 6379" -ForegroundColor White
Write-Host ""
Write-Host "Done!" -ForegroundColor Green
