<#
.SYNOPSIS
    Install/uninstall Windows Task Scheduler task for Embodier Trader auto-start.

.DESCRIPTION
    Creates a scheduled task that launches Embodier Trader on user logon.
    Role-aware: detects ESPENMAIN vs Profit Trader and configures accordingly.

    The task runs as the current user and starts the Electron app (or dev server
    in development mode) automatically when the user logs in.

.PARAMETER Uninstall
    Remove the scheduled task instead of creating it.

.PARAMETER DevMode
    Register the task in dev mode (runs uvicorn + vite + electron from source).

.PARAMETER FullStack24/7
    Register the task to run the full stack 24/7 launcher: port cleanup, API/WS fix,
    backend + frontend (and optionally Electron) with supervisor (auto-restart on crash).
    Keeps the system running 24/7 with one supervisor window. Use only one of DevMode or FullStack24/7.

.PARAMETER Delay
    Delay in seconds after logon before starting (default: 30).

.EXAMPLE
    .\scripts\install-task-scheduler.ps1                    # Install auto-start (Electron)
    .\scripts\install-task-scheduler.ps1 -DevMode           # Install dev-mode auto-start
    .\scripts\install-task-scheduler.ps1 -FullStack24/7     # Install 24/7 stack at logon (recommended for PC1)
    .\scripts\install-task-scheduler.ps1 -Uninstall         # Remove auto-start
#>

param(
    [switch]$Uninstall,
    [switch]$DevMode,
    [switch]$FullStack247,
    [int]$Delay = 30
)

$ErrorActionPreference = "Stop"

$TASK_NAME = "EmbodierTrader"
$TASK_DESCRIPTION = "Start Embodier Trader on logon"
$TASK_NAME_24_7 = "EmbodierTrader-24-7"
$HOSTNAME = $env:COMPUTERNAME

