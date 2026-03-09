# Ingestion Framework

Incremental data ingestion framework for the Elite Trading System.

## Overview

The ingestion framework provides a unified, extensible architecture for ingesting data from multiple external sources with:

- **Incremental ingestion** with checkpoint tracking
- **Per-adapter scheduling** with configurable intervals
- **Event-driven architecture** via MessageBus integration
- **DuckDB persistence** for analytics
- **Fault tolerance** with automatic retry and error handling

## Architecture

### Core Components

1. **BaseSourceAdapter** (`base.py`)
   - Abstract base class for all adapters
   - Implements common ingestion logic
   - Handles checkpoint management and event publishing

2. **SourceEvent** (`models/source_event.py`)
   - Pydantic model for ingestion events
   - Includes deduplication keys, timestamps, and metadata
   - Stored in DuckDB `ingestion_events` table

3. **CheckpointStore** (`data/checkpoint_store.py`)
   - Tracks ingestion progress per adapter
   - Enables resume from last successful position
   - Prevents duplicate processing

4. **AdapterRegistry** (`registry.py`)
   - Central registry for all adapters
   - Provides lifecycle management (start/stop)
   - Health monitoring and statistics

5. **IngestionScheduler** (`scheduler.py`)
   - APScheduler-based task scheduling
   - Per-adapter schedule configuration
   - Supports both interval and cron-based triggers

### Adapters

The framework includes 6 adapters:

| Adapter | Source | Kind | Schedule |
|---------|--------|------|----------|
| **FinvizAdapter** | Finviz Elite | screener | Daily 9:15 AM ET |
| **FREDAdapter** | Federal Reserve | economic | Daily 5:30 PM ET |
| **UnusualWhalesAdapter** | Unusual Whales | options_flow | Every 2 minutes |
| **SECEdgarAdapter** | SEC EDGAR | filings | Every 30 minutes |
| **OpenClawAdapter** | OpenClaw | regime_flow | Every 10 minutes |
| **AlpacaStreamAdapter** | Alpaca | stream | Continuous |

## Usage

### Basic Usage

The framework is automatically initialized in `main.py` during application startup:

```python
from app.data.checkpoint_store import CheckpointStore
from app.services.ingestion.registry import AdapterRegistry
from app.services.ingestion.scheduler import IngestionScheduler

# Initialize components
checkpoint_store = CheckpointStore()
adapter_registry = AdapterRegistry(checkpoint_store, message_bus)
adapter_registry.initialize_adapters()

# Schedule and start
ingestion_scheduler = IngestionScheduler(adapter_registry)
ingestion_scheduler.schedule_all_adapters()
ingestion_scheduler.start()
```

### Creating a Custom Adapter

```python
from app.services.ingestion.base import BaseSourceAdapter
from app.models.source_event import SourceEvent

class MyAdapter(BaseSourceAdapter):
    def get_source_name(self) -> str:
        return "my_source"

    def get_source_kind(self) -> str:
        return "custom"

    async def validate_credentials(self) -> bool:
        # Check API keys, credentials, etc.
        return True

    async def fetch_incremental(self, last_cursor=None, last_timestamp=None):
        # Fetch data since last checkpoint
        events = []

        # ... fetch logic here ...

        for data in fetched_data:
            event = SourceEvent(
                source=self.get_source_name(),
                source_kind=self.get_source_kind(),
                topic="my_source.data",
                occurred_at=data["timestamp"],
                payload_json=data
            )
            events.append(event)

        return events
```

### Running Adapter Manually

```python
# Get adapter from registry
adapter = adapter_registry.get_adapter("finviz")

# Run ingestion once
result = await adapter.ingest()
print(f"Ingested {result['row_count']} events")

# Check health
health = await adapter.health_check()
print(health)
```

### Monitoring

```python
# Get all checkpoints
checkpoints = checkpoint_store.get_all_checkpoints()
for cp in checkpoints:
    print(f"{cp['adapter_name']}: {cp['status']} - {cp['row_count']} rows")

# Get registry stats
stats = adapter_registry.get_registry_stats()
print(f"Total adapters: {stats['total_adapters']}")
print(f"Running: {stats['running_adapters']}")

# Get scheduled jobs
jobs = ingestion_scheduler.get_scheduled_jobs()
for job in jobs:
    print(f"{job['name']}: next run at {job['next_run_time']}")
```

