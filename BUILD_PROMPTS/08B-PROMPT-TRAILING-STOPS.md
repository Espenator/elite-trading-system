# PROMPT 8B: TRAILING STOPS AND SCALE-OUT
## Let Winners Run - CRITICAL ADDITION

Convert fixed 2 percent targets to dynamic 5-10 percent plus winners.

REQUIREMENTS:
1. Subscribe to position.created
2. Monitor position P and L in real-time
3. At plus 2 percent: Set stop to entry (breakeven)
4. At plus 5 percent: Scale out 25 percent, trail rest by 2x ATR
5. At plus 10 percent: Scale out 50 percent more, trail rest by 3x ATR
6. Let rest run to plus 20 percent plus
7. Publish position.scaled_out events
8. Update database with scale-out records

DELIVERABLES: trailing_stop_manager.py, scale_out_engine.py, position_monitor.py

Copy to Claude and ask: "Please write complete, production-ready code. Include ALL files, ALL functions, ALL imports. No TODOs."
