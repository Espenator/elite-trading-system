# start_embodier_24_7_auto.ps1 - One-shot 24/7 launcher: port cleanup, API/WS fix, auto-restart, optional auto_execute
# Usage: .\scripts\start_embodier_24_7_auto.ps1
#        .\scripts\start_embodier_24_7_auto.ps1 -NoElectron
#        .\scripts\start_embodier_24_7_auto.ps1 -EnableAutoExecute   # Enable trading via API after backend is up
#
# Use this for:
# - Running the stack 24/7 with one supervisor window (auto-restart on crash).
# - Port clearing so 8000/5173 are freed before start.
# - Frontend .env auto-updated (VITE_PORT, VITE_BACKEND_URL, VITE_WS_URL) so API and WebSocket work.
# - Optional: enable auto_execute via API after backend is healthy (passed to run_full_stack_24_7.ps1).
#
# For automatic start each day / at logon: install the task with -FullStack24/7 (see install-task-scheduler.ps1).

param(
    [switch]$NoElectron,
    [switch]$EnableAutoExecute
)

$ErrorActionPreference = "SilentlyContinue"
$Root = if (Test-Path (Join-Path $PSScriptRoot "..\backend")) { (Resolve-Path (Join-Path $PSScriptRoot "..")).Path } else { Split-Path -Parent $PSScriptRoot }
$FullStackScript = Join-Path $Root "scripts\run_full_stack_24_7.ps1"

if (-not (Test-Path $FullStackScript)) {
    Write-Host "ERROR: $FullStackScript not found." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "  ============================================" -ForegroundColor DarkCyan
Write-Host "    Embodier Trader — 24/7 Auto Launcher" -ForegroundColor DarkCyan
Write-Host "  ============================================" -ForegroundColor DarkCyan
Write-Host "  Port cleanup + API/WS fix + supervisor (auto-restart)" -ForegroundColor White
if ($EnableAutoExecute) { Write-Host "  Auto-execute: will enable after backend is up" -ForegroundColor Yellow }
Write-Host ""

# Build arguments for run_full_stack_24_7.ps1
$stackArgs = @("-Supervisor", "-CleanPorts")
if ($NoElectron) { $stackArgs += "-NoElectron" }
if ($EnableAutoExecute) { $stackArgs += "-EnableAutoExecute" }

# Start full stack (blocks in supervisor loop; backend/frontend run in child windows)
& $FullStackScript @stackArgs
