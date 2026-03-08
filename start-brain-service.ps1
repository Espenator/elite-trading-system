param([int]$Port = 0)

$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$BrainDir = Join-Path $Root "brain_service"
$EnvFile = Join-Path $BrainDir ".env"

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

# Resolve port
if ($Port -eq 0) { $Port = [int](Get-EnvValue "BRAIN_PORT" "50051") }

Write-Host ""
Write-Host "  ============================================" -ForegroundColor Magenta
Write-Host "   BRAIN SERVICE (gRPC + Ollama)" -ForegroundColor Magenta
Write-Host "   Port: $Port" -ForegroundColor Magenta
Write-Host "  ============================================" -ForegroundColor Magenta
Write-Host ""

# Validate Python
try {
    $pyVer = (& python --version 2>&1) | Out-String
    $pyVer = $pyVer.Trim()
    if ($pyVer -match "(\d+\.\d+)") {
        $v = [version]$Matches[1]
        if ($v -lt [version]"3.10") {
            Log "Python $($Matches[1]) found but 3.10+ required" Red
            exit 1
        } else {
            Log "$pyVer" Green
        }
    }
} catch {
    Log "Python not found on PATH. Install from https://python.org" Red
    exit 1
}

# Validate Ollama (optional but recommended)
try {
    $ollamaVer = (& ollama --version 2>&1) | Out-String
    $ollamaVer = $ollamaVer.Trim()
    Log "Ollama $ollamaVer" Green
} catch {
    Log "Ollama not found — LLM inference will fail" Yellow
    Log "Install from: https://ollama.ai" Yellow
    Log "Then run: ollama pull llama3.2" Yellow
    Log "Continuing anyway..." DarkGray
}

Set-Location $BrainDir

# Create .env if missing
if (-not (Test-Path $EnvFile)) {
    $envExample = Join-Path $BrainDir ".env.example"
    if (Test-Path $envExample) {
        Copy-Item $envExample $EnvFile
        Log "Created .env from .env.example" Yellow
    }
}

# Create venv if missing
if (-not (Test-Path "venv")) {
    Log "Creating Python virtual environment..." Cyan
    python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Log "Failed to create venv" Red
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

# Check if grpc is installed
$needInstall = $false
& $VenvPython -c "import grpc" 2>$null
if ($LASTEXITCODE -ne 0) { $needInstall = $true }
if ($needInstall) {
    Log "Installing Python dependencies..." Cyan
    & $VenvPip install -r requirements.txt --quiet 2>$null
    if ($LASTEXITCODE -ne 0) {
        Log "pip install failed - trying with verbose output:" Red
        & $VenvPip install -r requirements.txt 2>&1 | Select-Object -Last 20
        exit 1
    }
    Log "Dependencies installed" Green
}

# Proto compilation is now automatic in server.py, but we can still check
if (-not (Test-Path "proto\brain_pb2.py")) {
    Log "Proto stubs will be compiled automatically on first run" DarkGray
}

# Set environment variable for port
$env:BRAIN_PORT = $Port

# Start server
Log "Starting Brain Service on port $Port..." Green
Log "Press Ctrl+C to stop" DarkGray
Write-Host ""

try {
    & $VenvPython server.py
} catch {
    Log "Server stopped: $_" Red
} finally {
    Log "Brain Service stopped" Yellow
}
