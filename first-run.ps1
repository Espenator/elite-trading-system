# first-run.ps1 — Embodier Trader first-time setup & launch
# Usage: Right-click → Run with PowerShell  (or: powershell -ExecutionPolicy Bypass -File first-run.ps1)

$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Join-Path $Root "backend"
$FrontendDir = Join-Path $Root "frontend-v2"
$EnvFile = Join-Path $BackendDir ".env"
$EnvExample = Join-Path $BackendDir ".env.example"

function Banner {
    Write-Host ""
    Write-Host "  ============================================================" -ForegroundColor DarkCyan
    Write-Host "   EMBODIER TRADER  v4.1.0  —  First-Time Setup" -ForegroundColor DarkCyan
    Write-Host "  ============================================================" -ForegroundColor DarkCyan
    Write-Host ""
}

function Step($num, $msg) {
    Write-Host "  [$num] $msg" -ForegroundColor Cyan
}

function Ok($msg) {
    Write-Host "      $msg" -ForegroundColor Green
}

function Warn($msg) {
    Write-Host "      $msg" -ForegroundColor Yellow
}

function Fail($msg) {
    Write-Host "      $msg" -ForegroundColor Red
}

Banner

# ── Step 1: Check prerequisites ────────────────────────────────
Step 1 "Checking prerequisites..."

$pyOk = $false
try {
    $pyVer = (python --version 2>&1) | Out-String
    if ($pyVer -match "(\d+\.\d+)") {
        $v = [version]$Matches[1]
        if ($v -ge [version]"3.10") {
            Ok "Python $($pyVer.Trim())"
            $pyOk = $true
        } else {
            Fail "Python $($Matches[1]) found — 3.10+ required"
        }
    }
} catch {
    Fail "Python not found. Install from https://python.org/downloads"
}

$nodeOk = $false
try {
    $nodeVer = (node --version 2>&1) | Out-String
    if ($nodeVer -match "v(\d+)") {
        if ([int]$Matches[1] -ge 18) {
            Ok "Node.js $($nodeVer.Trim())"
            $nodeOk = $true
        } else {
            Fail "Node.js $($nodeVer.Trim()) found — v18+ required"
        }
    }
} catch {
    Fail "Node.js not found. Install from https://nodejs.org"
}

if (-not $pyOk -or -not $nodeOk) {
    Write-Host ""
    Fail "Install missing tools above and re-run this script."
    Write-Host ""
    pause
    exit 1
}

# ── Step 2: Create .env file ────────────────────────────────────
Step 2 "Setting up backend configuration..."

if (-not (Test-Path $EnvFile)) {
    if (Test-Path $EnvExample) {
        Copy-Item $EnvExample $EnvFile
        Ok "Created backend\.env from .env.example"
    } else {
        Fail "No .env.example found — cannot create .env"
    }
} else {
    Ok "backend\.env already exists"
}

Write-Host ""
Warn "IMPORTANT: Edit backend\.env with your API keys before trading!"
Warn "At minimum, set these for paper trading:"
Write-Host "      ALPACA_API_KEY=<your key>" -ForegroundColor White
Write-Host "      ALPACA_SECRET_KEY=<your secret>" -ForegroundColor White
Write-Host "      ALPACA_BASE_URL=https://paper-api.alpaca.markets" -ForegroundColor White
Write-Host "      TRADING_MODE=paper" -ForegroundColor White
Write-Host ""

# ── Step 3: Create Python venv & install deps ──────────────────
Step 3 "Setting up Python virtual environment..."

Set-Location $BackendDir
if (-not (Test-Path "venv")) {
    python -m venv venv
    if ($LASTEXITCODE -eq 0) {
        Ok "Virtual environment created"
    } else {
        Fail "Failed to create venv"
    }
} else {
    Ok "Virtual environment already exists"
}

$VenvPip = Join-Path $BackendDir "venv\Scripts\pip.exe"
if (Test-Path $VenvPip) {
    Write-Host "      Installing Python dependencies (this may take a minute)..." -ForegroundColor DarkGray
    & $VenvPip install -r requirements.txt --quiet 2>$null
    if ($LASTEXITCODE -eq 0) {
        Ok "Python dependencies installed"
    } else {
        Warn "Some dependencies may have failed — backend will report errors on start"
    }
}

