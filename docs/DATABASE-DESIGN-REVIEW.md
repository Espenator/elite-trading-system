# Database design review — two PCs, efficient storage, append-only

**Reviewed:** March 2026  
**Scope:** How pricing/symbol data is stored across ESPENMAIN and ProfitTrader; retaining all history while only adding fresh data.

---

## 1. Current layout (two PCs, no shared DB)

| Store | Location (per PC) | Purpose |
|-------|-------------------|--------|
| **DuckDB** | `backend/data/analytics.duckdb` | OHLCV, indicators, options flow, macro, trade outcomes, ML/features, postmortems, ingestion events |
| **SQLite** | `backend/data/trading_orders.db` | Orders, app **config** (including `symbol_universe`), alert rules, job idempotency |

- **ESPENMAIN** and **ProfitTrader** each have their **own** `backend/data/` and thus their own DuckDB and SQLite files.
- There is **no replication or sync** between the two PCs. Data is local to each machine.

---

## 2. How pricing data is stored today

### 2.1 Primary key = (symbol, date) — efficient “only add fresh”

- **`daily_ohlcv`** (and `technical_indicators`, `options_flow`) use **`(symbol, date)` as PRIMARY KEY**.
- Writes use **`INSERT OR REPLACE`** (DuckDB upsert):
  - New (symbol, date) → insert.
  - Existing (symbol, date) → replace (e.g. corrected bar or late tick).
- So we **never duplicate** (symbol, date); we only add new dates or overwrite existing ones. Old data is retained for all other dates.

### 2.2 Where new bars come from

| Source | How it hits DuckDB |
|--------|--------------------|
| **Real-time stream** | `market_data.bar` → 5s batched flush → `INSERT OR REPLACE INTO daily_ohlcv` (main.py) |
| **Historical backfill** | `data_ingestion.ingest_daily_bars(symbols, days)` → Alpaca bars API → `upsert_ohlcv(df)` |
| **Startup backfill** | `run_startup_backfill(days=252)` for all tracked symbols → same upsert path |
| **Daily incremental** | Scheduler at 4:30 AM ET → `ingest_all(symbols, days=7)` → same upsert |

So: **we only add/update rows; we don’t delete history.** Design is already “add fresh, keep old.”

### 2.3 Indexes (efficient range scans)

- `daily_ohlcv`: `idx_ohlcv_date`, `idx_ohlcv_symbol`.
- Queries filter by `symbol` and/or `date`; DuckDB is columnar and these indexes support “all history for symbol” and “all symbols for date” efficiently.

---

## 3. Symbol universe vs “every symbol” in the DB

- **Tracked symbols** today: come from **symbol_universe** (stored in SQLite `config` table, key `symbol_universe`), populated by Market Data Agent (e.g. Finviz) or manual watchlist.
- **DuckDB** does **not** have a dedicated “symbol registry” or “asset list” table. Symbols appear in `daily_ohlcv` (and related tables) only **after** we have at least one bar for them.
- **Fallback:** If symbol_universe is empty, data_ingestion uses `SELECT DISTINCT symbol FROM daily_ohlcv` or a small hardcoded list.

So: we do **not** yet have “every symbol and futures in the database” as a single source of truth. We have:
- A **config-driven** list of symbols to track (symbol_universe).
- **OHLCV (and related) rows** only for symbols we’ve actually requested or streamed.

---

## 4. Gaps and recommendations

### 4.1 Single symbol/asset registry (recommended)

To support “every symbol and futures in the database” and only add fresh data:

- Add a **symbol registry** (or “assets”) table in **DuckDB** (one place for analytics and reporting):

  - Example columns: `symbol`, `asset_class` (e.g. `us_equity`, `us_future`), `name`, `first_date`, `last_date`, `source`, `created_at`, `updated_at`.
  - Populate from:
    - Alpaca (and/or other) asset lists (stocks, futures, etc.).
    - When we first see a symbol in a bar or order, upsert into this table.
  - Use it to:
    - Drive “which symbols to backfill” (e.g. all equities + selected futures).
    - Report “what we have” and “what we’re tracking” without scanning all of `daily_ohlcv`.

