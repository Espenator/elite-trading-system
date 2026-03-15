# ============================================================
#  Embodier Trader — Bulletproof Dev Launcher (ProfitTrader PC2)
#  Resolves port conflicts, verifies deps, waits for health.
#  Usage: powershell -ExecutionPolicy Bypass -File start-embodier.ps1
# ============================================================

param(
    [int]$BackendPort  = 8000,
    [int]$FrontendPort = 5173,
    [switch]$NoElectron,
    [switch]$SkipFrontend
)

# Use Continue so non-critical failures don't halt the script.
# Critical failures (missing python, missing .env) exit explicitly.
$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$BackendDir  = Join-Path $Root "backend"
$FrontendDir = Join-Path $Root "frontend-v2"
$DesktopDir  = Join-Path $Root "desktop"

# ── Helpers ──────────────────────────────────────────────────

function Write-Step($num, $total, $msg) {
    Write-Host "`n  [$num/$total] " -NoNewline -ForegroundColor Cyan
    Write-Host $msg -ForegroundColor White
}

function Write-Ok($msg) {
    Write-Host "    [OK] $msg" -ForegroundColor Green
}

function Write-Warn($msg) {
    Write-Host "    [!!] $msg" -ForegroundColor Yellow
}

function Write-Fail($msg) {
    Write-Host "    [FAIL] $msg" -ForegroundColor Red
}

function Get-PortPid($port) {
    # Returns PID(s) listening on a given port, or empty array
    # Uses Get-NetTCPConnection (reliable) with netstat fallback
    $procIds = [System.Collections.ArrayList]@()
    try {
        $conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
        foreach ($c in $conns) {
            if ($c.OwningProcess -gt 0 -and $procIds -notcontains $c.OwningProcess) {
                [void]$procIds.Add($c.OwningProcess)
            }
        }
    } catch {
        # Fallback: parse netstat text output
        try {
            $lines = (netstat -ano | Out-String) -split "`n"
            foreach ($line in $lines) {
                if ($line -match ":$port\s" -and $line -match "LISTENING") {
                    $parts = $line.Trim() -split '\s+'
                    $procId = [int]$parts[-1]
                    if ($procId -gt 0 -and $procIds -notcontains $procId) { [void]$procIds.Add($procId) }
                }
            }
        } catch { }
    }
    return $procIds
}

function Free-Port($port, $serviceName) {
    $procIds = Get-PortPid $port
    if ($procIds.Count -eq 0) {
        Write-Ok "Port $port is free"
        return $true
    }

    foreach ($procId in $procIds) {
        try {
            $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
            $procName = if ($proc) { $proc.ProcessName } else { "unknown" }
            Write-Warn "Port $port in use by $procName (PID $procId) — killing..."
            Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
        } catch {
            Write-Warn "Could not kill PID $procId (may already be gone)"
        }
    }

    # Wait for port to be released
    $maxWait = 10
    for ($i = 0; $i -lt $maxWait; $i++) {
        Start-Sleep -Milliseconds 500
        $still = Get-PortPid $port
        if ($still.Count -eq 0) {
            Write-Ok "Port $port freed successfully"
            return $true
        }
    }

    Write-Fail "Could not free port $port after ${maxWait}s"
    return $false
}

function Wait-ForUrl($url, $timeoutSec, $label) {
    $deadline = (Get-Date).AddSeconds($timeoutSec)
    $startTime = Get-Date
    $dots = ""
    while ((Get-Date) -lt $deadline) {
        try {
            $resp = Invoke-WebRequest -Uri $url -TimeoutSec 2 -UseBasicParsing -ErrorAction SilentlyContinue
            if ($resp.StatusCode -eq 200) {
                $elapsed = [math]::Round(((Get-Date) - $startTime).TotalSeconds, 0)
                Write-Host ""
                Write-Ok "$label is ready (HTTP 200, ${elapsed}s)"
                return $true
            }
        } catch { }
        $dots += "."
        if ($dots.Length -gt 40) { $dots = "." }
        $elapsed = [math]::Round(((Get-Date) - $startTime).TotalSeconds, 0)
        Write-Host "`r    Waiting${dots} (${elapsed}s)   " -NoNewline -ForegroundColor DarkGray
        Start-Sleep -Seconds 2
    }
    Write-Host ""
    Write-Fail "$label did not respond within ${timeoutSec}s"
    return $false
}

