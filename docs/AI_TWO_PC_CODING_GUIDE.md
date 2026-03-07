# AI & Coding Instructions: Two-PC Development Workflow

> **For AI assistants (Perplexity/Comet, Claude, Copilot) and human developers working on Embodier Trader.**
> **Last Updated:** 2026-03-07

## Critical Context: This Project Runs on Two PCs

Embodier Trader is developed and deployed across two physical Windows PCs on the same LAN. Every code change, config edit, and deployment must account for this.

| | PC1 (Primary) | PC2 (Secondary) |
|--|--------------|----------------|
| **Hostname** | ESPENMAIN | ProfitTrader |
| **LAN IP** | 192.168.1.105 | 192.168.1.116 |
| **Role** | Backend API, frontend dev, primary coding | GPU ML training, secondary services |
| **User** | C:\Users\Espen | C:\Users\ProfitTrader |
| **Repo** | C:\Users\Espen\elite-trading-system | C:\Users\ProfitTrader\elite-trading-system |

Both IPs are DHCP-reserved (fixed) on the AT&T BGW320-505 router at 192.168.1.254.

## Rules for AI Assistants

### 1. Never Hardcode localhost for Cross-PC Communication
```python
# WRONG - only works on the same machine
api_url = "http://localhost:8000"
ws_url = "ws://localhost:8000/ws"

# RIGHT - use env vars that resolve to LAN IPs
import os
api_url = os.getenv("PC1_API_URL", "http://192.168.1.105:8000")
ws_url = os.getenv("PC1_WS_URL", "ws://192.168.1.105:8000/ws")
```

### 2. Always Bind to 0.0.0.0, Not 127.0.0.1
```python
# WRONG - only accessible from same machine
uvicorn.run(app, host="127.0.0.1", port=8000)

# RIGHT - accessible from both PCs
uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 3. Use Environment Variables for All PC-Specific Paths
```python
# WRONG - breaks on ProfitTrader
repo_path = "C:\\Users\\Espen\\elite-trading-system"

# RIGHT - works on both
import os
repo_path = os.getenv("REPO_PATH", os.path.dirname(os.path.abspath(__file__)))
```

### 4. Frontend Must Use LAN IP When Accessed Cross-PC
When ProfitTrader accesses the frontend served from ESPENMAIN:
```env
# frontend-v2/.env on ProfitTrader
VITE_API_URL=http://192.168.1.105:8000
VITE_WS_URL=ws://192.168.1.105:8000/ws
```

### 5. Git Sync Is the Source of Truth
Both PCs clone the same repo. To sync:
```powershell
# On the PC that needs updates:
git pull origin main
```
Never copy files manually between PCs. Always commit, push, pull.

### 6. Which PC Runs What

| Service | Runs On | Why |
|---------|---------|-----|
| FastAPI backend (primary) | ESPENMAIN (PC1) | Central API server |
| React frontend | ESPENMAIN (PC1) | Pairs with backend |
| ML model training | ProfitTrader (PC2) | Has GPU (dual RTX) |
| Brain service / agents | ESPENMAIN (PC1) | Needs backend access |
| Backtesting | Either | CPU-bound, can run anywhere |
| Database (DuckDB) | ESPENMAIN (PC1) | Single source of truth |

### 7. When Writing Code That Calls the Other PC
Always read from .env:
```python
# Service on PC2 calling PC1's API
pc1_url = os.getenv("PC1_API_URL")  # http://192.168.1.105:8000
response = requests.get(f"{pc1_url}/api/v1/signals")

# Service on PC1 calling PC2's training endpoint
pc2_url = os.getenv("PC2_API_URL")  # http://192.168.1.116:8000
response = requests.post(f"{pc2_url}/api/v1/train", json=payload)
```

### 8. WebSocket Connections Across PCs
```javascript
// Frontend on ProfitTrader connecting to ESPENMAIN backend
const ws = new WebSocket(import.meta.env.VITE_WS_URL || 'ws://192.168.1.105:8000/ws');
```

### 9. Testing Connectivity
Before debugging network issues, verify basics:
```powershell
# Quick test from either PC
Test-Connection 192.168.1.105 -Count 1  # ping ESPENMAIN
Test-Connection 192.168.1.116 -Count 1  # ping ProfitTrader
Invoke-RestMethod http://192.168.1.105:8000/api/v1/health
Invoke-RestMethod http://192.168.1.116:8000/api/v1/health
```

### 10. Docker / docker-compose Considerations
If using docker-compose, expose ports on 0.0.0.0:
```yaml
services:
  backend:
    ports:
      - "0.0.0.0:8000:8000"  # NOT 127.0.0.1:8000:8000
```

## Quick Reference Card

```
ESPENMAIN (PC1):  192.168.1.105  |  Primary  |  Backend + Frontend + DB
ProfitTrader (PC2): 192.168.1.116  |  Secondary |  GPU Training + ML
Router:           192.168.1.254  |  AT&T BGW320-505
Subnet:           192.168.1.0/24
Backend Port:     8000
Frontend Port:    3000
Bind Address:     0.0.0.0 (always)
```

## Related Docs
- [NETWORK_TWO_PC_SETUP.md](./NETWORK_TWO_PC_SETUP.md) - Full network config, IPs, firewall rules
- [../SETUP.md](../SETUP.md) - General setup and quick start
- [../.env.example](../.env.example) - All environment variables including network section
- [../AI-CONTEXT-GUIDE.md](../AI-CONTEXT-GUIDE.md) - General AI context for the project
