/**
 * ProfitBrainBar — compact status bar showing the profit brain's vital signs.
 * Fetches from /api/v1/cns/profit-brain every 10s via standard useApi hook.
 * Shows: win rate, total PnL, brain weights, feedback loop status, active systems count.
 */
import { useProfitBrain } from "../../hooks/useApi";

export default function ProfitBrainBar() {
  const { data: brain } = useProfitBrain();

  if (!brain) return null;

  const h = brain.health || {};
  const kelly = brain.cerebellum?.kelly_params || {};
  const weights = brain.cerebral_cortex?.unified_engine?.weights || {};
  const ot = brain.cerebellum?.outcome_tracker || {};

  const winRate = h.win_rate ?? ot.win_rate ?? 0;
  const pnl = h.total_pnl ?? ot.total_pnl ?? 0;
  const calibrated = h.feedback_loop_calibrated ?? false;
  const mlLoaded = h.ml_model_loaded ?? false;
  const sensory = h.sensory_systems_active ?? 0;
  const mode = brain.mode ?? "UNKNOWN";

  return (
    <div className="mx-4 mt-1 rounded-lg border border-gray-700/40 bg-gray-800/30 backdrop-blur-sm px-4 py-1.5 flex items-center justify-between gap-6 text-[10px]">
      {/* Profit Brain label */}
      <div className="flex items-center gap-2">
        <span className="text-cyan-400 font-bold tracking-wider">PROFIT BRAIN</span>
        <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${
          mode === "AGGRESSIVE" ? "bg-green-500/20 text-green-400" :
          mode === "DEFENSIVE" ? "bg-amber-500/20 text-amber-400" :
          mode === "HALTED" ? "bg-red-500/20 text-red-400" :
          "bg-cyan-500/20 text-cyan-400"
        }`}>{mode}</span>
      </div>

      {/* Win Rate */}
      <div className="text-center">
        <span className={`text-sm font-bold ${winRate >= 0.5 ? "text-green-400" : "text-red-400"}`}>
          {(winRate * 100).toFixed(1)}%
        </span>
        <div className="text-gray-500">Win Rate</div>
      </div>

      {/* Total PnL */}
      <div className="text-center">
        <span className={`text-sm font-bold ${pnl >= 0 ? "text-green-400" : "text-red-400"}`}>
          ${pnl >= 0 ? "+" : ""}{pnl.toFixed(0)}
        </span>
        <div className="text-gray-500">Total PnL</div>
      </div>

      {/* Resolved trades */}
      <div className="text-center">
        <span className="text-sm font-bold text-white">{ot.total_resolved ?? 0}</span>
        <div className="text-gray-500">Resolved</div>
      </div>

      {/* Brain weights mini-bar */}
      <div className="flex items-center gap-1">
        {Object.entries(weights).slice(0, 5).map(([key, val]) => (
          <div key={key} className="text-center" title={key}>
            <div className="h-3 w-5 bg-gray-700 rounded-sm overflow-hidden">
              <div
                className="bg-cyan-500 rounded-sm"
                style={{ height: `${(val ?? 0) * 100}%`, width: "100%" }}
              />
            </div>
            <div className="text-[8px] text-gray-600 truncate w-5">{key.slice(0, 2).toUpperCase()}</div>
          </div>
        ))}
      </div>

      {/* Status indicators */}
      <div className="flex items-center gap-3">
        <div className={`flex items-center gap-1 px-1.5 py-0.5 rounded ${calibrated ? "bg-green-500/10" : "bg-amber-500/10"}`}>
          <div className={`w-1.5 h-1.5 rounded-full ${calibrated ? "bg-green-400" : "bg-amber-400 animate-pulse"}`} />
          <span className={calibrated ? "text-green-400" : "text-amber-400"}>{calibrated ? "Kelly Calibrated" : "Learning..."}</span>
        </div>
        <div className={`flex items-center gap-1 px-1.5 py-0.5 rounded ${mlLoaded ? "bg-green-500/10" : "bg-gray-700/40"}`}>
          <div className={`w-1.5 h-1.5 rounded-full ${mlLoaded ? "bg-green-400" : "bg-gray-500"}`} />
          <span className={mlLoaded ? "text-green-400" : "text-gray-500"}>{mlLoaded ? "ML Active" : "ML Off"}</span>
        </div>
        <div className={`flex items-center gap-1 px-1.5 py-0.5 rounded ${sensory >= 3 ? "bg-green-500/10" : sensory > 0 ? "bg-amber-500/10" : "bg-gray-700/40"}`}>
          <div className={`w-1.5 h-1.5 rounded-full ${sensory >= 3 ? "bg-green-400" : sensory > 0 ? "bg-amber-400" : "bg-gray-500"}`} />
          <span className={sensory >= 3 ? "text-green-400" : sensory > 0 ? "text-amber-400" : "text-gray-500"}>{sensory}/4 Sensors</span>
        </div>
      </div>
    </div>
  );
}
