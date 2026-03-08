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

# Ensure logs directory
if (!(Test-Path $LogDir)) { New-Item -ItemType Directory $LogDir -Force | Out-Null }

# ── Timestamped log helper ──
function Log($msg, $color) {
    $ts = Get-Date -Format "HH:mm:ss"
    if ($color) { Write-Host "  [$ts] $msg" -ForegroundColor $color }
    else { Write-Host "  [$ts] $msg" }
}

# Helper: read value from .env
function Get-EnvValue($Key, $Default) {
    if (Test-Path $EnvFile) {
        $line = Get-Content $EnvFile | Where-Object { $_ -match "^$Key=" }
        if ($line) { return ($line -split "=", 2)[1].Trim() }
    }
    return $Default
}

# ── Pre-flight: Validate Python & Node are on PATH ──
function Test-Prerequisites {
    $ok = $true
    try {
        $pyVer = & python --version 2>&1
        if ($pyVer -match "(\d+\.\d+)") {
            $v = [version]$Matches[1]
            if ($v -lt [version]"3.10") {
                Log "Python $($Matches[1]) found but 3.10+ required" Red
                $ok = $false
            } else {
                Log "Python $pyVer" Green
            }
        }
    } catch {
        Log "Python not found on PATH. Install from https://python.org/downloads" Red
        $ok = $false
    }

    if (!$SkipFrontend) {
        try {
            $nodeVer = & node --version 2>&1
            if ($nodeVer -match "v(\d+)") {
                if ([int]$Matches[1] -lt 18) {
                    Log "Node.js $nodeVer found but v18+ required" Red
                    $ok = $false
                } else {
                    Log "Node.js $nodeVer" Green
                }
            }
        } catch {
            Log "Node.js not found on PATH. Install from https://nodejs.org" Red
            $ok = $false
        }
    }

    if (!$ok) {
        Log "Pre-flight check FAILED — install missing tools and retry" Red
        return $false
    }
    return $true
}

# Resolve ports
if ($BackendPort -eq 0) { $BackendPort = [int](Get-EnvValue "PORT" "8000") }
if ($FrontendPort -eq 0) { $FrontendPort = [int](Get-EnvValue "FRONTEND_PORT" "3000") }

# Banner
Write-Host ""
Write-Host "  ============================================" -ForegroundColor DarkCyan
Write-Host "   EMBODIER TRADER  v4.0.0" -ForegroundColor DarkCyan
Write-Host "   Backend :$BackendPort  |  Frontend :$FrontendPort" -ForegroundColor DarkCyan
Write-Host "  ============================================" -ForegroundColor DarkCyan
Write-Host ""

# Pre-flight
if (!(Test-Prerequisites)) {
    Write-Host ""
    Write-Host "  Press any key to exit..." -ForegroundColor Yellow
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit 1
}

# Fix .env encoding (remove BOM if present)
if (Test-Path $EnvFile) {
    $bytes = [IO.File]::ReadAllBytes($EnvFile)
    if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
        [IO.File]::WriteAllText($EnvFile, [IO.File]::ReadAllText($EnvFile, [Text.Encoding]::UTF8), (New-Object Text.UTF8Encoding($false)))
        Log "Removed BOM from .env" Yellow
    }
} elseif (Test-Path "$BackendDir\.env.example") {
    Copy-Item "$BackendDir\.env.example" $EnvFile
    Log "Created .env from .env.example — EDIT backend\.env with your API keys!" Yellow
}

# Validate .env has real Alpaca keys (not placeholders)
if (Test-Path $EnvFile) {
    $alpacaKey = Get-EnvValue "ALPACA_API_KEY" ""
    if ($alpacaKey -eq "" -or $alpacaKey -match "^your-") {
        Log "WARNING: ALPACA_API_KEY is not set or still a placeholder!" Yellow
        Log "Edit $EnvFile with your real Alpaca API keys." Yellow
        Log "Backend will start but market data will be unavailable." Yellow
    }
}

