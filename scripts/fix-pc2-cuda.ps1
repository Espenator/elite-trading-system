# fix-pc2-cuda.ps1 — Restore PyTorch CUDA on PC2 (ProfitTrader)
# Run ON PC2: powershell -ExecutionPolicy Bypass -File .\scripts\fix-pc2-cuda.ps1
#
# Problem: PyTorch falls back to CPU for all LLM inference because CUDA
# support was not installed. The RTX 4080 (17.2GB VRAM) sits idle.
#
# This script reinstalls PyTorch with CUDA 12.1 support and verifies.

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$BrainDir = Join-Path $Root "brain_service"
$BackendDir = Join-Path $Root "backend"

Write-Host ""
Write-Host "  ============================================" -ForegroundColor Cyan
Write-Host "    Fix PyTorch CUDA on PC2 (ProfitTrader)" -ForegroundColor Cyan
Write-Host "  ============================================" -ForegroundColor Cyan
Write-Host ""

# Try brain_service venv first, fall back to backend venv
$venvPython = Join-Path $BrainDir "venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    $venvPython = Join-Path $BrainDir ".venv\Scripts\python.exe"
}
if (-not (Test-Path $venvPython)) {
    $venvPython = Join-Path $BackendDir "venv\Scripts\python.exe"
}
if (-not (Test-Path $venvPython)) {
    Write-Host "  [ERROR] No Python venv found. Create one first:" -ForegroundColor Red
    Write-Host "    cd brain_service && python -m venv venv" -ForegroundColor Yellow
    exit 1
}

$pip = Join-Path (Split-Path $venvPython) "pip.exe"
Write-Host "  Using Python: $venvPython" -ForegroundColor Gray

# Step 1: Uninstall existing PyTorch
Write-Host "  [1/3] Uninstalling existing PyTorch..." -ForegroundColor Yellow
& $pip uninstall torch torchvision torchaudio -y 2>&1 | Out-Null

# Step 2: Install PyTorch with CUDA 12.1
Write-Host "  [2/3] Installing PyTorch with CUDA 12.1 support..." -ForegroundColor Yellow
& $pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
if ($LASTEXITCODE -ne 0) {
    Write-Host "  [ERROR] PyTorch install failed. Check network and try again." -ForegroundColor Red
    exit 1
}

# Step 3: Verify CUDA
Write-Host "  [3/3] Verifying CUDA..." -ForegroundColor Yellow
$result = & $venvPython -c "import torch; print('CUDA:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'NONE'); print('VRAM:', round(torch.cuda.get_device_properties(0).total_mem / 1024**3, 1), 'GB') if torch.cuda.is_available() else None" 2>&1
Write-Host $result -ForegroundColor Green

if ($result -match "CUDA: True") {
    Write-Host ""
    Write-Host "  [OK] CUDA is working! RTX 4080 ready for LLM inference." -ForegroundColor Green
    Write-Host ""
    Write-Host "  Next: restart brain_service to use GPU:" -ForegroundColor Gray
    Write-Host "    cd brain_service && python server.py" -ForegroundColor Gray
} else {
    Write-Host ""
    Write-Host "  [WARN] CUDA not available. Check:" -ForegroundColor Yellow
    Write-Host "    1. NVIDIA driver installed (nvidia-smi should work)" -ForegroundColor Yellow
    Write-Host "    2. CUDA toolkit version matches PyTorch (12.1)" -ForegroundColor Yellow
}

# Set env vars for .env if not present
$envFile = Join-Path $BrainDir ".env"
if (-not (Test-Path $envFile)) {
    $envFile = Join-Path $BackendDir ".env"
}
$envContent = ""
if (Test-Path $envFile) {
    $envContent = Get-Content $envFile -Raw -ErrorAction SilentlyContinue
}
if ($envContent -notmatch "CUDA_VISIBLE_DEVICES") {
    Write-Host ""
    Write-Host "  Add to your .env on PC2:" -ForegroundColor Yellow
    Write-Host "    CUDA_VISIBLE_DEVICES=0" -ForegroundColor Gray
    Write-Host "    CUDA_DEVICE_ORDER=PCI_BUS_ID" -ForegroundColor Gray
}