## Database Schema

### ingestion_events table (DuckDB)

```sql
CREATE TABLE ingestion_events (
    event_id VARCHAR PRIMARY KEY,
    source VARCHAR NOT NULL,           -- Adapter name (finviz, fred, etc.)
    source_kind VARCHAR NOT NULL,      -- screener, economic, options_flow, etc.
    topic VARCHAR,                     -- MessageBus topic
    symbol VARCHAR,                    -- Stock symbol if applicable
    entity_id VARCHAR,                 -- Unique ID from source
    occurred_at TIMESTAMP NOT NULL,    -- When event occurred at source
    ingested_at TIMESTAMP NOT NULL,    -- When we ingested it
    sequence INTEGER,                  -- Sequence number for ordered events
    dedupe_key VARCHAR,                -- Hash key for deduplication
    schema_version VARCHAR,            -- Event schema version
    payload_json VARCHAR,              -- Raw event data
    trace_id VARCHAR                   -- Distributed trace ID
);
```

Indexes:
- `idx_ingestion_source` on `source`
- `idx_ingestion_topic` on `topic`
- `idx_ingestion_symbol` on `symbol`
- `idx_ingestion_occurred_at` on `occurred_at`

### adapter_checkpoints table (CheckpointStore)

```sql
CREATE TABLE adapter_checkpoints (
    adapter_name VARCHAR PRIMARY KEY,
    source_key VARCHAR,
    last_cursor VARCHAR,
    last_timestamp TIMESTAMP,
    batch_id VARCHAR,
    status VARCHAR,
    row_count INTEGER,
    error_message VARCHAR,
    metadata JSON,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

## Configuration

### Adapter Schedules

Schedules are defined in `scheduler.py`:

```python
ADAPTER_SCHEDULES = {
    "finviz": {
        "type": "cron",
        "hour": "9",
        "minute": "15",
        "timezone": "America/New_York"
    },
    "fred": {
        "type": "cron",
        "hour": "17",
        "minute": "30",
        "timezone": "America/New_York"
    },
    "unusual_whales": {
        "type": "interval",
        "minutes": 2
    },
    # ... more adapters ...
}
```

### Custom Schedules

You can override schedules when scheduling adapters:

```python
# Custom schedule for an adapter
custom_schedule = {
    "type": "interval",
    "minutes": 5
}
scheduler.schedule_adapter("my_adapter", custom_schedule)
```

## MessageBus Integration

All ingestion events are published to the MessageBus for real-time consumption:

```python
# Subscribe to ingestion events
from app.core.message_bus import get_message_bus

bus = get_message_bus()

async def handle_finviz_data(data):
    print(f"Received Finviz data: {data}")

await bus.subscribe("finviz.screener", handle_finviz_data)
```

## Testing

Comprehensive tests are available in `tests/test_ingestion.py`:

```bash
cd backend
python -m pytest tests/test_ingestion.py -v
```

Tests cover:
- SourceEvent model creation
- CheckpointStore operations
- BaseSourceAdapter lifecycle
- AdapterRegistry management
- IngestionScheduler functionality
- Full ingestion workflow

## Future Enhancements

1. **Backfill Support**: Historical data ingestion
2. **Rate Limiting**: Per-adapter rate limit tracking
3. **Metrics & Monitoring**: Prometheus metrics for ingestion stats
4. **Dead Letter Queue**: Failed event handling
5. **Event Replay**: Replay events from checkpoint
6. **Adapter Auto-Discovery**: Dynamic adapter loading
7. **Parallel Ingestion**: Multi-threaded adapter execution

## Troubleshooting

### Adapter Not Running

Check if adapter is scheduled:
```python
jobs = scheduler.get_scheduled_jobs()
print([j['id'] for j in jobs])
```

### Checkpoints Not Saving

Check DuckDB connection:
```python
checkpoint = checkpoint_store.get_checkpoint("adapter_name")
print(checkpoint)
```

### Events Not Publishing

Verify MessageBus is running:
```python
from app.core.message_bus import get_message_bus
bus = get_message_bus()
print(f"MessageBus running: {bus._running}")
```

## References

- BaseSourceAdapter: `backend/app/services/ingestion/base.py`
- Adapters: `backend/app/services/ingestion/adapters/`
- Tests: `backend/tests/test_ingestion.py`
- Main integration: `backend/app/main.py:924-943`