# ── Robust port cleanup (netstat catches orphans that Get-NetTCPConnection misses) ──
function Kill-PortProcesses([int]$Port) {
    $pids = netstat -ano 2>$null |
        Select-String "\s+0\.0\.0\.0:$Port\s+|\s+127\.0\.0\.1:$Port\s+|\s+\[::]:$Port\s+" |
        ForEach-Object { ($_ -split '\s+')[-1] } |
        Where-Object { $_ -match '^\d+$' -and [int]$_ -ne 0 } |
        Sort-Object -Unique
    foreach ($pid in $pids) {
        $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
        if ($proc) {
            Log "Killing PID $pid ($($proc.ProcessName)) on port $Port" Yellow
            taskkill /F /PID $pid 2>$null | Out-Null
        }
    }
}

Log "Checking for stale processes..." Cyan
Kill-PortProcesses $BackendPort
Kill-PortProcesses $FrontendPort

# ── DuckDB lock file cleanup (targeted — only kill processes for THIS app) ──
$DuckDbFile = "$BackendDir\data\analytics.duckdb"
$DuckDbWal  = "$DuckDbFile.wal"
$DuckDbTmp  = "$DuckDbFile.tmp"
if (Test-Path $DuckDbWal) {
    # Only kill python processes that are running from the backend directory
    $lockHolders = Get-Process python*, uvicorn* -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Id -ne $PID -and (
                $_.Path -like "*$BackendDir*" -or
                $_.CommandLine -like "*$BackendDir*" -or
                $_.MainWindowTitle -like "*Embodier*"
            )
        }
    if ($lockHolders) {
        Log "Killing stale Python processes holding DuckDB lock:" Yellow
        $lockHolders | ForEach-Object {
            Log "  PID $($_.Id) ($($_.ProcessName))" Yellow
            taskkill /F /PID $($_.Id) 2>$null | Out-Null
        }
        Start-Sleep 1
    }
    # Remove stale WAL/tmp files if they survived
    @($DuckDbWal, $DuckDbTmp) | ForEach-Object {
        if (Test-Path $_) {
            Remove-Item $_ -Force -ErrorAction SilentlyContinue
            Log "Removed stale lock: $(Split-Path $_ -Leaf)" Yellow
        }
    }
}
Start-Sleep 1

# ── Ensure Python venv exists ──
Set-Location $BackendDir
if (!(Test-Path "venv")) {
    Log "Creating Python virtual environment..." Cyan
    python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Log "Failed to create venv. Is Python 3.10+ installed?" Red
        Log "Download from https://python.org/downloads" Yellow
        exit 1
    }
}

# ── Activate venv and install deps ──
# Use the venv's python directly (more reliable than Activate.ps1 in Start-Job)
$VenvPython = "$BackendDir\venv\Scripts\python.exe"
$VenvPip = "$BackendDir\venv\Scripts\pip.exe"

if (!(Test-Path $VenvPython)) {
    Log "venv/Scripts/python.exe not found — recreating venv..." Yellow
    Remove-Item "venv" -Recurse -Force -ErrorAction SilentlyContinue
    python -m venv venv
}

# Check if fastapi is installed
$needInstall = $false
& $VenvPython -c "import fastapi" 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) { $needInstall = $true }
if ($needInstall) {
    Log "Installing Python dependencies..." Cyan
    & $VenvPip install -r requirements.txt --quiet 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Log "pip install failed — trying with verbose output:" Red
        & $VenvPip install -r requirements.txt 2>&1 | Select-Object -Last 20
        exit 1
    }
    Log "Python dependencies installed" Green
}

# ── Start backend as background process (NOT Start-Job — avoids runspace issues) ──
$backendLogFile = "$LogDir\backend.log"
"" | Out-File $backendLogFile -Encoding utf8  # Clear log

$backendProc = Start-Process -FilePath $VenvPython -ArgumentList @(
    "-u",  # Unbuffered output
    "start_server.py"
) -WorkingDirectory $BackendDir -RedirectStandardOutput $backendLogFile -RedirectStandardError "$LogDir\backend-error.log" -PassThru -NoNewWindow:$false -WindowStyle Hidden

if (!$backendProc) {
    Log "Failed to start backend process" Red
    exit 1
}
Log "Backend PID: $($backendProc.Id)" DarkGray

