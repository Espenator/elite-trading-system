# Shared Ingestion Foundation

This package provides a locked, coherent foundation for ingesting data from all external sources into the trading system.

## Architecture

```
External API → Concrete Adapter (BaseSourceAdapter)
    ↓
SourceEvent (standardized event structure)
    ↓
EventSink (MessageBus) → CheckpointStore (deduplication)
    ↓
DuckDB (persistent storage)
```

## Core Components

### SourceEvent

Standardized event structure emitted by all source adapters.

```python
from app.ingestion import SourceEvent

event = SourceEvent(
    event_type='market_data.bar',
    source='alpaca_stream',
    data={'symbol': 'AAPL', 'close': 175.50, 'volume': 1000000},
)
```

**Fields:**
- `event_type`: Topic name (e.g., 'market_data.bar', 'perception.edgar')
- `source`: Source adapter name (e.g., 'alpaca', 'unusual_whales')
- `data`: Event payload (dict with symbol, price, volume, etc.)
- `timestamp`: When the event occurred (timezone-aware UTC datetime)
- `event_id`: Unique ID for deduplication (auto-generated UUID)
- `metadata`: Additional context (latency, confidence, etc.)

### BaseSourceAdapter

Abstract base class that all source adapters must inherit from.

```python
from app.ingestion import BaseSourceAdapter, SourceEvent

class MyAdapter(BaseSourceAdapter):
    @property
    def source_name(self) -> str:
        return "my_source"

    @property
    def event_type(self) -> str:
        return "market_data.custom"

    async def fetch_data(self):
        # Fetch from external API
        return await external_api.get_data()

    def transform_to_events(self, raw_data) -> List[SourceEvent]:
        # Transform to SourceEvent objects
        return [
            SourceEvent(
                event_type=self.event_type,
                source=self.source_name,
                data=item,
            )
            for item in raw_data
        ]
```

**Features:**
- Automatic health monitoring
- Event deduplication via checkpoint store
- Standardized error handling and retry logic
- Metrics collection (latency, error rate, etc.)
- Integration with MessageBus event sink

**Required Methods:**
- `source_name`: Unique identifier for this source
- `event_type`: Default event type for this source
- `fetch_data()`: Fetch raw data from external API
- `transform_to_events()`: Transform raw data into SourceEvent objects

**Built-in Methods:**
- `run_tick()`: Execute one ingestion cycle (fetch → transform → dedupe → publish)
- `get_health()`: Get current health metrics
- `validate_config()`: Validate adapter configuration

### CheckpointStore

In-memory deduplication cache with TTL-based expiration.

```python
from app.ingestion import CheckpointStore, SourceEvent

store = CheckpointStore(ttl_seconds=300, max_entries=10_000)

event = SourceEvent(...)
if not store.has_seen(event):
    store.mark_seen(event)
    # Process new event
else:
    # Skip duplicate
    pass
```

**Features:**
- Time-window cache (default: 5 minutes)
- Automatic pruning when max size exceeded
- Statistics tracking (cache size, hits, misses, etc.)

### HealthMetrics

Health and performance metrics for source adapters.

```python
from app.ingestion import HealthStatus, HealthMetrics

metrics = HealthMetrics(
    status=HealthStatus.HEALTHY,
    total_events=100,
    average_latency_ms=50.5,
)

if metrics.is_healthy():
    print("Adapter is healthy")
```

**Health Statuses:**
- `HEALTHY`: Operating normally
- `DEGRADED`: Some errors but still functional
- `RATE_LIMITED`: Hit API rate limits
- `AUTH_FAILURE`: Authentication/authorization failed
- `OFFLINE`: Too many consecutive errors (>= 5)

## Usage Example

### Creating a New Adapter

