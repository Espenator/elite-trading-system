# ML / Algorithms Engine

**Role**: Learn from memory and data; fuse signals; produce tradeable signals.

- Ingest: Symbol Universe, Social/News, Chart Patterns, price/volume, execution outcomes.
- Models: Online (e.g. River), offline (e.g. XGBoost), regime detection, risk scoring.
- **Out**: Signal scores, regime, sit-out flags → Execution; insights → UI.

Keep a stable interface (e.g. “signals with symbol, score, source”) so new models can be added without changing other modules.
