<#
.SYNOPSIS
    Creates an "Embodier Trader" desktop shortcut with the proper icon.
    Run once after cloning or pulling the repo.

.NOTES
    Run from PowerShell: .\scripts\create-shortcut.ps1
#>

$ErrorActionPreference = "Stop"

# Resolve repo root (parent of scripts/)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $ScriptDir

Write-Host ""
Write-Host "  ============================================" -ForegroundColor DarkCyan
Write-Host "   EMBODIER TRADER - Shortcut Creator" -ForegroundColor DarkCyan
Write-Host "  ============================================" -ForegroundColor DarkCyan
Write-Host ""

# Validate repo structure
$BatFile = Join-Path $Root "start-embodier.bat"
$IconFile = Join-Path $Root "desktop\icons\icon.ico"

if (-not (Test-Path $BatFile)) {
    Write-Host "  [ERROR] start-embodier.bat not found at:" -ForegroundColor Red
    Write-Host "          $BatFile" -ForegroundColor Yellow
    Write-Host "  Make sure you are running from the repo root." -ForegroundColor Yellow
    exit 1
}

# Generate ICO from SVG if ico does not exist but svg does
if (-not (Test-Path $IconFile)) {
    $SvgFile = Join-Path $Root "desktop\icons\icon.svg"
    if (Test-Path $SvgFile) {
        Write-Host "  [setup] icon.ico not found - generating from icon.svg..." -ForegroundColor Cyan
        try {
            $pyCode = @'
import sys
try:
    from PIL import Image, ImageDraw
    img = Image.new('RGBA', (256, 256), (10, 14, 26, 255))
    draw = ImageDraw.Draw(img)
    points = [(140,40),(90,130),(130,130),(110,216),(180,110),(135,110)]
    draw.polygon(points, fill=(0,217,255,242))
    sizes = [(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)]
    imgs = [img.resize(s, Image.LANCZOS) for s in sizes]
    imgs[0].save(sys.argv[1], format='ICO', sizes=sizes, append_images=imgs[1:])
    print('  [OK] Generated icon.ico')
except Exception as e:
    print('  [WARN] Could not generate ico: ' + str(e))
    sys.exit(1)
'@
            $pyCode | python - $IconFile 2>&1
            if ($LASTEXITCODE -ne 0) { throw "Python ico generation failed" }
        } catch {
            Write-Host "  [WARN] Could not auto-generate icon.ico - shortcut will use default icon" -ForegroundColor Yellow
            $IconFile = $null
        }
    } else {
        Write-Host "  [INFO] No icon file found - shortcut will use default icon" -ForegroundColor Yellow
        $IconFile = $null
    }
}

# Find Desktop path (handles OneDrive-synced desktops)
$DesktopPath = [Environment]::GetFolderPath("Desktop")
if (-not $DesktopPath -or -not (Test-Path $DesktopPath)) {
    $DesktopPath = Join-Path $env:USERPROFILE "Desktop"
}
# Some users have OneDrive Desktop
if (-not (Test-Path $DesktopPath)) {
    if ($env:OneDrive) {
        $DesktopPath = Join-Path $env:OneDrive "Desktop"
    }
}

$ShortcutPath = Join-Path $DesktopPath "Embodier Trader.lnk"

# Create the shortcut
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)

# Point directly at the .bat file with correct working directory
$Shortcut.TargetPath = $BatFile
$Shortcut.WorkingDirectory = $Root
$Shortcut.Description = "Embodier Trader"
$Shortcut.WindowStyle = 1  # Normal window

if ($IconFile -and (Test-Path $IconFile)) {
    $Shortcut.IconLocation = "$IconFile,0"
    Write-Host "  [OK] Icon: $IconFile" -ForegroundColor Green
}

$Shortcut.Save()
Write-Host "  [OK] Desktop shortcut created: $ShortcutPath" -ForegroundColor Green

# Also create Start Menu shortcut
try {
    $StartMenuDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
    if (Test-Path $StartMenuDir) {
        $StartShortcutPath = Join-Path $StartMenuDir "Embodier Trader.lnk"
        $StartShortcut = $WshShell.CreateShortcut($StartShortcutPath)
        $StartShortcut.TargetPath = $BatFile
        $StartShortcut.WorkingDirectory = $Root
        $StartShortcut.Description = "Embodier Trader"
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
try { [System.Runtime.Interopservices.Marshal]::ReleaseComObject($WshShell) | Out-Null } catch {}

Write-Host ""
Write-Host "  Done! Double-click Embodier Trader on your Desktop to launch." -ForegroundColor Cyan
Write-Host ""