# ── Banner ───────────────────────────────────────────────────

$totalSteps = 5
if ($SkipFrontend) { $totalSteps = 3 }
if ($NoElectron)   { $totalSteps-- }

Clear-Host
Write-Host ""
Write-Host "  ============================================" -ForegroundColor Magenta
Write-Host "    EMBODIER TRADER v5.0.0" -ForegroundColor Magenta
Write-Host "    Embodied Intelligence" -ForegroundColor Magenta
Write-Host "    Backend: :$BackendPort  Frontend: :$FrontendPort" -ForegroundColor DarkGray
Write-Host "  ============================================" -ForegroundColor Magenta
Write-Host ""

$stepNum = 0

# ── Step 1: Verify Dependencies ──────────────────────────────

$stepNum++
Write-Step $stepNum $totalSteps "Verifying dependencies..."

# Python
$pythonExe = $null
$venvPython = Join-Path $BackendDir "venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    $pythonExe = $venvPython
    $pyVer = & $pythonExe --version 2>&1
    Write-Ok "Python (venv): $pyVer"
} else {
    try {
        $pyVer = & python --version 2>&1
        $pythonExe = "python"
        Write-Warn "No venv found — using system Python: $pyVer"
    } catch {
        Write-Fail "Python not found! Install Python 3.11+ or create venv in backend/"
        Write-Host "    Run: cd backend && python -m venv venv && venv\Scripts\activate && pip install -r requirements.txt" -ForegroundColor DarkGray
        pause
        exit 1
    }
}

# Check backend .env
$envFile = Join-Path $BackendDir ".env"
if (Test-Path $envFile) {
    Write-Ok "Backend .env found"
} else {
    Write-Fail "Missing backend/.env — copy from .env.example and configure API keys"
    pause
    exit 1
}

if (-not $SkipFrontend) {
    # Node.js
    try {
        $nodeVer = & node --version 2>&1
        Write-Ok "Node.js: $nodeVer"
    } catch {
        Write-Fail "Node.js not found! Install from https://nodejs.org"
        pause
        exit 1
    }

    # node_modules
    $frontendModules = Join-Path $FrontendDir "node_modules"
    if (Test-Path $frontendModules) {
        Write-Ok "Frontend node_modules present"
    } else {
        Write-Warn "node_modules missing — running npm install..."
        Push-Location $FrontendDir
        & npm install 2>&1 | Out-Null
        Pop-Location
        if (Test-Path $frontendModules) {
            Write-Ok "npm install completed"
        } else {
            Write-Fail "npm install failed"
            pause
            exit 1
        }
    }

    # Electron node_modules (if using Electron)
    if (-not $NoElectron) {
        $electronModules = Join-Path $DesktopDir "node_modules"
        if (Test-Path $electronModules) {
            Write-Ok "Electron node_modules present"
        } else {
            Write-Warn "Electron node_modules missing — running npm install..."
            Push-Location $DesktopDir
            & npm install 2>&1 | Out-Null
            Pop-Location
            if (Test-Path $electronModules) {
                Write-Ok "npm install completed"
            } else {
                Write-Warn "Electron npm install failed — will skip Electron"
                $NoElectron = $true
            }
        }
    }
}

# ── Step 2: Resolve Port Conflicts ───────────────────────────

$stepNum++
Write-Step $stepNum $totalSteps "Resolving port conflicts..."

$backendOk = Free-Port $BackendPort "Backend"
if (-not $backendOk) {
    Write-Fail "Cannot start — port $BackendPort stuck. Check Task Manager for stale python.exe"
    pause
    exit 1
}

if (-not $SkipFrontend) {
    $frontendOk = Free-Port $FrontendPort "Frontend"
    if (-not $frontendOk) {
        Write-Warn "Port $FrontendPort stuck — Vite will try next available port"
    }
}

# ── Step 3: Start Backend ────────────────────────────────────

$stepNum++
Write-Step $stepNum $totalSteps "Starting backend on port $BackendPort..."

