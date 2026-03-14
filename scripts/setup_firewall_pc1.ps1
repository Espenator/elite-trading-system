# =========== Embodier Trader — Firewall Setup (PC1: ESPENMAIN) ===========
# Run as Administrator on PC1 (ESPENMAIN — 192.168.1.105)
# Opens required ports for cross-PC communication with PC2 (ProfitTrader — 192.168.1.116)

$ErrorActionPreference = "Stop"

Write-Host "=== Embodier Trader Firewall Setup (PC1: ESPENMAIN) ===" -ForegroundColor Cyan
Write-Host "PC1 IP: 192.168.1.105 | PC2 IP: 192.168.1.116`n"

# ── Step 1: Open port 8000/8001 inbound on PC1 (FastAPI API) ──
# So PC2 health proxy can reach PC1's backend API
Write-Host "[1/4] Opening port 8000-8001 inbound (FastAPI API)..." -ForegroundColor Yellow
$existingApi = Get-NetFirewallRule -DisplayName "EmbodierTrader API PC1" -ErrorAction SilentlyContinue
if ($existingApi) {
    Write-Host "  -> Rule already exists. Skipping." -ForegroundColor Green
} else {
    New-NetFirewallRule -DisplayName "EmbodierTrader API PC1" `
        -Direction Inbound -Protocol TCP -LocalPort 8000,8001 -Action Allow `
        -Description "Embodier Trader FastAPI backend (PC1). Allows PC2 health proxy access."
    Write-Host "  -> Created firewall rule for ports 8000-8001." -ForegroundColor Green
}

# ── Step 2: Open port 6379 inbound on PC1 (Redis) ──
# So PC2 can connect to PC1's Redis for cross-PC MessageBus
Write-Host "[2/4] Opening port 6379 inbound (Redis MessageBus bridge)..." -ForegroundColor Yellow
$existingRedis = Get-NetFirewallRule -DisplayName "EmbodierTrader Redis PC1" -ErrorAction SilentlyContinue
if ($existingRedis) {
    Write-Host "  -> Rule already exists. Skipping." -ForegroundColor Green
} else {
    New-NetFirewallRule -DisplayName "EmbodierTrader Redis PC1" `
        -Direction Inbound -Protocol TCP -LocalPort 6379 -Action Allow `
        -Description "Embodier Trader Redis (PC1). Cross-PC MessageBus bridge for PC2."
    Write-Host "  -> Created firewall rule for port 6379." -ForegroundColor Green
}

# ── Step 3: Verify PC2 port 50051 is reachable (gRPC brain_service) ──
Write-Host "[3/4] Testing PC2 brain_service reachability (192.168.1.116:50051)..." -ForegroundColor Yellow
$testResult = Test-NetConnection -ComputerName 192.168.1.116 -Port 50051 -WarningAction SilentlyContinue
if ($testResult.TcpTestSucceeded) {
    Write-Host "  -> PC2 brain_service REACHABLE on port 50051." -ForegroundColor Green
} else {
    Write-Host "  -> PC2 brain_service NOT reachable on port 50051." -ForegroundColor Red
    Write-Host "     Run this on PC2 (ProfitTrader) as Administrator:" -ForegroundColor Yellow
    Write-Host '     New-NetFirewallRule -DisplayName "EmbodierTrader brain_service gRPC" `' -ForegroundColor Gray
    Write-Host '         -Direction Inbound -Protocol TCP -LocalPort 50051 -Action Allow' -ForegroundColor Gray
    Write-Host "     Then start brain_service: cd brain_service && python server.py" -ForegroundColor Gray
}

# ── Step 4: Verify PC2 port 11434 is reachable (Ollama) ──
Write-Host "[4/4] Testing PC2 Ollama reachability (192.168.1.116:11434)..." -ForegroundColor Yellow
$ollamaResult = Test-NetConnection -ComputerName 192.168.1.116 -Port 11434 -WarningAction SilentlyContinue
if ($ollamaResult.TcpTestSucceeded) {
    Write-Host "  -> PC2 Ollama REACHABLE on port 11434." -ForegroundColor Green
} else {
    Write-Host "  -> PC2 Ollama NOT reachable on port 11434." -ForegroundColor Red
    Write-Host "     Ensure Ollama is running on PC2 with OLLAMA_HOST=0.0.0.0" -ForegroundColor Yellow
}

Write-Host "`n=== Firewall setup complete ===" -ForegroundColor Cyan
Write-Host "Summary:"
Write-Host "  PC1 port 8000-8001 (API):  OPEN"
Write-Host "  PC1 port 6379 (Redis):     OPEN"
Write-Host "  PC2 port 50051 (gRPC):     $(if ($testResult.TcpTestSucceeded) {'REACHABLE'} else {'BLOCKED'})"
Write-Host "  PC2 port 11434 (Ollama):   $(if ($ollamaResult.TcpTestSucceeded) {'REACHABLE'} else {'BLOCKED'})"
