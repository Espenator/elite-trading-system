/**
 * useSentiment - Production hook for Sentiment Intelligence page.
 * Fetches /summary (mood, sources, signals, heatmap, divergences)
 * and /history (rolling timeline), with 30s polling + WebSocket live updates.
 */
import { useState, useEffect, useCallback, useRef } from "react";
import { getApiUrl } from "../config/api";
import ws from "../services/websocket";
import log from "@/utils/logger";

const POLL_MS = 30000;

export function useSentiment() {
  const [summary, setSummary] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const mountedRef = useRef(true);

  const fetchSummary = useCallback(async () => {
    try {
      const url = getApiUrl("sentiment") + "/summary";
      const res = await fetch(url);
      if (!res.ok) throw new Error(`Summary ${res.status}`);
      const data = await res.json();
      if (mountedRef.current) {
        setSummary(data);
        setError(null);
        setLastUpdated(new Date());
      }
    } catch (err) {
      if (mountedRef.current) setError(err);
    }
  }, []);

  const fetchHistory = useCallback(async (hours = 24) => {
    try {
      const url = getApiUrl("sentiment") + `/history?hours=${hours}`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(`History ${res.status}`);
      const data = await res.json();
      if (mountedRef.current) setHistory(data.points || []);
    } catch (err) {
      log.error("Sentiment history error:", err);
    }
  }, []);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    await Promise.all([fetchSummary(), fetchHistory()]);
    if (mountedRef.current) setLoading(false);
  }, [fetchSummary, fetchHistory]);

  // Initial fetch + polling
  useEffect(() => {
    mountedRef.current = true;
    fetchAll();
    const timer = setInterval(fetchAll, POLL_MS);
    return () => {
      mountedRef.current = false;
      clearInterval(timer);
    };
  }, [fetchAll]);

  // WebSocket live updates
  useEffect(() => {
    ws.connect();
    const unsub = ws.on("sentiment", (msg) => {
      if (!mountedRef.current) return;
      if (msg?.type === "sentiment_updated" || msg?.type === "source_health_updated") {
        fetchSummary();
      }
      if (msg?.type === "sentiment_removed") {
        fetchSummary();
      }
    });
    return () => unsub();
  }, [fetchSummary]);

  return {
    summary,
    history,
    loading,
    error,
    lastUpdated,
    refetch: fetchAll,
    refetchHistory: fetchHistory,
    // Convenience accessors
    mood: summary?.mood || null,
    sourceHealth: summary?.sourceHealth || [],
    divergences: summary?.divergences || [],
    heatmap: summary?.heatmap || [],
    signals: summary?.signals || [],
    stats: summary?.stats || {},
  };
}
