<#
.SYNOPSIS
    Aurora Elite Trading System Launcher
.DESCRIPTION
    Launches the complete Aurora 24/7 trading system with all components
.NOTES
    Version: 7.0 (Aurora - Glass House Edition)
    Date: December 7, 2025
    Author: Elite Trading Team
#>

# ============================================================================
# CONFIGURATION
# ============================================================================

$PROJECT_ROOT = "C:\Users\Espen\elite-trading-system"
$BACKEND_PORT = 8000
$FRONTEND_PORT = 3000
$ORCHESTRATOR_ENABLED = $false

# Colors for output
$COLOR_SUCCESS = "Green"
$COLOR_ERROR = "Red"
$COLOR_INFO = "Cyan"
$COLOR_WARNING = "Yellow"

# ============================================================================
# BANNER
# ============================================================================

Clear-Host
Write-Host "================================================================================" -ForegroundColor $COLOR_INFO
Write-Host "  AURORA ELITE TRADING SYSTEM v7.0 - GLASS HOUSE EDITION" -ForegroundColor $COLOR_INFO
Write-Host "================================================================================" -ForegroundColor $COLOR_INFO
Write-Host ""

# ============================================================================
# STEP 1: CLEANUP
# ============================================================================

Write-Host "[1/7] Cleaning up processes..." -NoNewline -ForegroundColor $COLOR_INFO
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Get-Process pythonw -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Get-Process node -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
Write-Host " OK" -ForegroundColor $COLOR_SUCCESS

# ============================================================================
# STEP 2: RELEASE PORTS
# ============================================================================

Write-Host "[2/7] Releasing ports..." -NoNewline -ForegroundColor $COLOR_INFO
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
# STEP 3: VERIFY PROJECT
# ============================================================================

Write-Host "[3/7] Verifying project..." -NoNewline -ForegroundColor $COLOR_INFO
if (-not (Test-Path $PROJECT_ROOT)) {
    Write-Host " ERROR" -ForegroundColor $COLOR_ERROR
    Write-Host "      Project not found: $PROJECT_ROOT" -ForegroundColor $COLOR_ERROR
    pause
    exit 1
}
Set-Location $PROJECT_ROOT
Write-Host " OK" -ForegroundColor $COLOR_SUCCESS

# ============================================================================
# STEP 4: VERIFY FILES
# ============================================================================

