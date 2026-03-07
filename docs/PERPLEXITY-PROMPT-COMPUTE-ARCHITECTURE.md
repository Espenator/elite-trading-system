# Perplexity Implementation Prompt: Multi-PC Compute Architecture (Issue #39)

> **Context**: This is a prompt for Perplexity Computer to implement the compute infrastructure layer for the Elite Trading System. This must be built BEFORE Issue #38 (Continuous Discovery Architecture) because the firehose needs pipes before turning on the water.

---

## PROJECT CONTEXT

```
PROJECT: Embodier Trader (Elite Trading System)
REPO: github.com/Espenator/elite-trading-system
LOCAL PATH: C:\Users\Espen\elite-trading-system
VERSION: 3.5.0-dev (Continuous Discovery Architecture)
STACK: FastAPI + React (Vite) + DuckDB
PYTHON: 4-space indentation ALWAYS, async/await, Pydantic schemas
BRANCH: main
CI: GREEN (151 tests passing)
TRACKING: GitHub Issue #39

RULES:
  - 4-space indentation in Python (NEVER tabs)
  - All services use async/await
  - Config via pydantic Settings class in backend/app/core/config.py
  - Environment variables loaded from backend/.env via python-dotenv
  - MessageBus pub/sub for inter-service communication
  - Services initialized in main.py lifespan (_start_event_driven_pipeline)
  - No yfinance anywhere
  - No mock data in production components
```

---

## HARDWARE

| | PC1 (ESPENMAIN) | PC2 |
|---|---|---|
| GPU | RTX 4080 16GB VRAM | RTX 4080 16GB VRAM |
| Role | API + Council + Frontend + Ollama | LLM Farm + Brain Service + Scanner overflow |
| Network | Same LAN | Same LAN |
| Ollama | localhost:11434 | Will be at `<pc2-ip>:11434` |

---

## WHAT TO BUILD (8 Tasks)

### TASK E0.1: AlpacaKeyPool

**Create new file**: `backend/app/services/alpaca_key_pool.py`

**Purpose**: Manage multiple Alpaca API keys with role assignment, health tracking, and graceful fallback to single key.

**Why**: Alpaca allows exactly 1 WebSocket per account (hard limit — see `alpaca_stream_service.py` line 136). Multiple keys = multiple WebSocket streams = 1000+ symbols in real-time instead of 10.

**Requirements**:
- Load keys from environment: `ALPACA_KEY_1`/`ALPACA_SECRET_1`, `ALPACA_KEY_2`/`ALPACA_SECRET_2`, `ALPACA_KEY_3`/`ALPACA_SECRET_3`
- If none of those are set, fall back to existing `ALPACA_API_KEY`/`ALPACA_SECRET_KEY` (backward compatible)
- Each key has a role: `trading`, `discovery_a`, `discovery_b`
- Track health per key: rate limit hits, consecutive errors, avg latency
- Method: `get_key(role: str) -> AlpacaKeyConfig` returns the key for a given role
- Method: `get_all_keys() -> List[AlpacaKeyConfig]` for iteration
- Method: `report_error(role: str)` / `report_success(role: str)` for health tracking

**Follow this existing pattern** from `hyper_swarm.py` lines 118-123:
```python
def _load_ollama_pool(self) -> List[str]:
    """Load Ollama node URLs from environment."""
    env_urls = os.getenv("SCANNER_OLLAMA_URLS", "")
    if env_urls:
        return [u.strip() for u in env_urls.split(",") if u.strip()]
    return list(DEFAULT_OLLAMA_URLS)
```

**Config additions** to `backend/app/core/config.py` (add after line 74, after existing Alpaca section):
```python
# ── Multi-Key Alpaca Pool ─────────────────────────────────
ALPACA_KEY_1: str = ""
ALPACA_SECRET_1: str = ""
ALPACA_KEY_2: str = ""
ALPACA_SECRET_2: str = ""
ALPACA_KEY_3: str = ""
ALPACA_SECRET_3: str = ""
```

---

### TASK E0.2: AlpacaStreamManager

**Create new file**: `backend/app/services/alpaca_stream_manager.py`

**Purpose**: Orchestrate multiple WebSocket streams (one per API key), each covering a different symbol universe. Replaces single `AlpacaStreamService` as the top-level stream coordinator.

