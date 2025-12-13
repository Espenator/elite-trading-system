# PROMPT 11: UNUSUAL WHALES - OPTIONS FLOW
## Institutional and Smart Money Detection

Detect large options blocks and institutional positioning.

REQUIREMENTS:
1. Monitor options data
2. Detect blocks greater than 100 contracts
3. Calculate put/call ratios
4. Monitor IV skew
5. Publish whales.options_flow events
6. Score options activity as signal component

DELIVERABLES: whales_service.py, options_flow_detector.py, block_analyzer.py

Copy to Claude and ask: "Please write complete, production-ready code. Include ALL files, ALL functions, ALL imports. No TODOs."
