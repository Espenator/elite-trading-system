/**
 * AccountStatusCard - Display Alpaca paper trading account connection status
 */
import React from "react";
import { CheckCircle2, XCircle, Loader2, Wifi } from "lucide-react";

export function AccountStatusCard({ status = "disconnected", accountType = "paper", className = "" }) {
  const isConnected = status === "connected" || status === "active";
  const isConnecting = status === "connecting";
  const isDisconnected = status === "disconnected" || status === "inactive";

  return (
    <div
      className={`bg-[#111827] border rounded-lg p-3 ${
        isConnected
          ? "border-emerald-500/50"
          : isConnecting
            ? "border-cyan-500/50"
            : "border-red-500/50"
      } ${className}`}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Wifi className={`w-4 h-4 ${isConnected ? "text-emerald-400" : "text-gray-500"}`} />
          <span className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">
            Alpaca Account
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          {isConnecting && <Loader2 className="w-3 h-3 animate-spin text-cyan-400" />}
          {isConnected && <CheckCircle2 className="w-3 h-3 text-emerald-400" />}
          {isDisconnected && <XCircle className="w-3 h-3 text-red-400" />}
          <span
            className={`text-[10px] font-mono font-bold uppercase ${
              isConnected ? "text-emerald-400" : isConnecting ? "text-cyan-400" : "text-red-400"
            }`}
          >
            {isConnected ? "Connected" : isConnecting ? "Connecting" : "Disconnected"}
          </span>
        </div>
      </div>

      <div className="space-y-1 text-[10px]">
        <div className="flex items-center justify-between">
          <span className="text-gray-400">Account Type:</span>
          <span className="text-white font-mono uppercase font-bold">{accountType}</span>
        </div>
        {isConnected && (
          <>
            <div className="flex items-center justify-between">
              <span className="text-gray-400">Status:</span>
              <span className="text-emerald-400 font-mono">Active</span>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default AccountStatusCard;
