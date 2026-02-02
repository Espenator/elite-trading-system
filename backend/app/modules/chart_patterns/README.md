# Chart Patterns

**Role**: Visual / pattern database and detection.

- **Pattern library**: Definitions (head & shoulders, flags, support/resistance).
- **Detection**: Pipeline on OHLCV → “pattern X on symbol Y at T”.
- **In**: Symbol list, OHLCV data, pattern definitions.
- **Out**: Detected patterns → ML Engine.

Use Alpaca/Finviz bars; optional DB for storing detections for backtest and learning.