**Requirements**:
- Import and use `AlpacaKeyPool` from E0.1
- For each key in the pool, create an `AlpacaStreamService` instance (injecting that key)
- The `trading` key streams portfolio symbols only (from Alpaca positions API)
- The `discovery_a` key streams top 500 high-priority symbols
- The `discovery_b` key streams next 500 symbols (rotating universe)
- All streams publish to the SAME MessageBus topic `market_data.bar`
- If only 1 key is configured, behave exactly like current `AlpacaStreamService`
- Method: `rebalance_symbols(universe: List[str])` — redistribute symbols across streams
- Method: `get_status() -> Dict` — per-stream stats (symbols count, bars received, errors)

**Current AlpacaStreamService** (`backend/app/services/alpaca_stream_service.py`) has this constructor:
```python
class AlpacaStreamService:
    def __init__(self, message_bus, symbols: Optional[List[str]] = None):
        self.message_bus = message_bus
        self.symbols = symbols or [
            "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA",
            "TSLA", "META", "SPY", "QQQ", "IWM",
        ]
```

**You must modify `AlpacaStreamService`** to accept optional `api_key` and `secret_key` parameters:
```python
def __init__(self, message_bus, symbols=None, api_key=None, secret_key=None):
    # If api_key/secret_key provided, use them instead of settings/env
```

Then in the `start()` method (line 73-77), use the injected keys if provided:
```python
# Currently:
api_key = getattr(_settings, "ALPACA_API_KEY", "") or os.getenv("ALPACA_API_KEY", "")
secret_key = getattr(_settings, "ALPACA_SECRET_KEY", "") or os.getenv("ALPACA_SECRET_KEY", "")

# Change to:
api_key = self._api_key or getattr(_settings, "ALPACA_API_KEY", "") or os.getenv(...)
secret_key = self._secret_key or getattr(_settings, "ALPACA_SECRET_KEY", "") or os.getenv(...)
```

**Wire into main.py**: In `_start_event_driven_pipeline()` (line 236), replace the single `AlpacaStreamService` with `AlpacaStreamManager`. The manager creates the individual stream services internally.

---

### TASK E0.3: OllamaNodePool

**Create new file**: `backend/app/services/ollama_node_pool.py`

**Purpose**: Shared Ollama node pool with health checks, per-node semaphores, and round-robin distribution. Extracted from HyperSwarm to be reusable by all services.

**Requirements**:
- Load nodes from `SCANNER_OLLAMA_URLS` env var (comma-separated)
- Default to `["http://localhost:11434"]` if not set
- Per-node `asyncio.Semaphore(max_concurrent)` (default 10)
- Round-robin `get_next_node() -> str` with health-aware skip
- `report_success(url, latency_ms)` / `report_error(url)` for tracking
- Health check: periodic ping to `{url}/api/tags` (Ollama health endpoint)
- If a node fails 3 consecutive health checks, mark as unhealthy and skip
- Re-check unhealthy nodes every 60s
- `get_status() -> Dict` with per-node stats

**Current HyperSwarm implementation** to extract from (`hyper_swarm.py` lines 91-123):
```python
class HyperSwarm:
    def __init__(self, message_bus=None):
        self._ollama_urls = self._load_ollama_pool()
        self._ollama_semaphores: Dict[str, asyncio.Semaphore] = {
            url: asyncio.Semaphore(MAX_CONCURRENT_PER_OLLAMA) for url in self._ollama_urls
        }
        self._node_index = 0  # Round-robin counter

    def _load_ollama_pool(self) -> List[str]:
        env_urls = os.getenv("SCANNER_OLLAMA_URLS", "")
        if env_urls:
            return [u.strip() for u in env_urls.split(",") if u.strip()]
        return list(DEFAULT_OLLAMA_URLS)
```

**After creating OllamaNodePool, refactor HyperSwarm** to use it:
```python
from app.services.ollama_node_pool import get_ollama_pool

class HyperSwarm:
    def __init__(self, message_bus=None):
        self._pool = get_ollama_pool()
        # Remove _ollama_urls, _ollama_semaphores, _node_index, _load_ollama_pool
```

---

### TASK E0.4: Enable Brain Service

**Files to modify**:
- `backend/app/services/brain_client.py` — already built, just needs correct defaults
- `backend/app/core/config.py` — verify BRAIN_PORT is 50051

**Current state** (`brain_client.py` lines 22-26):
```python
BRAIN_ENABLED = os.getenv("BRAIN_ENABLED", "false").lower() == "true"
BRAIN_HOST = os.getenv("BRAIN_HOST", "localhost")
BRAIN_PORT = int(os.getenv("BRAIN_PORT", "50051"))
```

