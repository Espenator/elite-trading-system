/**
 * KillSwitchControl - Emergency kill switch for all trading activity
 */
import React, { useState } from "react";
import { Power, AlertTriangle } from "lucide-react";

export function KillSwitchControl({ onKill, isActive = false, className = "" }) {
  const [showConfirm, setShowConfirm] = useState(false);

  const handleKillClick = () => {
    if (isActive) {
      setShowConfirm(true);
    }
  };

  const handleConfirm = () => {
    if (onKill) {
      onKill();
    }
    setShowConfirm(false);
  };

  const handleCancel = () => {
    setShowConfirm(false);
  };

  return (
    <div className={`bg-[#111827] border border-red-500/50 rounded-lg p-3 ${className}`}>
      <div className="flex items-center gap-2 mb-3 pb-2 border-b border-gray-800/50">
        <Power className="w-4 h-4 text-red-400" />
        <span className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">
          Emergency Controls
        </span>
      </div>

      {!showConfirm ? (
        <button
          onClick={handleKillClick}
          disabled={!isActive}
          className={`w-full flex items-center justify-center gap-2 px-4 py-3 rounded font-mono font-bold uppercase text-xs transition-all ${
            isActive
              ? "bg-red-500/20 border border-red-500/50 text-red-400 hover:bg-red-500/30 hover:border-red-500 cursor-pointer"
              : "bg-gray-800/50 border border-gray-700/50 text-gray-600 cursor-not-allowed"
          }`}
        >
          <Power className="w-4 h-4" />
          <span>Kill Switch</span>
        </button>
      ) : (
        <div className="space-y-2">
          <div className="flex items-start gap-2 bg-red-500/10 border border-red-500/30 rounded p-2">
            <AlertTriangle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
            <div className="text-[10px] text-red-400 font-mono">
              This will immediately halt all trading activity and cancel pending orders. Confirm?
            </div>
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleConfirm}
              className="flex-1 bg-red-500/20 border border-red-500/50 text-red-400 hover:bg-red-500/30 px-3 py-2 rounded font-mono font-bold uppercase text-[10px] transition-all"
            >
              Confirm Kill
            </button>
            <button
              onClick={handleCancel}
              className="flex-1 bg-gray-800/50 border border-gray-600/50 text-gray-400 hover:bg-gray-700/50 px-3 py-2 rounded font-mono font-bold uppercase text-[10px] transition-all"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      <div className="mt-3 pt-2 border-t border-gray-800/50">
        <div className="flex items-center justify-between text-[10px]">
          <span className="text-gray-400">System Status</span>
          <span className={`font-mono font-bold ${isActive ? "text-emerald-400" : "text-red-400"}`}>
            {isActive ? "ACTIVE" : "HALTED"}
          </span>
        </div>
      </div>
    </div>
  );
}

export default KillSwitchControl;
