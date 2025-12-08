<#
.SYNOPSIS
    Elite Trading System Launcher (FIXED PATHS)
.DESCRIPTION
    Launches the complete Elite Trading System with correct paths
.NOTES
    Version: 1.0 FIXED
    Date: December 8, 2025
    NO ONEDRIVE PATHS
#>

# ============================================================================
# CONFIGURATION - AUTOMATIC PATH DETECTION
# ============================================================================

# Detect project root automatically
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$PROJECT_ROOT = $SCRIPT_DIR

$BACKEND_PORT = 8000
$FRONTEND_PORT = 3000

# Colors
$COLOR_SUCCESS = "Green"
$COLOR_ERROR = "Red"
$COLOR_INFO = "Cyan"
$COLOR_WARNING = "Yellow"

# ============================================================================
# BANNER
# ============================================================================

Clear-Host
Write-Host "================================================================================" -ForegroundColor $COLOR_INFO
Write-Host "  🚀 ELITE TRADING SYSTEM LAUNCHER v1.0 🚀" -ForegroundColor $COLOR_INFO
Write-Host "================================================================================" -ForegroundColor $COLOR_INFO
Write-Host ""
Write-Host "  Project Root: $PROJECT_ROOT" -ForegroundColor $COLOR_WARNING
Write-Host ""

# ============================================================================
# STEP 1: VERIFY PROJECT LOCATION
# ============================================================================

Write-Host "[1/7] Verifying project location..." -NoNewline -ForegroundColor $COLOR_INFO

if (-not (Test-Path $PROJECT_ROOT)) {
    Write-Host " ERROR" -ForegroundColor $COLOR_ERROR
    Write-Host "      Project not found: $PROJECT_ROOT" -ForegroundColor $COLOR_ERROR
    Write-Host ""
    Write-Host "  ⚠️ Please run this script from the project root directory!" -ForegroundColor $COLOR_ERROR
    pause
    exit 1
}

Set-Location $PROJECT_ROOT
Write-Host " OK" -ForegroundColor $COLOR_SUCCESS
Write-Host "      Path: $PROJECT_ROOT" -ForegroundColor $COLOR_SUCCESS

# ============================================================================
# STEP 2: VERIFY FILES
# ============================================================================

Write-Host "[2/7] Verifying critical files..." -NoNewline -ForegroundColor $COLOR_INFO

$criticalFiles = @(
    "backend\main.py",
    "elite-trader-ui\package.json",
    "config.yaml"
)

$missingFiles = @()
foreach ($file in $criticalFiles) {
    $fullPath = Join-Path $PROJECT_ROOT $file
    if (-not (Test-Path $fullPath)) {
        $missingFiles += $file
    }
}

if ($missingFiles.Count -gt 0) {
    Write-Host " ERROR" -ForegroundColor $COLOR_ERROR
    Write-Host "      Missing files:" -ForegroundColor $COLOR_ERROR
    foreach ($file in $missingFiles) {
        Write-Host "        - $file" -ForegroundColor $COLOR_ERROR
    }
    pause
    exit 1
}

Write-Host " OK" -ForegroundColor $COLOR_SUCCESS

# ============================================================================
# STEP 3: CLEANUP PROCESSES
# ============================================================================

Write-Host "[3/7] Cleaning up old processes..." -NoNewline -ForegroundColor $COLOR_INFO

Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Get-Process pythonw -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Get-Process node -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

Start-Sleep -Seconds 2
Write-Host " OK" -ForegroundColor $COLOR_SUCCESS

# ============================================================================
# STEP 4: RELEASE PORTS
# ============================================================================

Write-Host "[4/7] Releasing ports $BACKEND_PORT and $FRONTEND_PORT..." -NoNewline -ForegroundColor $COLOR_INFO

$backendConnections = Get-NetTCPConnection -LocalPort $BACKEND_PORT -ErrorAction SilentlyContinue
foreach ($conn in $backendConnections) {
    Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
}

$frontendConnections = Get-NetTCPConnection -LocalPort $FRONTEND_PORT -ErrorAction SilentlyContinue
foreach ($conn in $frontendConnections) {
    Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
}

Start-Sleep -Seconds 2
Write-Host " OK" -ForegroundColor $COLOR_SUCCESS

# ============================================================================
# STEP 5: START BACKEND
# ============================================================================

Write-Host "[5/7] Starting Backend API..." -ForegroundColor $COLOR_INFO
Write-Host "      URL: http://localhost:$BACKEND_PORT" -ForegroundColor $COLOR_WARNING
Write-Host "      Docs: http://localhost:$BACKEND_PORT/docs" -ForegroundColor $COLOR_WARNING

$backendScript = @"
    Set-Location '$PROJECT_ROOT'
    Write-Host "🚀 Starting Backend API on port $BACKEND_PORT..." -ForegroundColor Cyan
    python -m uvicorn backend.main:app --host 0.0.0.0 --port $BACKEND_PORT --reload