**Config.py** (line 162-165) already has:
```python
BRAIN_ENABLED: bool = True
BRAIN_HOST: str = "localhost"
BRAIN_PORT: int = 50051
```

**Problem**: `brain_client.py` reads from `os.getenv` directly, not from settings. The env default is `"false"` but config.py default is `True`. These are inconsistent. Fix `brain_client.py` to read from settings first, fallback to env:
```python
try:
    from app.core.config import settings
    BRAIN_ENABLED = settings.BRAIN_ENABLED
    BRAIN_HOST = settings.BRAIN_HOST
    BRAIN_PORT = settings.BRAIN_PORT
except Exception:
    BRAIN_ENABLED = os.getenv("BRAIN_ENABLED", "false").lower() == "true"
    BRAIN_HOST = os.getenv("BRAIN_HOST", "localhost")
    BRAIN_PORT = int(os.getenv("BRAIN_PORT", "50051"))
```

**The brain_service gRPC server already exists** at `brain_service/server.py` and `brain_service/ollama_client.py`. No changes needed there. It just needs to be started on PC2:
```bash
# On PC2:
cd elite-trading-system/brain_service
pip install grpcio grpcio-tools httpx
ollama serve  # Start Ollama
python server.py  # Start gRPC server on port 50051
```

---

### TASK E0.5: NodeDiscovery Service

**Create new file**: `backend/app/services/node_discovery.py`

**Purpose**: Lightweight service that discovers PC2 at startup and registers its capabilities. Fire-and-forget — NEVER blocks startup.

**Requirements**:
- Read `CLUSTER_PC2_HOST` from config (empty = single-PC mode, skip discovery)
- On startup, ping PC2 health endpoints:
  - `http://{pc2}:11434/api/tags` — Ollama
  - `http://{pc2}:50051` — Brain service (gRPC health check)
- If PC2 Ollama responds: add URL to `OllamaNodePool`
- If PC2 brain responds: update brain_client to use PC2 host
- Background task: re-check every 60s for late joiners or recovery
- `get_cluster_status() -> Dict` with per-node health

**Config additions** to `config.py`:
```python
# ── Cluster / Multi-PC ────────────────────────────────────
CLUSTER_PC2_HOST: str = ""  # Empty = single-PC mode
CLUSTER_HEALTH_INTERVAL: int = 60  # Seconds between health checks
```

**Wire into main.py**: Add to `_start_event_driven_pipeline()` near the top (before other services, so pools are populated):
```python
# 0. Node Discovery (non-blocking)
from app.services.node_discovery import NodeDiscovery
_node_discovery = NodeDiscovery()
asyncio.create_task(_node_discovery.start())  # Fire and forget
log.info("NodeDiscovery started (PC2: %s)", settings.CLUSTER_PC2_HOST or "disabled")
```

**Create new API route**: `backend/app/api/v1/cluster.py`
```python
from fastapi import APIRouter
router = APIRouter(prefix="/api/v1/cluster", tags=["cluster"])

@router.get("/status")
async def cluster_status():
    """Return cluster health: nodes, streams, GPU utilization."""
    from app.services.node_discovery import get_node_discovery
    discovery = get_node_discovery()
    return discovery.get_cluster_status()
```

Register in `main.py` imports and `app.include_router(cluster.router)`.

---

### TASK E0.6: Unusual Whales Optimization

**Files to modify**:
- `backend/app/services/unusual_whales_service.py`
- `backend/app/modules/openclaw/scanner/whale_flow.py`

**Current state**: `unusual_whales_service.py` only has `get_flow_alerts()` hitting `/option-trades/flow-alerts`.

**Add new methods to `UnusualWhalesService`**:
```python
async def get_congress_trades(self) -> Any:
    """Fetch congress trading activity (paid plan)."""
    self._validate_api_key()
    url = f"{self.base_url}/congress/trading"
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(url, headers=self._headers())
    r.raise_for_status()
    return r.json() if r.content else []

async def get_insider_trades(self) -> Any:
    """Fetch insider trading activity (paid plan)."""
    self._validate_api_key()
    url = f"{self.base_url}/insider/trading"
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(url, headers=self._headers())
    r.raise_for_status()
    return r.json() if r.content else []

async def get_darkpool_flow(self) -> Any:
    """Fetch dark pool transaction data (paid plan)."""
    self._validate_api_key()
    url = f"{self.base_url}/darkpool/recent"
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(url, headers=self._headers())
    r.raise_for_status()
    return r.json() if r.content else []
```

