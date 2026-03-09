/**
 * useWebSocketData - Hybrid hook for real-time data via WebSocket with polling fallback.
 *
 * This hook replaces useApi for endpoints that support WebSocket channels.
 * It subscribes to a WebSocket channel for real-time updates and uses polling
 * as a fallback when the WebSocket is disconnected.
 *
 * @param {string} channel - WebSocket channel name (e.g., 'signals', 'risk', 'agents')
 * @param {string} endpoint - API endpoint for initial fetch and fallback polling
 * @param {object} options - Configuration options
 * @param {number} options.fallbackPollMs - Polling interval when WebSocket disconnected (0 = no polling)
 * @param {boolean} options.enabled - Enable/disable the hook
 * @param {function} options.transform - Transform function for WebSocket messages
 * @param {boolean} options.fetchOnMount - Fetch initial data on mount (default: true)
 *
 * @returns {object} { data, loading, error, isStale, lastUpdated, refetch, isWebSocketActive }
 */
import { useState, useEffect, useCallback, useRef } from "react";
import ws from "../services/websocket";
import { getApiUrl, getAuthHeaders } from "../config/api";

export function useWebSocketData(channel, endpoint, options = {}) {
  const {
    fallbackPollMs = 30000,
    enabled = true,
    transform = null,
    fetchOnMount = true,
  } = options;

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(enabled && fetchOnMount);
  const [error, setError] = useState(null);
  const [isStale, setIsStale] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [isWebSocketActive, setIsWebSocketActive] = useState(false);
  const abortRef = useRef(null);

  // Fetch data from API endpoint
  const fetchData = useCallback(async () => {
    const url = getApiUrl(endpoint);
    if (!url) {
      setError(new Error(`Unknown endpoint: ${endpoint}`));
      setLoading(false);
      return;
    }

    // Abort previous request
    if (abortRef.current) {
      abortRef.current.abort();
    }
    abortRef.current = new AbortController();

    try {
      const response = await fetch(url, {
        headers: getAuthHeaders(),
        signal: abortRef.current.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const json = await response.json();
      const result = transform ? transform(json) : json;

      setData(result);
      setError(null);
      setIsStale(false);
      setLastUpdated(Date.now());
    } catch (err) {
      if (err.name === 'AbortError') return;
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [endpoint, transform]);

  // WebSocket message handler
  const handleWebSocketMessage = useCallback((message) => {
    const result = transform ? transform(message) : message;
    setData(result);
    setError(null);
    setIsStale(false);
    setLastUpdated(Date.now());
    setLoading(false);
  }, [transform]);

  // WebSocket connection status handler
  const handleConnectionStatus = useCallback((status) => {
    if (status.type === 'connected') {
      setIsWebSocketActive(true);
      setIsStale(false);
    } else if (status.type === 'disconnected') {
      setIsWebSocketActive(false);
      setIsStale(true);
    }
  }, []);

  // Set up WebSocket subscription
  useEffect(() => {
    if (!enabled || !channel) return;

    // Subscribe to channel for data updates
    const unsubscribeChannel = ws.on(channel, handleWebSocketMessage);

    // Subscribe to wildcard for connection status
    const unsubscribeStatus = ws.on("*", handleConnectionStatus);

    // Connect WebSocket if not already connected
    if (!ws.isConnected()) {
      ws.connect();
    }

    // Set initial WebSocket status
    setIsWebSocketActive(ws.isConnected());

    return () => {
      unsubscribeChannel();
      unsubscribeStatus();
    };
  }, [channel, enabled, handleWebSocketMessage, handleConnectionStatus]);

  // Initial fetch on mount
  useEffect(() => {
    if (!enabled || !fetchOnMount) return;
    fetchData();
  }, [enabled, fetchOnMount, fetchData]);

  // Fallback polling when WebSocket is disconnected
  useEffect(() => {
    if (!enabled || fallbackPollMs <= 0) return;
    if (isWebSocketActive) return; // Skip polling when WebSocket is active

    const id = setInterval(() => {
      fetchData();
    }, fallbackPollMs);

    return () => clearInterval(id);
  }, [enabled, fallbackPollMs, isWebSocketActive, fetchData]);

  // Page visibility handling - refetch on visibility change
  useEffect(() => {
    if (!enabled) return;

    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible' && !isWebSocketActive) {
        fetchData();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  }, [enabled, isWebSocketActive, fetchData]);

  return {
    data,
    loading,
    error,
    isStale,
    lastUpdated,
    refetch: fetchData,
    isWebSocketActive,
  };
}

/**
 * Convenience hook for common channels with sensible defaults.
 */

export function useSignalsWebSocket(options = {}) {
  return useWebSocketData('signals', 'signals', {
    fallbackPollMs: 15000,
    ...options,
  });
}

export function useRiskWebSocket(options = {}) {
  return useWebSocketData('risk', 'risk', {
    fallbackPollMs: 30000,
    ...options,
  });
}

export function useAgentsWebSocket(options = {}) {
  return useWebSocketData('agents', 'agents', {
    fallbackPollMs: 30000,
    ...options,
  });
}

export function useTradesWebSocket(options = {}) {
  return useWebSocketData('trades', 'portfolio', {
    fallbackPollMs: 15000,
    ...options,
  });
}

export function useSentimentWebSocket(options = {}) {
  return useWebSocketData('sentiment', 'sentiment', {
    fallbackPollMs: 30000,
    ...options,
  });
}

export function useKellyWebSocket(options = {}) {
  return useWebSocketData('kelly', 'kellyRanked', {
    fallbackPollMs: 30000,
    ...options,
  });
}

export function useMarketWebSocket(options = {}) {
  return useWebSocketData('market', 'market', {
    fallbackPollMs: 5000,
    ...options,
  });
}

export function useSwarmWebSocket(options = {}) {
  return useWebSocketData('swarm', 'swarmTopology', {
    fallbackPollMs: 30000,
    ...options,
  });
}

export function useCouncilWebSocket(options = {}) {
  return useWebSocketData('council', 'council', {
    fallbackPollMs: 30000,
    ...options,
  });
}

export function usePatternsWebSocket(options = {}) {
  return useWebSocketData('patterns', 'patterns', {
    fallbackPollMs: 30000,
    ...options,
  });
}

export function useDataSourcesWebSocket(options = {}) {
  return useWebSocketData('datasources', 'dataSources', {
    fallbackPollMs: 30000,
    ...options,
  });
}
