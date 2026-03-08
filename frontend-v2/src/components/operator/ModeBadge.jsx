/**
 * ModeBadge - Display current trading mode (Manual or Auto)
 * Product truth: Only 2 modes exist - Manual and Auto
 */
import React from "react";
import { Activity, User } from "lucide-react";

export function ModeBadge({ mode = "Manual", size = "md", className = "" }) {
  const isAuto = mode === "Auto" || mode === "AUTO";
  const isManual = mode === "Manual" || mode === "MANUAL";

  if (!isAuto && !isManual) {
    console.warn(`ModeBadge: Invalid mode "${mode}". Using Manual as fallback.`);
  }

  const actualMode = isAuto ? "Auto" : "Manual";

  const sizeClasses = {
    sm: "text-[9px] px-1.5 py-0.5 gap-1",
    md: "text-[10px] px-2 py-1 gap-1.5",
    lg: "text-xs px-3 py-1.5 gap-2",
  };

  const iconSizes = {
    sm: "w-2.5 h-2.5",
    md: "w-3 h-3",
    lg: "w-3.5 h-3.5",
  };

  return (
    <div
      className={`inline-flex items-center font-mono font-bold uppercase tracking-wider rounded ${sizeClasses[size]} ${
        actualMode === "Auto"
          ? "bg-gradient-to-r from-cyan-500/20 to-emerald-500/20 border border-cyan-500/50 text-cyan-400"
          : "bg-gray-800/50 border border-gray-600/50 text-gray-300"
      } ${className}`}
    >
      {actualMode === "Auto" ? (
        <Activity className={`${iconSizes[size]} animate-pulse`} />
      ) : (
        <User className={iconSizes[size]} />
      )}
      <span>{actualMode}</span>
    </div>
  );
}

export default ModeBadge;
