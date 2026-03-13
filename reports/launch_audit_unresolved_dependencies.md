# Unresolved Dependencies Preventing Verification

**Audit**: 2026-03-12 — Launch Commander

Items that could not be fully verified in this run. Mark as ⏭️ SKIPPED where applicable.

1. **Startup timing**  
   Backend was not started during audit. To verify: run `uvicorn app.main:app --host 0.0.0.0 --port 8000` and measure time to first successful `GET /health` or `GET /api/v1/status`.

2. **Real Alpaca connectivity**  
   No live or paper API calls were executed. To verify: run a dedicated integration test against paper account (e.g. GET account, place/cancel paper order) with credentials in `.env`.

3. **Frontend screenshot/console logs**  
   No browser or DevTools artifacts were captured. E2E audit tests provide API-level evidence only. To verify: run frontend against backend, capture screenshots for critical pages and save console/network logs to `artifacts/screenshots/` and `artifacts/logs/`.

4. **Brain service (gRPC) on PC2**  
   Not verified in this audit. Optional: confirm brain_service on ProfitTrader (192.168.1.116:50051) for hypothesis_agent LLM path.

5. **Full test suite 7 failures**  
   Not blocking launch but prevent green CI: feature_store (DuckDB file lock), jobs idempotency, redis_bridge. Fix for CI stability; not in order execution path.
