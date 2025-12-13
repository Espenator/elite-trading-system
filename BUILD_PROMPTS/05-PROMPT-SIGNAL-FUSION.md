# PROMPT 5: SIGNAL FUSION ENGINE
## Combine All Signals Into One Score

Fuse technical, ML, options, and regime into single confidence score.

REQUIREMENTS:
1. Subscribe to signal.technical_updated
2. Subscribe to ml.prediction_ready
3. Subscribe to whales.options_flow
4. Calculate regime state
5. Fuse all scores with weighting
6. Publish signal.fused_ready

DELIVERABLES: signal_engine.py, fusion_engine.py, regime_detector.py, score_calculator.py

Copy to Claude and ask: "Please write complete, production-ready code. Include ALL files, ALL functions, ALL imports. No TODOs."
