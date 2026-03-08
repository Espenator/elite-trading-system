<#
.SYNOPSIS
    Creates an "Embodier Trader" desktop shortcut with the proper icon.
    Run once after cloning or pulling the repo.

.DESCRIPTION
    - Creates a .lnk shortcut on the Desktop
    - Points to start-embodier.bat with correct working directory
    - Uses desktop/icons/icon.ico for the shortcut icon
    - Also creates a Start Menu shortcut (optional)

.NOTES
    Run from PowerShell: .\scripts\create-shortcut.ps1
    Or right-click > Run with PowerShell
#>

$ErrorActionPreference = "Stop"

# Resolve repo root (parent of scripts/)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $ScriptDir

Write-Host ""
Write-Host "  ============================================" -ForegroundColor DarkCyan
Write-Host "   EMBODIER TRADER — Shortcut Creator" -ForegroundColor DarkCyan
Write-Host "  ============================================" -ForegroundColor DarkCyan
Write-Host ""

# Validate repo structure
$BatFile = "$Root\start-embodier.bat"
$IconFile = "$Root\desktop\icons\icon.ico"

if (!(Test-Path $BatFile)) {
    Write-Host "  [ERROR] start-embodier.bat not found at:" -ForegroundColor Red
    Write-Host "          $BatFile" -ForegroundColor Yellow
    Write-Host "  Make sure you're running from the repo root." -ForegroundColor Yellow
    exit 1
}

# Generate ICO from SVG if ico doesn't exist but svg does
if (!(Test-Path $IconFile)) {
    $SvgFile = "$Root\desktop\icons\icon.svg"
    if (Test-Path $SvgFile) {
        Write-Host "  [setup] icon.ico not found — generating from icon.svg..." -ForegroundColor Cyan
        try {
            # Use Python + Pillow to convert (most Windows dev machines have these)
            $pyScript = @"
import sys
try:
    from PIL import Image, ImageDraw
    img = Image.new('RGBA', (256, 256), (10, 14, 26, 255))
    draw = ImageDraw.Draw(img)
    # Lightning bolt shape
    points = [(140,40),(90,130),(130,130),(110,216),(180,110),(135,110)]
    draw.polygon(points, fill=(0,217,255,242))
    sizes = [(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)]
    imgs = [img.resize(s, Image.LANCZOS) for s in sizes]
    imgs[0].save(sys.argv[1], format='ICO', sizes=sizes, append_images=imgs[1:])
    print('  [OK] Generated icon.ico')
except Exception as e:
    print(f'  [WARN] Could not generate ico: {e}')
    sys.exit(1)
"@
            $pyScript | python - "$IconFile" 2>&1
            if ($LASTEXITCODE -ne 0) { throw "Python ico generation failed" }
        } catch {
            Write-Host "  [WARN] Could not auto-generate icon.ico — shortcut will use default icon" -ForegroundColor Yellow
            $IconFile = $null
        }
    } else {
        Write-Host "  [INFO] No icon file found — shortcut will use default icon" -ForegroundColor Yellow
        $IconFile = $null
    }
}

# Find Desktop path (handles OneDrive-synced desktops)
$DesktopPath = [Environment]::GetFolderPath("Desktop")
if (!$DesktopPath -or !(Test-Path $DesktopPath)) {
    $DesktopPath = "$env:USERPROFILE\Desktop"
}
# Some users have OneDrive Desktop
if (!(Test-Path $DesktopPath)) {
    $DesktopPath = "$env:OneDrive\Desktop"
}

$ShortcutPath = "$DesktopPath\Embodier Trader.lnk"

# Create the shortcut
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)

# Use cmd.exe /c to ensure the working directory is always correct
# This prevents the "runs from System32" bug with shortcuts
$Shortcut.TargetPath = "$env:windir\system32\cmd.exe"
$Shortcut.Arguments = "/c `"cd /d `"$Root`" && start `"`" `"$BatFile`"`""
$Shortcut.WorkingDirectory = $Root
$Shortcut.Description = "Embodier Trader — AI-Powered Trading Platform"
$Shortcut.WindowStyle = 1  # Normal window

if ($IconFile -and (Test-Path $IconFile)) {
    $Shortcut.IconLocation = "$IconFile,0"
    Write-Host "  [OK] Icon: $IconFile" -ForegroundColor Green
}

$Shortcut.Save()
Write-Host "  [OK] Desktop shortcut created: $ShortcutPath" -ForegroundColor Green

# Also create Start Menu shortcut
try {
    $StartMenuDir = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs"
    if (Test-Path $StartMenuDir) {
        $StartShortcut = $WshShell.CreateShortcut("$StartMenuDir\Embodier Trader.lnk")
        $StartShortcut.TargetPath = "$env:windir\system32\cmd.exe"
        $StartShortcut.Arguments = "/c `"cd /d `"$Root`" && start `"`" `"$BatFile`"`""
        $StartShortcut.WorkingDirectory = $Root
        $StartShortcut.Description = "Embodier Trader — AI-Powered Trading Platform"
        if ($IconFile -and (Test-Path $IconFile)) {
            $StartShortcut.IconLocation = "$IconFile,0"
        }
        $StartShortcut.Save()
        Write-Host "  [OK] Start Menu shortcut created" -ForegroundColor Green
    }
} catch {
    Write-Host "  [WARN] Start Menu shortcut skipped: $_" -ForegroundColor Yellow
}

# Cleanup COM object
[System.Runtime.Interopservices.Marshal]::ReleaseComObject($WshShell) | Out-Null

Write-Host ""
Write-Host "  Done! Double-click 'Embodier Trader' on your Desktop to launch." -ForegroundColor Cyan
Write-Host ""
