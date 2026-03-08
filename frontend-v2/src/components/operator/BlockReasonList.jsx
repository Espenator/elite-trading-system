/**
 * BlockReasonList - Display why trades are being blocked, resized, or exited
 */
import React from "react";
import { XCircle, AlertCircle, TrendingDown, Shield } from "lucide-react";

export function BlockReasonList({ reasons = [], className = "" }) {
  if (!reasons || reasons.length === 0) {
    return (
      <div className={`bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-lg p-3 ${className}`}>
        <div className="flex items-center gap-2 mb-2">
          <Shield className="w-4 h-4 text-emerald-400" />
          <span className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">
            Trade Status
          </span>
        </div>
        <div className="text-[10px] text-emerald-400 font-mono">All systems clear</div>
      </div>
    );
  }

  const getIcon = (severity) => {
    switch (severity) {
      case "block":
        return XCircle;
      case "warning":
        return AlertCircle;
      case "resize":
        return TrendingDown;
      default:
        return AlertCircle;
    }
  };

  const getColor = (severity) => {
    switch (severity) {
      case "block":
        return "text-red-400 bg-red-500/10 border-red-500/30";
      case "warning":
        return "text-amber-400 bg-amber-500/10 border-amber-500/30";
      case "resize":
        return "text-cyan-400 bg-cyan-500/10 border-cyan-500/30";
      default:
        return "text-gray-400 bg-gray-500/10 border-gray-500/30";
    }
  };

  return (
    <div className={`bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded-lg p-3 ${className}`}>
      <div className="flex items-center gap-2 mb-2">
        <XCircle className="w-4 h-4 text-red-400" />
        <span className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">
          Trade Restrictions
        </span>
      </div>

      <div className="space-y-2">
        {reasons.map((reason, idx) => {
          const Icon = getIcon(reason.severity);
          const colorClass = getColor(reason.severity);

          return (
            <div
              key={idx}
              className={`flex items-start gap-2 border rounded p-2 ${colorClass}`}
            >
              <Icon className="w-3 h-3 mt-0.5 shrink-0" />
              <div className="flex-1 min-w-0">
                <div className="text-[10px] font-mono font-bold mb-0.5">
                  {reason.title || "Restriction Applied"}
                </div>
                <div className="text-[9px] text-gray-300 font-mono">
                  {reason.message || "No details provided"}
                </div>
                {reason.symbol && (
                  <div className="text-[9px] text-gray-500 font-mono mt-1">
                    Symbol: {reason.symbol}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default BlockReasonList;
