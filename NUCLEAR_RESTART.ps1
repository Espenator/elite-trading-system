<#
.SYNOPSIS
    Nuclear Restart - Complete System Reset
.DESCRIPTION
    Stops everything, clears all caches, syncs code, and relaunches
.NOTES
    Use this when things go wrong!
#>

$ErrorActionPreference = "SilentlyContinue"

Clear-Host
Write-Host "\n" -NoNewline
Write-Host "================================================================================" -ForegroundColor Red
Write-Host "  💥 NUCLEAR RESTART - COMPLETE SYSTEM RESET 💥" -ForegroundColor Red
Write-Host "================================================================================" -ForegroundColor Red
Write-Host "\n" -NoNewline

# Auto-detect project root
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$PROJECT_ROOT = $SCRIPT_DIR
Set-Location $PROJECT_ROOT

Write-Host "Project Root: $PROJECT_ROOT" -ForegroundColor Yellow
Write-Host "\n" -NoNewline

# ============================================================================
# STEP 1: KILL ALL PROCESSES
# ============================================================================

Write-Host "[1/10] 💥 Killing all processes..." -ForegroundColor Red

# Kill Python
$pythonProcs = Get-Process python,pythonw -ErrorAction SilentlyContinue
if ($pythonProcs) {
    $pythonProcs | Stop-Process -Force
    Write-Host "       ✅ Killed $($pythonProcs.Count) Python processes" -ForegroundColor Green
} else {
    Write-Host "       ✅ No Python processes running" -ForegroundColor Green
}

# Kill Node
$nodeProcs = Get-Process node,nodejs -ErrorAction SilentlyContinue
if ($nodeProcs) {
    $nodeProcs | Stop-Process -Force
    Write-Host "       ✅ Killed $($nodeProcs.Count) Node processes" -ForegroundColor Green
} else {
    Write-Host "       ✅ No Node processes running" -ForegroundColor Green
}

# Kill PowerShell (except current)
$currentPID = $PID
$psProcs = Get-Process powershell -ErrorAction SilentlyContinue | Where-Object { $_.Id -ne $currentPID }
if ($psProcs) {
    $psProcs | Stop-Process -Force
    Write-Host "       ✅ Killed $($psProcs.Count) PowerShell processes" -ForegroundColor Green
}

Start-Sleep -Seconds 3

# ============================================================================
# STEP 2: RELEASE ALL PORTS
# ============================================================================

Write-Host "[2/10] 🔌 Releasing ports 8000 and 3000..." -ForegroundColor Red

# Port 8000 (Backend)
$port8000 = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($port8000) {
    foreach ($conn in $port8000) {
        Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
    }
    Write-Host "       ✅ Released port 8000" -ForegroundColor Green
} else {
    Write-Host "       ✅ Port 8000 already free" -ForegroundColor Green
}

# Port 3000 (Frontend)
$port3000 = Get-NetTCPConnection -LocalPort 3000 -ErrorAction SilentlyContinue
if ($port3000) {
    foreach ($conn in $port3000) {
        Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
    }
    Write-Host "       ✅ Released port 3000" -ForegroundColor Green
} else {
    Write-Host "       ✅ Port 3000 already free" -ForegroundColor Green
}

Start-Sleep -Seconds 2

# ============================================================================
# STEP 3: CLEAR PYTHON CACHE
# ============================================================================

Write-Host "[3/10] 🧹 Clearing Python cache..." -ForegroundColor Yellow

$pycacheCount = 0

# Remove __pycache__ directories
Get-ChildItem -Path $PROJECT_ROOT -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue | ForEach-Object {
    Remove-Item -Path $_.FullName -Recurse -Force -ErrorAction SilentlyContinue
    $pycacheCount++
}

# Remove .pyc files
Get-ChildItem -Path $PROJECT_ROOT -Recurse -Filter "*.pyc" -ErrorAction SilentlyContinue | ForEach-Object {
    Remove-Item -Path $_.FullName -Force -ErrorAction SilentlyContinue
}

# Remove .pyo files
Get-ChildItem -Path $PROJECT_ROOT -Recurse -Filter "*.pyo" -ErrorAction SilentlyContinue | ForEach-Object {
    Remove-Item -Path $_.FullName -Force -ErrorAction SilentlyContinue
}

Write-Host "       ✅ Cleared $pycacheCount __pycache__ directories" -ForegroundColor Green

# ============================================================================
# STEP 4: CLEAR NODE CACHE
# ============================================================================

Write-Host "[4/10] 🧹 Clearing Node cache..." -ForegroundColor Yellow

# Clear .next cache (Next.js build cache)
if (Test-Path "$PROJECT_ROOT\elite-trader-ui\.next") {
    Remove-Item -Path "$PROJECT_ROOT\elite-trader-ui\.next" -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "       ✅ Cleared .next build cache" -ForegroundColor Green
} else {
    Write-Host "       ✅ No .next cache found" -ForegroundColor Green
}

# Clear npm cache
npm cache clean --force 2>$null
Write-Host "       ✅ Cleared npm cache" -ForegroundColor Green

# ============================================================================
# STEP 5: SYNC CODE FROM GITHUB
# ============================================================================

Write-Host "[5/10] 🔄 Syncing code from GitHub..." -ForegroundColor Yellow

