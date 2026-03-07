<#
.SYNOPSIS
    Embodier Trader — One-click launcher for backend + frontend.
.DESCRIPTION
    Starts the FastAPI backend and Vite dev server, with auto-restart,
    health checks, and clean shutdown on Ctrl+C.
.PARAMETER SkipFrontend
    Start backend only (useful for API-only work or ProfitTrader PC).
.PARAMETER BackendPort
    Override backend port (default: from .env PORT or 8000).
.PARAMETER FrontendPort
    Override frontend port (default: from .env FRONTEND_PORT or 3000).
.PARAMETER MaxRestarts
    Max restart attempts per service before giving up (default: 3).
#>
param(
    [switch]$SkipFrontend,
    [int]$BackendPort = 0,
    [int]$FrontendPort = 0,
    [int]$MaxRestarts = 3
)

$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = "$Root\backend"
$FrontendDir = "$Root\frontend-v2"
$LogDir = "$Root\logs"
$EnvFile = "$BackendDir\.env"

# ── Ensure logs directory ──
if (!(Test-Path $LogDir)) { New-Item -ItemType Directory $LogDir -Force | Out-Null }

# ── Helper: read value from .env ──
function Get-EnvValue($Key, $Default) {
    if (Test-Path $EnvFile) {
        $line = Get-Content $EnvFile | Where-Object { $_ -match "^$Key=" }
        if ($line) { return ($line -split "=", 2)[1].Trim() }
    }
    return $Default
}

# ── Resolve ports ──
if ($BackendPort -eq 0) { $BackendPort = [int](Get-EnvValue "PORT" "8000") }
if ($FrontendPort -eq 0) { $FrontendPort = [int](Get-EnvValue "FRONTEND_PORT" "3000") }

# ── Banner ──
Write-Host ""
Write-Host "  ╔══════════════════════════════════════════╗" -ForegroundColor DarkCyan
Write-Host "  ║        EMBODIER TRADER  v4.0.0           ║" -ForegroundColor DarkCyan
Write-Host "  ║  Backend :$BackendPort  |  Frontend :$FrontendPort        ║" -ForegroundColor DarkCyan
Write-Host "  ╚══════════════════════════════════════════╝" -ForegroundColor DarkCyan
Write-Host ""

# ── Fix .env encoding (remove BOM if present) ──
if (Test-Path $EnvFile) {
    $bytes = [IO.File]::ReadAllBytes($EnvFile)
    if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
        [IO.File]::WriteAllText($EnvFile, [IO.File]::ReadAllText($EnvFile, [Text.Encoding]::UTF8), (New-Object Text.UTF8Encoding($false)))
        Write-Host "  [fix] Removed BOM from .env" -ForegroundColor Yellow
    }
} elseif (Test-Path "$BackendDir\.env.example") {
    Copy-Item "$BackendDir\.env.example" $EnvFile
    Write-Host "  [setup] Created .env from .env.example — edit with your API keys" -ForegroundColor Yellow
}

# ── Kill any stale processes on our ports ──
@($BackendPort, $FrontendPort) | ForEach-Object {
    Get-NetTCPConnection -LocalPort $_ -ErrorAction SilentlyContinue | ForEach-Object {
        Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
    }
}
Start-Sleep 1

# ── Ensure Python venv exists ──
Set-Location $BackendDir
if (!(Test-Path "venv")) {
    Write-Host "  [setup] Creating Python virtual environment..." -ForegroundColor Cyan
    python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  [ERROR] Failed to create venv. Is Python 3.10+ installed?" -ForegroundColor Red
        Write-Host "          Download from https://python.org/downloads" -ForegroundColor Yellow
        exit 1
    }
}

# ── Activate venv and install deps if needed ──
& .\venv\Scripts\Activate.ps1
$needInstall = $false
try { python -c "import fastapi" 2>&1 | Out-Null } catch { $needInstall = $true }
if ($LASTEXITCODE -ne 0) { $needInstall = $true }
if ($needInstall) {
    Write-Host "  [setup] Installing Python dependencies..." -ForegroundColor Cyan
    pip install -r requirements.txt --quiet 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  [ERROR] pip install failed. Check requirements.txt" -ForegroundColor Red
        exit 1
    }
}

