# ================================================================
# ELITE TRADING SYSTEM - QUICK START
# Automatically finds repo location and launches system
# ================================================================

Write-Host "`n🚀 ELITE TRADING SYSTEM - QUICK START" -ForegroundColor Cyan
Write-Host "================================================`n" -ForegroundColor Cyan

# ================================================================
# STEP 1: Find the repository location
# ================================================================
Write-Host "📁 Searching for elite-trading-system repository..." -ForegroundColor Yellow

$possiblePaths = @(
    "$env:USERPROFILE\Documents\elite-trading-system",
    "$env:USERPROFILE\OneDrive\Documents\elite-trading-system",
    "$env:USERPROFILE\Desktop\elite-trading-system",
    "$env:USERPROFILE\OneDrive\Desktop\elite-trading-system",
    "C:\Users\$env:USERNAME\OneDrive\Documents\New folder (2)\OneDrive\Desktop\elite-trading-system",
    "C:\Projects\elite-trading-system",
    "D:\elite-trading-system"
)

$repoPath = $null
foreach ($path in $possiblePaths) {
    if (Test-Path $path) {
        $repoPath = $path
        Write-Host "✅ Found repository at: $repoPath" -ForegroundColor Green
        break
    }
}

if (-not $repoPath) {
    Write-Host "`n❌ Repository not found in common locations." -ForegroundColor Red
    Write-Host "🔍 Searching entire user directory (this may take a moment)..." -ForegroundColor Yellow
    
    $searchResult = Get-ChildItem -Path $env:USERPROFILE -Recurse -Directory -Filter "elite-trading-system" -ErrorAction SilentlyContinue | Select-Object -First 1
    
    if ($searchResult) {
        $repoPath = $searchResult.FullName
        Write-Host "✅ Found repository at: $repoPath" -ForegroundColor Green
    } else {
        Write-Host "`n⚠️  Could not find repository. Please clone it first:" -ForegroundColor Yellow
        Write-Host "git clone https://github.com/Espenator/elite-trading-system.git" -ForegroundColor White
        Write-Host "`nOr provide the path manually:`n" -ForegroundColor Yellow
        $repoPath = Read-Host "Enter the full path to elite-trading-system"
        
        if (-not (Test-Path $repoPath)) {
            Write-Host "`n❌ Path does not exist. Exiting." -ForegroundColor Red
            exit 1
        }
    }
}

Set-Location $repoPath
Write-Host "`n✅ Changed directory to: $repoPath`n" -ForegroundColor Green

# ================================================================
# STEP 2: Pull latest changes
# ================================================================
Write-Host "📥 Pulling latest changes from GitHub..." -ForegroundColor Yellow

try {
    git pull origin main
    Write-Host "✅ Repository updated successfully`n" -ForegroundColor Green
}
catch {
    Write-Host "⚠️  Could not pull changes: $_" -ForegroundColor Yellow
    Write-Host "Continuing with local version...`n" -ForegroundColor Yellow
}

# ================================================================
# STEP 3: Check if npm dependencies are installed
# ================================================================
$frontendPath = Join-Path $repoPath "elite-trader-ui"

if (Test-Path $frontendPath) {
    Write-Host "📦 Checking frontend dependencies..." -ForegroundColor Yellow
    
    $nodeModulesPath = Join-Path $frontendPath "node_modules"
    if (-not (Test-Path $nodeModulesPath)) {
        Write-Host "⚠️  node_modules not found. Installing dependencies..." -ForegroundColor Yellow
        Set-Location $frontendPath
        npm install
        Set-Location $repoPath
        Write-Host "✅ Dependencies installed`n" -ForegroundColor Green
    } else {
        Write-Host "✅ Dependencies already installed`n" -ForegroundColor Green
    }
} else {
    Write-Host "❌ Frontend directory not found at: $frontendPath" -ForegroundColor Red
    Write-Host "This might be a different repository structure.`n" -ForegroundColor Yellow
}

# ================================================================
# STEP 4: Check Python dependencies
# ================================================================
Write-Host "🐍 Checking Python environment..." -ForegroundColor Yellow

try {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ Python found: $pythonVersion" -ForegroundColor Green
    
    if (Test-Path "requirements.txt") {
        Write-Host "📦 Installing Python dependencies..." -ForegroundColor Yellow
        pip install -r requirements.txt --quiet
        Write-Host "✅ Python dependencies ready`n" -ForegroundColor Green
    }
}
catch {
    Write-Host "⚠️  Python not found. Backend will not start." -ForegroundColor Yellow
    Write-Host "Install Python from: https://www.python.org/downloads/`n" -ForegroundColor Yellow
}

# ================================================================
# STEP 5: Launch the system
# ================================================================
Write-Host "`n🚀 LAUNCHING ELITE TRADING SYSTEM" -ForegroundColor Cyan
Write-Host "================================================`n" -ForegroundColor Cyan

# Check if backend launch script exists
$backendLauncher = Join-Path $repoPath "LAUNCH_AURORA.ps1"
if (Test-Path $backendLauncher) {
    Write-Host "✅ Using existing LAUNCH_AURORA.ps1 script" -ForegroundColor Green
    & $backendLauncher
} else {
    # Manual launch
    Write-Host "📍 Repository Location: $repoPath" -ForegroundColor Cyan
    Write-Host "`n🎯 NEXT STEPS (run these in separate PowerShell windows):`n" -ForegroundColor Yellow
    
    Write-Host "1️⃣  START BACKEND:" -ForegroundColor Cyan
    Write-Host "   cd `"$repoPath`"" -ForegroundColor White
    Write-Host "   python backend/main.py`n" -ForegroundColor White
    
    Write-Host "2️⃣  START FRONTEND:" -ForegroundColor Cyan
    Write-Host "   cd `"$frontendPath`"" -ForegroundColor White
    Write-Host "   npm run dev`n" -ForegroundColor White
    
    Write-Host "3️⃣  OPEN BROWSER:" -ForegroundColor Cyan
    Write-Host "   Navigate to: http://localhost:3000`n" -ForegroundColor White
    
    Write-Host "`n💡 TIP: To auto-launch, run: .\LAUNCH_AURORA.ps1" -ForegroundColor Yellow
    
    # Offer to start backend now
    $response = Read-Host "`nWould you like to start the backend now? (Y/N)"
    if ($response -eq 'Y' -or $response -eq 'y') {
        Write-Host "`n🔥 Starting backend..." -ForegroundColor Green
        Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$repoPath'; python backend/main.py"
        
        Start-Sleep -Seconds 2
        
        $response2 = Read-Host "Would you like to start the frontend now? (Y/N)"
        if ($response2 -eq 'Y' -or $response2 -eq 'y') {
            Write-Host "🎨 Starting frontend..." -ForegroundColor Green
            Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$frontendPath'; npm run dev"
            
            Start-Sleep -Seconds 3
            Write-Host "`n🌐 Opening browser..." -ForegroundColor Green
            Start-Process "http://localhost:3000"
            
            Write-Host "`n✨ Elite Trading System launched successfully!" -ForegroundColor Cyan
        }
    }
}

Write-Host "`n================================================" -ForegroundColor Cyan
Write-Host "📝 Repository path saved for next time" -ForegroundColor Green
Write-Host "================================================`n" -ForegroundColor Cyan
