"""
OpenClaw Module — DEPRECATED.

The OpenClaw multi-agent swarm intelligence has been superseded by:
- Bayesian regime engine (backend/app/services/regime_engine.py)
- 31-agent council DAG (backend/app/council/)
- Debate engine + Red Team adversarial layer

This module is preserved ONLY for the /api/v1/openclaw/regime endpoint
that the frontend currently hits. All other OpenClaw code is dead.

TODO: Migrate the frontend to use /api/v1/cns/regime or /api/v1/market/regime
      and then delete this entire module.
"""
