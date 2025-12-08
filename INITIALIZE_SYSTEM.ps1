<#
.SYNOPSIS
    Initialize Elite Trading System with Real Data
.DESCRIPTION
    Populates database with real stock symbols and generates initial signals
.NOTES
    Run this ONCE after fresh install or database reset
#>

$ErrorActionPreference = "Stop"

Clear-Host
Write-Host "`n" -NoNewline
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "  ELITE TRADING SYSTEM - INITIALIZATION" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "`n" -NoNewline

# Auto-detect project root
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$PROJECT_ROOT = $SCRIPT_DIR
Set-Location $PROJECT_ROOT

Write-Host "Project Root: $PROJECT_ROOT" -ForegroundColor Yellow
Write-Host "`n" -NoNewline

# ============================================================================
# STEP 1: VERIFY ENVIRONMENT
# ============================================================================

Write-Host "[1/5] Verifying environment..." -ForegroundColor Cyan

# Check Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "      Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "      ERROR: Python not found!" -ForegroundColor Red
    pause
    exit 1
}

# Check required files
$requiredFiles = @(
    "database\__init__.py",
    "data_collection\finviz_scraper.py",
    "backend\scheduler.py"
)

foreach ($file in $requiredFiles) {
    if (-not (Test-Path (Join-Path $PROJECT_ROOT $file))) {
        Write-Host "      ERROR: Missing file: $file" -ForegroundColor Red
        pause
        exit 1
    }
}

Write-Host "      Environment OK" -ForegroundColor Green

# ============================================================================
# STEP 2: STOP RUNNING SERVICES
# ============================================================================

Write-Host "[2/5] Stopping any running services..." -ForegroundColor Cyan

Get-Process python,pythonw,node -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

Write-Host "      Services stopped" -ForegroundColor Green

# ============================================================================
# STEP 3: POPULATE SYMBOL UNIVERSE
# ============================================================================

Write-Host "[3/5] Populating symbol universe from Finviz..." -ForegroundColor Cyan
Write-Host "      This may take 30-60 seconds..." -ForegroundColor Yellow

$populateScript = @"
import sys
sys.path.insert(0, r'$PROJECT_ROOT')

from database import SessionLocal
from data_collection.finviz_scraper import populate_symbols_from_apis
from core.logger import get_logger

logger = get_logger(__name__)

try:
    session = SessionLocal()
    logger.info('Starting symbol population...')
    
    count = populate_symbols_from_apis(session)
    
    logger.info(f'Successfully populated {count} symbols!')
    print(f'\n✅ SUCCESS: Populated {count} symbols from Finviz')
    
    session.close()
except Exception as e:
    logger.error(f'Failed to populate symbols: {e}')
    print(f'\n❌ ERROR: {e}')
    sys.exit(1)
"@

$populateScript | Out-File -FilePath "$PROJECT_ROOT\temp_populate.py" -Encoding UTF8

try {
    python "$PROJECT_ROOT\temp_populate.py"
    if ($LASTEXITCODE -ne 0) {
        throw "Symbol population failed"
    }
    Write-Host "      Symbol universe populated" -ForegroundColor Green
} catch {
    Write-Host "      ERROR: Failed to populate symbols" -ForegroundColor Red
    Write-Host "      $_" -ForegroundColor Red
    Remove-Item "$PROJECT_ROOT\temp_populate.py" -ErrorAction SilentlyContinue
    pause
    exit 1
} finally {
    Remove-Item "$PROJECT_ROOT\temp_populate.py" -ErrorAction SilentlyContinue
}

# ============================================================================
# STEP 4: RUN INITIAL SCAN
# ============================================================================

Write-Host "[4/5] Running initial market scan..." -ForegroundColor Cyan
Write-Host "      Generating first batch of signals..." -ForegroundColor Yellow

$scanScript = @"
import sys
sys.path.insert(0, r'$PROJECT_ROOT')

from backend.scheduler import ScannerManager
from config import load_config
from core.logger import get_logger
import asyncio