# Set env vars for the backend process
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUNBUFFERED = "1"

# Wait for backend health (90s timeout with diagnostics on failure)
Log "Waiting for backend..." Cyan
$healthy = $false
for ($i = 0; $i -lt 90; $i++) {
    Start-Sleep 1
    try {
        $response = Invoke-WebRequest "http://localhost:$BackendPort/health" -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) { $healthy = $true; break }
    } catch { }
    # Detect early crash
    if ($backendProc.HasExited) {
        Write-Host ""
        Log "Backend process exited unexpectedly (exit code: $($backendProc.ExitCode))" Red
        break
    }
    Write-Host "." -NoNewline
}
Write-Host ""
if ($healthy) {
    Log "Backend   http://localhost:$BackendPort" Green
    Log "API Docs  http://localhost:$BackendPort/docs" DarkGray
} else {
    Log "Backend failed to become healthy." Yellow
    Log "--- Last 25 lines of backend.log ---" Yellow
    if (Test-Path $backendLogFile) {
        Get-Content $backendLogFile -Tail 25 | ForEach-Object { Write-Host "  $_" -ForegroundColor DarkGray }
    }
    if (Test-Path "$LogDir\backend-error.log") {
        Log "--- Last 25 lines of backend-error.log ---" Yellow
        Get-Content "$LogDir\backend-error.log" -Tail 25 | ForEach-Object { Write-Host "  $_" -ForegroundColor DarkGray }
    }
    Log "------------------------------------" Yellow
}

# ── Start frontend (unless skipped) ──
$frontendProc = $null
if (!$SkipFrontend) {
    Set-Location $FrontendDir

    if (!(Test-Path "node_modules")) {
        Log "Installing frontend dependencies..." Cyan
        npm install 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Log "npm install failed — trying with verbose output:" Red
            npm install 2>&1 | Select-Object -Last 20
        } else {
            Log "Frontend dependencies installed" Green
        }
    }

    $frontendLogFile = "$LogDir\frontend.log"
    "" | Out-File $frontendLogFile -Encoding utf8

    # Set VITE_BACKEND_URL for the frontend process
    $env:VITE_BACKEND_URL = "http://localhost:$BackendPort"

    $frontendProc = Start-Process -FilePath "npx" -ArgumentList @(
        "vite", "--port", $FrontendPort, "--host"
    ) -WorkingDirectory $FrontendDir -RedirectStandardOutput $frontendLogFile -RedirectStandardError "$LogDir\frontend-error.log" -PassThru -WindowStyle Hidden

    Start-Sleep 3
    Log "Frontend  http://localhost:$FrontendPort" Green

    Start-Sleep 2
    Start-Process "http://localhost:$FrontendPort"
}

# Running banner
Write-Host ""
Write-Host "  RUNNING  |  Press Ctrl+C to stop" -ForegroundColor Green
Write-Host "  Backend PID:  $($backendProc.Id)" -ForegroundColor DarkGray
if ($frontendProc) { Write-Host "  Frontend PID: $($frontendProc.Id)" -ForegroundColor DarkGray }
Write-Host "  Logs: $LogDir" -ForegroundColor DarkGray
Write-Host ""

# ── Monitor loop + clean shutdown ──
try {
    while ($true) {
        Start-Sleep 10
        if ($backendProc.HasExited) {
            Log "Backend crashed (exit: $($backendProc.ExitCode)). See logs\backend.log" Red
            break
        }
    }
} finally {
    Write-Host ""
    Log "Shutting down..." Yellow

    # Kill backend
    if ($backendProc -and !$backendProc.HasExited) {
        try { $backendProc.Kill() } catch { }
    }
    # Kill frontend
    if ($frontendProc -and !$frontendProc.HasExited) {
        try { $frontendProc.Kill() } catch { }
    }

    Kill-PortProcesses $BackendPort
    Kill-PortProcesses $FrontendPort

    # Clean up DuckDB lock files on shutdown
    @($DuckDbWal, $DuckDbTmp) | ForEach-Object {
        if (Test-Path $_) { Remove-Item $_ -Force -ErrorAction SilentlyContinue }
    }
    Log "Stopped." Green
}
