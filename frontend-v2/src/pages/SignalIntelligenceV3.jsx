import React, {
  useState,
  useEffect,
  useCallback,
  useRef,
  useMemo,
} from "react";
import { useSearchParams } from "react-router-dom";
import { useApi } from "../hooks/useApi";
import { getApiUrl, getAuthHeaders } from "../config/api";
import log from "@/utils/logger";
import { toast } from "react-toastify";
import { createChart, CrosshairMode, LineStyle } from "lightweight-charts";
import {
  Cpu,
  Zap,
  TrendingUp,
  TrendingDown,
  Shield,
  Database,
  BarChart2,
  Globe,
  RefreshCw,
  Rocket,
  FileText,
  Download,
  Share2,
  Search,
  Lock,
  Unlock,
  Save,
  Wifi,
  Target,
  Upload,
} from "lucide-react";
import ws from "../services/websocket";
import Slider from "../components/ui/Slider";

// ============================================================================
// No hardcoded fallback agents — real API data only
const FALLBACK_CORE_AGENTS = [];
const FALLBACK_EXTENDED_AGENTS = [];

/** Parse API agents response into { core, extended, all } using fallbacks */
function parseAgentsFromApi(apiData) {
  if (!apiData) return null;
  const list = Array.isArray(apiData)
    ? apiData
    : apiData?.agents
      ? apiData.agents
      : apiData?.data
        ? apiData.data
        : null;
  if (!list || list.length === 0) return null;
  const normalize = (a) => ({
    id: a.id || a.agent_id || a.name?.toLowerCase().replace(/\s+/g, "_"),
    name: a.name || a.label || a.id,
    type: a.type || a.role || "Swarm",
    defaultWeight: a.weight ?? a.defaultWeight ?? a.default_weight ?? 50,
    status: a.status || a.state || null,
  });
  const all = list.map(normalize);
  const coreTypes = new Set(["Core", "Risk", "Engine", "Orchestrator"]);
  const core = all.filter((a) => coreTypes.has(a.type));
  const extended = all.filter((a) => !coreTypes.has(a.type));
  return { core, extended, all };
}

const SCANNERS = [
  { id: "daily", name: "Daily Scanner", pct: 100 },
  { id: "finviz", name: "Finviz Screener", pct: 70 },
  { id: "amd", name: "AMD Detector", pct: 85 },
  { id: "pullback", name: "Pullback Detector", pct: 90 },
  { id: "rebound", name: "Rebound Detector", pct: 80 },
  { id: "squeeze", name: "Short Squeeze", pct: 65 },
  { id: "tech", name: "Technical Checker", pct: 75 },
  { id: "earnings", name: "Earnings Calendar", pct: 50 },
  { id: "fomc", name: "FOMC Expected", pct: 100 },
  { id: "sector", name: "Sector Rotation", pct: 85 },
  { id: "whale", name: "Whale Flow", pct: 95 },
  { id: "uw", name: "UW Agents", pct: 90 },
  { id: "tv_watch", name: "TV Watchlist", pct: 60 },
  { id: "tv_refresh", name: "TV Session Refresh", pct: 40 },
];

const INTEL_MODULES = [
  { id: "intel_hmm", name: "HMM Regime", defaultWeight: 100 },
  { id: "intel_llm", name: "LLM Client", defaultWeight: 85 },
  { id: "intel_lora", name: "LoRA Trainer", defaultWeight: 70 },
  { id: "intel_macro", name: "Macro Context", defaultWeight: 95 },
  { id: "intel_mem1", name: "Memory v1", defaultWeight: 60 },
  { id: "intel_mem3", name: "Memory v3", defaultWeight: 90 },
  { id: "intel_mtf", name: "MTF Alignment", defaultWeight: 85 },
  { id: "intel_perf", name: "Perf Tracker", defaultWeight: 100 },
  { id: "intel_regime", name: "Regime Detector", defaultWeight: 100 },
];

const ML_MODELS = [
  {
    id: "ml_lstm",
    name: "LSTM Daily",
    version: "v4.2.1",
    defaultStatus: "Ready",
  },
  {
    id: "ml_xgb",
    name: "XGBoost GPU",
    version: "v2.8.0",
    defaultStatus: "Ready",
  },
  {
    id: "ml_river",
    name: "River Online",
    version: "v1.1.5",
    defaultStatus: "Training",
  },
  {
    id: "ml_infer",
    name: "Inference Engine",
    version: "v3.0.0",
    defaultStatus: "Ready",
  },
  {
    id: "ml_wfv",
    name: "Walk-Forward Val",
    version: "v1.0.2",
    defaultStatus: "Idle",
  },
  {
    id: "ml_pipe",
    name: "ML Pipeline",
    version: "v5.1.0",
    defaultStatus: "Ready",
  },
];

const DATA_SOURCES = [
  { id: "ds_twitter", name: "Twitter/X API", connected: false },
  { id: "ds_reddit", name: "Reddit API", connected: false },
  { id: "ds_news", name: "NewsAPI", connected: false },
  { id: "ds_benzinga", name: "Benzinga Pro", connected: false },
  { id: "ds_rss", name: "RSS Aggregator", connected: false },
  { id: "ds_discord", name: "Discord Listener", connected: true },
  { id: "ds_youtube", name: "YouTube Agent", connected: false, weight: 1 },
];

const API_ENDPOINTS = [
  "agents",
  "alerts",
  "backtest",
  "data_sources",
  "flywheel",
  "logs",
  "market",
  "ml_brain",
  "openclaw",
  "orders",
  "patterns",
  "performance",
  "portfolio",
  "quotes",
  "risk",
  "risk_shield",
  "sentiment",
  "settings",
  "signals",
  "status",
  "stocks",
  "strategy",
  "system",
  "training",
  "youtube_knowledge",
  "websocket",
  "auth_bridge",
  "ext_webhooks",
];

const SHAP_FACTORS = [
  "UN Options Flow",
  "Velez Score",
  "Volume Surge",
  "Whale Flow",
  "RSI Divergence",
  "HTF Structure",
  "Compression",
  "Sector Momentum",
];

// ============================================================================
// REUSABLE UI COMPONENTS
// ============================================================================

const Panel = ({
  title,
  icon: Icon,
  children,
  className = "",
  headerAction = null,
}) => (
  <div
    className={`bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded overflow-hidden flex flex-col ${className}`}
  >
    <div className="px-2.5 py-1.5 border-b border-[rgba(42,52,68,0.5)] flex justify-between items-center bg-[#0B0E14] shrink-0">
      <div className="flex items-center gap-1.5">
        {Icon && <Icon className="w-3 h-3 text-[#00D9FF] shrink-0" />}
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">
          {title}
        </h3>
      </div>
      {headerAction && (
        <div className="flex items-center gap-1">{headerAction}</div>
      )}
    </div>
    <div className="p-2 flex-1 flex flex-col overflow-y-auto scrollbar-thin scrollbar-thumb-[#374151] scrollbar-track-transparent">
      {children}
    </div>
  </div>
);