Write-Host "[4/7] Verifying files..." -NoNewline -ForegroundColor $COLOR_INFO
$criticalFiles = @(
    "backend\main.py",
    "glass-house-ui\package.json",
    "config\config.yaml"
)
$missingFiles = @()
foreach ($file in $criticalFiles) {
    if (-not (Test-Path (Join-Path $PROJECT_ROOT $file))) {
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
# STEP 5: START BACKEND
# ============================================================================

Write-Host "[5/7] Starting Backend API..." -ForegroundColor $COLOR_INFO
Write-Host "      URL: http://localhost:$BACKEND_PORT" -ForegroundColor $COLOR_WARNING

$backendScript = {
    param($root, $port)
    Set-Location $root
    python -m uvicorn backend.main:app --host 0.0.0.0 --port $port --reload
}

Start-Process powershell -ArgumentList "-NoExit", "-Command", "& {$backendScript} -root '$PROJECT_ROOT' -port $BACKEND_PORT" -WindowStyle Normal
Start-Sleep -Seconds 5

$backendRunning = (Get-NetTCPConnection -LocalPort $BACKEND_PORT -ErrorAction SilentlyContinue) -ne $null
if ($backendRunning) {
    Write-Host "      Backend started successfully" -ForegroundColor $COLOR_SUCCESS
} else {
    Write-Host "      WARNING: Backend may not have started" -ForegroundColor $COLOR_WARNING
}

# ============================================================================
# STEP 6: START GLASS HOUSE UI
# ============================================================================

Write-Host "[6/7] Starting Glass House Dashboard..." -ForegroundColor $COLOR_INFO
Write-Host "      URL: http://localhost:$FRONTEND_PORT" -ForegroundColor $COLOR_WARNING

$frontendScript = {
    param($root)
    Set-Location (Join-Path $root "glass-house-ui")
    npm run dev
}

Start-Process powershell -ArgumentList "-NoExit", "-Command", "& {$frontendScript} -root '$PROJECT_ROOT'" -WindowStyle Normal
Start-Sleep -Seconds 10

$frontendRunning = (Get-NetTCPConnection -LocalPort $FRONTEND_PORT -ErrorAction SilentlyContinue) -ne $null
if ($frontendRunning) {
    Write-Host "      Glass House UI started successfully" -ForegroundColor $COLOR_SUCCESS
} else {
    Write-Host "      WARNING: Glass House UI may not have started" -ForegroundColor $COLOR_WARNING
}

# ============================================================================
# STEP 7: ORCHESTRATOR
# ============================================================================

Write-Host "[7/7] Orchestrator Status..." -NoNewline -ForegroundColor $COLOR_INFO
if ($ORCHESTRATOR_ENABLED) {
    Write-Host " Starting..." -ForegroundColor $COLOR_INFO
    $orchestratorScript = {
        param($root)
        Set-Location $root
        python -m core.orchestrator
    }
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "& {$orchestratorScript} -root '$PROJECT_ROOT'" -WindowStyle Normal
    Write-Host "      Orchestrator started" -ForegroundColor $COLOR_SUCCESS
} else {
    Write-Host " Not yet implemented" -ForegroundColor $COLOR_WARNING
}

# ============================================================================
# OPEN BROWSER
# ============================================================================

Write-Host ""
Write-Host "Opening dashboards..." -ForegroundColor $COLOR_INFO
Start-Sleep -Seconds 2
Start-Process "http://localhost:$FRONTEND_PORT"
Start-Sleep -Seconds 1
Start-Process "http://localhost:$BACKEND_PORT/docs"

# ============================================================================
# SUMMARY
# ============================================================================

Write-Host ""
Write-Host "================================================================================" -ForegroundColor $COLOR_INFO
Write-Host "  AURORA SYSTEM LAUNCHED" -ForegroundColor $COLOR_SUCCESS
Write-Host "================================================================================" -ForegroundColor $COLOR_INFO
Write-Host ""
Write-Host "  ACTIVE COMPONENTS:" -ForegroundColor $COLOR_INFO
Write-Host "    Backend API:      http://localhost:$BACKEND_PORT" -ForegroundColor $COLOR_SUCCESS
Write-Host "    Glass House UI:   http://localhost:$FRONTEND_PORT" -ForegroundColor $COLOR_SUCCESS
Write-Host ""
Write-Host "  FUTURE COMPONENTS:" -ForegroundColor $COLOR_INFO
Write-Host "    24/7 Orchestrator (Not yet active)" -ForegroundColor $COLOR_WARNING
Write-Host "    Prediction Engine (Not yet active)" -ForegroundColor $COLOR_WARNING
Write-Host "    Shadow Portfolio (Not yet active)" -ForegroundColor $COLOR_WARNING
Write-Host ""
Write-Host "================================================================================" -ForegroundColor $COLOR_INFO
Write-Host ""
Write-Host "Press Ctrl+C to exit health monitor..." -ForegroundColor $COLOR_INFO
Write-Host ""

# ============================================================================
# HEALTH CHECK
# ============================================================================

while ($true) {
    Start-Sleep -Seconds 30
    $backendAlive = (Get-NetTCPConnection -LocalPort $BACKEND_PORT -ErrorAction SilentlyContinue) -ne $null
    $frontendAlive = (Get-NetTCPConnection -LocalPort $FRONTEND_PORT -ErrorAction SilentlyContinue) -ne $null
    $timestamp = Get-Date -Format "HH:mm:ss"
    
    if ($backendAlive -and $frontendAlive) {
        Write-Host "[$timestamp] System healthy - Backend and Glass House UI running" -ForegroundColor $COLOR_SUCCESS
    } else {
        if (-not $backendAlive) {
            Write-Host "[$timestamp] WARNING: Backend not responding" -ForegroundColor $COLOR_ERROR
        }
        if (-not $frontendAlive) {
            Write-Host "[$timestamp] WARNING: Glass House UI not responding" -ForegroundColor $COLOR_ERROR
        }
    }
}
