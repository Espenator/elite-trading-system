param(
    [switch]$SkipFrontend,
    [int]$BackendPort = 0,
    [int]$FrontendPort = 0,
    [int]$MaxRestarts = 3
)

$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Join-Path $Root "backend"
$FrontendDir = Join-Path $Root "frontend-v2"
$LogDir = Join-Path $Root "logs"
$EnvFile = Join-Path $BackendDir ".env"

# Ensure logs directory
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory $LogDir -Force | Out-Null }

# Timestamped log helper
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

# Pre-flight: Validate Python and Node are on PATH
function Test-Prerequisites {
    $ok = $true
    try {
        $pyVer = (& python --version 2>&1) | Out-String
        $pyVer = $pyVer.Trim()
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

    if (-not $SkipFrontend) {
        try {
            $nodeVer = (& node --version 2>&1) | Out-String
            $nodeVer = $nodeVer.Trim()
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

    if (-not $ok) {
        Log "Pre-flight check FAILED - install missing tools and retry" Red
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
if (-not (Test-Prerequisites)) {
    Write-Host ""
    Write-Host "  Press any key to exit..." -ForegroundColor Yellow
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit 1
}

# Fix .env encoding - strip non-ASCII bytes and write as clean ASCII/UTF-8 without BOM
# Python on Windows uses cp1252 by default; slowapi/starlette reads .env with open() which
# uses system encoding. Any non-ASCII byte (e.g. 0x90) will crash with UnicodeDecodeError.
if (Test-Path $EnvFile) {
    $rawBytes = [IO.File]::ReadAllBytes($EnvFile)
    $cleanBytes = $rawBytes | Where-Object { $_ -lt 0x80 }
    $cleanText = [Text.Encoding]::ASCII.GetString($cleanBytes)
    $utf8NoBom = New-Object Text.UTF8Encoding($false)
    [IO.File]::WriteAllText($EnvFile, $cleanText, $utf8NoBom)
    $stripped = $rawBytes.Length - $cleanBytes.Length
    if ($stripped -gt 0) {
        Log "Stripped $stripped non-ASCII bytes from .env (fixes Windows encoding)" Yellow
    } else {
        Log ".env encoding OK" DarkGray
    }
} else {
    $envExample = Join-Path $BackendDir ".env.example"
    if (Test-Path $envExample) {
        Copy-Item $envExample $EnvFile
        Log "Created .env from .env.example - EDIT backend\.env with your API keys!" Yellow
    }
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

# Robust port cleanup
function Kill-PortProcesses([int]$Port) {
    $lines = netstat -ano 2>$null | Select-String "\s+0\.0\.0\.0:$Port\s+|\s+127\.0\.0\.1:$Port\s+|\s+\[::]:$Port\s+"
    $pids = @()
    foreach ($line in $lines) {
        $parts = "$line" -split '\s+'
        $pidStr = $parts[$parts.Length - 1]
        if ($pidStr -match '^\d+$' -and [int]$pidStr -ne 0) {
            $pids += $pidStr
        }
    }
    $pids = $pids | Sort-Object -Unique
    foreach ($procId in $pids) {
        $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
        if ($proc) {
            Log "Killing PID $procId ($($proc.ProcessName)) on port $Port" Yellow
            taskkill /F /PID $procId 2>$null | Out-Null
        }
    }
}

Log "Checking for stale processes..." Cyan
Kill-PortProcesses $BackendPort
Kill-PortProcesses $FrontendPort

# DuckDB lock file cleanup (targeted)
$DuckDbFile = Join-Path $BackendDir "data\analytics.duckdb"
$DuckDbWal  = "$DuckDbFile.wal"
$DuckDbTmp  = "$DuckDbFile.tmp"
if (Test-Path $DuckDbWal) {
    foreach ($f in @($DuckDbWal, $DuckDbTmp)) {
        if (Test-Path $f) {
            Remove-Item $f -Force -ErrorAction SilentlyContinue
            Log "Removed stale lock: $(Split-Path $f -Leaf)" Yellow
        }
    }
}
Start-Sleep 1

# Ensure Python venv exists
Set-Location $BackendDir
if (-not (Test-Path "venv")) {
    Log "Creating Python virtual environment..." Cyan
    python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Log "Failed to create venv. Is Python 3.10+ installed?" Red
        Log "Download from https://python.org/downloads" Yellow
        exit 1
    }
}

# Use the venv python directly (more reliable than Activate.ps1 in jobs)
$VenvPython = Join-Path $BackendDir "venv\Scripts\python.exe"
$VenvPip = Join-Path $BackendDir "venv\Scripts\pip.exe"

if (-not (Test-Path $VenvPython)) {
    Log "venv/Scripts/python.exe not found - recreating venv..." Yellow
    Remove-Item "venv" -Recurse -Force -ErrorAction SilentlyContinue
    python -m venv venv
}

# Check if fastapi is installed
$needInstall = $false
& $VenvPython -c "import fastapi" 2>$null
if ($LASTEXITCODE -ne 0) { $needInstall = $true }
if ($needInstall) {
    Log "Installing Python dependencies..." Cyan
    & $VenvPip install -r requirements.txt --quiet 2>$null
    if ($LASTEXITCODE -ne 0) {
        Log "pip install failed - trying with verbose output:" Red
        & $VenvPip install -r requirements.txt 2>&1 | Select-Object -Last 20
        exit 1
    }
    Log "Python dependencies installed" Green
}

# Start backend as background process (Start-Process, NOT Start-Job)
$backendLogFile = Join-Path $LogDir "backend.log"
$backendErrFile = Join-Path $LogDir "backend-error.log"
"" | Out-File $backendLogFile -Encoding utf8

# Force Python UTF-8 mode so starlette/slowapi never fall back to cp1252
$env:PYTHONUTF8 = "1"

$backendProc = Start-Process -FilePath $VenvPython -ArgumentList "-u", "start_server.py" `
    -WorkingDirectory $BackendDir `
    -RedirectStandardOutput $backendLogFile `
    -RedirectStandardError $backendErrFile `
    -PassThru -WindowStyle Hidden

if (-not $backendProc) {
    Log "Failed to start backend process" Red
    exit 1
}
Log "Backend PID: $($backendProc.Id)" DarkGray

# Wait for backend health (90s timeout)
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
    if (Test-Path $backendErrFile) {
        Log "--- Last 25 lines of backend-error.log ---" Yellow
        Get-Content $backendErrFile -Tail 25 | ForEach-Object { Write-Host "  $_" -ForegroundColor DarkGray }
    }
    Log "------------------------------------" Yellow
}

# Start frontend (unless skipped)
$frontendProc = $null
if (-not $SkipFrontend) {
    Set-Location $FrontendDir

    if (-not (Test-Path "node_modules")) {
        Log "Installing frontend dependencies..." Cyan
        npm install 2>$null
        if ($LASTEXITCODE -ne 0) {
            Log "npm install failed - trying with verbose output:" Red
            npm install 2>&1 | Select-Object -Last 20
        } else {
            Log "Frontend dependencies installed" Green
        }
    }

    $frontendLogFile = Join-Path $LogDir "frontend.log"
    $frontendErrFile = Join-Path $LogDir "frontend-error.log"
    "" | Out-File $frontendLogFile -Encoding utf8

    $env:VITE_BACKEND_URL = "http://localhost:$BackendPort"

    $npxCmd = "npx vite --port $FrontendPort --host"
    $frontendProc = Start-Process -FilePath "cmd.exe" -ArgumentList "/c", $npxCmd `
        -WorkingDirectory $FrontendDir `
        -RedirectStandardOutput $frontendLogFile `
        -RedirectStandardError $frontendErrFile `
        -PassThru -WindowStyle Hidden

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

# Monitor loop + clean shutdown
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

    if ($backendProc -and (-not $backendProc.HasExited)) {
        try { $backendProc.Kill() } catch { }
    }
    if ($frontendProc -and (-not $frontendProc.HasExited)) {
        try { $frontendProc.Kill() } catch { }
    }

    Kill-PortProcesses $BackendPort
    Kill-PortProcesses $FrontendPort

    foreach ($f in @($DuckDbWal, $DuckDbTmp)) {
        if (Test-Path $f) { Remove-Item $f -Force -ErrorAction SilentlyContinue }
    }
    Log "Stopped." Green
}
