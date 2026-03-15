# ============================================================
#  Create Desktop Shortcuts for Embodier Trader
#  Creates "Start Embodier" (and optionally "Stop Embodier") .lnk files.
#  Usage: powershell -ExecutionPolicy Bypass -File create-desktop-shortcut.ps1
#         -IncludeStop   -> also creates a "Stop Embodier" shortcut
#         -DevMode       -> shortcut runs start-embodier.ps1 instead of 24/7
# ============================================================

param(
    [switch]$IncludeStop,
    [switch]$DevMode
)

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$WshShell = New-Object -ComObject WScript.Shell

# -- Icon --

$iconPath = Join-Path $Root "desktop\build\icon.ico"
if (-not (Test-Path $iconPath)) {
    $iconPath = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe,0"
}

# -- Start Shortcut --

$startName = "Start Embodier Trader"
$startLnk = Join-Path $DesktopPath "$startName.lnk"

if ($DevMode) {
    $targetScript = Join-Path $Root "start-embodier.ps1"
} else {
    $targetScript = Join-Path $Root "scripts\run_full_stack_24_7.ps1"
}

$shortcut = $WshShell.CreateShortcut($startLnk)
$shortcut.TargetPath = "powershell.exe"
$shortcut.Arguments = "-ExecutionPolicy Bypass -File `"$targetScript`""
$shortcut.WorkingDirectory = $Root
$shortcut.Description = "Launch Embodier Trader (backend + frontend + supervisor)"
$shortcut.WindowStyle = 1
if (Test-Path (Join-Path $Root "desktop\build\icon.ico")) {
    $shortcut.IconLocation = $iconPath
}
$shortcut.Save()

Write-Host "  [OK] Created: $startLnk" -ForegroundColor Green
if ($DevMode) {
    Write-Host "       Mode: Dev (start-embodier.ps1)" -ForegroundColor Gray
} else {
    Write-Host "       Mode: 24/7 (run_full_stack_24_7.ps1)" -ForegroundColor Gray
}

# -- Stop Shortcut (optional) --

if ($IncludeStop) {
    $stopName = "Stop Embodier Trader"
    $stopLnk = Join-Path $DesktopPath "$stopName.lnk"
    $stopScript = Join-Path $Root "scripts\stop_embodier.ps1"

    if (Test-Path $stopScript) {
        $stopShortcut = $WshShell.CreateShortcut($stopLnk)
        $stopShortcut.TargetPath = "powershell.exe"
        $stopShortcut.Arguments = "-ExecutionPolicy Bypass -File `"$stopScript`""
        $stopShortcut.WorkingDirectory = $Root
        $stopShortcut.Description = "Stop all Embodier Trader processes"
        $stopShortcut.WindowStyle = 1
        $stopShortcut.Save()

        Write-Host "  [OK] Created: $stopLnk" -ForegroundColor Green
    } else {
        Write-Host "  [!!] stop_embodier.ps1 not found at $stopScript -- skipping stop shortcut" -ForegroundColor Yellow
    }
}

# -- Done --

Write-Host ""
Write-Host "  Shortcuts ready on your Desktop." -ForegroundColor Cyan
Write-Host "  Double-click '$startName' to launch everything." -ForegroundColor Gray
if ($IncludeStop) {
    Write-Host "  Double-click 'Stop Embodier Trader' to shut down all services." -ForegroundColor Gray
}