# ── Start backend (as a background job with restart loop) ──
$backendJob = Start-Job -ScriptBlock {
    param($dir, $port, $logFile, $maxRestarts)
    Set-Location $dir
    & .\venv\Scripts\Activate.ps1
    $env:PORT = $port
    $env:PYTHONIOENCODING = "utf-8"
    $env:PYTHONUNBUFFERED = "1"
    $restarts = 0
    while ($restarts -le $maxRestarts) {
        if ($restarts -gt 0) {
            "$(Get-Date -Format 'HH:mm:ss') [RESTART $restarts/$maxRestarts]" | Tee-Object $logFile -Append
            Start-Sleep 5
        }
        try {
            python start_server.py 2>&1 | Tee-Object $logFile -Append
        } catch {
            "$_" | Tee-Object $logFile -Append
        }
        $restarts++
    }
    "$(Get-Date -Format 'HH:mm:ss') [FATAL] Backend exceeded $maxRestarts restarts" | Tee-Object $logFile -Append
} -ArgumentList $BackendDir, $BackendPort, "$LogDir\backend.log", $MaxRestarts

# ── Wait for backend health ──
Write-Host "  Waiting for backend" -ForegroundColor Cyan -NoNewline
$healthy = $false
for ($i = 0; $i -lt 60; $i++) {
    Start-Sleep 1
    try {
        $response = Invoke-WebRequest "http://localhost:$BackendPort/health" -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) { $healthy = $true; break }
    } catch { }
    Write-Host "." -NoNewline
}
Write-Host ""
if ($healthy) {
    Write-Host "  [OK] Backend   http://localhost:$BackendPort" -ForegroundColor Green
    Write-Host "       API Docs  http://localhost:$BackendPort/docs" -ForegroundColor DarkGray
} else {
    Write-Host "  [WARN] Backend may not be ready yet. Check logs\backend.log" -ForegroundColor Yellow
    # Don't exit — it might still come up (23+ services take time)
}

# ── Start frontend (unless skipped) ──
$frontendJob = $null
if (!$SkipFrontend) {
    Set-Location $FrontendDir

    # Ensure node_modules
    if (!(Test-Path "node_modules")) {
        Write-Host "  [setup] Installing frontend dependencies..." -ForegroundColor Cyan
        npm install --silent 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Write-Host "  [ERROR] npm install failed. Is Node.js 18+ installed?" -ForegroundColor Red
            Write-Host "          Download from https://nodejs.org" -ForegroundColor Yellow
        }
    }

    $frontendJob = Start-Job -ScriptBlock {
        param($dir, $backendPort, $frontendPort, $logFile, $maxRestarts)
        Set-Location $dir
        $env:VITE_BACKEND_URL = "http://localhost:$backendPort"
        $restarts = 0
        while ($restarts -le $maxRestarts) {
            if ($restarts -gt 0) {
                "$(Get-Date -Format 'HH:mm:ss') [RESTART FE $restarts/$maxRestarts]" | Tee-Object $logFile -Append
                Start-Sleep 3
            }
            try {
                npx vite --port $frontendPort --host 2>&1 | Tee-Object $logFile -Append
            } catch {
                "$_" | Tee-Object $logFile -Append
            }
            $restarts++
        }
    } -ArgumentList $FrontendDir, $BackendPort, $FrontendPort, "$LogDir\frontend.log", $MaxRestarts

    Start-Sleep 3
    Write-Host "  [OK] Frontend  http://localhost:$FrontendPort" -ForegroundColor Green

    # Open browser
    Start-Sleep 2
    Start-Process "http://localhost:$FrontendPort"
}

# ── Running banner ──
Write-Host ""
Write-Host "  RUNNING  |  Press Ctrl+C to stop" -ForegroundColor Green
Write-Host "  Logs:  $LogDir\backend.log  /  frontend.log" -ForegroundColor DarkGray
Write-Host ""

# ── Monitor loop + clean shutdown ──
try {
    while ($true) {
        Start-Sleep 10
        if ($backendJob.State -eq "Failed") {
            Write-Host "  [ERROR] Backend crashed. See logs\backend.log" -ForegroundColor Red
            Receive-Job $backendJob
            break
        }
    }
} finally {
    Write-Host ""
    Write-Host "  Shutting down..." -ForegroundColor Yellow
    if ($backendJob) { Stop-Job $backendJob -ErrorAction SilentlyContinue; Remove-Job $backendJob -ErrorAction SilentlyContinue }
    if ($frontendJob) { Stop-Job $frontendJob -ErrorAction SilentlyContinue; Remove-Job $frontendJob -ErrorAction SilentlyContinue }
    @($BackendPort, $FrontendPort) | ForEach-Object {
        Get-NetTCPConnection -LocalPort $_ -ErrorAction SilentlyContinue | ForEach-Object {
            Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
        }
    }
    Write-Host "  [OK] Stopped." -ForegroundColor Green
}
