# setup-redis.ps1 - Install and configure Redis for cross-PC MessageBus
# Run on PC1 (ESPENMAIN) — PC2 connects to PC1's Redis instance
#
# WHAT THIS DOES:
#   The MessageBus already has full Redis bridge code built in (message_bus.py).
#   This script just installs Redis and configures both PCs to use it.
#
# IMPACT:
#   Before: PC1 and PC2 have separate MessageBus instances, can't share events
#   After:  22 topics bridged in real-time (signals, verdicts, telemetry, etc.)
#           High-frequency market_data.* stays local (zero overhead)
#           DLQ events persist across restarts
#           Cross-PC latency: <5ms on LAN
#
# After running this, set in both PCs' backend/.env:
#   REDIS_URL=redis://192.168.1.105:6379/0

param(
    [string]$PC1IP = "192.168.1.105",
    [int]$RedisPort = 6379
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "  ============================================" -ForegroundColor Cyan
Write-Host "    Redis Setup for Embodier Trader Cluster" -ForegroundColor Cyan
Write-Host "  ============================================" -ForegroundColor Cyan
Write-Host ""

# ----------------------------------------------------------------
# Step 1: Check if Redis is already installed
# ----------------------------------------------------------------
Write-Host "  [1/5] Checking for existing Redis..." -ForegroundColor Yellow

$redisInstalled = $false
try {
    $version = & redis-server --version 2>&1
    if ($version -match "Redis server v") {
        Write-Host "    Redis already installed: $version" -ForegroundColor Green
        $redisInstalled = $true
    }
} catch {
    Write-Host "    Redis not found — will install" -ForegroundColor Gray
}

# ----------------------------------------------------------------
# Step 2: Install Redis via winget or chocolatey
# ----------------------------------------------------------------
if (-not $redisInstalled) {
    Write-Host "  [2/5] Installing Redis..." -ForegroundColor Yellow

    # Try winget first
    $wingetAvailable = $false
    try {
        $null = & winget --version 2>&1
        $wingetAvailable = $true
    } catch {}

    if ($wingetAvailable) {
        Write-Host "    Installing via winget..." -ForegroundColor Gray
        winget install -e --id Redis.Redis --accept-source-agreements --accept-package-agreements
    } else {
        # Try chocolatey
        $chocoAvailable = $false
        try {
            $null = & choco --version 2>&1
            $chocoAvailable = $true
        } catch {}

        if ($chocoAvailable) {
            Write-Host "    Installing via chocolatey..." -ForegroundColor Gray
            choco install redis-64 -y
        } else {
            Write-Host ""
            Write-Host "    Neither winget nor chocolatey found." -ForegroundColor Red
            Write-Host "    Install Redis manually:" -ForegroundColor Red
            Write-Host "      Option A: winget install Redis.Redis" -ForegroundColor White
            Write-Host "      Option B: choco install redis-64" -ForegroundColor White
            Write-Host "      Option C: Download from https://github.com/microsoftarchive/redis/releases" -ForegroundColor White
            Write-Host "      Option D: Use WSL2: sudo apt install redis-server" -ForegroundColor White
            Write-Host ""
            Read-Host "  Press Enter after installing Redis manually"
        }
    }
}

# ----------------------------------------------------------------
# Step 3: Configure Redis for LAN access
# ----------------------------------------------------------------
Write-Host "  [3/5] Configuring Redis for LAN access..." -ForegroundColor Yellow

# Find redis.conf location
$redisConf = ""
$possiblePaths = @(
    "C:\Program Files\Redis\redis.windows.conf",
    "C:\Program Files\Redis\redis.conf",
    "C:\ProgramData\chocolatey\lib\redis-64\redis.windows.conf",
    "$env:USERPROFILE\scoop\apps\redis\current\redis.windows.conf"
)

foreach ($path in $possiblePaths) {
    if (Test-Path $path) {
        $redisConf = $path
        break
    }
}

if ($redisConf) {
    Write-Host "    Found config at: $redisConf" -ForegroundColor Gray

    # Backup original
    $backup = "$redisConf.bak"
    if (-not (Test-Path $backup)) {
        Copy-Item $redisConf $backup
        Write-Host "    Backed up original config" -ForegroundColor Gray
    }

    # Modify bind to allow LAN access
    $content = Get-Content $redisConf -Raw
    if ($content -match "bind 127.0.0.1") {
        $content = $content -replace "bind 127.0.0.1.*", "bind 0.0.0.0"
        Set-Content $redisConf $content
        Write-Host "    Updated bind to 0.0.0.0 (LAN accessible)" -ForegroundColor Green
    }

    # Disable protected mode for LAN
    if ($content -match "protected-mode yes") {
        $content = Get-Content $redisConf -Raw
        $content = $content -replace "protected-mode yes", "protected-mode no"
        Set-Content $redisConf $content
        Write-Host "    Disabled protected-mode (LAN only, no internet exposure)" -ForegroundColor Green
    }
} else {
    Write-Host "    redis.conf not found — Redis will use defaults (localhost only)" -ForegroundColor Yellow
    Write-Host "    You may need to start redis-server with: redis-server --bind 0.0.0.0 --protected-mode no" -ForegroundColor Yellow
}

# ----------------------------------------------------------------
# Step 4: Add firewall rule
# ----------------------------------------------------------------
Write-Host "  [4/5] Adding Windows Firewall rule..." -ForegroundColor Yellow

try {
    $existing = Get-NetFirewallRule -DisplayName "Redis - Embodier Trader" -ErrorAction SilentlyContinue
    if (-not $existing) {
        New-NetFirewallRule -DisplayName "Redis - Embodier Trader" `
            -Direction Inbound -Protocol TCP -LocalPort $RedisPort `
            -Action Allow -Profile Private `
            -Description "Allow Redis connections from LAN for Embodier Trader cluster"
        Write-Host "    Firewall rule created (port $RedisPort, Private network only)" -ForegroundColor Green
    } else {
        Write-Host "    Firewall rule already exists" -ForegroundColor Green
    }
} catch {
    Write-Host "    Could not create firewall rule (run as Admin)" -ForegroundColor Yellow
    Write-Host "    Manually allow TCP port $RedisPort for Private network" -ForegroundColor Yellow
}

# ----------------------------------------------------------------
# Step 5: Install Python redis package
# ----------------------------------------------------------------
Write-Host "  [5/5] Installing Python redis package..." -ForegroundColor Yellow

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$PythonExe = Join-Path $Root "backend\venv\Scripts\python.exe"

if (Test-Path $PythonExe) {
    & $PythonExe -m pip install redis --quiet
    Write-Host "    Python redis package installed" -ForegroundColor Green
} else {
    Write-Host "    Backend venv not found — install manually: pip install redis" -ForegroundColor Yellow
}

# ----------------------------------------------------------------
# Summary
# ----------------------------------------------------------------
Write-Host ""
Write-Host "  ============================================" -ForegroundColor Green
Write-Host "    Redis Setup Complete!" -ForegroundColor Green
Write-Host "  ============================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Next steps:" -ForegroundColor White
Write-Host ""
Write-Host "  1. Start Redis on PC1:" -ForegroundColor Cyan
Write-Host "     redis-server --bind 0.0.0.0 --protected-mode no" -ForegroundColor White
Write-Host ""
Write-Host "  2. Add to BOTH PCs' backend/.env:" -ForegroundColor Cyan
Write-Host "     REDIS_URL=redis://${PC1IP}:${RedisPort}/0" -ForegroundColor White
Write-Host ""
Write-Host "  3. Test from PC2:" -ForegroundColor Cyan
Write-Host "     redis-cli -h $PC1IP ping" -ForegroundColor White
Write-Host "     (should respond: PONG)" -ForegroundColor Gray
Write-Host ""
Write-Host "  4. Restart Embodier Trader on both PCs" -ForegroundColor Cyan
Write-Host "     Look for: 'MessageBus: Redis bridge CONNECTED'" -ForegroundColor Gray
Write-Host ""
Write-Host "  What gets bridged (22 topics):" -ForegroundColor White
Write-Host "     signals, verdicts, orders, risk alerts, telemetry," -ForegroundColor Gray
Write-Host "     swarm ideas/results, scout discoveries, triage," -ForegroundColor Gray
Write-Host "     model updates, knowledge, HITL approvals" -ForegroundColor Gray
Write-Host ""
Write-Host "  What stays local (zero overhead):" -ForegroundColor White
Write-Host "     market_data.bar, market_data.quote" -ForegroundColor Gray
Write-Host "     (thousands/sec — too fast for network)" -ForegroundColor Gray
Write-Host ""
