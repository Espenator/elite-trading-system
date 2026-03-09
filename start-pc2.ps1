# Elite Trading System — PC2 (ProfitTrader) Service Launcher
# Starts Brain Service (gRPC) and Ollama on PC2
# This script is meant to be run EITHER:
#   1. Locally on PC2 via double-click or manual PowerShell
#   2. Remotely from PC1 via Invoke-Command (in start-dual-pc.ps1)

param(
    [switch]$SkipOllama,
    [switch]$SkipBrain,
    [int]$BrainPort = 50051,
    [int]$OllamaPort = 11434
)

$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$BrainDir = Join-Path $Root "brain_service"
$LogDir = Join-Path $Root "logs"

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
    $EnvFile = Join-Path $BrainDir ".env"
    if (Test-Path $EnvFile) {
        $line = Get-Content $EnvFile | Where-Object { $_ -match "^$Key=" }
        if ($line) { return ($line -split "=", 2)[1].Trim() }
    }
    return $Default
}

# Banner
Write-Host ""
Write-Host "  ============================================" -ForegroundColor Magenta
Write-Host "   EMBODIER PC2 (ProfitTrader)" -ForegroundColor Magenta
Write-Host "   Brain gRPC :$BrainPort  |  Ollama :$OllamaPort" -ForegroundColor Magenta
Write-Host "  ============================================" -ForegroundColor Magenta
Write-Host ""

# Pre-flight: Check Python
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

    # Check Ollama if not skipped
    if (-not $SkipOllama) {
        try {
            $ollamaVer = (& ollama --version 2>&1) | Out-String
            if ($ollamaVer) {
                Log "Ollama installed" Green
            }
        } catch {
            Log "WARNING: Ollama not found on PATH. Install from https://ollama.ai" Yellow
            Log "Continuing without Ollama..." Yellow
            $script:SkipOllama = $true
        }
    }

    if (-not $ok) {
        Log "Pre-flight check FAILED - install missing tools and retry" Red
        return $false
    }
    return $true
}

