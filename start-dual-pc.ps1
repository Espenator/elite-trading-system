# Elite Trading System — Dual-PC Orchestrator
# Coordinates startup of both PC1 (ESPENMAIN) and PC2 (ProfitTrader)
# Prerequisites:
#   1. Both PCs on same LAN with reserved IPs (see docs/CLUSTER-NETWORK-SETUP.md)
#   2. PowerShell remoting enabled on PC2 (Enable-PSRemoting -Force)
#   3. Firewall rules configured (see docs/CLUSTER-NETWORK-SETUP.md)
#   4. Network profile set to Private on both PCs

param(
    [switch]$SkipFrontend,
    [switch]$SinglePCMode,        # Skip PC2, run everything on PC1 only
    [string]$PC2Host = "",        # PC2 IP address (e.g., "192.168.1.116")
    [string]$PC2User = "",        # PC2 username (e.g., "ProfitTrader")
    [switch]$NoRemoting,          # Don't use PowerShell remoting (manual PC2 start)
    [int]$BackendPort = 0,
    [int]$FrontendPort = 0,
    [int]$MaxRestarts = 3
)

$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Join-Path $Root "backend"
$EnvFile = Join-Path $BackendDir ".env"
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
    if (Test-Path $EnvFile) {
        $line = Get-Content $EnvFile | Where-Object { $_ -match "^$Key=" }
        if ($line) { return ($line -split "=", 2)[1].Trim() }
    }
    return $Default
}

# Load PC2 settings from .env if not provided
if ($PC2Host -eq "") {
    $PC2Host = Get-EnvValue "CLUSTER_PC2_HOST" "192.168.1.116"
}
if ($PC2User -eq "") {
    $PC2User = Get-EnvValue "CLUSTER_PC2_USER" "ProfitTrader"
}

# Resolve ports
if ($BackendPort -eq 0) { $BackendPort = [int](Get-EnvValue "PORT" "8000") }
if ($FrontendPort -eq 0) { $FrontendPort = [int](Get-EnvValue "FRONTEND_PORT" "3000") }

# Banner
Write-Host ""
Write-Host "  ============================================" -ForegroundColor Cyan
Write-Host "   EMBODIER DUAL-PC ORCHESTRATOR" -ForegroundColor Cyan
if ($SinglePCMode) {
    Write-Host "   Mode: SINGLE-PC (PC2 disabled)" -ForegroundColor Yellow
} else {
    Write-Host "   PC1: ESPENMAIN (Backend + Frontend)" -ForegroundColor Cyan
    Write-Host "   PC2: $PC2Host (Brain + Ollama)" -ForegroundColor Magenta
}
Write-Host "  ============================================" -ForegroundColor Cyan
Write-Host ""

# =============================================================================
# PHASE 1: PC2 CONNECTIVITY PRE-FLIGHT
# =============================================================================
$PC2Available = $false
if (-not $SinglePCMode) {
    Log "Testing connectivity to PC2 ($PC2Host)..." Cyan

    # Test 1: Ping
    $pingOk = $false
    try {
        $ping = Test-Connection -ComputerName $PC2Host -Count 2 -Quiet -ErrorAction SilentlyContinue
        if ($ping) {
            $pingOk = $true
            Log "  Ping $PC2Host: OK" Green
        }
    } catch { }

    if (-not $pingOk) {
        Log "  Ping $PC2Host: FAILED" Red
        Log "PC2 is not reachable. Falling back to SINGLE-PC mode." Yellow
        Log "To enable dual-PC mode:" Yellow
        Log "  1. Ensure PC2 is powered on and connected via LAN" Yellow
        Log "  2. Set CLUSTER_PC2_HOST in backend/.env to PC2's IP" Yellow
        Log "  3. See docs/CLUSTER-NETWORK-SETUP.md for network configuration" Yellow
        $SinglePCMode = $true
    } else {
        # Test 2: PowerShell Remoting (if not disabled)
        if (-not $NoRemoting) {
            try {
                $remotingOk = $false
                $testCmd = Invoke-Command -ComputerName $PC2Host -ScriptBlock { $env:COMPUTERNAME } -ErrorAction Stop
                if ($testCmd) {
                    $remotingOk = $true
                    Log "  PowerShell Remoting: OK (remote hostname: $testCmd)" Green
                    $PC2Available = $true
                }
            } catch {
                Log "  PowerShell Remoting: FAILED" Yellow
                Log "  Error: $($_.Exception.Message)" DarkGray
                Log "PC2 is reachable but PowerShell remoting is not enabled." Yellow
                Log "Options:" Yellow
                Log "  1. On PC2, run as Administrator: Enable-PSRemoting -Force" Yellow
                Log "  2. Use -NoRemoting flag and manually start PC2 services" Yellow
                $NoRemoting = $true
            }
        }

        if ($NoRemoting) {
            Log "  PowerShell Remoting: SKIPPED (manual PC2 start required)" Yellow
            Log "Please start PC2 services manually by running on PC2:" Yellow
            Log "  cd C:\Users\$PC2User\elite-trading-system" Yellow
            Log "  .\start-pc2.ps1" Yellow
            Write-Host ""
            Write-Host "  Press any key when PC2 services are running..." -ForegroundColor Yellow
            $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
            $PC2Available = $true
        }
    }
}

