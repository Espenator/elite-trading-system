<#
.SYNOPSIS
    Register Embodier Trader auto-start in Task Scheduler + Startup folder.
#>

$TASK_NAME = "EmbodierTrader-AutoStart"
$REPO = "C:\Users\Espen\elite-trading-system"
$SCRIPT = Join-Path $REPO "scripts\start-all.ps1"
$STARTUP_FOLDER = [System.IO.Path]::Combine($env:APPDATA, "Microsoft\Windows\Start Menu\Programs\Startup")

Write-Host ""
Write-Host "  Embodier Trader Auto-Start Registration"
Write-Host "  ========================================"
Write-Host ""

# Method 1: Task Scheduler
$registered = $false
try {
    $null = schtasks /Delete /TN $TASK_NAME /F 2>&1
    $tr = "powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -File ""$SCRIPT"""
    $null = schtasks /Create /TN $TASK_NAME /TR $tr /SC ONLOGON /RL HIGHEST /DELAY "0000:30" /F 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [OK] Task Scheduler registered"
        $registered = $true
    } else {
        Write-Host "  [WARN] Task Scheduler needs admin. Using Startup folder."
    }
} catch {
    Write-Host "  [WARN] Task Scheduler error."
}

# Method 2: Startup Folder shortcut (no admin needed)
$shortcutPath = Join-Path $STARTUP_FOLDER "EmbodierTrader.lnk"
try {
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = "powershell.exe"
    $shortcut.Arguments = "-ExecutionPolicy Bypass -WindowStyle Hidden -File ""$SCRIPT"""
    $shortcut.WorkingDirectory = $REPO
    $shortcut.WindowStyle = 7
    $shortcut.Description = "Embodier Trader auto-start"
    $shortcut.Save()
    Write-Host "  [OK] Startup folder shortcut created"
} catch {
    Write-Host "  [WARN] Startup shortcut failed"
}

Write-Host ""
Write-Host "  Services will auto-start on login."
Write-Host "  To remove: schtasks /Delete /TN $TASK_NAME /F"
Write-Host "  Shortcut: $shortcutPath"
Write-Host ""
