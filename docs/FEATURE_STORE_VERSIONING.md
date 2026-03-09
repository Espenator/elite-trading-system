# Feature Store Versioning Guide

## Overview

The feature store now includes comprehensive versioning support to track feature pipeline evolution, ensure model-feature compatibility, and enable reproducible ML workflows.

## Key Concepts

### 1. Pipeline Version
- Semantic version (e.g., "2.0.0") tracking the feature engineering code version
- Defined in `backend/app/modules/ml_engine/feature_pipeline.py` as `PIPELINE_VERSION`
- Incremented when feature computation logic changes

### 2. Schema Version
- Version tracking the structure/format of feature data (e.g., "1.0")
- Incremented when feature names, types, or organization changes
- Separate from pipeline version to allow bug fixes without schema changes

### 3. Feature Hash
- SHA256 hash of feature values for exact reproducibility
- Detects data drift and ensures identical inputs produce identical features

## Database Schema

The `features` table now includes:

```sql
CREATE TABLE features (
    symbol VARCHAR NOT NULL,
    ts TIMESTAMP NOT NULL,
    timeframe VARCHAR NOT NULL DEFAULT '1d',
    feature_json VARCHAR,
    feature_hash VARCHAR,
    pipeline_version VARCHAR DEFAULT '1.0.0',
    schema_version VARCHAR DEFAULT '1.0',
    feature_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (symbol, ts, timeframe)
)
```

Indexes:
- `idx_features_symbol_ts` - Fast lookups by symbol and timestamp
- `idx_features_pipeline_version` - Fast filtering by version

## Usage Examples

### Storing Features with Version

```python
from app.data.feature_store import feature_store
from datetime import datetime, timezone

features = {
    "close": 150.25,
    "volume": 1000000,
    "rsi_14": 0.65,
    "ma_20_dist": 0.02
}

hash_val = feature_store.store_features(
    symbol="AAPL",
    ts=datetime.now(timezone.utc),
    timeframe="1d",
    feature_dict=features,
    pipeline_version="2.0.0",
    schema_version="1.0"
)
```

### Retrieving Latest Features

```python
# Get latest features regardless of version
latest = feature_store.get_latest_features("AAPL", "1d")

# Get latest features for specific pipeline version
latest_v2 = feature_store.get_latest_features(
    "AAPL", "1d",
    pipeline_version="2.0.0"
)

# Response includes version metadata
# {
#     "features": {...},
#     "feature_hash": "30d60b0f6b1f5485",
#     "pipeline_version": "2.0.0",
#     "schema_version": "1.0",
#     "feature_count": 4,
#     "ts": "2026-03-09T02:00:00+00:00",
#     "created_at": "2026-03-09T02:05:00+00:00"
# }
```

### Getting Features in Time Window

```python
features = feature_store.get_features_window(
    symbol="AAPL",
    timeframe="1d",
    start="2026-01-01T00:00:00",
    end="2026-03-01T00:00:00",
    pipeline_version="2.0.0"  # Optional filter
)
```

### Checking Available Versions

```python
# Get all versions across all symbols
all_versions = feature_store.get_available_versions(timeframe="1d")

# Get versions for specific symbol
symbol_versions = feature_store.get_available_versions(
    symbol="AAPL",
    timeframe="1d"
)

# Response example:
# [
#     {
#         "pipeline_version": "2.0.0",
#         "schema_version": "1.0",
#         "record_count": 252,
#         "symbol_count": 55,
#         "earliest_ts": "2025-01-01T00:00:00",
#         "latest_ts": "2026-03-08T00:00:00",
#         "avg_feature_count": 30.5
#     },
#     {
#         "pipeline_version": "1.0.0",
#         "schema_version": "1.0",
#         "record_count": 1500,
#         "symbol_count": 200,
#         ...
#     }
# ]
```

### Checking Version Compatibility

```python
compat = feature_store.check_version_compatibility(
    required_version="2.0.0",
    symbol="AAPL",
    timeframe="1d"
)

# Response:
# {
#     "compatible": True,
#     "version": "2.0.0",
#     "symbol": "AAPL",
#     "timeframe": "1d",
#     "record_count": 252,
#     "earliest_ts": "2025-01-01T00:00:00",
#     "latest_ts": "2026-03-08T00:00:00"
# }
```

## API Endpoints

### GET /api/v1/features/latest
Get latest features for a symbol with optional version filtering.