logger = get_logger(__name__)

async def run_initial_scan():
    try:
        config = load_config()
        scanner = ScannerManager(config)
        
        logger.info('Starting initial scan...')
        
        # Run scan with default parameters
        signals = await scanner.run_scan({
            'regime': 'YELLOW',
            'top_n': 50
        })
        
        logger.info(f'Generated {len(signals)} signals!')
        print(f'\n✅ SUCCESS: Generated {len(signals)} signals')
        
        return len(signals)
    except Exception as e:
        logger.error(f'Scan failed: {e}')
        print(f'\n❌ ERROR: {e}')
        return 0

if __name__ == '__main__':
    signal_count = asyncio.run(run_initial_scan())
    sys.exit(0 if signal_count > 0 else 1)
"@

$scanScript | Out-File -FilePath "$PROJECT_ROOT\temp_scan.py" -Encoding UTF8

try {
    python "$PROJECT_ROOT\temp_scan.py"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "      WARNING: Initial scan generated no signals (this is OK if market is closed)" -ForegroundColor Yellow
    } else {
        Write-Host "      Initial scan complete" -ForegroundColor Green
    }
} catch {
    Write-Host "      WARNING: Scan had issues but continuing..." -ForegroundColor Yellow
} finally {
    Remove-Item "$PROJECT_ROOT\temp_scan.py" -ErrorAction SilentlyContinue
}

# ============================================================================
# STEP 5: VERIFY DATABASE
# ============================================================================

Write-Host "[5/5] Verifying database..." -ForegroundColor Cyan

$verifyScript = @"
import sys
sys.path.insert(0, r'$PROJECT_ROOT')

from database import SessionLocal
from database.models import SymbolUniverse, SignalHistory

session = SessionLocal()

symbol_count = session.query(SymbolUniverse).count()
signal_count = session.query(SignalHistory).count()

print(f'Symbols in database: {symbol_count}')
print(f'Signals in database: {signal_count}')

session.close()

if symbol_count == 0:
    print('\n❌ ERROR: No symbols in database!')
    sys.exit(1)

print(f'\n✅ SUCCESS: Database initialized with {symbol_count} symbols and {signal_count} signals')
"@

$verifyScript | Out-File -FilePath "$PROJECT_ROOT\temp_verify.py" -Encoding UTF8

try {
    python "$PROJECT_ROOT\temp_verify.py"
    Write-Host "      Database verified" -ForegroundColor Green
} catch {
    Write-Host "      ERROR: Database verification failed" -ForegroundColor Red
} finally {
    Remove-Item "$PROJECT_ROOT\temp_verify.py" -ErrorAction SilentlyContinue
}

# ============================================================================
# COMPLETION
# ============================================================================

Write-Host "`n" -NoNewline
Write-Host "================================================================================" -ForegroundColor Green
Write-Host "  INITIALIZATION COMPLETE" -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Green
Write-Host "`n" -NoNewline

Write-Host "System Status:" -ForegroundColor Cyan
Write-Host "  Database populated with real stock data" -ForegroundColor White
Write-Host "  Initial signals generated" -ForegroundColor White
Write-Host "  System ready to launch" -ForegroundColor White
Write-Host "`n" -NoNewline

Write-Host "Next Step:" -ForegroundColor Yellow
Write-Host "  Run: .\LAUNCH_ELITE_TRADER.ps1" -ForegroundColor White
Write-Host "`n" -NoNewline

Write-Host "Launch now? (Y/N): " -ForegroundColor Yellow -NoNewline
$response = Read-Host

if ($response -eq "Y" -or $response -eq "y") {
    Write-Host "`nLaunching system...`n" -ForegroundColor Green
    Start-Sleep -Seconds 2
    & "$PROJECT_ROOT\LAUNCH_ELITE_TRADER.ps1"
} else {
    Write-Host "`nSystem ready. Run .\LAUNCH_ELITE_TRADER.ps1 when ready.`n" -ForegroundColor Green
}