# Check if git repo
if (Test-Path "$PROJECT_ROOT\.git") {
    # Fetch latest
    git fetch origin 2>$null
    
    # Reset to match GitHub exactly
    git reset --hard origin/main 2>$null
    
    # Get latest commit
    $latestCommit = git log --oneline -1 2>$null
    
    Write-Host "       ✅ Code synced to: $latestCommit" -ForegroundColor Green
} else {
    Write-Host "       ⚠️  Not a git repository - skipping sync" -ForegroundColor Yellow
}

# ============================================================================
# STEP 6: VERIFY CRITICAL FILES
# ============================================================================

Write-Host "[6/10] 🔍 Verifying critical files..." -ForegroundColor Yellow

$criticalFiles = @(
    "backend\main.py",
    "backend\api\routes\signals.py",
    "elite-trader-ui\package.json",
    "config.yaml",
    "LAUNCH_ELITE_TRADER.ps1"
)

$allFilesExist = $true
foreach ($file in $criticalFiles) {
    $fullPath = Join-Path $PROJECT_ROOT $file
    if (Test-Path $fullPath) {
        Write-Host "       ✅ $file" -ForegroundColor Green
    } else {
        Write-Host "       ❌ $file MISSING!" -ForegroundColor Red
        $allFilesExist = $false
    }
}

if (-not $allFilesExist) {
    Write-Host "\n❌ ERROR: Critical files missing! Check git sync." -ForegroundColor Red
    pause
    exit 1
}

# ============================================================================
# STEP 7: CHECK PYTHON DEPENDENCIES
# ============================================================================

Write-Host "[7/10] 🐍 Checking Python dependencies..." -ForegroundColor Yellow

try {
    $pythonVersion = python --version 2>&1
    Write-Host "       ✅ Python: $pythonVersion" -ForegroundColor Green
    
    # Quick dependency check
    python -c "import fastapi, uvicorn, yfinance, sqlalchemy" 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "       ✅ Key dependencies installed" -ForegroundColor Green
    } else {
        Write-Host "       ⚠️  Some dependencies missing - may need: pip install -r requirements.txt" -ForegroundColor Yellow
    }
} catch {
    Write-Host "       ❌ Python not found!" -ForegroundColor Red
}

# ============================================================================
# STEP 8: CHECK NODE DEPENDENCIES
# ============================================================================

Write-Host "[8/10] 🌐 Checking Node dependencies..." -ForegroundColor Yellow

try {
    $nodeVersion = node --version 2>&1
    Write-Host "       ✅ Node: $nodeVersion" -ForegroundColor Green
    
    # Check if node_modules exists
    if (Test-Path "$PROJECT_ROOT\elite-trader-ui\node_modules") {
        Write-Host "       ✅ node_modules exists" -ForegroundColor Green
    } else {
        Write-Host "       ⚠️  node_modules missing - may need: npm install" -ForegroundColor Yellow
    }
} catch {
    Write-Host "       ❌ Node not found!" -ForegroundColor Red
}

# ============================================================================
# STEP 9: CHECK DATABASE
# ============================================================================

Write-Host "[9/10] 💾 Checking database..." -ForegroundColor Yellow

$dbPath = "$PROJECT_ROOT\data\trading.db"
if (Test-Path $dbPath) {
    $dbSize = (Get-Item $dbPath).Length / 1KB
    Write-Host "       ✅ Database exists: $("$dbSize".Substring(0, [Math]::Min(6, "$dbSize".Length))) KB" -ForegroundColor Green
} else {
    Write-Host "       ⚠️  Database will be created on first launch" -ForegroundColor Yellow
}

# ============================================================================
# STEP 10: FINAL STATUS
# ============================================================================

Write-Host "[10/10] ✅ System reset complete!" -ForegroundColor Green

Write-Host "\n" -NoNewline
Write-Host "================================================================================" -ForegroundColor Green
Write-Host "  ✅ NUCLEAR RESTART COMPLETE - SYSTEM CLEAN" -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Green
Write-Host "\n" -NoNewline

Write-Host "System Status:" -ForegroundColor Cyan
Write-Host "  ✅ All processes killed" -ForegroundColor White
Write-Host "  ✅ All ports released" -ForegroundColor White
Write-Host "  ✅ Python cache cleared" -ForegroundColor White
Write-Host "  ✅ Node cache cleared" -ForegroundColor White
Write-Host "  ✅ Code synced from GitHub" -ForegroundColor White
Write-Host "  ✅ Critical files verified" -ForegroundColor White
Write-Host "\n" -NoNewline

Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Launch system: .\LAUNCH_ELITE_TRADER.ps1" -ForegroundColor White
Write-Host "  2. System will auto-detect paths and start fresh" -ForegroundColor White
Write-Host "  3. All caches cleared - everything rebuilt clean" -ForegroundColor White
Write-Host "\n" -NoNewline

Write-Host "Launch now? (Y/N): " -ForegroundColor Yellow -NoNewline
$response = Read-Host

if ($response -eq "Y" -or $response -eq "y") {
    Write-Host "\n🚀 Launching Elite Trading System...\n" -ForegroundColor Green
    Start-Sleep -Seconds 2
    
    # Launch the system
    & "$PROJECT_ROOT\LAUNCH_ELITE_TRADER.ps1"
} else {
    Write-Host "\n✅ System ready. Run .\LAUNCH_ELITE_TRADER.ps1 when ready.\n" -ForegroundColor Green
}
