# Social / News Engine

**Role**: Real-time search and compute for social media and news signals.

- Ingest: Twitter/X, Reddit, NewsAPI, Benzinga, RSS, etc.
- Compute: sentiment, keyword hits, correlation with price/volume.
- **In**: Symbol list from Symbol Universe; config (keywords, sources).
- **Out**: Time-stamped signals/scores → ML Engine.

Add data source adapters and a scheduler (e.g. background task or cron); expose status and “run once” for glass-box UI.
