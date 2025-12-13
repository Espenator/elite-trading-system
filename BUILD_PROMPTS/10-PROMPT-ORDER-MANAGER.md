# PROMPT 10: ORDER MANAGEMENT AND POSITION TRACKING
## Real-Time P and L and Performance

Track all positions, calculate live P and L, monitor Greeks.

REQUIREMENTS:
1. Subscribe to order.placed
2. Subscribe to price.updated
3. Calculate real-time P and L
4. Track Greeks (delta, gamma, theta, vega)
5. Publish position.updated events
6. Maintain position state

DELIVERABLES: order_manager.py, position_tracker.py, pnl_calculator.py

Copy to Claude and ask: "Please write complete, production-ready code. Include ALL files, ALL functions, ALL imports. No TODOs."
