# PROMPT 14: MARKET CALENDAR AND EARNINGS MONITOR
## Know When NOT to Trade - CRITICAL ADDITION

Block trading on earnings, FOMC, VIX spikes, economic releases.

REQUIREMENTS:
1. Load earnings calendar (IEX Cloud or similar)
2. Load economic calendar (FOMC, NFP, etc.)
3. Monitor VIX for spikes (greater than 3 std dev)
4. Publish market.tradeable_changed events
5. Approval system checks this before approving
6. Reduce position size on economic events
7. Block entirely on earnings

DELIVERABLES: market_calendar.py, earnings_monitor.py, economic_calendar.py

Copy to Claude and ask: "Please write complete, production-ready code. Include ALL files, ALL functions, ALL imports. No TODOs."
