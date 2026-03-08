/**
 * RiskGuardrailPanel - Display risk controls and limits
 * Makes risk controls visible and understandable
 */
import React from "react";
import { Shield, AlertTriangle, TrendingDown, Lock } from "lucide-react";

export function RiskGuardrailPanel({ riskPolicy = {}, className = "" }) {
  const {
    maxRiskPerTrade = 2.0,
    maxOpenPositions = 5,
    portfolioHeat = 0,
    maxPortfolioHeat = 10.0,
    dailyLossCap = 500,
    weeklyDrawdownCap = 1000,
    stopLossRequired = true,
    takeProfitPolicy = "trail",
    cooldownAfterLossStreak = 3,
    currentLossStreak = 0,
  } = riskPolicy;

  const heatPercentage = maxPortfolioHeat > 0 ? (portfolioHeat / maxPortfolioHeat) * 100 : 0;
  const isHeatHigh = heatPercentage > 80;
  const isHeatMedium = heatPercentage > 50 && heatPercentage <= 80;

  return (
    <div className={`bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-lg p-3 ${className}`}>
      <div className="flex items-center gap-2 mb-3 pb-2 border-b border-gray-800/50">
        <Shield className="w-4 h-4 text-cyan-400" />
        <span className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">
          Risk Guardrails
        </span>
      </div>

      <div className="space-y-2">
        {/* Portfolio Heat */}
        <div className="bg-[#0B0E14] rounded p-2">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[10px] text-gray-400">Portfolio Heat</span>
            <span
              className={`text-[10px] font-mono font-bold ${
                isHeatHigh ? "text-red-400" : isHeatMedium ? "text-amber-400" : "text-emerald-400"
              }`}
            >
              {portfolioHeat.toFixed(1)}% / {maxPortfolioHeat.toFixed(1)}%
            </span>
          </div>
          <div className="w-full bg-gray-800 rounded-full h-1.5 overflow-hidden">
            <div
              className={`h-full transition-all ${
                isHeatHigh
                  ? "bg-red-500"
                  : isHeatMedium
                    ? "bg-amber-500"
                    : "bg-emerald-500"
              }`}
              style={{ width: `${Math.min(heatPercentage, 100)}%` }}
            />
          </div>
        </div>

        {/* Risk Limits */}
        <div className="grid grid-cols-2 gap-2 text-[10px]">
          <div className="flex items-center justify-between bg-[#0B0E14] rounded px-2 py-1.5">
            <span className="text-gray-400">Max Risk/Trade</span>
            <span className="text-white font-mono font-bold">{maxRiskPerTrade}%</span>
          </div>
          <div className="flex items-center justify-between bg-[#0B0E14] rounded px-2 py-1.5">
            <span className="text-gray-400">Max Positions</span>
            <span className="text-white font-mono font-bold">{maxOpenPositions}</span>
          </div>
          <div className="flex items-center justify-between bg-[#0B0E14] rounded px-2 py-1.5">
            <span className="text-gray-400">Daily Loss Cap</span>
            <span className="text-white font-mono font-bold">${dailyLossCap}</span>
          </div>
          <div className="flex items-center justify-between bg-[#0B0E14] rounded px-2 py-1.5">
            <span className="text-gray-400">Weekly DD Cap</span>
            <span className="text-white font-mono font-bold">${weeklyDrawdownCap}</span>
          </div>
        </div>

        {/* Safety Policies */}
        <div className="space-y-1 text-[10px]">
          <div className="flex items-center justify-between">
            <span className="text-gray-400">Stop-Loss Required</span>
            <span className={`font-mono font-bold ${stopLossRequired ? "text-emerald-400" : "text-red-400"}`}>
              {stopLossRequired ? "YES" : "NO"}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-gray-400">Take-Profit Policy</span>
            <span className="text-cyan-400 font-mono uppercase">{takeProfitPolicy}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-gray-400">Loss Streak Cooldown</span>
            <span className="text-white font-mono">{cooldownAfterLossStreak} trades</span>
          </div>
        </div>

        {/* Current Loss Streak Warning */}
        {currentLossStreak >= cooldownAfterLossStreak && (
          <div className="flex items-center gap-2 bg-amber-500/10 border border-amber-500/30 rounded p-2 mt-2">
            <AlertTriangle className="w-3 h-3 text-amber-400 shrink-0" />
            <span className="text-[10px] text-amber-400 font-mono">
              Cooldown active: {currentLossStreak} consecutive losses
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

export default RiskGuardrailPanel;
