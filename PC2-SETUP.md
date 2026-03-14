# CLAUDE.md — ProfitTrader (PC2) Setup Instructions

> **IMPORTANT**: This file contains setup instructions for **ProfitTrader (PC2)**.
> If you are a Claude Code session on ProfitTrader, follow these instructions exactly.
> PC2 is the GPU/ML/Brain node in the two-PC Embodier Trader cluster.

## First Things First — Pull Fresh Code

```powershell
cd C:\Users\ProfitTrader\elite-trading-system
git fetch origin main
git checkout main
git pull origin main
```

Then read `CLAUDE.md` (root) for full project context and `PC2-SETUP.md` (this file) for PC2-specific setup.

---

## PC2 Identity

| Property | Value |
|----------|-------|
| **Hostname** | ProfitTrader |
| **LAN IP** | 192.168.1.116 (DHCP-reserved) |
| **Role** | GPU training, ML inference, brain_service (gRPC), Ollama LLM |
| **Repo path** | `C:\Users\ProfitTrader\elite-trading-system` |
| **Alpaca account** | Profit Trader (Key 2 — discovery scanning) |
| **Connects to** | ESPENMAIN (PC1) at 192.168.1.105 |

## PC2 Services & Ports

| Service | Port | Binds To | Purpose |
|---------|------|----------|---------|
| Brain Service (gRPC) | 50051 | 0.0.0.0 | LLM inference for council hypothesis/critic agents |
| Ollama | 11434 | 0.0.0.0 | Local LLM serving (llama3.2, deepseek-r1:14b, mixtral) |
| Backend API (optional) | 8000 | 0.0.0.0 | Discovery scanning (uses Alpaca Key 2) |
| GPU Telemetry | 8001 | 0.0.0.0 | NVIDIA GPU stats for cluster dashboard |

## Complete Setup — Run This in PowerShell

Paste this entire block into an **Administrator PowerShell** on ProfitTrader:

```powershell
# ══════════════════════════════════════════════════════════════
#  ProfitTrader (PC2) — One-Shot Setup & Launch
# ══════════════════════════════════════════════════════════════

# ── 1. Pull fresh code ──
cd C:\Users\ProfitTrader\elite-trading-system
git fetch origin main
git checkout main
git pull origin main
Write-Host "`n✅ Code updated" -ForegroundColor Green

# ── 2. Set up Brain Service ──
cd brain_service
if (-not (Test-Path venv)) { python -m venv venv }
venv\Scripts\Activate.ps1
pip install -r requirements.txt -q

# Create brain_service/.env
@"
GRPC_PORT=50051
OLLAMA_HOST=localhost
OLLAMA_PORT=11434
OLLAMA_MODEL=llama3.2
LOG_LEVEL=INFO
"@ | Out-File -FilePath .env -Encoding utf8
Write-Host "✅ brain_service/.env created" -ForegroundColor Green

# ── 3. Set up Backend (for discovery scanning) ──
cd ..\backend
if (-not (Test-Path venv)) { python -m venv venv }
venv\Scripts\Activate.ps1
pip install -r requirements.txt -q

# Create backend/.env for PC2
if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
    Write-Host "⚠️  backend/.env copied — FILL IN ALPACA KEY 2 (Profit Trader account)" -ForegroundColor Yellow
}
Write-Host "✅ Backend dependencies installed" -ForegroundColor Green

