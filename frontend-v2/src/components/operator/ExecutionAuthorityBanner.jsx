/**
 * ExecutionAuthorityBanner - Display who has execution authority and current state
 * Shows Manual mode = human decides, Auto mode = system may execute (with clear state)
 */
import React from "react";
import { Shield, User, Zap, AlertTriangle, Pause, Lock } from "lucide-react";

export function ExecutionAuthorityBanner({ mode = "Manual", autoState = "armed", className = "" }) {
  const isAuto = mode === "Auto" || mode === "AUTO";

  // Auto states: armed, active, paused, blocked
  const autoStateConfig = {
    armed: {
      icon: Shield,
      color: "text-emerald-400",
      bgColor: "bg-emerald-500/10",
      borderColor: "border-emerald-500/30",
      label: "Armed",
      description: "System ready to execute paper trades",
    },
    active: {
      icon: Zap,
      color: "text-cyan-400",
      bgColor: "bg-cyan-500/10",
      borderColor: "border-cyan-500/30",
      label: "Active",
      description: "System actively placing paper trades",
    },
    paused: {
      icon: Pause,
      color: "text-amber-400",
      bgColor: "bg-amber-500/10",
      borderColor: "border-amber-500/30",
      label: "Paused",
      description: "Auto execution paused by user",
    },
    blocked: {
      icon: Lock,
      color: "text-red-400",
      bgColor: "bg-red-500/10",
      borderColor: "border-red-500/30",
      label: "Blocked",
      description: "Execution blocked by risk controls",
    },
  };

  const currentAutoState = autoStateConfig[autoState] || autoStateConfig.armed;
  const Icon = isAuto ? currentAutoState.icon : User;

  return (
    <div
      className={`bg-[#111827] border rounded-lg p-3 ${
        isAuto ? currentAutoState.borderColor : "border-gray-600/50"
      } ${className}`}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div
            className={`flex items-center justify-center w-10 h-10 rounded-lg ${
              isAuto ? currentAutoState.bgColor : "bg-gray-800/50"
            }`}
          >
            <Icon className={`w-5 h-5 ${isAuto ? currentAutoState.color : "text-gray-400"}`} />
          </div>
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">
                Execution Authority
              </span>
              {isAuto && (
                <span
                  className={`text-[10px] font-mono font-bold uppercase px-2 py-0.5 rounded ${currentAutoState.bgColor} ${currentAutoState.color}`}
                >
                  {currentAutoState.label}
                </span>
              )}
            </div>
            <p className="text-[10px] text-gray-400 font-mono">
              {isAuto ? currentAutoState.description : "Human operator makes all trade decisions"}
            </p>
          </div>
        </div>
        <div className="text-right">
          <div className="text-xs text-gray-400 mb-1">Mode</div>
          <div
            className={`text-sm font-mono font-bold ${
              isAuto ? "text-cyan-400" : "text-gray-300"
            }`}
          >
            {isAuto ? "AUTO" : "MANUAL"}
          </div>
        </div>
      </div>
    </div>
  );
}

export default ExecutionAuthorityBanner;
