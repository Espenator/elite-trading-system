"""Scouts package — 12 dedicated continuous-discovery scout agents (E2).

Public API
----------
* :class:`~app.services.scouts.base_scout.BaseScout` — abstract base contract
* :class:`~app.services.scouts.registry.ScoutRegistry` — orchestrator singleton
* :func:`~app.services.scouts.registry.get_scout_registry` — access singleton
* :mod:`~app.services.scouts.schemas` — DiscoveryPayload, ScoutHealth

Scout Fleet (12 agents)
-----------------------
1.  AlpacaTradeScout         — volume spikes / unusual activity
2.  AlpacaNewsScout          — Alpaca news stream catalysts
3.  AlpacaPremarketScout     — pre-market gap scanner
4.  UnusualWhalesFlowScout   — options flow anomalies
5.  UnusualWhalesDarkpoolScout — dark pool prints
6.  FinvizMomentumScout      — RSI/momentum screener
7.  FinvizBreakoutScout      — new-high / volume breakout screener
8.  FredMacroScout           — FRED macro shift detector
9.  SecEdgarScout            — 8-K / insider filing monitor
10. NewsSentimentScout       — RSS news sentiment aggregator
11. SocialSentimentScout     — social media momentum
12. SectorRotationScout      — sector ETF relative strength
"""
from app.services.scouts.schemas import DiscoveryPayload, ScoutHealth
from app.services.scouts.base_scout import BaseScout
from app.services.scouts.registry import ScoutRegistry, get_scout_registry

__all__ = [
    "DiscoveryPayload",
    "ScoutHealth",
    "BaseScout",
    "ScoutRegistry",
    "get_scout_registry",
]