"@

Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendScript -WindowStyle Normal
Start-Sleep -Seconds 5

$backendRunning = (Get-NetTCPConnection -LocalPort $BACKEND_PORT -ErrorAction SilentlyContinue) -ne $null
if ($backendRunning) {
    Write-Host "      ✅ Backend started successfully" -ForegroundColor $COLOR_SUCCESS
} else {
    Write-Host "      ⚠️ WARNING: Backend may not have started" -ForegroundColor $COLOR_WARNING
}

# ============================================================================
# STEP 6: START FRONTEND
# ============================================================================

Write-Host "[6/7] Starting Elite Trader UI..." -ForegroundColor $COLOR_INFO
Write-Host "      URL: http://localhost:$FRONTEND_PORT" -ForegroundColor $COLOR_WARNING

$frontendScript = @"
    Set-Location '$PROJECT_ROOT\elite-trader-ui'
    Write-Host "🌐 Starting Elite Trader UI on port $FRONTEND_PORT..." -ForegroundColor Cyan
    npm run dev
"@

Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendScript -WindowStyle Normal
Start-Sleep -Seconds 10

$frontendRunning = (Get-NetTCPConnection -LocalPort $FRONTEND_PORT -ErrorAction SilentlyContinue) -ne $null
if ($frontendRunning) {
    Write-Host "      ✅ Elite Trader UI started successfully" -ForegroundColor $COLOR_SUCCESS
} else {
    Write-Host "      ⚠️ WARNING: Elite Trader UI may not have started" -ForegroundColor $COLOR_WARNING
}

# ============================================================================
# STEP 7: OPEN BROWSER
# ============================================================================

Write-Host "[7/7] Opening browser..." -NoNewline -ForegroundColor $COLOR_INFO

Start-Sleep -Seconds 3
Start-Process "http://localhost:$FRONTEND_PORT"
Start-Sleep -Seconds 1
Start-Process "http://localhost:$BACKEND_PORT/docs"

Write-Host " OK" -ForegroundColor $COLOR_SUCCESS

# ============================================================================
# SUMMARY
# ============================================================================

Write-Host ""
Write-Host "================================================================================" -ForegroundColor $COLOR_INFO
Write-Host "  ✅ ELITE TRADING SYSTEM LAUNCHED SUCCESSFULLY" -ForegroundColor $COLOR_SUCCESS
Write-Host "================================================================================" -ForegroundColor $COLOR_INFO
Write-Host ""
Write-Host "  🎯 ACTIVE SERVICES:" -ForegroundColor $COLOR_INFO
Write-Host "    • Backend API:      http://localhost:$BACKEND_PORT" -ForegroundColor $COLOR_SUCCESS
Write-Host "    • API Docs:         http://localhost:$BACKEND_PORT/docs" -ForegroundColor $COLOR_SUCCESS
Write-Host "    • Elite Trader UI:  http://localhost:$FRONTEND_PORT" -ForegroundColor $COLOR_SUCCESS
Write-Host "    • WebSocket:        ws://localhost:$BACKEND_PORT/ws" -ForegroundColor $COLOR_SUCCESS
Write-Host ""
Write-Host "  📌 PROJECT LOCATION:" -ForegroundColor $COLOR_INFO
Write-Host "    $PROJECT_ROOT" -ForegroundColor $COLOR_WARNING
Write-Host ""
Write-Host "  🛡️ SYSTEM HEALTH:" -ForegroundColor $COLOR_INFO
if ($backendRunning -and $frontendRunning) {
    Write-Host "    ✅ All services running" -ForegroundColor $COLOR_SUCCESS
} else {
    Write-Host "    ⚠️ Some services may need manual start" -ForegroundColor $COLOR_WARNING
}
Write-Host ""
Write-Host "================================================================================" -ForegroundColor $COLOR_INFO
Write-Host ""
Write-Host "Press Ctrl+C to exit health monitor..." -ForegroundColor $COLOR_INFO
Write-Host ""

# ============================================================================
# HEALTH MONITOR
# ============================================================================

while ($true) {
    Start-Sleep -Seconds 30
    
    $backendAlive = (Get-NetTCPConnection -LocalPort $BACKEND_PORT -ErrorAction SilentlyContinue) -ne $null
    $frontendAlive = (Get-NetTCPConnection -LocalPort $FRONTEND_PORT -ErrorAction SilentlyContinue) -ne $null
    $timestamp = Get-Date -Format "HH:mm:ss"
    
    if ($backendAlive -and $frontendAlive) {
        Write-Host "[$timestamp] ✅ System healthy - All services running" -ForegroundColor $COLOR_SUCCESS
    } else {
        if (-not $backendAlive) {
            Write-Host "[$timestamp] ❌ Backend not responding on port $BACKEND_PORT" -ForegroundColor $COLOR_ERROR
        }
        if (-not $frontendAlive) {
            Write-Host "[$timestamp] ❌ Frontend not responding on port $FRONTEND_PORT" -ForegroundColor $COLOR_ERROR
        }
    }
}