# Clean stale PID file
$pidFile = Join-Path $BackendDir ".embodier.pid"
if (Test-Path $pidFile) {
    try {
        $pidContent = Get-Content $pidFile -ErrorAction SilentlyContinue
        $pidLine = $pidContent | Where-Object { $_ -match "^pid=" }
        if ($pidLine) {
            $stalePid = [int]($pidLine -replace "^pid=", "")
            $proc = Get-Process -Id $stalePid -ErrorAction SilentlyContinue
            if (-not $proc) {
                Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
                Write-Ok "Cleaned stale PID file (PID $stalePid)"
            }
        }
    } catch {}
}

# Write .embodier-ports.json for Electron and other tools
$portsFile = Join-Path $Root ".embodier-ports.json"
@{ backendPort = $BackendPort; frontendPort = $FrontendPort; updated = (Get-Date).ToString("o") } |
    ConvertTo-Json | Set-Content -Path $portsFile -Encoding utf8 -Force
Write-Ok "Ports saved to .embodier-ports.json (backend:$BackendPort, frontend:$FrontendPort)"

# Activate venv and start
if (Test-Path $venvPython) {
    $activateScript = Join-Path $BackendDir "venv\Scripts\Activate.ps1"
    Start-Process powershell -ArgumentList @(
        "-NoExit", "-Command",
        "`$Host.UI.RawUI.WindowTitle = 'Embodier Backend :$BackendPort'; " +
        "Set-Location '$BackendDir'; " +
        "& '$activateScript'; " +
        "python run_server.py"
    ) -WindowStyle Normal
} else {
    Start-Process cmd -ArgumentList "/k", "title Embodier Backend :$BackendPort && cd /d `"$BackendDir`" && python run_server.py" -WindowStyle Normal
}

# Wait for backend health (backend loads 20+ services, typically takes 30-60s)
$healthy = Wait-ForUrl "http://localhost:$BackendPort/healthz" 120 "Backend"
if (-not $healthy) {
    # Double-check: maybe /healthz is slow but API works
    try {
        $fallback = Invoke-WebRequest -Uri "http://localhost:$BackendPort/healthz" -TimeoutSec 3 -UseBasicParsing -ErrorAction SilentlyContinue
        if ($fallback.StatusCode -eq 200) {
            Write-Ok "Backend responding on /healthz (startup still completing)"
            $healthy = $true
        }
    } catch { }
    if (-not $healthy) {
        Write-Warn "Backend may still be starting — check the backend terminal for errors"
    }
}

if ($SkipFrontend) {
    Write-Host "`n  ============================================" -ForegroundColor Green
    Write-Host "    Backend started on http://localhost:$BackendPort" -ForegroundColor Green
    Write-Host "  ============================================" -ForegroundColor Green
    Write-Host ""
    pause
    exit 0
}

# ── Step 4: Start Frontend ───────────────────────────────────

$stepNum++
Write-Step $stepNum $totalSteps "Starting frontend on port $FrontendPort..."

Start-Process cmd -ArgumentList "/k", "title Embodier Frontend :$FrontendPort && cd /d `"$FrontendDir`" && npm run dev" -WindowStyle Normal

# Wait for Vite dev server
$viteReady = Wait-ForUrl "http://localhost:$FrontendPort" 30 "Frontend (Vite)"
if (-not $viteReady) {
    Write-Warn "Vite may still be bundling — continuing..."
}

# ── Step 5: Start Electron ───────────────────────────────────

if (-not $NoElectron) {
    $stepNum++
    Write-Step $stepNum $totalSteps "Starting Electron desktop app..."

    $env:NODE_ENV = "development"
    Start-Process cmd -ArgumentList "/k", "title Embodier Electron && cd /d `"$DesktopDir`" && set NODE_ENV=development && npx electron ." -WindowStyle Normal

    Start-Sleep -Seconds 2
    Write-Ok "Electron launched"
}

# ── Done ─────────────────────────────────────────────────────

Write-Host ""
Write-Host "  ============================================" -ForegroundColor Green
Write-Host "    All services launched!" -ForegroundColor Green
Write-Host "    Backend:  http://localhost:$BackendPort" -ForegroundColor Green
Write-Host "    Frontend: http://localhost:$FrontendPort" -ForegroundColor Green
Write-Host "    API Health: http://localhost:$BackendPort/healthz" -ForegroundColor DarkGray
Write-Host "  ============================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Press any key to close this launcher window..." -ForegroundColor DarkGray
Write-Host "  (Services keep running independently)" -ForegroundColor DarkGray
pause