**Query Parameters:**
- `symbol` (required): Stock symbol
- `timeframe` (optional): Timeframe, default "1d"
- `pipeline_version` (optional): Filter by specific pipeline version

**Example:**
```bash
curl "http://localhost:8000/api/v1/features/latest?symbol=AAPL&pipeline_version=2.0.0"
```

### GET /api/v1/features/versions
Get all available pipeline versions in the feature store.

**Query Parameters:**
- `symbol` (optional): Filter by specific symbol
- `timeframe` (optional): Timeframe filter, default "1d"

**Example:**
```bash
curl "http://localhost:8000/api/v1/features/versions?symbol=AAPL"
```

### GET /api/v1/features/compatibility
Check if features exist for a specific pipeline version.

**Query Parameters:**
- `symbol` (required): Stock symbol
- `version` (required): Pipeline version to check
- `timeframe` (optional): Timeframe filter, default "1d"

**Example:**
```bash
curl "http://localhost:8000/api/v1/features/compatibility?symbol=AAPL&version=2.0.0"
```

## Migration

For existing feature data, use the migration script:

```bash
# Dry run to see what will change
python backend/scripts/migrate_feature_store_versioning.py --dry-run

# Run migration
python backend/scripts/migrate_feature_store_versioning.py
```

The migration script:
1. Adds `pipeline_version`, `schema_version`, and `feature_count` columns
2. Backfills existing records with default values
3. Updates `feature_count` from `feature_json` data
4. Creates performance indexes

## Best Practices

### 1. Version Incrementing
- **Patch version** (2.0.1): Bug fixes, no feature changes
- **Minor version** (2.1.0): New features added, backward compatible
- **Major version** (3.0.0): Breaking changes to feature schema

### 2. Feature Pipeline Updates
When updating the feature pipeline:

```python
# In feature_pipeline.py
PIPELINE_VERSION = "2.1.0"  # Increment appropriately

# Update FeatureManifest if schema changes
@dataclass
class FeatureManifest:
    version: str = PIPELINE_VERSION
    schema_version: str = "1.1"  # Increment if structure changes
    ...
```

### 3. Model Training
Always record pipeline version with trained models:

```python
from app.modules.ml_engine.feature_pipeline import PIPELINE_VERSION

registry.log_training_run(
    model_name="xgboost_daily",
    model=trained_model,
    params=params,
    metrics=metrics,
    feature_cols=feature_cols,
    notes=f"Pipeline v{PIPELINE_VERSION}"
)
```

### 4. Model Inference
Verify feature compatibility before inference:

```python
# Check if features are available for model's required version
compat = feature_store.check_version_compatibility(
    required_version=model_pipeline_version,
    symbol=symbol,
    timeframe=timeframe
)

if not compat["compatible"]:
    # Generate features with correct pipeline version
    # or retrain model with available features
    ...
```

## Feature Manifest

The `FeatureManifest` now includes schema versioning:

```python
@dataclass
class FeatureManifest:
    version: str = PIPELINE_VERSION
    schema_version: str = "1.0"
    feature_cols: List[str]
    label_cols: List[str]
    n_features: int
    n_labels: int
    data_hash: str
    created_at: str
    feature_types: Dict[str, str]  # feature_name -> category
```

Saved to: `backend/app/modules/ml_engine/artifacts/feature_manifest.json`

## Troubleshooting

### Version Mismatch
**Problem:** Model expects features from pipeline v2.0.0 but only v1.0.0 available.

**Solution:**
1. Regenerate features using pipeline v2.0.0
2. Or retrain model using v1.0.0 features
3. Or add feature transformation layer for compatibility

### Missing Version Data
**Problem:** Existing features have no version information.

**Solution:** Run migration script to backfill default versions.

### Schema Evolution
**Problem:** Need to add new features without breaking existing models.

**Solution:**
1. Increment minor version (2.0.0 → 2.1.0)
2. Ensure new features are optional/have defaults
3. Update schema_version if structure changes
4. Test backward compatibility

## Performance Considerations

1. **Indexes**: Pipeline version column is indexed for fast filtering
2. **Query optimization**: Version filtering happens at database level
3. **Caching**: Consider caching version metadata for frequently accessed symbols
4. **Backfilling**: Run migrations during off-peak hours for large datasets

## Future Enhancements

Potential improvements to the versioning system:
- Automatic version detection from git commit
- Feature schema validation against manifest
- Migration helpers for version upgrades
- Version compatibility matrix
- Automated testing across versions
- Feature lineage tracking
