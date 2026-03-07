# Cluster Network Setup Guide — Dual-PC (PC1 + PC2)

> **Prerequisites**: Both PCs on the same LAN via Gigabit Ethernet (not Wi-Fi).

---

## 1. Lock PC2's IP Address (AT&T Router)

PC2 must have a **static/reserved IP** so `CLUSTER_PC2_HOST` never goes stale.

### Option A: DHCP Reservation (Recommended)
1. Open AT&T router admin: `http://192.168.1.254` (or your gateway IP)
2. Navigate to **Settings → LAN → DHCP**
3. Find PC2 (ProfitTrader) in the connected devices list
4. Click **Reserve** or **Add DHCP Reservation**
5. Note the assigned IP (e.g., `192.168.1.50`)
6. Reboot PC2 to confirm it gets the same IP

### Option B: Static IP on PC2 (Windows)
1. **Settings → Network & Internet → Ethernet → Edit IP**
2. Switch from Automatic (DHCP) to **Manual**
3. Set:
   - IP: `192.168.1.50` (or your chosen address, outside DHCP range)
   - Subnet: `255.255.255.0`
   - Gateway: `192.168.1.254` (your router)
   - DNS: `8.8.8.8` / `8.8.4.4`

---

## 2. Set Windows Network Profile to Private

**Critical**: Windows Firewall rules for "Private" networks allow LAN traffic.
"Public" profile blocks inbound connections — Ollama and Brain gRPC will be unreachable.

### On BOTH PC1 (ESPENMAIN) and PC2 (ProfitTrader):
1. **Settings → Network & Internet → Ethernet**
2. Click your active connection
3. Set **Network profile type** to **Private network**

### Verify via PowerShell:
```powershell
Get-NetConnectionProfile | Select-Object Name, NetworkCategory
# Should show "Private" for your LAN adapter
```

### Force-set if needed:
```powershell
Set-NetConnectionProfile -InterfaceAlias "Ethernet" -NetworkCategory Private
```

---

## 3. Windows Firewall Rules

Allow inbound traffic for Ollama and Brain Service on **both PCs**.

### PowerShell (Run as Administrator on both PCs):
```powershell
# Ollama API (port 11434)
New-NetFirewallRule -DisplayName "Ollama API" -Direction Inbound -Protocol TCP -LocalPort 11434 -Action Allow -Profile Private

# Brain gRPC Service (port 50051)
New-NetFirewallRule -DisplayName "Brain gRPC" -Direction Inbound -Protocol TCP -LocalPort 50051 -Action Allow -Profile Private

# GPU Telemetry (if running telemetry daemon on PC2, port 8001)
New-NetFirewallRule -DisplayName "GPU Telemetry" -Direction Inbound -Protocol TCP -LocalPort 8001 -Action Allow -Profile Private
```

### Verify rules:
```powershell
Get-NetFirewallRule -DisplayName "Ollama*","Brain*","GPU*" | Select-Object DisplayName, Enabled, Direction, Profile
```

---

## 4. Configure the Elite Trading System

Once PC2's IP is locked, update your `.env` on PC1:

```env
# backend/.env (on PC1 — ESPENMAIN)

# Point to PC2's reserved IP
CLUSTER_PC2_HOST=192.168.1.50
CLUSTER_HEALTH_INTERVAL=60

# Brain service on PC2
BRAIN_ENABLED=true
BRAIN_HOST=192.168.1.50
BRAIN_PORT=50051

# Ollama multi-node pool (both PCs)
SCANNER_OLLAMA_URLS=http://localhost:11434,http://192.168.1.50:11434

# Dual-PC Ollama
OLLAMA_PC2_URL=http://192.168.1.50:11434
```

> Replace `192.168.1.50` with PC2's actual reserved IP.

---

## 5. Start Services on PC2

```bash
# Terminal 1: Start Ollama
set OLLAMA_HOST=0.0.0.0
ollama serve

# Terminal 2: Start Brain Service (gRPC)
cd elite-trading-system/brain_service
pip install grpcio grpcio-tools httpx
python server.py
```

**Important**: `OLLAMA_HOST=0.0.0.0` makes Ollama listen on all interfaces (not just localhost). Without this, PC1 cannot reach PC2's Ollama.

---

## 6. Verify Connectivity

From PC1, test that PC2 is reachable:

```powershell
# Ping
ping 192.168.1.50

# Ollama health
curl http://192.168.1.50:11434/api/tags

# Ollama loaded models
curl http://192.168.1.50:11434/api/ps

# Brain gRPC (TCP connect test)
Test-NetConnection -ComputerName 192.168.1.50 -Port 50051
```

Then start the trading system on PC1 and check:
```
GET http://localhost:8000/api/v1/cluster/status
```

You should see:
```json
{
  "cluster_mode": true,
  "pc2": {
    "ollama": { "available": true, "models": ["deepseek-r1:14b", ...] },
    "brain_service": { "available": true }
  }
}
```

---

## 7. Network Performance Notes

- **Gigabit LAN** = ~125 MB/s throughput, <1ms latency
- **Do NOT** transfer model weights (.gguf) over the network at runtime
- **Do** pre-download all required models to both PCs:
  ```bash
  # On PC2
  ollama pull deepseek-r1:14b
  ollama pull mixtral:8x7b
  ollama pull llama3.2
  ```
- gRPC and HTTP inference requests are lightweight (~KB per request) — Gigabit is massive overkill and that's perfect
- Set `OLLAMA_CUDA_GRAPHS=1` and `OLLAMA_FLASH_ATTENTION=1` on both PCs for optimal GPU performance

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| PC1 can't reach PC2 Ollama | Firewall blocking | Check network profile is Private, add firewall rule |
| Ollama "connection refused" on PC2 | Ollama bound to localhost | Set `OLLAMA_HOST=0.0.0.0` before starting |
| PC2 IP changed | DHCP lease expired | Set DHCP reservation on router |
| Cluster status shows "single-PC mode" | `CLUSTER_PC2_HOST` empty | Set it in `.env` |
| Brain service unreachable | gRPC not started on PC2 | Run `python server.py` on PC2 |
| High latency between PCs | Using Wi-Fi | Use Ethernet cable, not Wi-Fi |