- Keep **symbol_universe** in SQLite as the **trading/watchlist** subset (which symbols we care about for signals and execution). Sync or derive it from the DuckDB registry if you want one source of truth.

### 4.2 Futures and other asset classes

- Today: **daily_ohlcv** (and ingestion) are **equity-oriented** (Alpaca stocks bars, symbol list from Finviz/Alpaca equities).
- There is **no** `asset_class` (or similar) column in `daily_ohlcv`; no dedicated futures tables.
- To support **futures** (and retain all history, only add fresh):
  - Option A: Add `asset_class` (and optionally `underlying` or product id) to `daily_ohlcv`, and ingest futures bars the same way (Alpaca or another provider) with upsert by (symbol, date).
  - Option B: Separate table, e.g. `daily_ohlcv_futures`, same shape and same upsert semantics, so we still “only add fresh” and keep history.

Either way, re-use the same pattern: **primary key (symbol, date), INSERT OR REPLACE**.

### 4.3 Cross-PC consistency (ESPENMAIN vs ProfitTrader)

- Today: **no sync.** Each PC’s DuckDB/SQLite are independent.
- Implications:
  - Backfill and stream on **ESPENMAIN** only grow ESPENMAIN’s DB; **ProfitTrader** does not get that data unless you add a sync.
  - If ProfitTrader runs discovery/ML, it only sees its own local data.

Options:

- **Option A — Single writer (recommended for simplicity):**  
  Treat **ESPENMAIN** as the “data hub”: all bar ingestion and backfill run there. Then:
  - **One-way sync** from ESPENMAIN → ProfitTrader (e.g. periodic export of `daily_ohlcv` / `technical_indicators` / macro to file or API, then import on ProfitTrader), or
  - **Shared storage:** mount the same `backend/data/` (or just `analytics.duckdb`) from ESPENMAIN on ProfitTrader (NFS/SMB), so both see the same file (DuckDB supports single-writer, multiple readers if you use a shared filesystem and one writer).

- **Option B — Both PCs ingest:**  
  Each PC runs its own backfill/stream for the **same** symbol set and date ranges. No sync, but duplicate work and risk of small differences (e.g. corrections only on one side).

Recommendation: **single writer on ESPENMAIN + sync or shared storage** so both PCs see the same history and “only add fresh” is true in one place.

### 4.4 Retention and “only add fresh”

- Current design **does** retain all old data and only add/update by (symbol, date). No automatic purging of old OHLCV in the code reviewed.
- If you ever need retention (e.g. drop data older than N years), do it explicitly (e.g. scheduled `DELETE FROM daily_ohlcv WHERE date < ?`) and document it; otherwise keep the current “keep everything” behavior.

---

## 5. Summary

| Question | Answer |
|----------|--------|
| Do we retain all old data and only add fresh? | **Yes** for OHLCV/indicators/flow: upsert by (symbol, date), no duplicate dates, old dates kept. |
| Where is the DB? | Per PC: `backend/data/analytics.duckdb` (DuckDB), `backend/data/trading_orders.db` (SQLite). |
| Is there one “symbol + futures” list in the DB? | **No.** Symbol list is in SQLite config (symbol_universe); DuckDB has no asset registry yet. |
| Futures? | Not in schema yet; can add via same (symbol, date) upsert pattern, with or without a separate table. |
| Same data on both PCs? | **No.** No sync today; recommend single writer (ESPENMAIN) + sync or shared storage. |

**Concrete next steps:**

1. Add a **symbol/asset registry** in DuckDB (and optionally backfill from Alpaca assets + first-seen bars).
2. Keep **only add fresh** as-is (INSERT OR REPLACE by (symbol, date)); extend to futures if needed with same pattern.
3. Introduce **one-way sync or shared storage** so both PCs use the same DuckDB (or a copy) for pricing and history.
