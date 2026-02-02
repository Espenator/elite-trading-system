# Symbol Universe

**Role**: Stock/symbol database — single source of “what symbols we track.”

- Watchlists, screener results, symbol metadata (sector, market cap, liquidity).
- **In**: Screener runs (Finviz), manual edits, imports.
- **Out**: Symbol lists + metadata → Social/News, Chart Patterns, ML.

Extend current DB or add dedicated `symbols` / `watchlists` tables; wire to existing stocks API and screener.
