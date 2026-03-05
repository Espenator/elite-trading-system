/**
 * SwarmIntelligence — Dashboard for the scanner/swarm/outcome layer.
 *
 * Shows real-time status of:
 *   - TurboScanner (10 parallel screens)
 *   - HyperSwarm (50 micro-swarm workers)
 *   - NewsAggregator (RSS + SEC + FRED feeds)
 *   - MarketWideSweep (8000+ symbol universe)
 *   - UnifiedProfitEngine (adaptive brain weights)
 *   - OutcomeTracker (feedback loop health)
 *   - PositionManager (active trailing stops)
 *   - ML Scorer (live model status)
 */
import {
  useSwarmTurbo,
  useSwarmHyper,
  useSwarmNews,
  useSwarmSweep,
  useSwarmUnified,
  useSwarmOutcomes,
  useSwarmKelly,
  useSwarmPositions,
  useSwarmMlScorer,
} from "../hooks/useApi";

// Status badge
function Badge({ status, label }) {
  const colors = {
    running: "bg-green-500/20 text-green-400 border-green-500/30",
    stopped: "bg-red-500/20 text-red-400 border-red-500/30",
    true: "bg-green-500/20 text-green-400 border-green-500/30",
    false: "bg-gray-500/20 text-gray-400 border-gray-500/30",
    loaded: "bg-cyan-500/20 text-cyan-400 border-cyan-500/30",
  };
  const color = colors[String(status)] || colors.stopped;
  return (
    <span className={`px-2 py-0.5 text-xs rounded border ${color}`}>
      {label || String(status)}
    </span>
  );
}

// Metric card
function Metric({ label, value, sub }) {
  return (
    <div className="text-center">
      <div className="text-2xl font-bold text-white">{value ?? "-"}</div>
      <div className="text-xs text-gray-400">{label}</div>
      {sub && <div className="text-xs text-gray-500 mt-0.5">{sub}</div>}
    </div>
  );
}

// Section card
function Card({ title, badge, children }) {
  return (
    <div className="bg-gray-800/50 rounded-lg border border-gray-700/50 p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-200">{title}</h3>
        {badge}
      </div>
      {children}
    </div>
  );
}

