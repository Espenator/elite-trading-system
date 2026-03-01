# Performance Analytics - UI Mockup

> Design reference for the Performance Analytics page (`/performance` route)
> Generated: Feb 28, 2026 | Source: Gemini AI (Embodier.ai project)

## Full-Page Mockup (1920x1080)

![Performance Analytics Mockup](https://lh3.googleusercontent.com/rd-gg-dl/AOI_d_9yknmipbZpTS7FF-J3isAJyvSS2FJpl5JpbC4DK921iRLTJwRYoEUbeRonfcEvac3KXEt6ai2oWDCtpHUrkHrZ6_XVNZEnKhE-c4Q9OFPEsrUChmafxzC0CjoMBktrIE7G1Eq_rB2HinlWVD0FkmEtv0SFxXjD05JPoPGE3lxitNir7ie4bcigsiZSvlA92dLCwC3nHTkEeip9CH2rJl5q5dPxnx9cwTdwcBA5jZ_s03McJw_JfbpQlrX1ZIQ4C6FY711p_JAjFf5Enq8X6GHGA8spvzdldzx_Lv6ONWXvHvyKDaj68caNpEEzq0noCrUSd9bqWHW_iEfr1oB9uMU0NqNW3bOOOm3MGXTDVUnR7Oh8najVdQ44R9jq9LmNfms-87is1O_NAD8_c9GYAtAQXWk2opSh7v9RVD0OdHmdnrZOtzXu23qYavBhkMds1RrLQuaO4TJZ5qFVysDGO8DrMQwjf97jrjDWjKawVXJCN32zDoxsnwEQYKFyOBqD3uhvj7GDyDsHFqbubZ-dzw5PuDhAJxhNXFOEtwM3ShOV-SSQ1ztNjbe0atHlO9G61acKw1oXFm4K2FVsZ50GXDPi2oM_KtDmb6BkPNwbEcz-PFkmUsfJi-xPLTekwVeecQlFSJhzpzdWWAAWFArRy4HqpVeoEa5qpm0QGkA6O9HeBj8HP7d6uaw39tNTvoWdCUERVO7Zv0J3HrW-5UXVvenDzIX_zyDmwnZ7xNVk1owyw3J7NXx9yTBOcSUyGDZy-uevJV1Svbpv6cQQN81jEQUrTXLu5_PtJJP0IWUNd9LkSIGAhnsvwVvxJH1bZ5Lr9RsqOIF1XJan36avCtkI1qYRBFTyYXVxWilOKWhjAe3mT7mi0RmP0l6r7sIXz6n8jnxRmzjiKAm7RE2ak9N0gqru6Ye3aXvEzQQn6qwvAfdzz6M5g2543rb7S)

## Layout Structure

### Left Sidebar (w-64 expanded)
- **Embodier.ai** logo + "Trading Intelligence" tagline
- 15 pages in 5 sections: COMMAND, INTELLIGENCE, ML & ANALYSIS, EXECUTION, SYSTEM
- "Performance Analytics" is the active/highlighted item (under ML & ANALYSIS)
- System status indicator at bottom with agent count + health dot

### Top Metrics Bar
- Total Trades: 247
- Net P&L: +$12,847.32
- Win Rate: 68.4%
- Avg Win: $312.50
- Avg Loss: -$187.20
- Profit Factor: 2.14
- Max DD: -4,230 / -8.2%
- Sharpe: 1.87
- Expectancy: $89.40
- R:R: 1.67:1

### Main Content - 3 Column Layout

#### Left Column (3/12)
- Trading Grade Hero (A - Excellent)
- Risk Ratio Cluster (Sharpe, Sortino, Calmar)
- Kelly Criterion Panel
- Risk/Reward + Expectancy chart

#### Center Column (5/12)
- Equity + Drawdown chart (primary visualization)
- Agent Attribution Leaderboard table
- ML & Flywheel Engine (accuracy trend, staged inferences, pipeline health)

#### Right Column (4/12)
- AI + Rolling Risk (Nested Concentric AI Dial)
- Attribution + Agent ELO (P&L by Symbol, Agent Attribution, Returns Heatmap)
- Enhanced Trades Table
- Risk Cockpit Expanded + Strategy & Signals

### Footer Status Bar (28px)
- "Embodier Trader - Performance Analytics v2.0"
- Green dot "Connected"
- Active filters in cyan
- "Data: Jan 1 - Feb 28, 2026 - 312 trades"

## Design Tokens
- **Theme**: Dark mode (bg-background: #0a0e17, bg-surface: #111827)
- **Primary/Accent**: Cyan (#06b6d4)
- **Success**: Green (#10b981)
- **Danger**: Red (#ef4444)
- **Warning**: Amber (#f59e0b)
- **Typography**: System/Inter, high-density Bloomberg-style
- **Cards**: Rounded-lg, border border-secondary/50, subtle hover effects