# =============================================================================
# PHASE 2: START PC2 SERVICES (if available and remoting enabled)
# =============================================================================
$PC2Session = $null
if ($PC2Available -and -not $NoRemoting -and -not $SinglePCMode) {
    Log "Starting PC2 services remotely..." Cyan

    try {
        # Create a persistent session
        $PC2Session = New-PSSession -ComputerName $PC2Host -ErrorAction Stop
        Log "  Created PowerShell session to $PC2Host" Green

        # Copy start-pc2.ps1 to PC2 if it doesn't exist
        $pc2ScriptPath = "C:\Users\$PC2User\elite-trading-system\start-pc2.ps1"
        $localScriptPath = Join-Path $Root "start-pc2.ps1"

        if (-not (Invoke-Command -Session $PC2Session -ScriptBlock { param($path) Test-Path $path } -ArgumentList $pc2ScriptPath)) {
            Log "  Copying start-pc2.ps1 to PC2..." Yellow
            Copy-Item -Path $localScriptPath -Destination $pc2ScriptPath -ToSession $PC2Session
        }

        # Start PC2 services in background job
        Log "  Launching start-pc2.ps1 on PC2..." Cyan
        $PC2Job = Invoke-Command -Session $PC2Session -ScriptBlock {
            param($scriptPath)
            Set-Location (Split-Path -Parent $scriptPath)
            & $scriptPath
        } -ArgumentList $pc2ScriptPath -AsJob

        # Wait a few seconds for services to start
        Start-Sleep 5

        # Check if Ollama and Brain Service are reachable from PC1
        Log "  Validating PC2 services..." Cyan

        # Test Ollama
        $ollamaOk = $false
        try {
            $ollamaResp = Invoke-WebRequest "http://$PC2Host:11434/api/tags" -TimeoutSec 5 -UseBasicParsing -ErrorAction SilentlyContinue
            if ($ollamaResp.StatusCode -eq 200) {
                $ollamaOk = $true
                Log "    Ollama http://$PC2Host:11434 - OK" Green
            }
        } catch { }

        if (-not $ollamaOk) {
            Log "    Ollama http://$PC2Host:11434 - NOT READY YET (may still be starting)" Yellow
        }

        # Test Brain Service gRPC
        $brainOk = $false
        $tcp = New-Object Net.Sockets.TcpClient
        try {
            $tcp.Connect($PC2Host, 50051)
            $brainOk = $true
            $tcp.Close()
            Log "    Brain gRPC $PC2Host:50051 - OK" Green
        } catch {
            try { $tcp.Close() } catch { }
            Log "    Brain gRPC $PC2Host:50051 - NOT READY YET (may still be starting)" Yellow
        }

    } catch {
        Log "Failed to start PC2 services: $($_.Exception.Message)" Red
        Log "Continuing in SINGLE-PC mode" Yellow
        $SinglePCMode = $true
        if ($PC2Session) {
            Remove-PSSession $PC2Session
            $PC2Session = $null
        }
    }
}

# =============================================================================
# PHASE 3: START PC1 SERVICES (Backend + Frontend)
# =============================================================================
Log "Starting PC1 services..." Cyan

# Delegate to the existing start-embodier.ps1 script
$startEmbodierPath = Join-Path $Root "start-embodier.ps1"
if (-not (Test-Path $startEmbodierPath)) {
    Log "start-embodier.ps1 not found at $startEmbodierPath" Red
    exit 1
}

# Build arguments for start-embodier.ps1
$args = @()
if ($SkipFrontend) { $args += "-SkipFrontend" }
if ($BackendPort -ne 0) { $args += "-BackendPort", $BackendPort }
if ($FrontendPort -ne 0) { $args += "-FrontendPort", $FrontendPort }
if ($MaxRestarts -ne 3) { $args += "-MaxRestarts", $MaxRestarts }

Log "Invoking start-embodier.ps1 for PC1 services..." Green
Write-Host ""

# Run start-embodier.ps1 in a script block so we can catch Ctrl+C
$pc1ScriptBlock = {
    param($scriptPath, $arguments)
    & $scriptPath @arguments
}

try {
    & $startEmbodierPath @args
} finally {
    # Cleanup: Stop PC2 services if we started them
    if ($PC2Session -and $PC2Job) {
        Write-Host ""
        Log "Stopping PC2 services..." Yellow

        # Stop the remote job
        try {
            Stop-Job -Job $PC2Job -ErrorAction SilentlyContinue
            Remove-Job -Job $PC2Job -Force -ErrorAction SilentlyContinue
        } catch { }

        # Kill PC2 service processes
        try {
            Invoke-Command -Session $PC2Session -ScriptBlock {
                # Kill Ollama
                Get-Process -Name "ollama" -ErrorAction SilentlyContinue | Stop-Process -Force

                # Kill Python (Brain Service)
                $pythonProcs = Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object {
                    $_.CommandLine -like "*brain_service*" -or $_.CommandLine -like "*server.py*"
                }
                $pythonProcs | Stop-Process -Force

                Write-Output "PC2 services stopped"
            } -ErrorAction SilentlyContinue
        } catch {
            Log "Could not cleanly stop PC2 services: $($_.Exception.Message)" Yellow
        }

        Remove-PSSession $PC2Session
        Log "PC2 session closed" Green
    }

    Write-Host ""
    Log "Dual-PC orchestrator shutdown complete." Green
}
