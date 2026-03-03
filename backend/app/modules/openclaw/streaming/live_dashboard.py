#!/usr/bin/env python3
"""
live_dashboard.py — OpenClaw Real-Time Trading Dashboard (Task 8f)

Flask-based web dashboard providing real-time visibility into:
  - Pipeline status & regime
  - Risk governor state (exposure, P&L, circuit breaker)
  - Open positions with live P&L
  - Watchlist candidates & scores
  - Agent health / heartbeats
  - Recent trade log & rejections

Auto-refreshes via Server-Sent Events (SSE) every 5 seconds.
Access at http://localhost:5001

Usage:
  python live_dashboard.py          # Standalone
  python main.py --dashboard        # Via orchestrator
"""

import os
import json
import time
import logging
import threading
from datetime import datetime
from zoneinfo import ZoneInfo
from flask import Flask, Response, render_template_string, jsonify

logger = logging.getLogger("openclaw.dashboard")
ET = ZoneInfo("America/New_York")

# ── HTML Template ────────────────────────────────────────────
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>OpenClaw Live Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Courier New', monospace; background: #0a0e17; color: #e0e0e0; padding: 16px; }
        h1 { color: #ff6b35; margin-bottom: 8px; font-size: 1.6em; }
        h2 { color: #4ecdc4; margin: 16px 0 8px 0; font-size: 1.1em; border-bottom: 1px solid #1a2332; padding-bottom: 4px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(420px, 1fr)); gap: 12px; }
        .card { background: #111827; border: 1px solid #1f2937; border-radius: 8px; padding: 14px; }
        .metric { display: inline-block; margin: 4px 12px 4px 0; }
        .metric-label { color: #9ca3af; font-size: 0.75em; text-transform: uppercase; }
        .metric-value { font-size: 1.2em; font-weight: bold; }
        .green { color: #10b981; }
        .red { color: #ef4444; }
        .yellow { color: #f59e0b; }
        .blue { color: #3b82f6; }
        .orange { color: #ff6b35; }
        table { width: 100%; border-collapse: collapse; font-size: 0.85em; margin-top: 6px; }
        th, td { padding: 5px 8px; text-align: left; border-bottom: 1px solid #1f2937; }
        th { color: #9ca3af; font-size: 0.75em; text-transform: uppercase; }
        .badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.75em; font-weight: bold; }
        .badge-green { background: #064e3b; color: #34d399; }
        .badge-red { background: #7f1d1d; color: #fca5a5; }
        .badge-yellow { background: #78350f; color: #fcd34d; }
        .status-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; padding: 8px 14px; background: #111827; border-radius: 6px; border: 1px solid #1f2937; }
        .pulse { animation: pulse 2s infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
        #last-update { color: #6b7280; font-size: 0.8em; }
    </style>
</head>
<body>
    <h1>🦀 OpenClaw Live Dashboard</h1>
    <div class="status-bar">
        <span id="regime-badge" class="badge badge-green">LOADING</span>
        <span id="pipeline-status">Connecting...</span>
        <span id="last-update">—</span>
    </div>

    <div class="grid">
        <!-- Risk Governor -->
        <div class="card">
            <h2>⚡ Risk Governor</h2>
            <div id="risk-metrics">Loading...</div>
        </div>

        <!-- Portfolio -->
        <div class="card">
            <h2>💼 Portfolio</h2>
            <div id="portfolio-metrics">Loading...</div>
            <table id="positions-table"><tbody></tbody></table>
        </div>

        <!-- Watchlist -->
        <div class="card" style="grid-column: span 2;">
            <h2>📋 Watchlist (Top Candidates)</h2>
            <table id="watchlist-table">
                <thead><tr><th>Ticker</th><th>Grade</th><th>Score</th><th>Entry</th><th>Stop</th><th>Target</th><th>R:R</th><th>Setup</th><th>Risk</th></tr></thead>
                <tbody></tbody>
            </table>
        </div>

        <!-- Recent Rejections -->
        <div class="card">
            <h2>🚫 Recent Rejections</h2>
            <div id="rejections">None</div>
        </div>

        <!-- Agent Health -->
        <div class="card">
            <h2>🤖 Agent Health</h2>
            <div id="agent-health">Loading...</div>
        </div>
    </div>

    <script>
        function formatMoney(v) { return (v >= 0 ? '+' : '') + '$' + Math.abs(v).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2}); }
        function colorClass(v) { return v >= 0 ? 'green' : 'red'; }
        function regimeBadge(r) {
            const cls = r === 'GREEN' || r === 'bull' ? 'badge-green' : r === 'RED' || r === 'bear' ? 'badge-red' : 'badge-yellow';
            return `<span class="badge ${cls}">${(r || 'UNKNOWN').toUpperCase()}</span>`;
        }

        const evtSource = new EventSource('/stream');
        evtSource.onmessage = function(event) {
            const d = JSON.parse(event.data);
            document.getElementById('last-update').textContent = 'Updated: ' + new Date().toLocaleTimeString();

            // Regime
            const regime = (d.regime || 'unknown').toUpperCase();
            document.getElementById('regime-badge').outerHTML = regimeBadge(regime);
            document.getElementById('pipeline-status').innerHTML =
                `Equity: <span class="green">$${(d.risk?.equity || 100000).toLocaleString()}</span> | ` +
                `Trades: ${d.risk?.daily_trades || 0}/${d.risk?.max_daily_trades || 10}`;

            // Risk
            const r = d.risk || {};
            document.getElementById('risk-metrics').innerHTML =
                `<div class="metric"><div class="metric-label">Daily P&L</div><div class="metric-value ${colorClass(r.daily_pnl || 0)}">${formatMoney(r.daily_pnl || 0)}</div></div>` +
                `<div class="metric"><div class="metric-label">Exposure</div><div class="metric-value ${(r.exposure_pct || 0) > 50 ? 'yellow' : 'blue'}">${(r.exposure_pct || 0).toFixed(1)}%</div></div>` +
                `<div class="metric"><div class="metric-label">Circuit Breaker</div><div class="metric-value ${r.circuit_breaker_ok ? 'green' : 'red'}">${r.circuit_breaker_ok ? 'OK' : 'TRIPPED'}</div></div>` +
                `<div class="metric"><div class="metric-label">Positions</div><div class="metric-value blue">${r.open_positions || 0}</div></div>`;

            // Portfolio
            document.getElementById('portfolio-metrics').innerHTML =
                `<div class="metric"><div class="metric-label">Total Value</div><div class="metric-value green">$${(r.total_exposure || 0).toLocaleString()}</div></div>` +
                `<div class="metric"><div class="metric-label">Buying Power</div><div class="metric-value blue">$${((r.equity || 100000) - (r.total_exposure || 0)).toLocaleString()}</div></div>`;

            const posBody = document.querySelector('#positions-table tbody');
            posBody.innerHTML = '';
            if (r.positions) {
                Object.entries(r.positions).forEach(([sym, p]) => {
                    posBody.innerHTML += `<tr><td class="orange">${sym}</td><td>$${(p.value || 0).toLocaleString()}</td><td>${p.shares || 0} sh</td><td>${p.sector || '-'}</td></tr>`;
                });
            }

            // Watchlist
            const wBody = document.querySelector('#watchlist-table tbody');
            wBody.innerHTML = '';
            (d.candidates || []).slice(0, 15).forEach(c => {
                const gradeClass = c.entry_grade === 'A' ? 'green' : c.entry_grade === 'B' ? 'yellow' : 'red';
                const riskStatus = c.risk_approved === true ? '<span class="green">✓</span>' : c.risk_approved === false ? '<span class="red">✗</span>' : '-';
                wBody.innerHTML += `<tr>
                    <td class="orange">${c.ticker || c.symbol || '?'}</td>
                    <td class="${gradeClass}">${c.entry_grade || '-'}</td>
                    <td>${(c.entry_score || 0).toFixed(0)}</td>
                    <td>$${(c.limit_price || c.price || 0).toFixed(2)}</td>
                    <td>$${(c.stop_loss || 0).toFixed(2)}</td>
                    <td>$${(c.take_profit || 0).toFixed(2)}</td>
                    <td>${(c.reward_risk || 0).toFixed(1)}</td>
                    <td>${c.setup_type || c.recommendation || '-'}</td>
                    <td>${riskStatus}</td>
                </tr>`;
            });

            // Rejections
            const rejs = r.recent_rejections || [];
            document.getElementById('rejections').innerHTML = rejs.length === 0 ? '<span class="green">No rejections</span>' :
                rejs.slice(-8).map(j => `<div style="margin:3px 0"><span class="orange">${j.ticker}</span> — <span class="red">${j.reason}</span> <span style="color:#6b7280;font-size:0.8em">${j.time || ''}</span></div>`).join('');

            // Agent Health
            const agents = d.agents || {};
            document.getElementById('agent-health').innerHTML = Object.keys(agents).length === 0 ? 'No agent data' :
                Object.entries(agents).map(([name, info]) => {
                    const alive = info.alive !== false;
                    return `<span class="badge ${alive ? 'badge-green' : 'badge-red'}" style="margin:2px">${name}</span>`;
                }).join(' ');
        };
    </script>
</body>
</html>
"""


# ── Dashboard State Collector ────────────────────────────────

class DashboardState:
    """Collects state from all OpenClaw subsystems."""

    def __init__(self):
        self._cache = {}
        self._cache_time = 0
        self._lock = threading.Lock()

    def get_state(self) -> dict:
        now = time.time()
        if now - self._cache_time < 3:  # 3s cache
            return self._cache

        state = {
            "timestamp": datetime.now(ET).isoformat(),
            "regime": "neutral",
            "risk": {},
            "candidates": [],
            "agents": {},
        }

        # Risk governor
        try:
            from risk_governor import get_governor
            gov = get_governor()
            state["risk"] = gov.get_status()
        except Exception:
            state["risk"] = {"equity": 100000, "daily_pnl": 0, "exposure_pct": 0,
                             "open_positions": 0, "daily_trades": 0, "max_daily_trades": 10,
                             "circuit_breaker_ok": True, "positions": {}, "recent_rejections": []}

        # Regime
        try:
            from config import BLACKBOARD_PERSIST_PATH
            if os.path.exists(BLACKBOARD_PERSIST_PATH):
                with open(BLACKBOARD_PERSIST_PATH) as f:
                    bb = json.load(f)
                state["regime"] = bb.get("regime", "neutral")
        except Exception:
            pass

        # Candidates from daily watchlist
        try:
            from config import WATCHLIST_PATH
            if os.path.exists(WATCHLIST_PATH):
                with open(WATCHLIST_PATH) as f:
                    wl = json.load(f)
                state["candidates"] = wl if isinstance(wl, list) else wl.get("candidates", [])
        except Exception:
            pass

        # Agent heartbeats
        try:
            heartbeat_path = os.path.join("data", "agent_heartbeats.json")
            if os.path.exists(heartbeat_path):
                with open(heartbeat_path) as f:
                    state["agents"] = json.load(f)
        except Exception:
            pass

        with self._lock:
            self._cache = state
            self._cache_time = now
        return state


# ── Flask App Factory ────────────────────────────────────────

def create_app() -> Flask:
    app = Flask(__name__)
    dashboard = DashboardState()

    @app.route("/")
    def index():
        return render_template_string(DASHBOARD_HTML)

    @app.route("/api/state")
    def api_state():
        return jsonify(dashboard.get_state())

    @app.route("/stream")
    def stream():
        def event_stream():
            while True:
                state = dashboard.get_state()
                yield f"data: {json.dumps(state, default=str)}\n\n"
                time.sleep(5)
        return Response(event_stream(), mimetype="text/event-stream",
                        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    @app.route("/api/risk")
    def api_risk():
        try:
            from risk_governor import get_governor
            return jsonify(get_governor().get_status())
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/health")
    def api_health():
        return jsonify({"status": "ok", "timestamp": datetime.now(ET).isoformat()})

    logger.info("Dashboard app created — available at http://localhost:5001")
    return app


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
    app = create_app()
    print("\n🦀 OpenClaw Live Dashboard starting on http://localhost:5001")
    app.run(host="0.0.0.0", port=5001, debug=False)