```python
from typing import Any, List
from app.ingestion import BaseSourceAdapter, SourceEvent

class AlpacaBarAdapter(BaseSourceAdapter):
    """Adapter for Alpaca real-time bars."""

    def __init__(self, api_key: str, **kwargs):
        super().__init__(**kwargs)
        self.api_key = api_key

    @property
    def source_name(self) -> str:
        return "alpaca_stream"

    @property
    def event_type(self) -> str:
        return "market_data.bar"

    async def fetch_data(self) -> Any:
        # Fetch from Alpaca WebSocket or REST API
        response = await alpaca_client.get_bars(
            symbols=["AAPL", "MSFT"],
            timeframe="1Min",
        )
        return response

    def transform_to_events(self, raw_data: Any) -> List[SourceEvent]:
        events = []
        for bar in raw_data.get("bars", []):
            event = SourceEvent(
                event_type=self.event_type,
                source=self.source_name,
                data={
                    "symbol": bar["symbol"],
                    "open": bar["open"],
                    "high": bar["high"],
                    "low": bar["low"],
                    "close": bar["close"],
                    "volume": bar["volume"],
                },
                metadata={
                    "session": "market_hours",
                    "data_quality": "realtime",
                },
            )
            events.append(event)
        return events

    def validate_config(self) -> bool:
        return bool(self.api_key)
```

### Running the Adapter

```python
from app.core.message_bus import MessageBus
from app.ingestion import checkpoint_store

# Setup
bus = MessageBus()
await bus.start()

adapter = AlpacaBarAdapter(
    api_key="your-api-key",
    event_sink=bus,
    checkpoint_store=checkpoint_store,
)

# Run ingestion cycle
report = await adapter.run_tick()
print(f"Status: {report['status']}")
print(f"Events fetched: {report['events_fetched']}")
print(f"Events published: {report['events_published']}")
print(f"Duplicates: {report['events_duplicate']}")

# Check health
health = adapter.get_health()
print(f"Health: {health.status}")
print(f"Total events: {health.total_events}")
print(f"Avg latency: {health.average_latency_ms}ms")
```

## Testing

Run the foundation tests:

```bash
python3 -m pytest tests/test_ingestion_foundation.py -v
```

All 26 tests cover:
- SourceEvent creation, validation, serialization
- CheckpointStore deduplication and TTL expiration
- HealthMetrics tracking and status transitions
- BaseSourceAdapter tick execution and error handling
- End-to-end integration flow

## Import Safety

All components are import-safe and can be used independently:

```python
# Import only what you need
from app.ingestion import SourceEvent
from app.ingestion import BaseSourceAdapter
from app.ingestion import CheckpointStore
from app.ingestion import HealthStatus, HealthMetrics

# Or import everything
from app.ingestion import (
    SourceEvent,
    BaseSourceAdapter,
    CheckpointStore,
    HealthStatus,
    HealthMetrics,
)
```

## Integration with Existing Systems

The foundation integrates seamlessly with existing infrastructure:

- **MessageBus**: Events are published to the existing MessageBus
- **DuckDB**: Persistent storage via existing `duckdb_storage.py`
- **Health Monitoring**: Compatible with existing health check endpoints

## Scope

This foundation is locked and covers:
- ✅ `SourceEvent` - Standardized event structure
- ✅ `BaseSourceAdapter` - Base class for all adapters
- ✅ `CheckpointStore` - Deduplication and state management
- ✅ Event sink integration (MessageBus)
- ✅ Health/metrics primitives
- ✅ Comprehensive tests (26 tests)
- ✅ Example adapter implementation

**Out of scope for this pass:**
- Refactoring existing source services (future work)
- Persistent checkpoint storage (in-memory is sufficient for now)
- Advanced retry strategies (simple retry count is implemented)

## Future Enhancements

Potential improvements for future iterations:
- Persistent checkpoint store (Redis/DuckDB) for cross-restart deduplication
- Advanced retry strategies (exponential backoff with jitter)
- Circuit breaker integration
- Adapter lifecycle hooks (pre_fetch, post_transform, etc.)
- Adapter registry for auto-discovery
- Metrics export to Prometheus/Grafana