**Update `whale_flow.py`** constants (line 63-68):
```python
# BEFORE:
POLL_INTERVAL = int(os.getenv('WHALE_POLL_INTERVAL', '120'))
_CACHE_TTL = 600

# AFTER:
POLL_INTERVAL = int(os.getenv('WHALE_POLL_INTERVAL', '30'))  # Paid plan allows faster
_CACHE_TTL = 60  # 1 min cache for faster discovery
```

---

### TASK E0.7: Finviz Elite Optimization

**File to modify**: `backend/app/services/finviz_service.py`

**Add intraday support and retry logic**. Currently there is no retry. Add:
```python
import asyncio

MAX_RETRIES = 3
RETRY_BASE_DELAY = 2.0  # seconds

async def _fetch_with_retry(url: str, params: dict, timeout: float = 30.0) -> httpx.Response:
    """Fetch with exponential backoff retry."""
    for attempt in range(MAX_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                r = await client.get(url, params=params)
                r.raise_for_status()
                return r
        except (httpx.HTTPStatusError, httpx.ConnectError) as e:
            if attempt == MAX_RETRIES - 1:
                raise
            delay = RETRY_BASE_DELAY * (2 ** attempt)
            logger.warning("Finviz retry %d/%d after %.1fs: %s", attempt + 1, MAX_RETRIES, delay, e)
            await asyncio.sleep(delay)
```

**Add intraday screener method**:
```python
async def get_intraday_screen(self, timeframe: str = "i5", filters: str = None) -> List[Dict]:
    """Run Finviz Elite intraday screener.

    Args:
        timeframe: i1, i3, i5, i15, i30, h (Elite plan required for intraday)
        filters: Comma-separated Finviz filter string
    """
    # Use existing screener logic but with intraday timeframe
```

**Add parallel preset runner**:
```python
FINVIZ_PRESETS = {
    "breakout": "ta_highlow52w_nh,sh_avgvol_o500,ta_sma20_pa,ta_sma200_pa",
    "momentum": "ta_sma20_pa,ta_sma200_pa,sh_relvol_o1.5",
    "swing_pullback": "ta_pattern_channelup,ta_sma20_cross20above,ta_sma200_pa",
    "pas_gate": "ta_pattern_channelup,ta_sma20_pa,ta_sma200_pa",
}

async def run_all_presets(self) -> Dict[str, List[Dict]]:
    """Run all 4 filter presets in parallel. Returns {preset_name: [results]}."""
    tasks = {
        name: self.get_screener(filters=filters)
        for name, filters in FINVIZ_PRESETS.items()
    }
    results = {}
    for name, coro in tasks.items():
        try:
            results[name] = await coro
        except Exception as e:
            logger.warning("Finviz preset %s failed: %s", name, e)
            results[name] = []
    return results
```

---

### TASK E0.8: Config & Environment Updates

**Modify**: `backend/app/core/config.py`

Add after the Dual-PC Ollama section (after line 180):
```python
# ── Cluster / Multi-PC ────────────────────────────────────
CLUSTER_PC2_HOST: str = ""  # Empty = single-PC mode
CLUSTER_HEALTH_INTERVAL: int = 60  # Seconds between health checks
```

Add multi-key Alpaca (after line 74):
```python
# ── Multi-Key Alpaca Pool ─────────────────────────────────
ALPACA_KEY_1: str = ""
ALPACA_SECRET_1: str = ""
ALPACA_KEY_2: str = ""
ALPACA_SECRET_2: str = ""
ALPACA_KEY_3: str = ""
ALPACA_SECRET_3: str = ""
```

**Modify**: `backend/.env.example` — Add template entries:
```env
# Multi-Key Alpaca (optional — leave empty for single-key mode)
ALPACA_KEY_1=
ALPACA_SECRET_1=
ALPACA_KEY_2=
ALPACA_SECRET_2=
ALPACA_KEY_3=
ALPACA_SECRET_3=

# Cluster (optional — leave empty for single-PC mode)
CLUSTER_PC2_HOST=
CLUSTER_HEALTH_INTERVAL=60

# Ollama multi-node pool (comma-separated, optional)
SCANNER_OLLAMA_URLS=
```