# ── Step 4: Install frontend deps ──────────────────────────────
Step 4 "Setting up frontend..."

Set-Location $FrontendDir
if (-not (Test-Path "node_modules")) {
    Write-Host "      Installing npm packages (this may take a minute)..." -ForegroundColor DarkGray
    npm install --silent 2>$null
    if ($LASTEXITCODE -eq 0) {
        Ok "Frontend dependencies installed"
    } else {
        Warn "npm install had warnings — frontend may still work"
    }
} else {
    Ok "node_modules already exists"
}

# ── Step 5: Create desktop shortcut ────────────────────────────
Step 5 "Creating desktop shortcut..."

Set-Location $Root
try {
    $ws = New-Object -ComObject WScript.Shell
    $desktopPath = [Environment]::GetFolderPath("Desktop")
    $shortcutPath = Join-Path $desktopPath "Embodier Trader.lnk"
    $shortcut = $ws.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = Join-Path $Root "start-embodier.bat"
    $shortcut.WorkingDirectory = $Root
    $shortcut.Description = "Launch Embodier Trader — AI-Powered Trading Platform"
    $icoPath = Join-Path $Root "desktop\icons\icon.ico"
    if (Test-Path $icoPath) { $shortcut.IconLocation = "$icoPath,0" }
    $shortcut.Save()
    Ok "Desktop shortcut created"
} catch {
    Warn "Could not create desktop shortcut (run manually with start-embodier.bat)"
}

# ── Step 6: Generate security tokens ───────────────────────────
Step 6 "Generating security tokens..."

$VenvPython = Join-Path $BackendDir "venv\Scripts\python.exe"
if (Test-Path $VenvPython) {
    $authToken = & $VenvPython -c "import secrets; print(secrets.token_urlsafe(32))" 2>$null
    if ($authToken) {
        Ok "Auth token generated. Add to .env:"
        Write-Host "      API_AUTH_TOKEN=$authToken" -ForegroundColor White
    }

    $fernetKey = & $VenvPython -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 2>$null
    if ($fernetKey) {
        Ok "Fernet encryption key generated. Add to .env:"
        Write-Host "      FERNET_KEY=$fernetKey" -ForegroundColor White
    }
}

# ── Done ────────────────────────────────────────────────────────
Write-Host ""
Write-Host "  ============================================================" -ForegroundColor DarkCyan
Write-Host "   SETUP COMPLETE" -ForegroundColor Green
Write-Host "  ============================================================" -ForegroundColor DarkCyan
Write-Host ""
Write-Host "  Next steps:" -ForegroundColor White
Write-Host "    1. Edit backend\.env with your Alpaca API keys" -ForegroundColor DarkGray
Write-Host "    2. (Optional) Add other API keys for full intelligence" -ForegroundColor DarkGray
Write-Host "    3. Launch via:" -ForegroundColor DarkGray
Write-Host "         - Desktop shortcut (Embodier Trader icon)" -ForegroundColor DarkGray
Write-Host "         - Double-click start-embodier.bat" -ForegroundColor DarkGray
Write-Host "         - PowerShell: .\start-embodier.ps1" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  Services (after launch):" -ForegroundColor White
Write-Host "    Backend API:   http://localhost:8000" -ForegroundColor DarkGray
Write-Host "    API Docs:      http://localhost:8000/docs" -ForegroundColor DarkGray
Write-Host "    Frontend UI:   http://localhost:3000" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  Would you like to launch Embodier Trader now? (Y/N) " -ForegroundColor Yellow -NoNewline
$response = Read-Host
if ($response -match "^[Yy]") {
    Write-Host ""
    & (Join-Path $Root "start-embodier.ps1")
} else {
    Write-Host ""
    Write-Host "  Ready when you are. Double-click the desktop shortcut to launch!" -ForegroundColor Green
    Write-Host ""
    pause
}
