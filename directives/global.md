# Global Trading Directives

## Circuit Breaker Thresholds
- VIX spike threshold: 35
- Daily drawdown limit: 3%
- Flash crash threshold: 5% in 5min
- Max positions: 10
- Max single position: 20%

## Confidence Thresholds
- Hypothesis buy threshold: 0.6
- Hypothesis sell threshold: 0.4
- Arbiter minimum confidence: 0.4
- Strategy buy pass rate: 0.6
- Strategy sell pass rate: 0.3

## Risk Rules
- Always honor veto from risk_agent or execution_agent
- Maximum portfolio heat: 6%
- Maximum single position: 2% of portfolio
- Risk score below 30 triggers veto
- Extreme volatility (>50% annualized) triggers veto

## Execution Rules
- Minimum volume: 50,000 shares/day
- Orders require council_decision_id
- All decisions expire after 30 seconds (TTL)
- No trade without full council evaluation