if (-not (Test-Prerequisites)) {
    Write-Host ""
    Write-Host "  Press any key to exit..." -ForegroundColor Yellow
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit 1
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
if (-not $SkipOllama) { Kill-PortProcesses $OllamaPort }
if (-not $SkipBrain) { Kill-PortProcesses $BrainPort }
Start-Sleep 1

# =============================================================================
# START OLLAMA
# =============================================================================
$ollamaProc = $null
if (-not $SkipOllama) {
    Log "Starting Ollama service..." Cyan

    # Set OLLAMA_HOST to bind to all interfaces (not just localhost)
    # This allows PC1 to reach Ollama on PC2 via LAN
    $env:OLLAMA_HOST = "0.0.0.0:$OllamaPort"

    # Optional performance tuning (if RTX GPU present)
    $env:OLLAMA_CUDA_GRAPHS = "1"
    $env:OLLAMA_FLASH_ATTENTION = "1"

    $ollamaLogFile = Join-Path $LogDir "ollama.log"
    $ollamaErrFile = Join-Path $LogDir "ollama-error.log"
    "" | Out-File $ollamaLogFile -Encoding utf8
    "" | Out-File $ollamaErrFile -Encoding utf8

    # Start Ollama serve in background
    # Note: Ollama serve runs as a daemon, so we use Start-Process
    $ollamaProc = Start-Process -FilePath "ollama" -ArgumentList "serve" `
        -RedirectStandardOutput $ollamaLogFile `
        -RedirectStandardError $ollamaErrFile `
        -PassThru -WindowStyle Hidden

    if (-not $ollamaProc) {
        Log "Failed to start Ollama process" Red
        exit 1
    }
    Log "Ollama PID: $($ollamaProc.Id)" DarkGray

    # Wait for Ollama to become ready (30s timeout)
    Log "Waiting for Ollama API..." Cyan
    $ollamaReady = $false
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep 1
        try {
            $response = Invoke-WebRequest "http://localhost:$OllamaPort/api/tags" -TimeoutSec 3 -UseBasicParsing -ErrorAction SilentlyContinue
            if ($response.StatusCode -eq 200) {
                $ollamaReady = $true
                break
            }
        } catch { }
        Write-Host "." -NoNewline
    }
    Write-Host ""

    if ($ollamaReady) {
        Log "Ollama   http://0.0.0.0:$OllamaPort (accessible from PC1)" Green

        # List loaded models
        try {
            $modelsResp = Invoke-WebRequest "http://localhost:$OllamaPort/api/tags" -UseBasicParsing
            $models = ($modelsResp.Content | ConvertFrom-Json).models
            if ($models.Count -gt 0) {
                Log "Models: $($models.name -join ', ')" DarkGray
            } else {
                Log "No models loaded. Run 'ollama pull llama3.2' to download." Yellow
            }
        } catch {
            Log "Could not list Ollama models" Yellow
        }
    } else {
        Log "Ollama failed to become ready." Yellow
        Log "--- Last 20 lines of ollama.log ---" Yellow
        if (Test-Path $ollamaLogFile) {
            Get-Content $ollamaLogFile -Tail 20 | ForEach-Object { Write-Host "  $_" -ForegroundColor DarkGray }
        }
    }
}

# =============================================================================
# START BRAIN SERVICE (gRPC)
# =============================================================================
$brainProc = $null
if (-not $SkipBrain) {
    Set-Location $BrainDir

    # Ensure Python venv exists
    if (-not (Test-Path "venv")) {
        Log "Creating Python virtual environment for Brain Service..." Cyan
        python -m venv venv
        if ($LASTEXITCODE -ne 0) {
            Log "Failed to create venv. Is Python 3.10+ installed?" Red
            exit 1
        }
    }

    $VenvPython = Join-Path $BrainDir "venv\Scripts\python.exe"
    $VenvPip = Join-Path $BrainDir "venv\Scripts\pip.exe"

    if (-not (Test-Path $VenvPython)) {
        Log "venv/Scripts/python.exe not found - recreating venv..." Yellow
        Remove-Item "venv" -Recurse -Force -ErrorAction SilentlyContinue
        python -m venv venv
    }

    # Check if grpcio is installed
    $needInstall = $false
    & $VenvPython -c "import grpc" 2>$null
    if ($LASTEXITCODE -ne 0) { $needInstall = $true }
    if ($needInstall) {
        Log "Installing Brain Service dependencies..." Cyan
        & $VenvPip install -r requirements.txt --quiet 2>$null
        if ($LASTEXITCODE -ne 0) {
            Log "pip install failed - trying with verbose output:" Red
            & $VenvPip install -r requirements.txt 2>&1 | Select-Object -Last 20
            exit 1
        }
        Log "Brain Service dependencies installed" Green
    }

    # Compile protobuf if not already done
    if (-not (Test-Path "brain_pb2.py")) {
        Log "Compiling protobuf..." Cyan
        & $VenvPython compile_proto.py
        if ($LASTEXITCODE -ne 0) {
            Log "Failed to compile protobuf" Red
            exit 1
        }
    }

    # Start Brain Service
    Log "Starting Brain Service gRPC..." Cyan

    # Set environment variables for Brain Service
    $env:BRAIN_PORT = "$BrainPort"
    $env:OLLAMA_HOST = "localhost"
    $env:OLLAMA_PORT = "$OllamaPort"
    $env:OLLAMA_MODEL = Get-EnvValue "OLLAMA_MODEL" "llama3.2"

    $brainLogFile = Join-Path $LogDir "brain_service.log"
    $brainErrFile = Join-Path $LogDir "brain_service-error.log"
    "" | Out-File $brainLogFile -Encoding utf8
    "" | Out-File $brainErrFile -Encoding utf8

    $brainProc = Start-Process -FilePath $VenvPython -ArgumentList "-u", "server.py" `
        -WorkingDirectory $BrainDir `
        -RedirectStandardOutput $brainLogFile `
        -RedirectStandardError $brainErrFile `
        -PassThru -WindowStyle Hidden

    if (-not $brainProc) {
        Log "Failed to start Brain Service process" Red
        exit 1
    }
    Log "Brain Service PID: $($brainProc.Id)" DarkGray

    # Wait for Brain Service to become ready (30s timeout)
    Log "Waiting for Brain Service gRPC..." Cyan
    $brainReady = $false
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep 1
        # gRPC doesn't have an HTTP health endpoint, so we check if the port is listening
        $tcp = New-Object Net.Sockets.TcpClient
        try {
            $tcp.Connect("127.0.0.1", $BrainPort)
            $brainReady = $true
            $tcp.Close()
            break
        } catch {
            try { $tcp.Close() } catch { }
        }
        Write-Host "." -NoNewline
    }
    Write-Host ""

    if ($brainReady) {
        Log "Brain Service gRPC  0.0.0.0:$BrainPort (accessible from PC1)" Green
    } else {
        Log "Brain Service failed to become ready." Yellow
        Log "--- Last 20 lines of brain_service.log ---" Yellow
        if (Test-Path $brainLogFile) {
            Get-Content $brainLogFile -Tail 20 | ForEach-Object { Write-Host "  $_" -ForegroundColor DarkGray }
        }
        if (Test-Path $brainErrFile) {
            Log "--- Last 20 lines of brain_service-error.log ---" Yellow
            Get-Content $brainErrFile -Tail 20 | ForEach-Object { Write-Host "  $_" -ForegroundColor DarkGray }
        }
    }
}

# Running banner
Write-Host ""
Write-Host "  PC2 SERVICES RUNNING  |  Press Ctrl+C to stop" -ForegroundColor Green
if ($ollamaProc) { Write-Host "  Ollama PID:       $($ollamaProc.Id)" -ForegroundColor DarkGray }
if ($brainProc) { Write-Host "  Brain Service PID: $($brainProc.Id)" -ForegroundColor DarkGray }
Write-Host "  Logs: $LogDir" -ForegroundColor DarkGray
Write-Host ""

# Monitor loop + clean shutdown
$consecutiveFails = 0
try {
    while ($true) {
        Start-Sleep 10

        # Check if Ollama is still alive
        if ($ollamaProc -and -not $SkipOllama) {
            $alive = $false
            try {
                $r = Invoke-WebRequest "http://localhost:$OllamaPort/api/tags" -TimeoutSec 5 -UseBasicParsing -ErrorAction SilentlyContinue
                if ($r.StatusCode -eq 200) { $alive = $true }
            } catch { }

            if (-not $alive) {
                $consecutiveFails++
                if ($consecutiveFails -ge 3) {
                    Log "Ollama unresponsive (3 consecutive failures). See logs\ollama.log" Red
                    break
                }
            } else {
                $consecutiveFails = 0
            }
        }

        # Check if Brain Service is still alive
        if ($brainProc -and -not $SkipBrain) {
            $tcp = New-Object Net.Sockets.TcpClient
            $tcpAlive = $false
            try {
                $tcp.Connect("127.0.0.1", $BrainPort)
                $tcpAlive = $true
                $tcp.Close()
            } catch {
                try { $tcp.Close() } catch { }
            }

            if (-not $tcpAlive) {
                $consecutiveFails++
                if ($consecutiveFails -ge 3) {
                    Log "Brain Service unresponsive (3 consecutive failures). See logs\brain_service.log" Red
                    break
                }
            } else {
                $consecutiveFails = 0
            }
        }
    }
} finally {
    Write-Host ""
    Log "Shutting down PC2 services..." Yellow

    # Kill by port
    if (-not $SkipOllama) { Kill-PortProcesses $OllamaPort }
    if (-not $SkipBrain) { Kill-PortProcesses $BrainPort }

    Log "PC2 services stopped." Green
}
