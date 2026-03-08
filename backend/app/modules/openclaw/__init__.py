"""
OpenClaw Module — DEPRECATED.

The OpenClaw multi-agent swarm intelligence has been superseded by:
- Bayesian regime engine (backend/app/services/regime_engine.py)
- 17-agent council DAG (backend/app/council/)
- Debate engine + Red Team adversarial layer

This module is preserved for the /api/v1/openclaw/* endpoints that the
frontend still hits directly (scan, macro, sectors, whale-flow, memory,
health).

NOTE: The /api/v1/openclaw/regime endpoint has been mirrored at
      /api/v1/market/regime.  The frontend useRegimeState hook now uses
      /api/v1/market/regime.  When all remaining openclaw endpoint
      consumers are migrated, this entire module can be deleted.
"""