---

## MESSAGEBUS TOPICS (Reference)

These are the valid topics defined in `backend/app/core/message_bus.py`:
```python
VALID_TOPICS = {
    "market_data.bar",
    "market_data.quote",
    "signal.generated",
    "order.submitted",
    "order.filled",
    "order.cancelled",
    "model.updated",
    "risk.alert",
    "system.heartbeat",
    "council.verdict",
    "hitl.approval_needed",
    "swarm.idea",
    "swarm.spawned",
    "swarm.result",
    "knowledge.ingested",
    "scout.discovery",
}
```

All new discovery streams should publish to `market_data.bar` (for price data) or `swarm.idea` (for analysis signals).

---

## FILE TREE (Key Files)

```
backend/
├── app/
│   ├── main.py                          # FastAPI app, lifespan, pipeline init
│   ├── core/
│   │   ├── config.py                    # Pydantic Settings (ALL config here)
│   │   ├── message_bus.py               # Async pub/sub event bus
│   │   └── logging_config.py
│   ├── api/v1/
│   │   ├── cluster.py                   # NEW — /api/v1/cluster/status
│   │   └── ... (25 existing route files)
│   ├── services/
│   │   ├── alpaca_key_pool.py           # NEW — Multi-key pool
│   │   ├── alpaca_stream_manager.py     # NEW — Multi-stream orchestrator
│   │   ├── alpaca_stream_service.py     # MODIFY — Accept injected keys
│   │   ├── alpaca_service.py            # Alpaca REST client (single key OK)
│   │   ├── ollama_node_pool.py          # NEW — Shared Ollama pool
│   │   ├── node_discovery.py            # NEW — PC2 discovery
│   │   ├── hyper_swarm.py               # MODIFY — Use OllamaNodePool
│   │   ├── brain_client.py              # MODIFY — Read from settings
│   │   ├── unusual_whales_service.py    # MODIFY — Add endpoints
│   │   ├── finviz_service.py            # MODIFY — Intraday + retry
│   │   ├── signal_engine.py             # DO NOT MODIFY
│   │   ├── turbo_scanner.py             # DO NOT MODIFY (yet)
│   │   └── ...
│   └── modules/
│       └── openclaw/scanner/
│           ├── whale_flow.py            # MODIFY — Faster polling
│           └── finviz_scanner.py        # MODIFY — Parallel presets
├── .env.example                         # MODIFY — Add multi-key template
└── tests/
    └── test_api.py                      # Add tests for new endpoints
brain_service/
├── server.py                            # gRPC server (already built, runs on PC2)
├── ollama_client.py                     # Ollama HTTP client
├── proto/brain.proto                    # gRPC protocol definition
└── .env.example
docker-compose.yml                       # MODIFY — Add optional PC2 profile
```

---

## IMPLEMENTATION ORDER

Build in this exact order to avoid import errors:

1. **E0.8** — Config updates first (other modules import from config)
2. **E0.1** — AlpacaKeyPool (no dependencies)
3. **E0.3** — OllamaNodePool (no dependencies)
4. **E0.5** — NodeDiscovery (depends on OllamaNodePool)
5. **E0.2** — AlpacaStreamManager (depends on AlpacaKeyPool + AlpacaStreamService)
6. **E0.4** — Brain Service enablement (depends on NodeDiscovery)
7. **E0.6** — UW optimization (independent)
8. **E0.7** — Finviz optimization (independent)

---

## TESTING

After implementation, verify:
1. `cd backend && python -m pytest tests/ -v` — all 151+ tests pass
2. Single-key mode works (only `ALPACA_API_KEY` set, no `ALPACA_KEY_1`)
3. Single-PC mode works (`CLUSTER_PC2_HOST` empty)
4. `GET /api/v1/cluster/status` returns valid JSON
5. HyperSwarm still works after OllamaNodePool extraction

---

## DO NOT TOUCH

These files are critical and should NOT be modified in this PR:
- `backend/app/services/signal_engine.py` — Core signal generation
- `backend/app/council/` — Entire council directory
- `backend/app/services/order_executor.py` — Order execution
- `backend/app/services/kelly_position_sizer.py` — Position sizing
- `frontend-v2/` — Entire frontend
- `brain_service/server.py` — Already working, runs on PC2

---

## COMMIT STYLE

One commit per task (E0.1, E0.2, etc.) with message format:
```
feat(compute): E0.X — description

Part of #39
```
