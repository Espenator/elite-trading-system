# Execution Engine

**Role**: Execute orders with paper-first default and full audit.

- **Paper by default**: Alpaca paper API; no real money until TRADING_MODE=live.
- Order placement/cancel, risk checks (size, exposure, daily loss), audit log.
- **In**: Signals from ML Engine; user overrides.
- **Out**: Orders to Alpaca; fill/status → DB and ML (for learning).

Current `alpaca_service` and orders API live in `services/` and `api/v1/orders`; this module exposes status and mode; full orchestration (risk, audit) can be moved here incrementally.
