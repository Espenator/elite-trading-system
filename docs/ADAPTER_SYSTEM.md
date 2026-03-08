# Data Ingestion Adapter System

## Overview

The scheduled adapter system provides a unified framework for ingesting data from external sources. All adapters inherit from `BaseSourceAdapter` and are automatically scheduled via APScheduler.

## Architecture

### Core Components

1. **BaseSourceAdapter** (`app/services/ingestion/base.py`)
   - Abstract base class for all adapters
   - Handles event fetching, MessageBus publishing, and checkpoint management
   - Provides health monitoring and error tracking

2. **SourceEvent** (`app/models/source_event.py`)
   - Unified event model for all data sources
   - Contains: `event_id`, `source`, `event_type`, `event_time`, `symbol`, `data`, `metadata`

3. **CheckpointStore** (`app/data/checkpoint_store.py`)
   - Persists adapter state in DuckDB `ingestion_checkpoints` table
   - Enables incremental ingestion (fetch only new data since last run)

4. **AdapterRegistry** (`app/services/ingestion/adapter_registry.py`)
   - Central registry for all adapters
   - Provides batch operations and health monitoring
   - Global singleton via `get_adapter_registry()`

5. **Scheduler Integration** (`app/jobs/scheduler.py`)
   - APScheduler with CronTrigger for each adapter
   - Different intervals based on data update frequency

## Registered Adapters

| Adapter | Source | Poll Interval | Event Types | Topic |
|---------|--------|---------------|-------------|-------|
| **finviz** | Finviz Elite | 5 min (market hours) | `screener_breakout`, `screener_momentum`, `screener_swing_pullback`, `screener_pas_gate` | `perception.finviz.screener` |
| **fred** | FRED API | 15 min | `economic_indicator` | `perception.macro` |
| **unusual_whales** | Unusual Whales | 2 min (market hours) | `options_flow`, `congress_trade`, `insider_trade`, `darkpool_flow` | `perception.unusualwhales` |
| **sec_edgar** | SEC Edgar | 30 min | `filing_8-k`, `filing_10-q`, `filing_10-k`, `filing_s-1`, `filing_13f-hr` | `perception.edgar` |
| **openclaw** | OpenClaw Bridge | 10 min | `regime`, `candidate`, `whale_flow` | `perception.regime.openclaw` |

## Schedule Details

**Market Hours:** Monday-Friday, 9:00-16:30 ET (14:00-21:30 UTC)

```python
# Finviz - High-frequency during market hours
CronTrigger(minute="*/5", hour="14-21", day_of_week="mon-fri", timezone="UTC")

# FRED - Low-frequency (economic data updates slowly)
CronTrigger(minute="*/15", timezone="UTC")

# Unusual Whales - Very high-frequency for options flow
CronTrigger(minute="*/2", hour="14-21", day_of_week="mon-fri", timezone="UTC")

# SEC Edgar - Medium-frequency (filings are not real-time)
CronTrigger(minute="*/30", timezone="UTC")

# OpenClaw - Medium-frequency for regime/signals
CronTrigger(minute="*/10", timezone="UTC")
```

## Creating a New Adapter

### 1. Implement BaseSourceAdapter

```python
from app.services.ingestion.base import BaseSourceAdapter
from app.models.source_event import SourceEvent

class MyAdapter(BaseSourceAdapter):
    def __init__(self, **kwargs):
        super().__init__(adapter_id="my_adapter", **kwargs)
        # Initialize your service client here

    async def fetch_events(self, since: Optional[datetime] = None) -> List[SourceEvent]:
        """Fetch events from your data source.

        Args:
            since: Fetch events after this timestamp (from checkpoint)

        Returns:
            List of SourceEvent objects
        """
        events = []

        # Fetch data from your source
        data = await self.my_service.fetch_data(since=since)

        # Convert to SourceEvent format
        for item in data:
            event = SourceEvent(
                event_id=f"my_source_{item['id']}",
                source="my_adapter",
                event_type="my_event_type",
                event_time=item['timestamp'],
                symbol=item.get('symbol'),
                data=item,
                metadata={"source_metadata": "value"}
            )
            events.append(event)

        return events

    def get_topic(self) -> str:
        """Return MessageBus topic for events."""
        return "perception.my_source"
```

### 2. Register Adapter

Add to `app/services/ingestion/adapter_registry.py`:

```python
def initialize_adapters():
    from app.services.ingestion.my_adapter import MyAdapter

    registry = get_adapter_registry()
    registry.register(MyAdapter())
    # ... other adapters
```

### 3. Add Schedule

Add to `app/jobs/scheduler.py`:

```python
_scheduler.add_job(
    lambda: _run_adapter("my_adapter"),
    CronTrigger(minute="*/10", timezone="UTC"),
    id="adapter_my_adapter",
    name="My Adapter Ingestion",
    replace_existing=True,
)
```

### 4. Add MessageBus Topic

Add to `app/core/message_bus.py` VALID_TOPICS if needed:

```python
VALID_TOPICS = [
    # ... existing topics
    "perception.my_source",
]
```

## API Endpoints

### List Adapters
```
GET /api/v1/adapters
```

### Get Health Summary
```
GET /api/v1/adapters/health
```

Response:
```json
{
  "total_adapters": 5,
  "healthy_adapters": 5,
  "unhealthy_adapters": 0,
  "total_events_ingested": 1234,
  "adapters": {
    "finviz": {
      "adapter_id": "finviz",
      "is_healthy": true,
      "last_run": "2026-03-08T14:30:00Z",
      "last_success": "2026-03-08T14:30:00Z",
      "events_ingested": 250
    }
  }
}
```

### Get Adapter Health
```
GET /api/v1/adapters/{adapter_id}/health
```

### Manual Trigger
```
POST /api/v1/adapters/{adapter_id}/run
```

### Run All Adapters
```
POST /api/v1/adapters/run-all
```

### Reset Checkpoint
```
POST /api/v1/adapters/{adapter_id}/reset-checkpoint
```

## Event Flow

```
1. Scheduler triggers adapter.run()
   ↓
2. adapter.fetch_events(since=checkpoint_time)
   ↓
3. Convert raw data → SourceEvent objects
   ↓
4. Publish each event to MessageBus topic
   ↓
5. Update checkpoint with latest event
   ↓
6. Update health metrics
```

## Checkpoint System

Checkpoints enable incremental ingestion:

```python
# First run: no checkpoint, fetches all data
await adapter.run()  # Fetches everything

# Second run: uses checkpoint, only fetches new data
await adapter.run()  # Fetches only events after last checkpoint

# Reset to force full re-ingestion
adapter.reset_checkpoint()
await adapter.run()  # Fetches everything again
```

Checkpoint data stored in DuckDB:
```sql
CREATE TABLE ingestion_checkpoints (
    adapter_id VARCHAR PRIMARY KEY,
    last_event_id VARCHAR,
    last_event_time TIMESTAMP,
    checkpoint_data JSON,
    updated_at TIMESTAMP
)
```

## Health Monitoring

Each adapter tracks:
- `is_healthy`: Whether adapter is functioning correctly
- `last_run`: Timestamp of last run attempt
- `last_success`: Timestamp of last successful run
- `last_error`: Error message if last run failed
- `events_ingested`: Total count of events ingested

Access via:
```python
registry = get_adapter_registry()
health = registry.get_health("finviz")
```

## Error Handling

Adapters follow fail-open pattern for enrichment:
- Errors are logged but don't stop the scheduler
- Failed adapters report unhealthy status
- Next scheduled run will retry automatically

## Testing

Tests located at `backend/tests/test_ingestion.py`:

```bash
# Run all ingestion tests
pytest tests/test_ingestion.py -v

# Run specific test
pytest tests/test_ingestion.py::test_finviz_adapter -v
```

40+ test cases covering:
- SourceEvent creation
- CheckpointStore operations
- Adapter lifecycle (fetch, publish, checkpoint)
- Registry operations
- Error handling
- Health monitoring

## Configuration

Enable/disable scheduler via environment variable:
```bash
SCHEDULER_ENABLED=true  # Enable all scheduled jobs (default)
SCHEDULER_ENABLED=false # Disable scheduler completely
```

Individual adapter API keys:
```bash
FINVIZ_API_KEY=your_key
FRED_API_KEY=your_key
UNUSUAL_WHALES_API_KEY=your_key
SEC_EDGAR_USER_AGENT="CompanyName/1.0 email@example.com"
OPENCLAW_BRIDGE_TOKEN=your_token
```

## Migration from Manual Polling

**Old Pattern:**
```python
# market_data_agent.run_tick() called manually
await market_data_agent.run_tick(
    run_finviz=True,
    run_fred=True,
    run_unusual_whales=True
)
```

**New Pattern:**
```python
# Adapters run automatically on schedule
# No manual intervention needed
# Check status via API:
GET /api/v1/adapters/health
```

**Backward Compatibility:**
- Existing services (FinvizService, FredService, etc.) unchanged
- Adapters wrap existing services
- Manual API triggers still available via `/api/v1/adapters/{id}/run`

## Troubleshooting

### Adapter not running
1. Check scheduler is enabled: `SCHEDULER_ENABLED=true`
2. Check logs for startup errors
3. Verify adapter initialized: `GET /api/v1/adapters`

### No events being ingested
1. Check adapter health: `GET /api/v1/adapters/{id}/health`
2. Review `last_error` in health response
3. Check API keys are configured
4. Manually trigger: `POST /api/v1/adapters/{id}/run`

### Duplicate events
1. Checkpoint may be corrupted
2. Reset checkpoint: `POST /api/v1/adapters/{id}/reset-checkpoint`
3. Check event_id generation is deterministic

### Missing old data
1. Adapters use checkpoints for incremental ingestion
2. Reset checkpoint to re-fetch all data
3. Some sources (FRED, Finviz) always return latest state