export default function SwarmIntelligence() {
  const { data: turbo } = useSwarmTurbo();
  const { data: hyper } = useSwarmHyper();
  const { data: news } = useSwarmNews();
  const { data: sweep } = useSwarmSweep();
  const { data: unified } = useSwarmUnified();
  const { data: outcomes } = useSwarmOutcomes();
  const { data: positions } = useSwarmPositions();
  const { data: mlStatus } = useSwarmMlScorer();
  const { data: kelly } = useSwarmKelly();

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-white">Swarm Intelligence</h1>
        <div className="text-xs text-gray-500">Auto-refresh: 10s</div>
      </div>

      {/* Top row: Key metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 bg-gray-800/30 rounded-lg p-4 border border-gray-700/30">
        <Metric
          label="Win Rate"
          value={outcomes?.win_rate != null ? `${(outcomes.win_rate * 100).toFixed(1)}%` : "-"}
          sub={outcomes ? `${outcomes.wins}W / ${outcomes.losses}L` : ""}
        />
        <Metric
          label="Total PnL"
          value={outcomes?.total_pnl != null ? `$${outcomes.total_pnl.toFixed(0)}` : "-"}
          sub={outcomes ? `${outcomes.total_resolved} trades` : ""}
        />
        <Metric
          label="Kelly Calibrated"
          value={outcomes?.kelly_calibrated ? "Yes" : "No"}
          sub={kelly ? `WR=${(kelly.win_rate * 100).toFixed(0)}% W=${(kelly.avg_win_pct * 100).toFixed(1)}%` : ""}
        />
        <Metric
          label="Active Positions"
          value={positions?.managed_positions ?? outcomes?.open_positions ?? 0}
        />
        <Metric
          label="Signals Today"
          value={turbo?.stats?.total_signals ?? 0}
          sub={`${hyper?.stats?.total_triaged ?? 0} triaged`}
        />
        <Metric
          label="ML Model"
          value={mlStatus?.model_loaded ? "Active" : "Offline"}
          sub={mlStatus?.val_accuracy ? `Acc: ${(mlStatus.val_accuracy * 100).toFixed(1)}%` : ""}
        />
      </div>

      {/* Brain weights */}
      {unified && (
        <Card
          title="Unified Profit Engine — Brain Weights"
          badge={<Badge status={unified.running ? "running" : "stopped"} label={unified.running ? "ADAPTIVE" : "OFF"} />}
        >
          <div className="grid grid-cols-5 gap-3">
            {Object.entries(unified.weights || {}).map(([brain, weight]) => (
              <div key={brain} className="text-center bg-gray-900/50 rounded p-2">
                <div className="text-lg font-bold text-cyan-400">{(weight * 100).toFixed(1)}%</div>
                <div className="text-xs text-gray-400 capitalize">{brain.replace("_", " ")}</div>
                {unified.brain_accuracy?.[brain] != null && (
                  <div className="text-xs text-gray-500">acc: {(unified.brain_accuracy[brain] * 100).toFixed(0)}%</div>
                )}
              </div>
            ))}
          </div>
          <div className="text-xs text-gray-500 mt-2">
            {unified.scores_produced} unified scores produced | Adapts every {unified.adaptation_interval_s}s
          </div>
        </Card>
      )}

      {/* Scanner row */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* TurboScanner */}
        <Card
          title="TurboScanner"
          badge={<Badge status={turbo?.running ? "running" : "stopped"} label={turbo?.running ? "SCANNING" : "OFF"} />}
        >
          {turbo ? (
            <div className="space-y-2">
              <div className="grid grid-cols-3 gap-2">
                <Metric label="Signals" value={turbo.stats?.total_signals ?? 0} />
                <Metric label="Screens/Cycle" value={turbo.stats?.screens_per_cycle ?? 10} />
                <Metric label="Interval" value={`${turbo.scan_interval ?? 60}s`} />
              </div>
              <div className="text-xs text-gray-500">
                Universe: Tier 1 ({turbo.stats?.tier1_symbols ?? 60}) + Tier 2 ({turbo.stats?.tier2_symbols ?? 200})
              </div>
            </div>
          ) : (
            <div className="text-gray-500 text-sm">Loading...</div>
          )}
        </Card>

        {/* HyperSwarm */}
        <Card
          title="HyperSwarm"
          badge={<Badge status={hyper?.running ? "running" : "stopped"} label={hyper?.running ? "SWARMING" : "OFF"} />}
        >
          {hyper ? (
            <div className="space-y-2">
              <div className="grid grid-cols-3 gap-2">
                <Metric label="Triaged" value={hyper.stats?.total_triaged ?? 0} />
                <Metric label="Escalated" value={hyper.stats?.total_escalated ?? 0} />
                <Metric label="Workers" value={hyper.stats?.active_workers ?? 0} />
              </div>
              <div className="text-xs text-gray-500">
                Ollama nodes: {hyper.stats?.ollama_nodes ?? 0} | Escalation threshold: 65
              </div>
            </div>
          ) : (
            <div className="text-gray-500 text-sm">Loading...</div>
          )}
        </Card>
      </div>

      {/* Data sources row */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* NewsAggregator */}
        <Card
          title="News Aggregator"
          badge={<Badge status={news?.running ? "running" : "stopped"} label={news?.running ? "MONITORING" : "OFF"} />}
        >
          {news ? (
            <div className="space-y-2">
              <div className="grid grid-cols-3 gap-2">
                <Metric label="RSS Feeds" value={news.rss_feeds ?? 0} />
                <Metric label="Items Found" value={news.stats?.total_items ?? 0} />
                <Metric label="Symbols" value={news.stats?.unique_symbols ?? 0} />
              </div>
              <div className="text-xs text-gray-500">
                SEC filings: {news.stats?.sec_filings ?? 0} | FRED alerts: {news.stats?.fred_alerts ?? 0}
              </div>
            </div>
          ) : (
            <div className="text-gray-500 text-sm">Loading...</div>
          )}
        </Card>

        {/* MarketWideSweep */}
        <Card
          title="Market-Wide Sweep"
          badge={<Badge status={sweep?.running ? "running" : "stopped"} label={sweep?.running ? "SWEEPING" : "OFF"} />}
        >
          {sweep ? (
            <div className="space-y-2">
              <div className="grid grid-cols-3 gap-2">
                <Metric label="Universe" value={sweep.universe_size ?? 0} />
                <Metric label="Screens" value={sweep.screens_run ?? 0} />
                <Metric label="Hits" value={sweep.total_hits ?? 0} />
              </div>
              <div className="text-xs text-gray-500">
                Full sweep: every 4hr | Incremental: every 30min
              </div>
            </div>
          ) : (
            <div className="text-gray-500 text-sm">Loading...</div>
          )}
        </Card>
      </div>

      {/* Position management row */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* OutcomeTracker */}
        <Card
          title="Outcome Tracker (Feedback Loop)"
          badge={<Badge status={outcomes?.running ? "running" : "stopped"} label={outcomes?.kelly_calibrated ? "CALIBRATED" : "LEARNING"} />}
        >
          {outcomes ? (
            <div className="space-y-2">
              <div className="grid grid-cols-4 gap-2">
                <Metric label="Wins" value={outcomes.wins} />
                <Metric label="Losses" value={outcomes.losses} />
                <Metric label="Win Rate" value={`${(outcomes.win_rate * 100).toFixed(1)}%`} />
                <Metric label="Avg R" value={outcomes.avg_r_multiple?.toFixed(2) ?? "-"} />
              </div>
              <div className="text-xs text-gray-500">
                Open: {outcomes.open_positions} | Resolved: {outcomes.total_resolved} | Kelly: {outcomes.kelly_calibrated ? "calibrated from real data" : "using heuristic (need 10+ trades)"}
              </div>
            </div>
          ) : (
            <div className="text-gray-500 text-sm">Loading...</div>
          )}
        </Card>

        {/* PositionManager */}
        <Card
          title="Position Manager"
          badge={<Badge status={positions?.running ? "running" : "stopped"} label={positions?.running ? "MANAGING" : "OFF"} />}
        >
          {positions ? (
            <div className="space-y-2">
              <div className="grid grid-cols-3 gap-2">
                <Metric label="Active" value={positions.managed_positions} />
                <Metric label="Trail Exits" value={positions.stats?.exits_trailing ?? 0} />
                <Metric label="Time Exits" value={positions.stats?.exits_time ?? 0} />
              </div>
              {positions.positions && Object.keys(positions.positions).length > 0 && (
                <div className="mt-2 space-y-1">
                  {Object.entries(positions.positions).slice(0, 5).map(([sym, p]) => (
                    <div key={sym} className="flex justify-between text-xs bg-gray-900/50 rounded px-2 py-1">
                      <span className="text-cyan-400 font-mono">{sym}</span>
                      <span className="text-gray-400">
                        Entry: ${p.entry?.toFixed(2)} | Trail: ${p.trailing_stop?.toFixed(2)} | {p.hold_time_min?.toFixed(0)}min
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="text-gray-500 text-sm">Loading...</div>
          )}
        </Card>
      </div>

      {/* ML Model status */}
      <Card
        title="ML XGBoost Scorer"
        badge={<Badge status={mlStatus?.model_loaded ? "loaded" : "stopped"} label={mlStatus?.model_loaded ? "LOADED" : "NO MODEL"} />}
      >
        {mlStatus ? (
          <div className="grid grid-cols-4 gap-4">
            <Metric label="Predictions" value={mlStatus.predictions_made} />
            <Metric label="Features" value={mlStatus.feature_count} />
            <Metric label="Val Accuracy" value={mlStatus.val_accuracy ? `${(mlStatus.val_accuracy * 100).toFixed(1)}%` : "-"} />
            <Metric label="Last Trained" value={mlStatus.last_trained || "never"} />
          </div>
        ) : (
          <div className="text-gray-500 text-sm">Loading...</div>
        )}
      </Card>
    </div>
  );
}
