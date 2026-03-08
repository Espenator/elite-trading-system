/**
 * useOperatorCockpit - Shared state management for operator cockpit
 * Provides trading mode, execution authority, Alpaca status, risk policy, and auto state
 */
import { useState, useEffect, useCallback } from "react";
import { getApiUrl, getAuthHeaders } from "../config/api";
import ws from "../services/websocket";

export function useOperatorCockpit() {
  // Core operator state
  const [tradingMode, setTradingMode] = useState("Manual"); // Manual or Auto
  const [executionAuthority, setExecutionAuthority] = useState("human"); // human or system
  const [autoState, setAutoState] = useState("armed"); // armed, active, paused, blocked
  const [alpacaStatus, setAlpacaStatus] = useState({
    connected: false,
    accountType: "paper",
    status: "disconnected",
  });

  // Risk policy state
  const [riskPolicy, setRiskPolicy] = useState({
    maxRiskPerTrade: 2.0,
    maxOpenPositions: 5,
    portfolioHeat: 0,
    maxPortfolioHeat: 10.0,
    dailyLossCap: 500,
    weeklyDrawdownCap: 1000,
    stopLossRequired: true,
    takeProfitPolicy: "trail",
    cooldownAfterLossStreak: 3,
    currentLossStreak: 0,
  });

  // Block reasons for trade restrictions
  const [blockReasons, setBlockReasons] = useState([]);

  // System active state
  const [isSystemActive, setIsSystemActive] = useState(true);

  // ── Fetch operator status from backend ──────────────────────────
  const fetchOperatorStatus = useCallback(async () => {
    try {
      const res = await fetch(getApiUrl("operator-status"), {
        headers: getAuthHeaders(),
        cache: "no-store",
      });
      if (!res.ok) {
        console.warn("Failed to fetch operator status:", res.status);
        return;
      }
      const data = await res.json();

      // Update state from backend
      if (data.tradingMode) {
        setTradingMode(data.tradingMode);
      }
      if (data.executionAuthority) {
        setExecutionAuthority(data.executionAuthority);
      }
      if (data.autoState) {
        setAutoState(data.autoState);
      }
      if (data.alpacaStatus) {
        setAlpacaStatus(data.alpacaStatus);
      }
      if (data.riskPolicy) {
        setRiskPolicy(data.riskPolicy);
      }
      if (data.blockReasons) {
        setBlockReasons(data.blockReasons);
      }
      if (typeof data.isSystemActive === "boolean") {
        setIsSystemActive(data.isSystemActive);
      }
    } catch (err) {
      console.error("Error fetching operator status:", err);
    }
  }, []);

  // ── Fetch settings for risk policy ──────────────────────────────
  const fetchSettings = useCallback(async () => {
    try {
      const res = await fetch(getApiUrl("settings"), {
        headers: getAuthHeaders(),
        cache: "no-store",
      });
      if (!res.ok) return;
      const data = await res.json();

      // Extract risk policy from settings
      if (data.risk) {
        setRiskPolicy((prev) => ({
          ...prev,
          maxRiskPerTrade: data.risk.maxRiskPerTrade ?? prev.maxRiskPerTrade,
          maxOpenPositions: data.risk.maxOpenPositions ?? prev.maxOpenPositions,
          maxPortfolioHeat: data.risk.maxPortfolioHeat ?? prev.maxPortfolioHeat,
          dailyLossCap: data.risk.dailyLossCap ?? prev.dailyLossCap,
          weeklyDrawdownCap: data.risk.weeklyDrawdownCap ?? prev.weeklyDrawdownCap,
          stopLossRequired: data.risk.stopLossRequired ?? prev.stopLossRequired,
          takeProfitPolicy: data.risk.takeProfitPolicy ?? prev.takeProfitPolicy,
          cooldownAfterLossStreak: data.risk.cooldownAfterLossStreak ?? prev.cooldownAfterLossStreak,
        }));
      }

      // Extract trading mode
      if (data.trading?.mode) {
        setTradingMode(data.trading.mode);
      }

      // Extract Alpaca status
      if (data.dataSources?.alpacaApiKey) {
        setAlpacaStatus((prev) => ({
          ...prev,
          connected: true,
          status: "connected",
        }));
      }
    } catch (err) {
      console.error("Error fetching settings:", err);
    }
  }, []);

  // ── Subscribe to WebSocket updates ───────────────────────────────
  useEffect(() => {
    const handleOperatorUpdate = (data) => {
      if (data.tradingMode) setTradingMode(data.tradingMode);
      if (data.executionAuthority) setExecutionAuthority(data.executionAuthority);
      if (data.autoState) setAutoState(data.autoState);
      if (data.alpacaStatus) setAlpacaStatus((prev) => ({ ...prev, ...data.alpacaStatus }));
      if (data.riskPolicy) setRiskPolicy((prev) => ({ ...prev, ...data.riskPolicy }));
      if (data.blockReasons) setBlockReasons(data.blockReasons);
      if (typeof data.isSystemActive === "boolean") setIsSystemActive(data.isSystemActive);
    };

    const handleRiskUpdate = (data) => {
      if (data.portfolioHeat !== undefined) {
        setRiskPolicy((prev) => ({ ...prev, portfolioHeat: data.portfolioHeat }));
      }
      if (data.currentLossStreak !== undefined) {
        setRiskPolicy((prev) => ({ ...prev, currentLossStreak: data.currentLossStreak }));
      }
    };

    ws.subscribe("operator.status", handleOperatorUpdate);
    ws.subscribe("risk.update", handleRiskUpdate);

    return () => {
      ws.unsubscribe("operator.status", handleOperatorUpdate);
      ws.unsubscribe("risk.update", handleRiskUpdate);
    };
  }, []);

  // ── Initial fetch ────────────────────────────────────────────────
  useEffect(() => {
    fetchOperatorStatus();
    fetchSettings();

    // Poll every 30 seconds
    const interval = setInterval(() => {
      fetchOperatorStatus();
    }, 30000);

    return () => clearInterval(interval);
  }, [fetchOperatorStatus, fetchSettings]);

  // ── Actions ──────────────────────────────────────────────────────
  const switchMode = useCallback(async (newMode) => {
    try {
      const res = await fetch(getApiUrl("operator-status/mode"), {
        method: "PUT",
        headers: { "Content-Type": "application/json", ...getAuthHeaders() },
        body: JSON.stringify({ mode: newMode }),
      });
      if (res.ok) {
        const data = await res.json();
        setTradingMode(data.tradingMode || newMode);
        setAutoState(data.autoState || "armed");
      }
    } catch (err) {
      console.error("Error switching mode:", err);
    }
  }, []);

  const setAutoStateAction = useCallback(async (newState) => {
    try {
      const res = await fetch(getApiUrl("operator-status/auto-state"), {
        method: "PUT",
        headers: { "Content-Type": "application/json", ...getAuthHeaders() },
        body: JSON.stringify({ state: newState }),
      });
      if (res.ok) {
        const data = await res.json();
        setAutoState(data.autoState || newState);
      }
    } catch (err) {
      console.error("Error setting auto state:", err);
    }
  }, []);

  const triggerKillSwitch = useCallback(async () => {
    try {
      const res = await fetch(getApiUrl("operator-status/kill-switch"), {
        method: "POST",
        headers: { "Content-Type": "application/json", ...getAuthHeaders() },
        body: JSON.stringify({}),
      });
      if (res.ok) {
        setIsSystemActive(false);
        setAutoState("blocked");
        setTradingMode("Manual");
      }
    } catch (err) {
      console.error("Error triggering kill switch:", err);
    }
  }, []);

  return {
    // State
    tradingMode,
    executionAuthority,
    autoState,
    alpacaStatus,
    riskPolicy,
    blockReasons,
    isSystemActive,

    // Actions
    switchMode,
    setAutoState: setAutoStateAction,
    triggerKillSwitch,
    refreshStatus: fetchOperatorStatus,
  };
}

export default useOperatorCockpit;
