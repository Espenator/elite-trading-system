/**
 * useSettings - production hook for the Settings page.
 * Fetches all settings on mount, provides save/reset/testConnection/validate helpers.
 * Matches the corrected settings_routes.py API:
 *   GET  /api/v1/settings                  - all settings (nested by category)
 *   PUT  /api/v1/settings                  - bulk update
 *   PUT  /api/v1/settings/{category}       - update one category
 *   POST /api/v1/settings/reset/{category} - reset category to defaults
 *   POST /api/v1/settings/validate         - validate API key
 *   POST /api/v1/settings/test-connection  - test live connection
 *   GET  /api/v1/settings/export           - export JSON
 *   POST /api/v1/settings/import           - import JSON
 */
import { useState, useEffect, useCallback } from "react";
import { getApiUrl } from "../config/api";

const BASE = () => getApiUrl("settings");

export function useSettings() {
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [dirty, setDirty] = useState(false);
  const [connectionResults, setConnectionResults] = useState({});

  // ── Fetch all settings ──────────────────────────────────────
  const fetchSettings = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(BASE(), { cache: "no-store" });
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

  // ── Update a single field inside a category ─────────────────
  // updateField("dataSources", "alpacaApiKey", "NEW_KEY")
  const updateField = useCallback((category, key, value) => {
    setSettings((prev) => ({
      ...prev,
      [category]: { ...(prev?.[category] ?? {}), [key]: value },
    }));
    setDirty(true);
  }, []);

  // ── Save one category (PUT /settings/{category}) ─────────────
  const saveCategory = useCallback(async (category) => {
    setSaving(true);
    try {
      const payload = settings?.[category] ?? {};
      const res = await fetch(`${BASE()}/${category}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      setSettings((prev) => ({ ...prev, [category]: json }));
      setDirty(false);
      return json;
    } catch (err) {
      setError(err);
      throw err;
    } finally {
      setSaving(false);
    }
  }, [settings]);

  // ── Save all categories (PUT /settings) ───────────────────
  const saveAllSettings = useCallback(async () => {
    setSaving(true);
    try {
      const res = await fetch(BASE(), {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(settings),
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

  // ── Reset one category (POST /settings/reset/{category}) ──────
  const resetCategory = useCallback(async (category) => {
    try {
      const res = await fetch(`${BASE()}/reset/${category}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      setSettings((prev) => ({ ...prev, [category]: json }));
      return json;
    } catch (err) {
      setError(err);
      throw err;
    }
  }, []);

  // ── Validate a single API key ─────────────────────────────
  const validateKey = useCallback(async (provider, apiKey, secretKey = "") => {
    try {
      const res = await fetch(`${BASE()}/validate`, {
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

  // ── Test connection to a data source ───────────────────────
  const testConnection = useCallback(async (source) => {
    setConnectionResults((prev) => ({ ...prev, [source]: { testing: true } }));
    try {
      const res = await fetch(`${BASE()}/test-connection`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const result = await res.json();
      setConnectionResults((prev) => ({ ...prev, [source]: result }));
      return result;
    } catch (err) {
      const fail = { valid: false, source, message: err.message, testing: false };
      setConnectionResults((prev) => ({ ...prev, [source]: fail }));
      return fail;
    }
  }, []);

  // ── Export settings ────────────────────────────────────────
  const exportSettings = useCallback(async () => {
    const res = await fetch(`${BASE()}/export`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  }, []);

  // ── Import settings ────────────────────────────────────────
  const importSettings = useCallback(async (payload) => {
    const res = await fetch(`${BASE()}/import`, {
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
    saving,
    error,
    dirty,
    connectionResults,
    updateField,
    saveCategory,
    saveAllSettings,
    resetCategory,
    validateKey,
    testConnection,
    exportSettings,
    importSettings,
    refetch: fetchSettings,
  };
}