const Toggle = ({ checked, onChange, size = "md", variant = "cyan" }) => {
  const h = size === "sm" ? "h-3" : "h-4";
  const w = size === "sm" ? "w-6" : "w-8";
  const dot = size === "sm" ? "w-2 h-2" : "w-3 h-3";
  const translate = size === "sm" ? "translate-x-3" : "translate-x-4";
  const bgChecked = variant === "orange" ? "bg-amber-500" : "bg-cyan-500";
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      className={`${w} ${h} rounded-full relative transition-colors duration-200 focus:outline-none shrink-0 ${checked ? bgChecked : "bg-[#374151]"}`}
    >
      <span
        className={`absolute top-0.5 left-0.5 bg-white rounded-full transition-transform duration-200 ${dot} ${checked ? translate : "translate-x-0"}`}
      />
    </button>
  );
};

// ============================================================================
// MAIN DASHBOARD COMPONENT
// ============================================================================
export default function SignalIntelligenceV3() {
  const [searchParams] = useSearchParams();
  const searchQuery = searchParams.get("q")?.toUpperCase() || "";

  // --- REAL API HOOKS (mapped to config/api.js endpoints) ---
  // useApi already has: 503 backoff (3 retries), concurrency limit (6), dedup, visibility-pause
  const { data: apiSignals, loading: sigLoading, error: sigError, refetch: refetchSignals } = useApi('signals', { pollIntervalMs: 15000 });
  const { data: apiAgents } = useApi('agents', { pollIntervalMs: 60000 });
  const { data: apiOpenclaw } = useApi('openclaw', { pollIntervalMs: 30000 });
  const { data: apiDataSources } = useApi('dataSources', { pollIntervalMs: 60000 });
  const { data: apiSentiment } = useApi('sentiment', { pollIntervalMs: 60000 });
  const { data: apiYoutube } = useApi('youtubeKnowledge', { pollIntervalMs: 120000 });
  const { data: apiTraining } = useApi('training', { pollIntervalMs: 60000 });
  const { data: apiMlBrain } = useApi('mlBrain', { pollIntervalMs: 60000 });
  const { data: apiPatterns } = useApi('patterns', { pollIntervalMs: 60000 });
  const { data: apiRisk } = useApi('risk', { pollIntervalMs: 30000 });
  const { data: apiAlerts } = useApi('alerts', { pollIntervalMs: 30000 });
  const { data: apiStatus } = useApi('status', { pollIntervalMs: 30000 });
  const { data: apiPerf } = useApi('performance', { pollIntervalMs: 60000 });
  const { data: apiMarket } = useApi('market', { pollIntervalMs: 30000 });
  const { data: apiPortfolio } = useApi('portfolio', { pollIntervalMs: 30000 });
  const { data: apiStrategy } = useApi('strategy', { pollIntervalMs: 60000 });
  const { data: apiSettings } = useApi('settings', { pollIntervalMs: 0 });

  // --- DERIVE AGENT LISTS FROM API (with hardcoded fallbacks) ---
  const parsedAgents = useMemo(
    () => parseAgentsFromApi(apiAgents),
    [apiAgents],
  );
  const CORE_AGENTS = useMemo(
    () =>
      parsedAgents?.core?.length ? parsedAgents.core : FALLBACK_CORE_AGENTS,
    [parsedAgents],
  );
  const EXTENDED_AGENTS = useMemo(
    () => parsedAgents?.extended ?? FALLBACK_EXTENDED_AGENTS,
    [parsedAgents],
  );
  const ALL_AGENTS = useMemo(
    () => (parsedAgents?.all?.length ? parsedAgents.all : FALLBACK_CORE_AGENTS),
    [parsedAgents],
  );

  // --- LOCAL STATE ---
  const [agentStates, setAgentStates] = useState({});
  const [scannerStates, setScannerStates] = useState(() =>
    SCANNERS.reduce(
      (acc, scan) => ({
        ...acc,
        [scan.id]: { active: true, pct: scan.pct, status: "green", runs: 0 },
      }),
      {},
    ),
  );
  const [intelStates, setIntelStates] = useState(() =>
    INTEL_MODULES.reduce(
      (acc, mod) => ({
        ...acc,
        [mod.id]: { active: true, weight: mod.defaultWeight, status: "green" },
      }),
      {},
    ),
  );
  const [scoringFormula, setScoringFormula] = useState({
    ocTaBlend: 60,
    tierSlamDunk: 90,
    tierStrongGo: 75,
    tierWatch: 60,
    regimeMultiplier: 1.2,
  });
  const [shapWeights, setShapWeights] = useState(() =>
    SHAP_FACTORS.reduce(
      (acc, factor, i) => ({
        ...acc,
        [factor]: [8, 8, 8, 8, 5, 9, 8, 8][i] ?? 8,
      }),
      {},
    ),
  );
  const [mlStates, setMlStates] = useState(() =>
    ML_MODELS.reduce(
      (acc, mod) => ({
        ...acc,
        [mod.id]: {
          active: true,
          confThreshold: 75,
          status: mod.defaultStatus,
        },
      }),
      {},
    ),
  );
  const [dataSourceStates, setDataSourceStates] = useState(() =>
    DATA_SOURCES.reduce(
      (acc, ds) => ({
        ...acc,
        [ds.id]: {
          active: true,
          weight: ds.weight ?? 100,
          connected: ds.connected,
        },
      }),
      {},
    ),
  );
  const [regimeLock, setRegimeLock] = useState(false);
  const [autoExecute, setAutoExecute] = useState(false);
  const [tradingMode, setTradingMode] = useState("PAPER TRADING");
  const [maxHeat, setMaxHeat] = useState(25);
  const [lossLimit, setLossLimit] = useState(5);
  const [wsLatency, setWsLatency] = useState(42);
  const [saving, setSaving] = useState(false);
  const fileInputRef = useRef(null);
  const [signals, setSignals] = useState([]);
  const [selectedSymbol, setSelectedSymbol] = useState("NVDA");
  const [chartTimeframe, setChartTimeframe] = useState("W1");

  const chartContainerRef = useRef(null);
  const chartRef = useRef(null);

  // --- WEBSOCKET CONNECTION (uses services/websocket.js singleton) ---
  useEffect(() => {
    ws.connect();
    const unsubSignals = ws.on("signals", (msg) => {
      if (msg?.type === "signals_updated") refetchSignals();
      if (msg?.type === "signal" && msg.payload) {
        setSignals((prev) => [msg.payload, ...prev].slice(0, 50));
      }
    });
    const unsubLatency = ws.on("*", (msg) => {
      if (msg?.data?.type === "ping" && msg.data.latency)
        setWsLatency(msg.data.latency);
    });
    return () => {
      unsubSignals();
      unsubLatency();
    };
  }, [refetchSignals]);

  // --- SYNC API AGENTS INTO LOCAL agentStates ---
  useEffect(() => {
    if (!ALL_AGENTS || ALL_AGENTS.length === 0) return;
    setAgentStates((prev) => {
      const next = { ...prev };
      for (const agent of ALL_AGENTS) {
        const existing = prev[agent.id];
        const apiStatus = agent.status;
        const statusColor =
          apiStatus === "active" || apiStatus === "running"
            ? "green"
            : apiStatus === "degraded" || apiStatus === "warming"
              ? "yellow"
              : apiStatus === "error" || apiStatus === "stopped"
                ? "red"
                : existing?.status || "green";
        if (existing) {
          next[agent.id] = { ...existing, status: statusColor };
        } else {
          next[agent.id] = {
            active: true,
            weight: agent.defaultWeight,
            status: statusColor,
          };
        }
      }
      return next;
    });
  }, [ALL_AGENTS]);

  // --- SYNC API DATA SOURCES INTO LOCAL dataSourceStates ---
  useEffect(() => {
    if (!apiDataSources) return;
    const sources = Array.isArray(apiDataSources)
      ? apiDataSources
      : apiDataSources?.sources || apiDataSources?.data || [];
    if (sources.length === 0) return;
    setDataSourceStates((prev) => {
      const next = { ...prev };
      for (const src of sources) {
        const id = src.id || src.source_id;
        if (!id) continue;
        const isActive =
          src.active !== false &&
          src.status !== "down" &&
          src.status !== "error";
        next[id] = {
          active: isActive,
          weight: src.weight ?? prev[id]?.weight ?? 100,
        };
      }
      return next;
    });
  }, [apiDataSources]);

  // --- SYNC ML BRAIN / TRAINING STATUS INTO LOCAL mlStates ---
  useEffect(() => {
    const models = apiMlBrain?.models || apiTraining?.models || null;
    if (!models || !Array.isArray(models)) return;
    setMlStates((prev) => {
      const next = { ...prev };
      for (const m of models) {
        const id = m.id || m.model_id;
        if (!id || !prev[id]) continue;
        next[id] = {
          ...prev[id],
          status: m.status || m.state || prev[id].status,
          confThreshold:
            m.confidence_threshold ?? m.confThreshold ?? prev[id].confThreshold,
        };
      }
      return next;
    });
  }, [apiMlBrain, apiTraining]);

  // --- SYNC SETTINGS FROM API INTO LOCAL STATE (#4) ---
  useEffect(() => {
    if (!apiSettings) return;
    const profile = apiSettings?.profile || apiSettings;
    const trading = apiSettings?.trading || profile?.trading || {};
    if (trading.tradingMode === "live" || trading.tradingMode === "LIVE TRADING") setTradingMode("LIVE TRADING");
    if (trading.autoExecute === true) setAutoExecute(true);
    if (profile?.maxHeat != null) setMaxHeat(profile.maxHeat);
    if (profile?.lossLimit != null) setLossLimit(profile.lossLimit);
    if (profile?.regimeLock != null) setRegimeLock(profile.regimeLock);
    if (profile?.scoringFormula) setScoringFormula((p) => ({ ...p, ...profile.scoringFormula }));
    if (profile?.shapWeights) setShapWeights((p) => ({ ...p, ...profile.shapWeights }));
    const risk = apiSettings?.risk || {};
    if (risk.maxHeat != null) setMaxHeat(risk.maxHeat);
    if (risk.dailyLossLimit != null) setLossLimit(risk.dailyLossLimit);
  }, [apiSettings]);

  // --- LIGHTWEIGHT CHARTS SETUP ---
  useEffect(() => {
    if (!chartContainerRef.current || chartRef.current) return;
    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { color: "transparent" },
        textColor: "#9ca3af",
        fontFamily: "JetBrains Mono, monospace",
        fontSize: 9,
      },
      grid: {
        vertLines: { color: "#1e293b", style: LineStyle.SparseDotted },
        horzLines: { color: "#1e293b", style: LineStyle.SparseDotted },
      },
      crosshair: { mode: CrosshairMode.Normal },
      timeScale: {
        borderColor: "#374151",
        timeVisible: true,
        secondsVisible: false,
      },
      rightPriceScale: { borderColor: "#374151" },
    });
    const candleSeries = chart.addCandlestickSeries({
      upColor: "#10b981",
      downColor: "#ef4444",
      borderVisible: false,
      wickUpColor: "#10b981",
      wickDownColor: "#ef4444",
    });
    const volSeries = chart.addHistogramSeries({
      color: "#26a69a",
      priceFormat: { type: "volume" },
      priceScaleId: "",
      scaleMargins: { top: 0.8, bottom: 0 },
    });
    const sma20 = chart.addLineSeries({
      color: "#00D9FF",
      lineWidth: 1,
      title: "SMA20",
    });
    const sma50 = chart.addLineSeries({
      color: "#a855f7",
      lineWidth: 1,
      title: "SMA50",
    });
    const sma200 = chart.addLineSeries({
      color: "#F97316",
      lineWidth: 1,
      lineStyle: LineStyle.Dashed,
      title: "SMA200",
    });
    const vwap = chart.addLineSeries({
      color: "#ffffff",
      lineWidth: 1,
      lineStyle: LineStyle.Dotted,
      title: "VWAP",
    });
    // Fetch real OHLCV data from backend quotes API
    const fetchChart = async () => {
      try {
        const url =
          getApiUrl("quotes") +
          `/${selectedSymbol}?timeframe=${chartTimeframe}`;
        const res = await fetch(url);
        if (!res.ok) throw new Error("Quote fetch failed");
        const json = await res.json();
        const bars = json.bars || json.data || json || [];
        if (bars.length === 0) return;
        const rawData = bars.map((b) => {
          const t = b.timestamp ?? b.t ?? b.time;
          const ts = t != null ? Math.floor(new Date(t).getTime() / 1000) : NaN;
          const open = Number(b.open ?? b.o);
          const high = Number(b.high ?? b.h);
          const low = Number(b.low ?? b.l);
          const close = Number(b.close ?? b.c);
          const volume = Number(b.volume ?? b.v ?? 0);
          return {
            time: Number.isFinite(ts) ? ts : NaN,
            open,
            high,
            low,
            close,
            volume,
          };
        });
        const sorted = rawData
          .filter((d) => Number.isFinite(d.time) && Number.isFinite(d.close))
          .sort((a, b) => a.time - b.time);
        const data = [];
        let prevTime = -1;
        for (const d of sorted) {
          if (d.time > prevTime) {
            data.push(d);
            prevTime = d.time;
          } else if (d.time === prevTime && data.length > 0) {
            data[data.length - 1] = d;
          }
        }
        if (data.length === 0) return;
        const volData = data.map((d) => ({
          time: d.time,
          value: d.volume,
          color: d.close >= d.open ? "#10b98144" : "#ef444444",
        }));
        const s20 = [];
        const s50 = [];
        const s200 = [];
        const vwapData = [];
        let cumVol = 0,
          cumVolPrice = 0;
        data.forEach((d, i) => {
          const vol = d.volume;
          const tp = (d.high + d.low + d.close) / 3;
          cumVol += vol;
          cumVolPrice += tp * vol;
          if (cumVol > 0)
            vwapData.push({ time: d.time, value: cumVolPrice / cumVol });
          if (i >= 19)
            s20.push({
              time: d.time,
              value:
                data.slice(i - 19, i + 1).reduce((a, b) => a + b.close, 0) / 20,
            });
          if (i >= 49)
            s50.push({
              time: d.time,
              value:
                data.slice(i - 49, i + 1).reduce((a, b) => a + b.close, 0) / 50,
            });
          if (i >= 199)
            s200.push({
              time: d.time,
              value:
                data.slice(i - 199, i + 1).reduce((a, b) => a + b.close, 0) /
                200,
            });
        });
        candleSeries.setData(data);
        volSeries.setData(volData);
        sma20.setData(s20);
        sma50.setData(s50);
        sma200.setData(s200);
        vwap.setData(vwapData);
        const lastPrice = data[data.length - 1].close;
        candleSeries.createPriceLine({
          price: lastPrice,
          color: "#00D9FF",
          lineWidth: 2,
          lineStyle: LineStyle.Solid,
          title: "ENTRY",
        });
        candleSeries.createPriceLine({
          price: lastPrice * 1.05,
          color: "#10b981",
          lineWidth: 2,
          lineStyle: LineStyle.Dashed,
          title: "TARGET",
        });
        candleSeries.createPriceLine({
          price: lastPrice * 0.98,
          color: "#ef4444",
          lineWidth: 2,
          lineStyle: LineStyle.Dotted,
          title: "STOP",
        });
      } catch (err) {
        log.warn(
          "Chart data fetch (expected if no quotes endpoint):",
          err.message,
        );
      }
    };
    fetchChart();
    chartRef.current = chart;
    const handleResize = () => {
      if (chartContainerRef.current)
        chart.applyOptions({ width: chartContainerRef.current.clientWidth });
    };
    window.addEventListener("resize", handleResize);
    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
      chartRef.current = null;
    };
  }, [selectedSymbol, chartTimeframe]);

  // --- SYNC API SIGNALS TO LOCAL STATE (no mock data; empty state when API returns none) ---
  useEffect(() => {
    if (apiSignals) {
      const list = Array.isArray(apiSignals)
        ? apiSignals
        : apiSignals?.signals
          ? apiSignals.signals
          : [];
      setSignals(list.length > 0 ? list.slice(0, 50) : []);
    }
  }, [apiSignals]);

  // --- HANDLERS (Real API Mapped) ---
  const handleUpdateWeight = useCallback(async (category, id, value) => {
    if (category === "agent")
      setAgentStates((p) => ({ ...p, [id]: { ...p[id], weight: value } }));
    else if (category === "scanner")
      setScannerStates((p) => ({ ...p, [id]: { ...p[id], weight: value } }));
    else if (category === "intel")
      setIntelStates((p) => ({ ...p, [id]: { ...p[id], weight: value } }));
    else if (category === "shap") {
      setShapWeights((p) => ({ ...p, [id]: value }));
      return;
    }
    try {
      const url = getApiUrl(`${category}s`) + `/${id}/weight`;
      await fetch(url, {
        method: "PUT",
        headers: { "Content-Type": "application/json", ...getAuthHeaders() },
        body: JSON.stringify({ weight: value }),
      });
    } catch (err) {
      log.error(`Failed to update ${category} weight:`, err);
    }
  }, []);

  const triggerRetrain = useCallback(async (id) => {
    try {
      setMlStates((p) => ({ ...p, [id]: { ...p[id], status: "Training" } }));
      const url = getApiUrl("training") + "/retrain";
      await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...getAuthHeaders() },
        body: JSON.stringify({ modelId: id }),
      });
    } catch (e) {
      log.error(e);
    }
  }, []);

  // --- SAVE PROFILE (persist all weights/toggles to backend settings) ---
  const handleSaveProfile = useCallback(async () => {
    setSaving(true);
    try {
      const payload = {
        agentStates,
        scannerStates,
        intelStates,
        mlStates,
        dataSourceStates,
        scoringFormula,
        shapWeights,
        regimeLock,
        autoExecute,
        tradingMode,
        maxHeat,
        lossLimit,
      };
      const url = getApiUrl("settings");
      const res = await fetch(url, {
        method: "PUT",
        headers: { "Content-Type": "application/json", ...getAuthHeaders() },
        body: JSON.stringify({
          page: "signal_intelligence_v3",
          profile: payload,
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      toast.success("Profile saved successfully");
    } catch (err) {
      log.error("Failed to save profile:", err);
      toast.error(`Failed to save profile: ${err.message}`);
    } finally {
      setSaving(false);
    }
  }, [
    agentStates,
    scannerStates,
    intelStates,
    mlStates,
    dataSourceStates,
    scoringFormula,
    shapWeights,
    regimeLock,
    autoExecute,
    tradingMode,
    maxHeat,
    lossLimit,
  ]);

  // --- SIGNAL ACTIONS: Stage for execution via orders endpoint ---
  const handleStageSignal = useCallback(async (signal) => {
    try {
      const url = getApiUrl("orders");
      await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...getAuthHeaders() },
        body: JSON.stringify({
          symbol: signal.symbol || signal.ticker,
          side:
            signal.dir === "LONG" || signal.action === "BUY" ? "buy" : "sell",
          type: "limit",
          limit_price: signal.price,
          source: "signal_intelligence_v3",
          signal_id: signal.id,
        }),
      });
    } catch (err) {
      log.error("Failed to stage signal:", err);
    }
  }, []);

  // --- Download profile as JSON ---
  const handleDownloadProfile = useCallback(() => {
    const payload = { agentStates, scannerStates, intelStates, mlStates, dataSourceStates, scoringFormula, shapWeights, regimeLock, autoExecute, tradingMode, maxHeat, lossLimit };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `signal-profile-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success("Profile downloaded");
  }, [agentStates, scannerStates, intelStates, mlStates, dataSourceStates, scoringFormula, shapWeights, regimeLock, autoExecute, tradingMode, maxHeat, lossLimit]);

  // --- Upload profile from JSON ---
  const handleUploadProfile = useCallback((e) => {
    const file = e.target?.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      try {
        const profile = JSON.parse(ev.target.result);
        if (profile.scoringFormula) setScoringFormula((p) => ({ ...p, ...profile.scoringFormula }));
        if (profile.shapWeights) setShapWeights((p) => ({ ...p, ...profile.shapWeights }));
        if (profile.maxHeat != null) setMaxHeat(profile.maxHeat);
        if (profile.lossLimit != null) setLossLimit(profile.lossLimit);
        if (profile.autoExecute != null) setAutoExecute(profile.autoExecute);
        if (profile.tradingMode) setTradingMode(profile.tradingMode);
        if (profile.regimeLock != null) setRegimeLock(profile.regimeLock);
        toast.success(`Profile loaded from ${file.name}`);
      } catch {
        toast.error("Invalid profile JSON");
      }
    };
    reader.readAsText(file);
    e.target.value = "";
  }, []);

  // --- Share profile link ---
  const handleShareProfile = useCallback(() => {
    const url = window.location.href;
    navigator.clipboard.writeText(url).then(
      () => toast.success("Page link copied to clipboard"),
      () => toast.error("Failed to copy link")
    );
  }, []);

  // --- Override regime (uses ref to avoid TDZ with regimeData) ---
  const regimeStateRef = useRef("BULL_TREND");
  const handleOverrideRegime = useCallback(async () => {
    const newRegime = window.prompt("Override regime to which state?\n(BULL_TREND, BEAR_TREND, SIDEWAYS, HIGH_VOL)", regimeStateRef.current);
    if (!newRegime) return;
    try {
      const url = getApiUrl("openclaw") + "/regime/override";
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...getAuthHeaders() },
        body: JSON.stringify({ state: newRegime.toUpperCase().trim() }),
      });
      if (res.ok) {
        toast.success(`Regime overridden to ${newRegime.toUpperCase()}`);
      } else {
        const err = await res.json().catch(() => ({}));
        toast.error(err?.detail || `Override failed: HTTP ${res.status}`);
      }
    } catch (err) {
      toast.error(`Override failed: ${err.message}`);
    }
  }, []);

  // --- DERIVED DATA ---
  const { data: regimeApiData } = useApi('openclawRegime', { pollIntervalMs: 30000 });
  const { data: flywheelData } = useApi('flywheel', { pollIntervalMs: 15000 });
  const regimeData = useMemo(() => regimeApiData || apiOpenclaw?.regime || { state: 'BULL_TREND', conf: 87, color: 'emerald', since: null }, [regimeApiData, apiOpenclaw]);
  regimeStateRef.current = regimeData.state || "BULL_TREND";

  const regimeBanner = useMemo(() => {
    const state = regimeData.state || "";
    if (state.includes("BULL"))
      return {
        color: "#10B981",
        bg: "rgba(16,185,129,0.08)",
        border: "rgba(16,185,129,0.3)",
        text: "#10B981",
        label: "BULL",
        icon: "trending-up",
      };
    if (state.includes("BEAR"))
      return {
        color: "#EF4444",
        bg: "rgba(239,68,68,0.08)",
        border: "rgba(239,68,68,0.3)",
        text: "#EF4444",
        label: "BEAR",
        icon: "trending-down",
      };
    if (state.includes("HIGH_VOL") || state.includes("VOLATILE"))
      return {
        color: "#F97316",
        bg: "rgba(249,115,22,0.08)",
        border: "rgba(249,115,22,0.3)",
        text: "#F97316",
        label: "HIGH_VOL",
        icon: "alert",
      };
    if (
      state.includes("SIDE") ||
      state.includes("RANGE") ||
      state.includes("CHOP")
    )
      return {
        color: "#F59E0B",
        bg: "rgba(245,158,11,0.08)",
        border: "rgba(245,158,11,0.3)",
        text: "#F59E0B",
        label: "SIDEWAYS",
        icon: "minus",
      };
    return {
      color: "#10B981",
      bg: "rgba(16,185,129,0.08)",
      border: "rgba(16,185,129,0.3)",
      text: "#10B981",
      label: "BULL",
      icon: "trending-up",
    };
  }, [regimeData]);

  const scannerMetrics = useMemo(() => {
    const sigs = Array.isArray(apiSignals)
      ? apiSignals
      : apiSignals?.signals || signals;
    const signalsToday = sigs.length;
    const highConfSignals = sigs.filter(
      (s) => (s.score || s.confidence || 0) >= 80,
    ).length;
    const hitRate =
      signalsToday > 0 ? Math.round((highConfSignals / signalsToday) * 100) : 0;
    return { signalsToday, hitRate };
  }, [apiSignals, signals]);

  const timeframes = ["1m", "5m", "15m", "1H", "4H", "D1", "W1"];

  const filteredSignals = useMemo(() => {
    if (!searchQuery) return signals;
    return signals.filter((s) =>
      (s.symbol || "").toUpperCase().includes(searchQuery)
    );
  }, [signals, searchQuery]);

  // --- RENDER ---
  return (
    <div className="min-h-screen bg-[#0B0E14] text-gray-200 font-mono flex flex-col overflow-hidden">
      {/* ================================================================== */}
      {/* TOP HEADER BAR                                                     */}
      {/* ================================================================== */}
      <div className="flex items-center justify-between px-4 py-2 bg-[#0B0E14] border-b border-[rgba(42,52,68,0.5)] shrink-0">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-[#00D9FF]" />
            <span className="text-xs font-bold text-[#00D9FF] tracking-wider">
              SIGNAL_INTELLIGENCE_V3
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-[#00D9FF]" />
            <span className="text-xs font-mono text-gray-400">
              OC_CORE_v5.2.1
            </span>
          </div>
          <span className="text-[10px] text-gray-500 font-mono">
            WS_LATENCY: {wsLatency}ms
          </span>
          <span className="text-[10px] text-gray-500 font-mono">
            SWARM_SIZE: {ALL_AGENTS.length}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleDownloadProfile}
            className="p-1.5 rounded text-gray-500 hover:text-[#00D9FF] transition-colors"
            title="Download profile"
          >
            <Download className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => fileInputRef.current?.click()}
            className="p-1.5 rounded text-gray-500 hover:text-[#00D9FF] transition-colors"
            title="Upload profile"
          >
            <Upload className="w-3.5 h-3.5" />
          </button>
          <input ref={fileInputRef} type="file" accept=".json" className="hidden" onChange={handleUploadProfile} />
          <button
            onClick={handleShareProfile}
            className="p-1.5 rounded text-gray-500 hover:text-[#00D9FF] transition-colors"
            title="Copy page link"
          >
            <Share2 className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={handleSaveProfile}
            disabled={saving}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 rounded text-xs font-medium text-white transition-colors"
          >
            <Save className="w-3.5 h-3.5" /> {saving ? "Saving..." : "Save Profile"}
          </button>
        </div>
      </div>

      {/* BULL_TREND REGIME Banner — prominent top panel */}
      <div
        className="shrink-0 px-4 py-2.5 border-b border-[rgba(42,52,68,0.5)]"
        style={{
          background: regimeBanner.bg,
          borderColor: regimeBanner.border,
        }}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <span
                className="text-lg font-bold font-mono"
                style={{ color: regimeBanner.text }}
              >
                ((-)) {regimeData.state || "BULL_TREND"} REGIME
              </span>
              <Zap
                className="w-4 h-4 animate-pulse"
                style={{ color: regimeBanner.text }}
              />
            </div>
            <span className="text-[10px] text-gray-500 font-mono">
              Hidden Markov Model (Layer 3)
            </span>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-[10px] text-gray-400 font-mono">
              HMM Confidence: {regimeData.conf ?? 87}%
            </span>
            <button onClick={handleOverrideRegime} className="px-2 py-0.5 text-[9px] font-medium border rounded border-gray-600 text-gray-400 hover:border-[#00D9FF]/50 hover:text-[#00D9FF] transition-colors">
              Override
            </button>
            <button
              onClick={() => setRegimeLock(!regimeLock)}
              className="p-1 text-gray-500 hover:text-gray-400 transition-colors"
            >
              {regimeLock ? (
                <Lock className="w-3.5 h-3.5" />
              ) : (
                <Unlock className="w-3.5 h-3.5" />
              )}
            </button>
          </div>
        </div>
      </div>

      {/* ================================================================== */}
      {/* MAIN 4-COLUMN GRID LAYOUT                                          */}
      {/* ================================================================== */}
      <div className="flex-1 grid grid-cols-[300px_1fr_300px_240px] gap-1 p-1 overflow-hidden min-h-0">
        {/* ============================================================== */}
        {/* COLUMN 1: Scanner Modules (Layer 1) + OpenClaw Score (Layer 4) */}
        {/* ============================================================== */}
        <div className="flex flex-col gap-1 overflow-hidden min-h-0">
          {/* Scanner Modules (Layer 1) */}
          <Panel
            title="Scanner Modules (Layer 1)"
            icon={Search}
            className="flex-[5] min-h-0"
            headerAction={
              <span className="text-[7px] text-gray-500">
                {SCANNERS.length} SCANNER TOGGLES
              </span>
            }
          >
            <div className="space-y-1">
              {SCANNERS.map((scan) => {
                const pct = scannerStates[scan.id]?.pct ?? scan.pct ?? 50;
                return (
                  <Slider
                    key={scan.id}
                    label={scan.name}
                    min={0}
                    max={100}
                    step={1}
                    value={pct}
                    onChange={(v) =>
                      setScannerStates((p) => ({
                        ...p,
                        [scan.id]: { ...p[scan.id], pct: v },
                      }))
                    }
                    suffix="%"
                    className="py-0.5"
                    valueClassName="text-[8px] min-w-[2.5rem]"
                  />
                );
              })}
            </div>
          </Panel>

          {/* OpenClaw Swarm (Layer 4) */}
          <Panel
            title="OpenClaw Swarm (Layer 4)"
            icon={Cpu}
            className="flex-[5] min-h-0"
            headerAction={
              <span className="text-[7px] text-gray-500">7 CORE AGENTS</span>
            }
          >
            <div className="space-y-1">
              {CORE_AGENTS.length === 0 ? (
                <div className="text-[9px] text-gray-500 text-center py-3">Awaiting agent data from /api/v1/agents...</div>
              ) : (
                CORE_AGENTS.slice(0, 7).map((agent) => (
                  <Slider
                    key={agent.id}
                    label={agent.name}
                    min={0}
                    max={100}
                    step={1}
                    value={agentStates[agent.id]?.weight ?? agent.defaultWeight}
                    onChange={(v) => handleUpdateWeight("agent", agent.id, v)}
                    suffix="%"
                    className="py-0.5"
                    valueClassName="text-[8px] min-w-[2.5rem]"
                  />
                ))
              )}
            </div>
            <div className="mt-2 pt-1 border-t border-[rgba(42,52,68,0.5)]">
              <span className="text-[8px] text-gray-500 uppercase tracking-wider">
                EXTENDED SWARM ({EXTENDED_AGENTS.length || 0})
              </span>
              {EXTENDED_AGENTS.length > 0 && (
                <div className="mt-1 space-y-1">
                  {EXTENDED_AGENTS.slice(0, 5).map((agent) => (
                    <div key={agent.id} className="flex items-center gap-1.5 py-0.5">
                      <span className={`w-1.5 h-1.5 rounded-full ${agentStates[agent.id]?.status === "red" ? "bg-red-500" : agentStates[agent.id]?.status === "yellow" ? "bg-amber-500" : "bg-emerald-500"}`} />
                      <span className="text-[8px] text-gray-400 truncate flex-1">{agent.name}</span>
                      <span className="text-[7px] text-gray-600 font-mono">{agent.type}</span>
                    </div>
                  ))}
                  {EXTENDED_AGENTS.length > 5 && (
                    <div className="text-[7px] text-gray-600 text-center">+{EXTENDED_AGENTS.length - 5} more agents</div>
                  )}
                </div>
              )}
            </div>
          </Panel>
        </div>

        {/* ============================================================== */}
        {/* COLUMN 2: Chart + Signal Data Table                            */}
        {/* ============================================================== */}
        <div className="flex flex-col gap-1 overflow-hidden min-h-0">
          {/* Chart */}
          <div className="bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded flex-[6] min-h-0 flex flex-col overflow-hidden">
            {/* Chart header */}
            <div className="px-2.5 py-1 border-b border-[rgba(42,52,68,0.5)] flex items-center justify-between bg-[#0B0E14] shrink-0">
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-bold text-white">
                  {selectedSymbol}
                </span>
                <span className="text-[8px] text-gray-500">OHLCV</span>
                <div className="flex items-center gap-1.5 ml-2">
                  <span className="flex items-center gap-0.5">
                    <span className="w-2 h-0.5 bg-[#00D9FF] inline-block rounded" />
                    <span className="text-[7px] text-[#00D9FF]">SMA200</span>
                  </span>
                  <span className="flex items-center gap-0.5">
                    <span className="w-2 h-0.5 bg-white inline-block rounded" />
                    <span className="text-[7px] text-gray-300">VWAP</span>
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-0.5">
                {timeframes.map((t) => (
                  <button
                    key={t}
                    onClick={() => setChartTimeframe(t)}
                    className={`text-[10px] uppercase tracking-wider font-bold rounded-md px-3 py-1 transition-all ${
                      chartTimeframe === t
                        ? "bg-cyan-500/20 text-[#00D9FF] border border-[#00D9FF]/50/30"
                        : "bg-transparent text-gray-500 border border-gray-700"
                    }`}
                  >
                    {t}
                  </button>
                ))}
              </div>
            </div>
            <div
              ref={chartContainerRef}
              className="w-full flex-1 min-h-[200px]"
            />
          </div>

          {/* Signal Data Table */}
          <Panel
            title="Signal data table"
            icon={FileText}
            className="flex-[3] min-h-0"
            headerAction={
              <div className="flex items-center gap-2">
                <span className="text-[7px] text-gray-600 font-mono">
                  {filteredSignals.length}{searchQuery ? `/${signals.length}` : ""} signals
                </span>
                <button
                  onClick={refetchSignals}
                  className="text-gray-500 hover:text-[#00D9FF] transition-colors"
                >
                  <RefreshCw className="w-2.5 h-2.5" />
                </button>
              </div>
            }
          >
            <div className="overflow-auto flex-1 min-h-0">
              <table className="w-full text-[8px]">
                <thead className="sticky top-0 bg-[#111827] z-10">
                  <tr className="text-gray-500 border-b border-[rgba(42,52,68,0.5)] uppercase tracking-wider">
                    <th className="text-left py-1 px-1">Symbol</th>
                    <th className="text-left py-1 px-1">Score</th>
                    <th className="text-left py-1 px-1">Dir</th>
                    <th className="text-left py-1 px-1">Price</th>
                    <th className="text-left py-1 px-1">Origin Agent</th>
                    <th className="text-left py-1 px-1">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredSignals.length === 0 && (
                    <tr>
                      <td colSpan={6} className="text-center py-4 text-gray-500 text-[9px]">
                        {sigLoading ? "Loading signals..." : sigError ? "Service temporarily unavailable — retrying..." : "No signals available — awaiting signal generation from agents"}
                      </td>
                    </tr>
                  )}
                  {filteredSignals.map((sig, idx) => (
                    <tr
                      key={sig.id || idx}
                      className="border-b border-[rgba(42,52,68,0.5)]/30 hover:bg-[#00D9FF]/5 cursor-pointer transition-colors"
                      onClick={() =>
                        setSelectedSymbol(sig.symbol || sig.ticker)
                      }
                    >
                      <td className="py-0.5 px-1 font-bold font-mono text-[#00D9FF]">
                        {sig.symbol || sig.ticker}
                      </td>
                      <td className="py-0.5 px-1">
                        <div className="flex items-center gap-1">
                          <div className="w-8 h-1 bg-[#1e293b] rounded-full overflow-hidden">
                            <div
                              className="h-full rounded-full"
                              style={{
                                width: `${sig.score || sig.confidence || 0}%`,
                                backgroundColor:
                                  (sig.score || sig.confidence || 0) >= 80
                                    ? "#10b981"
                                    : (sig.score || sig.confidence || 0) >= 50
                                      ? "#f59e0b"
                                      : "#ef4444",
                              }}
                            />
                          </div>
                          <span
                            className={`font-mono font-bold ${(sig.score || sig.confidence || 0) >= 80 ? "text-emerald-400" : (sig.score || sig.confidence || 0) >= 50 ? "text-amber-400" : "text-red-400"}`}
                          >
                            {sig.score || sig.confidence || "--"}
                          </span>
                        </div>
                      </td>
                      <td className="py-0.5 px-1">
                        <span
                          className={`flex items-center gap-0.5 text-[7px] font-bold ${sig.dir === "LONG" || sig.action === "BUY" ? "text-emerald-400" : "text-red-400"}`}
                        >
                          {sig.dir === "LONG" || sig.action === "BUY" ? (
                            <TrendingUp className="w-2.5 h-2.5" />
                          ) : (
                            <TrendingDown className="w-2.5 h-2.5" />
                          )}
                          {sig.dir || sig.action || "--"}
                        </span>
                      </td>
                      <td className="py-0.5 px-1 font-mono text-gray-300">
                        <span className="font-mono">
                          $
                          {typeof sig.price === "number"
                            ? sig.price.toFixed(2)
                            : sig.price || "--"}
                        </span>
                      </td>
                      <td className="py-0.5 px-1">
                        <span className="text-[#00D9FF] underline cursor-pointer truncate max-w-[80px] block">
                          {sig.agent || sig.source || "--"}
                        </span>
                      </td>
                      <td className="py-0.5 px-1">
                        <div className="flex items-center gap-0.5">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                            }}
                            className="px-1 py-0.5 text-[7px] font-medium text-emerald-400 border border-emerald-500/40 rounded hover:bg-emerald-500/10"
                          >
                            Accept
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                            }}
                            className="px-1 py-0.5 text-[7px] font-medium text-red-400 border border-red-500/40 rounded hover:bg-red-500/10"
                          >
                            Reject
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                            }}
                            className="px-1 py-0.5 text-[7px] font-medium text-gray-400 border border-gray-600 rounded hover:bg-gray-500/10"
                          >
                            Watch
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleStageSignal(sig);
                            }}
                            className="px-1 py-0.5 text-[7px] font-medium text-emerald-400 border border-emerald-500/40 rounded hover:bg-emerald-500/10"
                          >
                            Execute
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>
        </div>

        {/* ============================================================== */}
        {/* COLUMN 3: Global Scoring Engine + Intelligence Modules          */}
        {/* ============================================================== */}
        <div className="flex flex-col gap-1 overflow-y-auto min-h-0 scrollbar-thin scrollbar-thumb-[#374151] scrollbar-track-transparent">
          {/* Global Scoring Engine (Layer 2) */}
          <Panel
            title="Global Scoring Engine (Layer 2)"
            icon={Target}
            className="shrink-0"
          >
            <div className="space-y-1.5">
              <div className="text-[8px] font-bold text-gray-400 uppercase tracking-wider mb-1">
                OpenClaw Core vs Tech Analysis
              </div>
              <Slider
                label="Blend 60/40"
                min={0}
                max={100}
                value={scoringFormula.ocTaBlend}
                onChange={(v) =>
                  setScoringFormula((p) => ({ ...p, ocTaBlend: v }))
                }
                suffix="%"
                className="py-0.5"
                valueClassName="text-[8px] min-w-[2.5rem]"
              />
              <Slider
                label="Regime Multiplier"
                min={0}
                max={3}
                step={0.1}
                value={scoringFormula.regimeMultiplier || 1.2}
                onChange={(v) =>
                  setScoringFormula((p) => ({ ...p, regimeMultiplier: v }))
                }
                formatValue={(v) => v.toFixed(1)}
                className="py-0.5"
                valueClassName="text-[8px] min-w-[2rem]"
              />
              <Slider
                label="SLAM DUNK Tier"
                min={0}
                max={100}
                value={scoringFormula.tierSlamDunk}
                onChange={(v) =>
                  setScoringFormula((p) => ({ ...p, tierSlamDunk: v }))
                }
                suffix=""
                className="py-0.5"
                valueClassName="text-[8px] min-w-[2rem]"
              />
              <div className="text-[8px] font-bold text-gray-400 uppercase tracking-wider mt-2 mb-1">
                PER-FACTOR SHAP WEIGHTS
              </div>
              {SHAP_FACTORS.map((f) => {
                const v = shapWeights[f] ?? 8;
                return (
                  <Slider
                    key={f}
                    label={f}
                    min={0}
                    max={10}
                    step={1}
                    value={v}
                    onChange={(val) =>
                      setShapWeights((p) => ({ ...p, [f]: val }))
                    }
                    className="py-0.5"
                    valueClassName="text-[8px] min-w-[1.5rem]"
                  />
                );
              })}
            </div>
          </Panel>

          {/* Intelligence Modules (Layer 3) + ML Model Control (Layer 5) side by side */}
          <Panel
            title="Intelligence Modules (Layer 3)"
            icon={Shield}
            className="flex-1 min-w-0"
          >
            <div className="space-y-1">
              {INTEL_MODULES.map((mod) => (
                <Slider
                  key={mod.id}
                  label={mod.name}
                  min={0}
                  max={100}
                  step={1}
                  value={intelStates[mod.id]?.weight ?? mod.defaultWeight}
                  onChange={(v) => handleUpdateWeight("intel", mod.id, v)}
                  suffix="%"
                  className="py-0.5"
                  valueClassName="text-[8px] min-w-[2.5rem]"
                />
              ))}
            </div>
          </Panel>
          <Panel
            title="ML Model Control (Layer 5)"
            icon={Cpu}
            className="flex-1 min-w-0"
          >
            <div className="space-y-1">
              {ML_MODELS.map((model) => {
                const status =
                  mlStates[model.id]?.status ?? model.defaultStatus;
                const statusColor =
                  status === "Ready"
                    ? "text-emerald-400"
                    : status === "Training"
                      ? "text-amber-400"
                      : "text-gray-500";
                const conf = mlStates[model.id]?.confThreshold ?? 75;
                return (
                  <div
                    key={model.id}
                    className="flex items-center gap-2 py-0.5 border-b border-[rgba(42,52,68,0.5)]/30 last:border-0"
                  >
                    <span className="text-[8px] text-gray-300 shrink-0 truncate w-24">
                      {model.name}
                    </span>
                    <span className="text-[7px] text-gray-500 font-mono shrink-0">
                      {model.version}
                    </span>
                    <span
                      className={`text-[7px] font-mono ${statusColor} shrink-0`}
                    >
                      {status}
                    </span>
                    <Slider
                      label="Confidence"
                      min={0}
                      max={100}
                      step={1}
                      value={conf}
                      onChange={(v) =>
                        setMlStates((p) => ({
                          ...p,
                          [model.id]: { ...p[model.id], confThreshold: v },
                        }))
                      }
                      suffix="%"
                      className="flex-1 min-w-0 py-0"
                      valueClassName="text-[8px] min-w-[2.5rem]"
                    />
                    <button
                      onClick={() => triggerRetrain(model.id)}
                      className="shrink-0 px-2 py-0.5 text-[7px] font-medium bg-gray-700 text-gray-300 border border-gray-600 rounded hover:bg-gray-600 transition-colors"
                    >
                      RETRAIN
                    </button>
                  </div>
                );
              })}
            </div>
          </Panel>
        </div>

        {/* ============================================================== */}
        {/* COLUMN 4: External Sensors + Execution + Telemetry             */}
        {/* ============================================================== */}
        <div className="flex flex-col gap-1 overflow-y-auto min-h-0 scrollbar-thin scrollbar-thumb-[#374151] scrollbar-track-transparent">
          {/* External Sensors */}
          <Panel title="External Sensors" icon={Globe} className="shrink-0">
            {DATA_SOURCES.map((ds) => (
              <div key={ds.id} className="flex items-center gap-1.5 py-0.5">
                <span className="text-[8px] text-gray-300 flex-1 truncate">
                  {ds.name}
                </span>
                {ds.connected ? (
                  <span className="text-[8px] text-emerald-400 font-medium">
                    Connected
                  </span>
                ) : (
                  <Toggle
                    checked={dataSourceStates[ds.id]?.active ?? true}
                    onChange={() => {
                      const newActive = !dataSourceStates[ds.id]?.active;
                      setDataSourceStates((p) => ({
                        ...p,
                        [ds.id]: { ...p[ds.id], active: newActive },
                      }));
                      toast.info(`${ds.name}: ${newActive ? "enabled" : "disabled"} (save profile to persist)`);
                    }}
                    size="sm"
                  />
                )}
                {ds.weight != null && (
                  <span className="text-[7px] text-gray-500 font-mono">
                    Weight {ds.weight}
                  </span>
                )}
              </div>
            ))}
          </Panel>

          {/* Execution & Automation Engine */}
          <Panel
            title="Execution & Automation Engine"
            icon={Rocket}
            className="shrink-0"
          >
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="text-[8px] text-gray-400 uppercase tracking-wider font-bold">
                  AUTO EXECUTION
                </span>
                <Toggle
                  checked={autoExecute}
                  onChange={setAutoExecute}
                  size="sm"
                  variant="orange"
                />
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[8px] text-gray-500 w-24">
                  Trading Mode:
                </span>
                <select value={tradingMode} onChange={(e) => setTradingMode(e.target.value)} className="bg-[#1e293b] border border-[#374151] rounded px-1.5 py-0.5 text-[8px] text-gray-300 outline-none font-mono flex-1">
                  <option>PAPER TRADING</option>
                  <option>LIVE TRADING</option>
                </select>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[8px] text-gray-500 w-24">
                  Position Sizer:
                </span>
                <select className="bg-[#1e293b] border border-[#374151] rounded px-1.5 py-0.5 text-[8px] text-gray-300 outline-none font-mono flex-1">
                  <option>KELLY CRITERION</option>
                </select>
              </div>
              <Slider
                label="Max Portfolio Heat"
                min={0}
                max={100}
                value={maxHeat}
                onChange={setMaxHeat}
                suffix="%"
                className="py-0.5"
                valueClassName="text-[8px] min-w-[2.5rem]"
              />
              <Slider
                label="Daily Loss Limit"
                min={0}
                max={100}
                value={lossLimit}
                onChange={setLossLimit}
                suffix="%"
                className="py-0.5"
                valueClassName="text-[8px] min-w-[2.5rem]"
              />
              <div className="text-[8px] font-bold text-gray-400 uppercase tracking-wider mt-2 mb-1">
                IF/THEN rules
              </div>
              <input
                type="text"
                placeholder="IF comp&gt;90"
                className="w-full bg-[#0B0E14] border border-[#374151] rounded px-2 py-1 text-[8px] text-gray-300 font-mono placeholder-gray-600 outline-none"
                readOnly
              />
              <input
                type="text"
                placeholder="IF comp&gt;90 AND regime=BULL"
                className="w-full bg-[#0B0E14] border border-[#374151] rounded px-2 py-1 text-[8px] text-gray-300 font-mono placeholder-gray-600 outline-none"
                readOnly
              />
              <input
                type="text"
                placeholder="THEN stage"
                className="w-full bg-[#0B0E14] border border-[#374151] rounded px-2 py-1 text-[8px] text-gray-300 font-mono placeholder-gray-600 outline-none"
                readOnly
              />
            </div>
          </Panel>

          {/* System Telemetry */}
          <Panel
            title="System Telemetry"
            icon={BarChart2}
            className="shrink-0"
            headerAction={
              <span className="text-[7px] text-gray-500">
                API ENDPOINT HEALTH
              </span>
            }
          >
            <div className="grid grid-cols-6 gap-x-2 gap-y-4 mb-2">
              {API_ENDPOINTS.slice(0, 24).map((ep) => {
                const health = apiStatus?.endpoints?.[ep];
                const isErr = health?.status === "down" || health?.error;
                const isWarn = health?.status === "degraded";
                return (
                  <div key={ep} className="flex justify-center">
                    <div
                      className={`w-4 h-4 rounded-full ${
                        isErr
                          ? "bg-red-500"
                          : isWarn
                            ? "bg-amber-500"
                            : "bg-emerald-500"
                      }`}
                      title={ep}
                    />
                  </div>
                );
              })}
            </div>
            <div className="text-[8px] text-gray-500 font-mono">
              DB: {apiStatus?.db_latency_ms ?? "4.2"}ms MEM:{" "}
              {apiStatus?.memory_percent ?? 64}%
            </div>
          </Panel>
        </div>
      </div>

      {/* ================================================================== */}
      {/* BOTTOM STATUS BAR                                                  */}
      {/* ================================================================== */}
      <div className="flex items-center justify-between px-3 py-1 bg-[#0B0E14] border-t border-[rgba(42,52,68,0.5)] shrink-0 text-[8px] text-gray-500">
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_4px_rgba(16,185,129,0.5)]" />
            <span className="text-emerald-400">
              {Object.values(agentStates).filter((a) => a.active).length} agents
              connected
            </span>
          </span>
          <span className="flex items-center gap-1">
            <Wifi className="w-3 h-3 text-gray-600" />
            WS: {wsLatency}ms
          </span>
          <span className="flex items-center gap-1">
            <Database className="w-3 h-3 text-gray-600" />
            DB: {apiStatus?.db_latency_ms ?? "--"}ms
          </span>
        </div>
        <div className="flex items-center gap-3">
          <span>
            Signals:{" "}
            <span className="font-mono">{scannerMetrics.signalsToday}</span>
          </span>
          <span>
            Hit Rate:{" "}
            <span className="font-mono">{scannerMetrics.hitRate}%</span>
          </span>
          <span className="text-gray-600">
            {new Date().toLocaleTimeString()}
          </span>
        </div>
      </div>
    </div>
  );
}