# ── 4. Windows Firewall rules (requires Admin) ──
$rules = @(
    @{Name="Ollama LLM"; Port=11434},
    @{Name="Brain gRPC"; Port=50051},
    @{Name="GPU Telemetry"; Port=8001},
    @{Name="Backend API"; Port=8000}
)
foreach ($r in $rules) {
    $existing = Get-NetFirewallRule -DisplayName $r.Name -ErrorAction SilentlyContinue
    if (-not $existing) {
        New-NetFirewallRule -DisplayName $r.Name -Direction Inbound -Protocol TCP `
            -LocalPort $r.Port -Action Allow -Profile Private | Out-Null
        Write-Host "✅ Firewall rule added: $($r.Name) (port $($r.Port))" -ForegroundColor Green
    } else {
        Write-Host "✔  Firewall rule exists: $($r.Name)" -ForegroundColor Gray
    }
}

# ── 5. Verify Ollama is installed ──
$ollamaPath = Get-Command ollama -ErrorAction SilentlyContinue
if ($ollamaPath) {
    Write-Host "✅ Ollama found at $($ollamaPath.Source)" -ForegroundColor Green
    # Pull required models
    Write-Host "Pulling LLM models (this may take a while on first run)..." -ForegroundColor Cyan
    ollama pull llama3.2
    ollama pull deepseek-r1:14b
} else {
    Write-Host "⚠️  Ollama not installed! Download from https://ollama.com/download" -ForegroundColor Red
}

# ── 6. Create Desktop shortcut ──
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\ProfitTrader Brain.lnk")
$Shortcut.TargetPath = "powershell.exe"
$Shortcut.Arguments = "-NoExit -Command `"cd 'C:\Users\ProfitTrader\elite-trading-system'; " +
    "Start-Process powershell '-NoExit -Command ollama serve'; " +
    "Start-Sleep 3; " +
    "Start-Process powershell '-NoExit -Command cd C:\Users\ProfitTrader\elite-trading-system\brain_service; .\venv\Scripts\Activate.ps1; python server.py'; " +
    "cd backend; .\venv\Scripts\Activate.ps1; uvicorn app.main:app --host 0.0.0.0 --port 8000`""
$Shortcut.WorkingDirectory = "C:\Users\ProfitTrader\elite-trading-system"
$Shortcut.Description = "ProfitTrader PC2 - Brain + Ollama + Discovery"
$Shortcut.IconLocation = "shell32.dll,76"
$Shortcut.Save()
Write-Host "`n✅ Desktop shortcut created: ProfitTrader Brain" -ForegroundColor Green

# ── 7. Launch everything ──
Write-Host "`n🚀 Launching ProfitTrader services..." -ForegroundColor Cyan

# Start Ollama in background
Start-Process powershell -ArgumentList "-NoExit", "-Command", "ollama serve"
Start-Sleep 3

# Start Brain Service (gRPC on :50051)
Start-Process powershell -ArgumentList "-NoExit", "-Command", `
    "cd 'C:\Users\ProfitTrader\elite-trading-system\brain_service'; .\venv\Scripts\Activate.ps1; python server.py"

# Start Backend (discovery scanning on :8000)
cd C:\Users\ProfitTrader\elite-trading-system\backend
venv\Scripts\Activate.ps1

Write-Host ""
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  ProfitTrader (PC2) — ONLINE" -ForegroundColor Green
Write-Host ""
Write-Host "  Ollama LLM:     http://localhost:11434" -ForegroundColor White
Write-Host "  Brain gRPC:     localhost:50051" -ForegroundColor White
Write-Host "  Backend API:    http://localhost:8000" -ForegroundColor White
Write-Host "  ESPENMAIN (PC1): 192.168.1.105:8000" -ForegroundColor Yellow
Write-Host ""
Write-Host "  Test from PC1:" -ForegroundColor Gray
Write-Host "    Test-Connection 192.168.1.116 -Count 2" -ForegroundColor Gray
Write-Host "    curl http://192.168.1.116:8000/health" -ForegroundColor Gray
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Backend .env Overrides for PC2

After setup, edit `backend/.env` and set these PC2-specific values:

```env
# ── PC2 uses Alpaca Key 2 (discovery scanning) ──
ALPACA_API_KEY=<your-profit-trader-api-key>
ALPACA_SECRET_KEY=<your-profit-trader-secret-key>
APCA_API_KEY_ID=<your-profit-trader-api-key>
APCA_API_SECRET_KEY=<your-profit-trader-secret-key>

# ── Brain runs locally on PC2 ──
BRAIN_SERVICE_URL=localhost:50051
BRAIN_HOST=localhost
BRAIN_PORT=50051

# ── Cluster identity (PC2 connects to PC1) ──
CLUSTER_PC2_HOST=
PC1_HOSTNAME=ESPENMAIN
PC1_IP=192.168.1.105
PC2_HOSTNAME=ProfitTrader
PC2_IP=192.168.1.116

# ── Ollama is local on PC2 ──
OLLAMA_BASE_URL=http://localhost:11434
```

## Verify Cluster Connectivity

Run these from **each PC** to confirm the link:

**From ProfitTrader (PC2) → test PC1:**
```powershell
Test-Connection 192.168.1.105 -Count 2
Invoke-RestMethod http://192.168.1.105:8000/health
```

**From ESPENMAIN (PC1) → test PC2:**
```powershell
Test-Connection 192.168.1.116 -Count 2
Invoke-RestMethod http://192.168.1.116:8000/health
# Test brain gRPC port
Test-NetConnection 192.168.1.116 -Port 50051
```

## What Runs Where

```
ESPENMAIN (PC1: 192.168.1.105)          ProfitTrader (PC2: 192.168.1.116)
┌──────────────────────────┐            ┌──────────────────────────────┐
│ Frontend (Vite :5173)    │            │ Ollama LLM (:11434)          │
│ Backend API (:8000)      │◄──gRPC────►│ Brain Service (:50051)       │
│ DuckDB (analytics)       │            │ Backend API (:8000)          │
│ Order Execution          │            │ GPU Training (RTX)           │
│ Signal Engine            │            │ Discovery Scanning           │
│ Council (35 agents)      │            │ Model Artifacts              │
│ WebSocket Manager        │            │ GPU Telemetry (:8001)        │
└──────────────────────────┘            └──────────────────────────────┘
         Alpaca Key 1                            Alpaca Key 2
       (portfolio trading)                   (discovery scanning)
```

## LLM Model Pinning (Which Models Run Where)

| PC | Models | Tasks |
|----|--------|-------|
| PC1 (ESPENMAIN) | llama3.2, mistral:7b | regime_classification, signal_scoring, risk_check, quick_hypothesis, feature_summary |
| PC2 (ProfitTrader) | deepseek-r1:14b, mixtral:8x7b | trade_thesis, strategy_critic, deep_postmortem, strategy_evolution, overnight_analysis |

## Troubleshooting

**Brain service won't start:**
- Check Ollama is running: `curl http://localhost:11434/api/tags`
- Check port isn't in use: `netstat -an | findstr 50051`
- Check firewall: `Get-NetFirewallRule -DisplayName "Brain gRPC"`

**PC1 can't reach PC2:**
- Both PCs must be on same subnet (192.168.1.x)
- Windows network profile must be **Private** (not Public)
- Check firewall rules were added (Step 4 above)

**Ollama model missing:**
```powershell
ollama list                    # See installed models
ollama pull llama3.2           # Pull if missing
ollama pull deepseek-r1:14b    # Heavy model for PC2
```