# Detect role from hostname
$ROLE = "full"
if ($HOSTNAME -match "ESPENMAIN") {
    $ROLE = "primary"
} elseif ($HOSTNAME -match "Profit" -or $HOSTNAME -match "PROFITTRADER") {
    $ROLE = "secondary"
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Embodier Trader — Task Scheduler Setup" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Hostname: $HOSTNAME"
Write-Host "  Role:     $ROLE"
Write-Host "  Task:     $TASK_NAME"
Write-Host ""

# ── Uninstall ────────────────────────────────────────────────────────────────

if ($Uninstall) {
    $removed = $false
    foreach ($tn in @($TASK_NAME, $TASK_NAME_24_7)) {
        $existing = Get-ScheduledTask -TaskName $tn -ErrorAction SilentlyContinue
        if ($existing) {
            Unregister-ScheduledTask -TaskName $tn -Confirm:$false
            Write-Host "  Removed scheduled task: $tn" -ForegroundColor Green
            $removed = $true
        }
    }
    if (-not $removed) { Write-Host "  No Embodier tasks found (nothing to remove)." -ForegroundColor Yellow }
    exit 0
}

# ── Resolve paths ────────────────────────────────────────────────────────────

$ROOT = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
if (-not (Test-Path (Join-Path $ROOT "backend"))) {
    $ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
}

$DESKTOP_DIR = Join-Path $ROOT "desktop"
$BACKEND_DIR = Join-Path $ROOT "backend"
$AUTO_SCRIPT_24_7 = Join-Path $ROOT "scripts\start_embodier_24_7_auto.ps1"

# ── Build the action ─────────────────────────────────────────────────────────

if ($FullStack247) {
    # 24/7 full stack: port cleanup, API/WS fix, supervisor (auto-restart). One window stays open.
    if (-not (Test-Path $AUTO_SCRIPT_24_7)) {
        Write-Host "ERROR: 24/7 launcher not found: $AUTO_SCRIPT_24_7" -ForegroundColor Red
        exit 1
    }
    $Action = New-ScheduledTaskAction `
        -Execute "powershell.exe" `
        -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$AUTO_SCRIPT_24_7`" -NoElectron" `
        -WorkingDirectory $ROOT
    $Trigger = New-ScheduledTaskTrigger -AtLogOn
    $Trigger.Delay = "PT${Delay}S"
    $Settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -StartWhenAvailable `
        -ExecutionTimeLimit (New-TimeSpan -Hours 0) `
        -RestartCount 3 `
        -RestartInterval (New-TimeSpan -Minutes 5)
    $Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
    $existing = Get-ScheduledTask -TaskName $TASK_NAME_24_7 -ErrorAction SilentlyContinue
    if ($existing) { Unregister-ScheduledTask -TaskName $TASK_NAME_24_7 -Confirm:$false }
    Register-ScheduledTask `
        -TaskName $TASK_NAME_24_7 `
        -Description "Embodier Trader 24/7 — port cleanup, API/WS fix, auto-restart at logon" `
        -Action $Action `
        -Trigger $Trigger `
        -Settings $Settings `
        -Principal $Principal | Out-Null
    Write-Host ""
    Write-Host "  Scheduled task created: $TASK_NAME_24_7" -ForegroundColor Green
    Write-Host "  At logon: runs start_embodier_24_7_auto.ps1 (backend + frontend, supervisor, no Electron)." -ForegroundColor Green
    Write-Host "  To enable auto-execute at start: edit script or run .\scripts\start_embodier_24_7_auto.ps1 -EnableAutoExecute manually once." -ForegroundColor Gray
    Write-Host "  To remove: .\scripts\install-task-scheduler.ps1 -Uninstall" -ForegroundColor Cyan
    Write-Host ""
    exit 0
}

if ($DevMode) {
    # Dev mode: run a batch script that starts backend + frontend + electron
    $LAUNCH_SCRIPT = Join-Path $ROOT "scripts" "launch-electron-dev.bat"

    if (-not (Test-Path $LAUNCH_SCRIPT)) {
        Write-Host "ERROR: Dev launch script not found: $LAUNCH_SCRIPT" -ForegroundColor Red
        Write-Host "  Run 'scripts\launch-electron-dev.ps1' first to generate it." -ForegroundColor Yellow
        exit 1
    }

    $Action = New-ScheduledTaskAction `
        -Execute "cmd.exe" `
        -Argument "/c `"$LAUNCH_SCRIPT`"" `
        -WorkingDirectory $ROOT

    $TASK_DESCRIPTION = "Start Embodier Trader (DEV MODE) on logon — $ROLE"
} else {
    # Production mode: run the installed Electron app
    # Look for the installed app or the local electron
    $ELECTRON_EXE = $null

    # Check common install locations
    $installPaths = @(
        "$env:LOCALAPPDATA\Programs\Embodier Trader\Embodier Trader.exe",
        "$env:PROGRAMFILES\Embodier Trader\Embodier Trader.exe",
        (Join-Path $DESKTOP_DIR "release\win-unpacked\Embodier Trader.exe")
    )

    foreach ($p in $installPaths) {
        if (Test-Path $p) {
            $ELECTRON_EXE = $p
            break
        }
    }

    if (-not $ELECTRON_EXE) {
        # Fallback: run from source via npx electron
        Write-Host "  No installed app found — using source-mode fallback" -ForegroundColor Yellow
        $Action = New-ScheduledTaskAction `
            -Execute "cmd.exe" `
            -Argument "/c cd /d `"$DESKTOP_DIR`" && npx electron ." `
            -WorkingDirectory $DESKTOP_DIR
    } else {
        Write-Host "  App found: $ELECTRON_EXE" -ForegroundColor Green
        $Action = New-ScheduledTaskAction `
            -Execute $ELECTRON_EXE `
            -WorkingDirectory (Split-Path $ELECTRON_EXE)
    }

    $TASK_DESCRIPTION = "Start Embodier Trader on logon — $ROLE"
}

# ── Trigger: on user logon with delay ────────────────────────────────────────

$Trigger = New-ScheduledTaskTrigger -AtLogOn
$Trigger.Delay = "PT${Delay}S"  # e.g. PT30S = 30 seconds

# ── Settings ─────────────────────────────────────────────────────────────────

$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 0) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 5)

# Don't stop on idle
$Settings.IdleSettings.StopOnIdleEnd = $false
$Settings.IdleSettings.RestartOnIdle = $false

# ── Register ─────────────────────────────────────────────────────────────────

# Remove existing task if present
$existing = Get-ScheduledTask -TaskName $TASK_NAME -ErrorAction SilentlyContinue
if ($existing) {
    Unregister-ScheduledTask -TaskName $TASK_NAME -Confirm:$false
    Write-Host "  Replaced existing task" -ForegroundColor Yellow
}

$Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask `
    -TaskName $TASK_NAME `
    -Description $TASK_DESCRIPTION `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Principal $Principal | Out-Null

Write-Host ""
Write-Host "  Scheduled task created: $TASK_NAME" -ForegroundColor Green
Write-Host "  Trigger: At logon + ${Delay}s delay" -ForegroundColor Green
Write-Host "  Role: $ROLE" -ForegroundColor Green
Write-Host ""
Write-Host "  To test: schtasks /run /tn `"$TASK_NAME`"" -ForegroundColor Cyan
Write-Host "  To remove: .\scripts\install-task-scheduler.ps1 -Uninstall" -ForegroundColor Cyan
Write-Host ""
