# Two-PC Network Setup Guide

> **Last Updated:** 2026-03-07
> **Router:** AT&T BGW320-505 | **Admin:** http://192.168.1.254

## Network Overview

Embodier Trader runs across two PCs on the same LAN. Both IPs are DHCP-reserved (fixed allocation) on the AT&T gateway so they never change.

| Property | PC1 (Primary) | PC2 (Secondary) |
|----------|--------------|----------------|
| **Hostname** | ESPENMAIN | ProfitTrader |
| **LAN IP** | 192.168.1.105 | 192.168.1.116 |
| **MAC Address** | CC:96:E5:38:F9:79 | CC:96:E5:3B:58:4E |
| **Role** | Backend API host, primary dev | GPU training, secondary services |
| **User Path** | C:\Users\Espen\ | C:\Users\ProfitTrader\ |
| **Repo Path** | C:\Users\Espen\elite-trading-system | C:\Users\ProfitTrader\elite-trading-system |

## Network Details

| Setting | Value |
|---------|-------|
| Subnet | 192.168.1.0/24 |
| Gateway | 192.168.1.254 |
| DHCP Range | 192.168.1.64 - 192.168.1.253 |
| DNS | Automatic (AT&T) |
| Wi-Fi SSID | ATT |
| Wi-Fi Security | WPA2 |
| Port Forwarding | None needed (same LAN) |
| AP/LAN Isolation | Disabled |
| Guest Network | Disabled |

## How the Two PCs Communicate

Both PCs are on the same 192.168.1.x subnet. No port forwarding or special firewall rules are needed.

### From ProfitTrader, access ESPENMAIN:
```
Backend API:  http://192.168.1.105:8000
API Docs:     http://192.168.1.105:8000/docs
WebSocket:    ws://192.168.1.105:8000/ws
Frontend:     http://192.168.1.105:3000
```

### From ESPENMAIN, access ProfitTrader:
```
Backend API:  http://192.168.1.116:8000
API Docs:     http://192.168.1.116:8000/docs
WebSocket:    ws://192.168.1.116:8000/ws
Frontend:     http://192.168.1.116:3000
```

## .env Configuration Per Machine

### ESPENMAIN (.env)
```env
# Server binds to all interfaces so ProfitTrader can reach it
HOST=0.0.0.0
PORT=8000

# This machine's identity
PC1_HOSTNAME=ESPENMAIN
PC1_IP=192.168.1.105
PC1_ROLE=primary

# Reach ProfitTrader
PC2_API_URL=http://192.168.1.116:8000
PC2_WS_URL=ws://192.168.1.116:8000/ws
```

### ProfitTrader (.env)
```env
# Server binds to all interfaces so ESPENMAIN can reach it
HOST=0.0.0.0
PORT=8000

# This machine's identity
PC2_HOSTNAME=ProfitTrader
PC2_IP=192.168.1.116
PC2_ROLE=secondary

# Reach ESPENMAIN
PC1_API_URL=http://192.168.1.105:8000
PC1_WS_URL=ws://192.168.1.105:8000/ws

# Frontend on ProfitTrader points to ESPENMAIN backend
VITE_API_URL=http://192.168.1.105:8000
VITE_WS_URL=ws://192.168.1.105:8000/ws
```

## Quick Connectivity Test

Run from either PC in PowerShell:
```powershell
# From ESPENMAIN, test ProfitTrader
Test-Connection 192.168.1.116 -Count 2
Invoke-RestMethod http://192.168.1.116:8000/api/v1/health

# From ProfitTrader, test ESPENMAIN
Test-Connection 192.168.1.105 -Count 2
Invoke-RestMethod http://192.168.1.105:8000/api/v1/health
```

## Windows Firewall Note

If connectivity fails, ensure Windows Firewall allows Python/Node through:
```powershell
# Run as Administrator on BOTH PCs
New-NetFirewallRule -DisplayName "Embodier Backend" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
New-NetFirewallRule -DisplayName "Embodier Frontend" -Direction Inbound -LocalPort 3000 -Protocol TCP -Action Allow
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Can't ping other PC | Check Windows Firewall, ensure both on same SSID/Ethernet |
| API timeout across PCs | Verify HOST=0.0.0.0 in .env (not 127.0.0.1) |
| IP changed | Re-check router at http://192.168.1.254 > IP Allocation |
| WebSocket won't connect | Ensure ws:// URL uses LAN IP, not localhost |
| Frontend can't reach backend | Set VITE_API_URL to the backend PC's LAN IP |
