/**
 * useSettings – production hook for the Settings page.
 * Fetches all settings on mount, provides save/reset/testConnection/validate helpers.
 * Uses the same useApi pattern + getApiUrl from config/api.js.
 */
import { useState, useEffect, useCallback } from "react";
import { getApiUrl } from "../config/api";

export function useSettings() {
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [connectionResults, setConnectionResults] = useState({});

  // ── Fetch all settings ──────────────────────────────────────
  const fetchSettings = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(getApiUrl("settings"), { cache: "no-store" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      setSettings(json);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchSettings(); }, [fetchSettings]);

  // ── Local field change (marks dirty) ────────────────────────
  const updateField = useCallback((key, value) => {
    setSettings((prev) => ({ ...prev, [key]: value }));
    setDirty(true);
  }, []);

  // ── Save (PUT all settings) ─────────────────────────────────
  const saveSettings = useCallback(async (overrides) => {
    setSaving(true);
    try {
      const payload = overrides || settings;
      const res = await fetch(getApiUrl("settings"), {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      setSettings(json);
      setDirty(false);
      return json;
    } catch (err) {
      setError(err);
      throw err;
    } finally {
      setSaving(false);
    }
  }, [settings]);

  // ── Reset to defaults ───────────────────────────────────────
  const resetSettings = useCallback(async (category) => {
    try {
      const url = `${getApiUrl("settings")}/reset`;
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(category ? { category } : {}),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      setSettings(json);
      setDirty(false);
      return json;
    } catch (err) {
      setError(err);
      throw err;
    }
  }, []);

  // ── Test connection ─────────────────────────────────────────
  const testConnection = useCallback(async (source) => {
    setConnectionResults((prev) => ({ ...prev, [source]: { testing: true } }));
    try {
      const url = `${getApiUrl("settings")}/test-connection`;
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const result = await res.json();
      setConnectionResults((prev) => ({ ...prev, [source]: result }));
      return result;
    } catch (err) {
      const fail = { valid: false, source, message: err.message };
      setConnectionResults((prev) => ({ ...prev, [source]: fail }));
      return fail;
    }
  }, []);

  // ── Validate a single API key ───────────────────────────────
  const validateKey = useCallback(async (provider, apiKey, secretKey) => {
    try {
      const url = `${getApiUrl("settings")}/validate`;
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ provider, apiKey, secretKey }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (err) {
      return { valid: false, provider, message: err.message };
    }
  }, []);

  // ── Export / Import ─────────────────────────────────────────
  const exportSettings = useCallback(async () => {
    const url = `${getApiUrl("settings")}/export`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  }, []);

  const importSettings = useCallback(async (payload) => {
    const url = `${getApiUrl("settings")}/import`;
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const json = await res.json();
    setSettings(json);
    setDirty(false);
    return json;
  }, []);

  return {
    settings,
    loading,
    error,
    saving,
    dirty,
    connectionResults,
    updateField,
    saveSettings,
    resetSettings,
    testConnection,
    validateKey,
    exportSettings,
    importSettings,
    refetch: fetchSettings,
  };
}
