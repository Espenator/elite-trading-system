// SCREENER AND PATTERNS - Embodier.ai Trading Intelligence System
// Mockup: 07-screener-and-patterns.png
// Two-column layout: Screening Engine (left) + Pattern Intelligence (right)
// Bottom: 3-panel row: Consolidated Live Feed | Pattern Arsenal | Forming Detections
// Backend: GET /api/v1/patterns, /api/v1/signals
// Uses: useApi, Recharts mini charts, lucide-react icons, dark theme with cyan/teal

import React, { useState, useEffect, useRef, useCallback, useMemo } from "react";
import {
  Search, Filter, Zap, Brain, Activity, Target, TrendingUp, TrendingDown,
  Play, Square, Copy, Trash2, Plus, Bot, Cpu, Layers, Eye, Settings,
  ChevronDown, ChevronRight, BarChart2, AlertTriangle, CheckCircle,
  Radio, Radar, Crosshair, Boxes, Network, Gauge, Shield, RefreshCw,
  Clock, Terminal, Power, Skull, Sparkles, GitBranch, Waves,
  Minimize2, Maximize2, X,
} from "lucide-react";
import { AreaChart, Area, ResponsiveContainer } from "recharts";
import clsx from "clsx";
import { format } from "date-fns";
import { useApi } from "../hooks/useApi";
import PageHeader from "../components/ui/PageHeader";
import Slider from "../components/ui/Slider";
import log from "@/utils/logger";
import { toast } from "react-toastify";
import { getApiUrl, getAuthHeaders } from "../config/api";

// ═══════════════════════════════════════════════════
// CONFIG & CONSTANTS
// ═══════════════════════════════════════════════════

const TIMEFRAMES = ["1M", "5M", "15M", "1H", "4H", "D", "W"];

const SCANNER_TYPES = [
  "Alpha Scanner", "Momentum Scanner", "Mean Reversion", "Breakout Hunter",
  "Volume Profiler", "Dark Pool Tracker", "Options Flow", "Sector Rotator",
];


const VOLATILITY_REGIMES = ["Expansion", "Contraction", "Normal", "Extreme"];
const VOLUME_PROFILES = ["Value Area High", "Value Area Low", "POC", "HVN", "LVN"];
const OPTIONS_FLOW_OPTS = ["Bullish Put Spreads", "Bearish Call Spreads", "Iron Condor", "Straddle", "Strangle"];
const SCANNER_NAMES = ["AlphaHunter_V4", "Beta Rotator", "Momentum Scanner", "Dark Pool Tracker"];

const SCANNER_AGENTS = [];

const PATTERN_AGENTS = [];

const SWARM_TEMPLATES = [
  { id: "aggressive", name: "Aggressive Momentum", agents: 5, type: "scanner", desc: "High-frequency momentum scanners for volatile markets" },
  { id: "conservative", name: "Conservative Value", agents: 3, type: "scanner", desc: "Low-frequency value screeners for stable assets" },
  { id: "pattern-discovery", name: "Pattern Discovery", agents: 4, type: "pattern", desc: "Multi-timeframe pattern recognition swarm" },
  { id: "full-spectrum", name: "Full Spectrum", agents: 8, type: "both", desc: "Combined scanner + pattern agents for broad coverage" },
];

// Pattern Arsenal: display names + icons per mockup (Wyckoff, Elliot Wave, Head & Shoulders, etc.)
const PATTERNS_ARSENAL_DISPLAY = [
  { id: "wyckoff", name: "Wyckoff Accumulation", icon: "W" },
  { id: "elliott3", name: "Elliot Wave 3", icon: "E" },
  { id: "hs", name: "Head & Shoulders", icon: "H" },
  { id: "cup", name: "Cup & Handle", icon: "C" },
  { id: "flag", name: "Bull Flag", icon: "B" },
  { id: "wedge", name: "Rising Wedge", icon: "R" },
];

const LLM_MODELS = ["GPT-4", "GPT-4o", "Claude 3", "Llama 3"];
const ML_ARCHITECTURES = ["Transformer", "LSTM", "CNN-LSTM", "Attention-Net"];
const PATTERN_COMPLEXITY_OPTS = ["Simple", "Compound", "Multi-Timeframe"];

// ═══════════════════════════════════════════════════
// STYLED SUB-COMPONENTS
// ═══════════════════════════════════════════════════

/** Section wrapper with title bar and window controls (minimize/maximize/close) */
function SectionBox({ title, icon: Icon, children, className, headerRight, windowControls }) {
  const [panelState, setPanelState] = useState("normal"); // "normal" | "minimized" | "hidden"

  if (panelState === "hidden") {
    return (
      <button
        onClick={() => setPanelState("normal")}
        className="flex items-center gap-2 px-3 py-1.5 bg-[#1e293b] border border-[rgba(42,52,68,0.5)] rounded-lg text-[10px] text-gray-400 hover:text-cyan-300 transition-colors"
      >
        {Icon && <Icon size={11} className="text-gray-500" />}
        <span>{title}</span>
        <span className="text-[9px] text-gray-600">(click to restore)</span>
      </button>
    );
  }

  return (
    <div className={clsx(
      "border border-[rgba(42,52,68,0.5)] rounded-lg bg-[#0B0E14]/90 overflow-hidden shadow-lg",
      className
    )}>
      <div className="flex items-center justify-between px-3 py-1.5 bg-[#1e293b] border-b border-[rgba(42,52,68,0.5)]">
        <div className="flex items-center gap-2">
          {Icon && <Icon size={13} className="text-[#00D9FF]" />}
          <span className="text-[11px] font-semibold text-gray-200">{title}</span>
        </div>
        <div className="flex items-center gap-2">
          {headerRight}
          {windowControls && (
            <div className="flex items-center gap-0.5">
              <button onClick={() => setPanelState(panelState === "minimized" ? "normal" : "minimized")} className="p-0.5 text-gray-500 hover:text-gray-400 transition-colors" aria-label="Minimize">
                <Minimize2 size={10} />
              </button>
              <button onClick={() => setPanelState("normal")} className="p-0.5 text-gray-500 hover:text-gray-400 transition-colors" aria-label="Maximize">
                <Maximize2 size={10} />
              </button>
              <button onClick={() => setPanelState("hidden")} className="p-0.5 text-gray-500 hover:text-red-400 transition-colors" aria-label="Close">
                <X size={10} />
              </button>
            </div>
          )}
        </div>
      </div>
      {panelState !== "minimized" && (
        <div className="p-2">
          {children}
        </div>
      )}
    </div>
  );
}

/** Tiny toggle switch */
function Toggle({ value, onChange, label }) {
  return (
    <button
      onClick={() => onChange?.(!value)}
      className="flex items-center gap-1.5 group"
      title={label}
    >
      <div className={clsx(
        "w-7 h-3.5 rounded-full relative transition-colors",
        value ? "bg-cyan-500" : "bg-gray-700"
      )}>
        <div className={clsx(
          "absolute top-0.5 w-2.5 h-2.5 rounded-full bg-white transition-all",
          value ? "left-[14px]" : "left-0.5"
        )} />
      </div>
      {label && <span className="text-[10px] text-gray-400 group-hover:text-gray-300">{label}</span>}
    </button>
  );
}

/** Small teal button */
function TealButton({ children, onClick, variant = "primary", className, icon: Icon, disabled }) {
  const base = "flex items-center gap-1 px-2 py-1 rounded text-[10px] font-medium transition-all whitespace-nowrap disabled:opacity-40";
  const variants = {
    primary: "bg-cyan-600/80 hover:bg-cyan-500/90 text-white border border-[#00D9FF]/50/40",
    secondary: "bg-gray-800/80 hover:bg-gray-700/90 text-cyan-300 border border-cyan-800/40",
    danger: "bg-red-900/60 hover:bg-red-800/80 text-red-300 border border-red-700/40",
  };
  return (
    <button onClick={onClick} disabled={disabled} className={clsx(base, variants[variant], className)}>
      {Icon && <Icon size={11} />}
      {children}
    </button>
  );
}

/** Horizontal progress bar */
function ProgressBar({ value, max = 100, color = "bg-cyan-500", className }) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));
  return (
    <div className={clsx("h-1.5 rounded-full bg-gray-800 overflow-hidden", className)}>
      <div className={clsx("h-full rounded-full transition-all", color)} style={{ width: `${pct}%` }} />
    </div>
  );
}

/** Status dot */
function StatusDot({ status }) {
  const colors = {
    active: "bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.7)]",
    idle: "bg-amber-400 shadow-[0_0_6px_rgba(251,191,36,0.6)]",
    error: "bg-red-500 shadow-[0_0_6px_rgba(239,68,68,0.7)]",
    stopped: "bg-gray-500",
  };
  return <div className={clsx("w-2 h-2 rounded-full", colors[status] || colors.idle)} />;
}

// ═══════════════════════════════════════════════════
// SCANNER AGENT CARD
// ═══════════════════════════════════════════════════

function ScannerAgentCard({ agent, selected, onSelect }) {
  return (
    <button
      onClick={() => onSelect?.(agent.id)}
      className={clsx(
        "w-full text-left p-2 rounded border transition-all",
        selected
          ? "border-[#00D9FF]/50/60 bg-cyan-950/40 shadow-[0_0_8px_rgba(6,182,212,0.15)]"
          : "border-gray-800/60 bg-gray-900/40 hover:border-cyan-800/40"
      )}
    >
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-1.5">
          <StatusDot status={agent.status} />
          <span className="text-[11px] font-semibold text-cyan-200">{agent.name}</span>
        </div>
        <span className="text-[9px] text-gray-500">{agent.uptime}</span>
      </div>
      <div className="flex items-center gap-3 text-[9px] text-gray-400">
        <span>Type: <span className="text-[#00D9FF]">{agent.type}</span></span>
        <span>Hits: <span className="text-emerald-400">{agent.hits}</span></span>
      </div>
    </button>
  );
}

// ═══════════════════════════════════════════════════
// SCREENING ENGINE (LEFT COLUMN)
// ═══════════════════════════════════════════════════

function SwarmTemplateDropdown({ type, onClose }) {
  const templates = SWARM_TEMPLATES.filter(t => t.type === type || t.type === "both");
  const handleSelect = async (template) => {
    try {
      const r = await fetch(getApiUrl("agents"), {
        method: "POST",
        headers: { "Content-Type": "application/json", ...getAuthHeaders() },
        body: JSON.stringify({ type, action: "spawn_swarm", config: { count: template.agents, template: template.id, name: template.name } }),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      toast.success(`Swarm "${template.name}" spawned (${template.agents} agents)`);
    } catch (e) {
      toast.error(`Spawn swarm failed: ${e.message}`);
    }
    onClose();
  };
  return (
    <div className="absolute z-50 mt-1 w-64 bg-[#1e293b] border border-cyan-800/50 rounded-lg shadow-xl overflow-hidden">
      <div className="px-3 py-2 bg-[#0B0E14] border-b border-gray-700/50 flex items-center justify-between">
        <span className="text-[10px] font-semibold text-cyan-300 uppercase">Swarm Templates</span>
        <button onClick={onClose} className="text-gray-500 hover:text-red-400"><X size={12} /></button>
      </div>
      {templates.map(t => (
        <button key={t.id} onClick={() => handleSelect(t)}
          className="w-full text-left px-3 py-2 hover:bg-cyan-950/40 border-b border-gray-800/30 transition-colors">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-semibold text-cyan-200">{t.name}</span>
            <span className="text-[9px] text-gray-500">{t.agents} agents</span>
          </div>
          <p className="text-[9px] text-gray-500 mt-0.5">{t.desc}</p>
        </button>
      ))}
    </div>
  );
}

function ScreeningEngine() {
  const [selectedScanner, setSelectedScanner] = useState("s1");
  const [scannerName, setScannerName] = useState("AlphaHunter_V4");
  const [scannerType, setScannerType] = useState("Alpha Scanner");
  const [activeTimeframe, setActiveTimeframe] = useState("1M");
  const [showScannerTemplates, setShowScannerTemplates] = useState(false);

  // Trading metric controls - mockup values
  const [betaThreshold, setBetaThreshold] = useState(1.2);
  const [alphaTarget, setAlphaTarget] = useState(15);
  const [mfi, setMfi] = useState(70);
  const [shortInterest, setShortInterest] = useState(10);
  const [relativeStrength, setRelativeStrength] = useState(1.5);
  const [optionsFlowFilter, setOptionsFlowFilter] = useState("Bullish Put Spreads");
  const [volatilityRegime, setVolatilityRegime] = useState("Expansion");
  const [volumeProfile, setVolumeProfile] = useState("Value Area High");
  const [darkPoolActivity, setDarkPoolActivity] = useState(true);
  const [institutionalAccum, setInstitutionalAccum] = useState(true);
  const [sectorMomentum, setSectorMomentum] = useState(true);

  // API data (graceful fallback)
  const { data: signalsData } = useApi("signals", { pollIntervalMs: 30000 });

  return (
    <div className="flex flex-col gap-2 h-full">
      {/* Section Title - mockup: SCREENING ENGINE */}
      <div className="flex items-center gap-2 px-1">
        <Radar size={15} className="text-[#00D9FF]" />
        <span className="text-xs font-bold text-[#00D9FF] uppercase tracking-wider">SCREENING ENGINE</span>
      </div>

      {/* SCAN AGENT FLEET - with filter icon per mockup */}
      <SectionBox title="SCAN AGENT FLEET" icon={Bot} headerRight={<Filter size={10} className="text-gray-400" />} windowControls className="flex-shrink-0">
        {/* Scanner Agent Cards - overlapping stack per mockup */}
        <div className="mb-2 relative">
          {/* Overlapping card effect */}
          <div className="absolute top-1.5 left-1.5 right-1.5 h-16 bg-[#1e293b]/80 rounded border border-gray-700/50 -z-10 transform translate-x-1 translate-y-1" />
          <div className="absolute top-1 left-1 right-1 h-14 bg-[#1e293b]/60 rounded border border-gray-700/40 -z-10 transform translate-x-0.5 translate-y-0.5" />
          <div className="bg-[#1e293b] rounded border border-gray-700/50 overflow-hidden">
            <div className="flex items-center justify-between px-2 py-1 bg-[#0B0E14] border-b border-gray-700/40">
              <span className="text-[10px] text-gray-400">Scanner Agent Cards</span>
              <div className="flex items-center gap-0.5">
                <button className="p-0.5 text-gray-500 hover:text-gray-400 transition-colors" aria-label="Minimize"><Minimize2 size={10} /></button>
                <button className="p-0.5 text-gray-500 hover:text-gray-400 transition-colors" aria-label="Maximize"><Maximize2 size={10} /></button>
                <button className="p-0.5 text-gray-500 hover:text-red-400 transition-colors" aria-label="Close"><X size={10} /></button>
              </div>
            </div>
            <div className="p-2 space-y-2">
              {SCANNER_AGENTS.length > 0 && (
                <div className="flex flex-col gap-1 max-h-[60px] overflow-y-auto scrollbar-thin">
                  {SCANNER_AGENTS.map(a => (
                    <ScannerAgentCard
                      key={a.id}
                      agent={a}
                      selected={a.id === selectedScanner}
                      onSelect={setSelectedScanner}
                    />
                  ))}
                </div>
              )}
              {/* Name, Type, Timeframe - mockup: dropdowns + segment buttons */}
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[9px] text-gray-500 block mb-0.5">Name:</label>
                  <select
                    value={scannerName}
                    onChange={e => setScannerName(e.target.value)}
                    className="w-full bg-[#0B0E14] border border-gray-600 rounded px-1.5 py-0.5 text-[10px] text-cyan-200 focus:outline-none focus:border-cyan-600/60"
                  >
                    {SCANNER_NAMES.map(n => <option key={n} value={n}>[{n}]</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-[9px] text-gray-500 block mb-0.5">Type:</label>
                  <select
                    value={scannerType}
                    onChange={e => setScannerType(e.target.value)}
                    className="w-full bg-[#0B0E14] border border-gray-600 rounded px-1 py-0.5 text-[10px] text-cyan-200 focus:outline-none focus:border-cyan-600/60"
                  >
                    {SCANNER_TYPES.map(t => <option key={t} value={t}>[{t}]</option>)}
                  </select>
                </div>
              </div>
              <div>
                <div className="flex gap-0.5 flex-wrap">
                  {TIMEFRAMES.map(tf => (
                    <button
                      key={tf}
                      onClick={() => setActiveTimeframe(tf)}
                      className={clsx(
                        "px-1.5 py-0.5 rounded text-[8px] font-medium transition-colors",
                        activeTimeframe === tf
                          ? "bg-[#00D9FF] text-white"
                          : "bg-gray-700 text-gray-400 hover:bg-gray-600"
                      )}
                    >
                      {tf}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* TRADING METRIC CONTROLS - mockup: sliders + dropdowns + toggles */}
        <div className="border-t border-gray-700/40 pt-2 mt-2">
          <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-1.5 flex items-center gap-1">
            <Settings size={10} />
            TRADING METRIC CONTROLS
          </div>
          <div>
            <label className="text-[9px] text-gray-500 block mb-0.5">Name</label>
            <input
              type="text"
              value={scannerName}
              onChange={e => setScannerName(e.target.value)}
              className="w-full bg-gray-900/80 border border-cyan-900/40 rounded px-1.5 py-0.5 text-[10px] text-cyan-200 focus:outline-none focus:border-cyan-600/60"
            />
          </div>
          <div>
            <label className="text-[9px] text-gray-500 block mb-0.5">Type</label>
            <select
              value={scannerType}
              onChange={e => setScannerType(e.target.value)}
              className="w-full bg-gray-900/80 border border-cyan-900/40 rounded px-1 py-0.5 text-[10px] text-cyan-200 focus:outline-none focus:border-cyan-600/60 appearance-none"
            >
              {SCANNER_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div>
            <label className="text-[9px] text-gray-500 block mb-0.5">Timeframe</label>
            <div className="flex gap-0.5 flex-wrap">
              {TIMEFRAMES.map(tf => (
                <button
                  key={tf}
                  onClick={() => setActiveTimeframe(tf)}
                  className={clsx(
                    "px-1 py-0.5 rounded text-[8px] font-medium transition-colors",
                    activeTimeframe === tf
                      ? "bg-cyan-600 text-white"
                      : "bg-gray-800 text-gray-400 hover:bg-gray-700"
                  )}
                >
                  {tf}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* TRADING METRIC CONTROLS */}
        <div className="border-t border-cyan-900/30 pt-2">
          <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-1.5 flex items-center gap-1">
            <Settings size={10} />
            Trading Metric Controls
          </div>

          <div className="space-y-1">
            <Slider label="Beta Threshold 0-3" min={0} max={3} step={0.1} value={betaThreshold} onChange={setBetaThreshold}
              formatValue={v => v.toFixed(1)} className="py-0.5" valueClassName="text-[10px] min-w-[2rem]" />
            <Slider label="Alpha Target" min={0} max={50} step={1} value={alphaTarget} onChange={setAlphaTarget}
              suffix="%" formatValue={v => `+${v}%`} className="py-0.5" valueClassName="text-[10px] min-w-[2.5rem]" />
            <Slider label="MFI 0-100" min={0} max={100} step={1} value={mfi} onChange={setMfi}
              className="py-0.5" valueClassName="text-[10px] min-w-[2rem]" />
            <Slider label="Short Interest" min={0} max={100} step={1} value={shortInterest} onChange={setShortInterest}
              suffix="%" formatValue={v => `>${v}%`} className="py-0.5" valueClassName="text-[10px] min-w-[2.5rem]" />
            <Slider label="Relative Strength vs SPX" min={0.5} max={3} step={0.1} value={relativeStrength} onChange={setRelativeStrength}
              formatValue={v => `>${v.toFixed(1)}`} className="py-0.5" valueClassName="text-[10px] min-w-[2.5rem]" />
            <div className="flex items-center justify-between gap-2 py-[3px]">
              <span className="text-[10px] text-gray-400 shrink-0 w-40">Options Flow Filter</span>
              <select value={optionsFlowFilter} onChange={e => setOptionsFlowFilter(e.target.value)}
                className="flex-1 bg-[#0B0E14] border border-gray-600 rounded px-1 py-0.5 text-[10px] text-cyan-200 focus:outline-none">
                {OPTIONS_FLOW_OPTS.map(o => <option key={o} value={o}>{o}</option>)}
              </select>
            </div>
            <div className="flex items-center justify-between gap-2 py-[3px]">
              <span className="text-[10px] text-gray-400 shrink-0 w-40">Volatility Regime</span>
              <select value={volatilityRegime} onChange={e => setVolatilityRegime(e.target.value)}
                className="flex-1 bg-[#0B0E14] border border-gray-600 rounded px-1 py-0.5 text-[10px] text-cyan-200 focus:outline-none">
                {VOLATILITY_REGIMES.map(v => <option key={v} value={v}>{v}</option>)}
              </select>
            </div>
            <div className="flex items-center justify-between gap-2 py-[3px]">
              <span className="text-[10px] text-gray-400 shrink-0 w-40">Volume Profile</span>
              <select value={volumeProfile} onChange={e => setVolumeProfile(e.target.value)}
                className="flex-1 bg-[#0B0E14] border border-gray-600 rounded px-1 py-0.5 text-[10px] text-cyan-200 focus:outline-none">
                {VOLUME_PROFILES.map(v => <option key={v} value={v}>{v}</option>)}
              </select>
            </div>
            <div className="flex items-center justify-between py-[3px]">
              <span className="text-[10px] text-gray-400">Dark Pool Activity</span>
              <div className="flex items-center gap-1">
                <Toggle value={darkPoolActivity} onChange={setDarkPoolActivity} />
                <span className="text-[10px] text-[#00D9FF]">{darkPoolActivity ? "ON" : "OFF"}</span>
              </div>
            </div>
            <div className="flex items-center justify-between py-[3px]">
              <span className="text-[10px] text-gray-400">Institutional Accumulation</span>
              <div className="flex items-center gap-1">
                <Toggle value={institutionalAccum} onChange={setInstitutionalAccum} />
                <span className="text-[10px] text-[#00D9FF]">{institutionalAccum ? "ON" : "OFF"}</span>
              </div>
            </div>
            <div className="flex items-center justify-between py-[3px]">
              <span className="text-[10px] text-gray-400">Sector Momentum</span>
              <div className="flex items-center gap-1">
                <Toggle value={sectorMomentum} onChange={setSectorMomentum} />
                <span className="text-[10px] text-[#00D9FF]">{sectorMomentum ? "ON" : "OFF"}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Action buttons - mockup: + Spawn, Clone, Spawn Swarm (green), Swarm Templates (red), Kill All (red) */}
        <div className="flex flex-wrap gap-1.5 mt-2 pt-2 border-t border-gray-700/40">
          <TealButton icon={Plus} onClick={async () => { try { const r = await fetch(getApiUrl("agents"), { method: "POST", headers: { "Content-Type": "application/json", ...getAuthHeaders() }, body: JSON.stringify({ type: "scanner", action: "spawn" }) }); if (!r.ok) throw new Error(`HTTP ${r.status}`); toast.success("Scanner agent spawned"); } catch (e) { toast.error(`Spawn failed: ${e.message}`); } }}>+ Spawn New Scanner Agent</TealButton>
          <TealButton icon={Copy} onClick={async () => { try { const r = await fetch(getApiUrl("agents"), { method: "POST", headers: { "Content-Type": "application/json", ...getAuthHeaders() }, body: JSON.stringify({ type: "scanner", action: "clone" }) }); if (!r.ok) throw new Error(`HTTP ${r.status}`); toast.success("Agent cloned"); } catch (e) { toast.error(`Clone failed: ${e.message}`); } }} className="!text-emerald-400 !border-emerald-500/40 !bg-emerald-500/20">Clone Agent</TealButton>
          <TealButton icon={Boxes} onClick={async () => { try { const r = await fetch(getApiUrl("agents"), { method: "POST", headers: { "Content-Type": "application/json", ...getAuthHeaders() }, body: JSON.stringify({ type: "scanner", action: "spawn_swarm" }) }); if (!r.ok) throw new Error(`HTTP ${r.status}`); toast.success("Swarm spawned"); } catch (e) { toast.error(`Spawn swarm failed: ${e.message}`); } }} className="!text-emerald-400 !border-emerald-500/40 !bg-emerald-500/20">Spawn Swarm</TealButton>
          <div className="relative">
            <TealButton icon={Layers} variant="danger" onClick={() => setShowScannerTemplates(v => !v)}>Swarm Templates</TealButton>
            {showScannerTemplates && <SwarmTemplateDropdown type="scanner" onClose={() => setShowScannerTemplates(false)} />}
          </div>
          <TealButton icon={Trash2} variant="danger" onClick={async () => { if (!window.confirm("Kill ALL scanner agents?")) return; try { const r = await fetch(getApiUrl("agents") + "/batch/stop", { method: "POST", headers: { "Content-Type": "application/json", ...getAuthHeaders() }, body: JSON.stringify({ type: "scanner" }) }); if (!r.ok) throw new Error(`HTTP ${r.status}`); toast.success("All scanner agents killed"); } catch (e) { toast.error(`Kill failed: ${e.message}`); } }}>Kill All Agents</TealButton>
        </div>
      </SectionBox>
    </div>
  );
}

// ═══════════════════════════════════════════════════
// PATTERN AGENT CARD
// ═══════════════════════════════════════════════════

function PatternAgentCard({ agent, selected, onSelect }) {
  return (
    <button
      onClick={() => onSelect?.(agent.id)}
      className={clsx(
        "w-full text-left p-2 rounded border transition-all",
        selected
          ? "border-[#00D9FF]/50/60 bg-cyan-950/40 shadow-[0_0_8px_rgba(6,182,212,0.15)]"
          : "border-gray-800/60 bg-gray-900/40 hover:border-cyan-800/40"
      )}
    >
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-1.5">
          <StatusDot status={agent.status} />
          <span className="text-[11px] font-semibold text-cyan-200">{agent.name}</span>
        </div>
        <span className="text-[9px] text-emerald-400">{agent.accuracy}%</span>
      </div>
      <div className="flex items-center gap-3 text-[9px] text-gray-400">
        <span>Type: <span className="text-[#00D9FF]">{agent.type}</span></span>
        <span>Arch: <span className="text-purple-400">{agent.architecture}</span></span>
        <span>Found: <span className="text-emerald-400">{agent.patternsFound}</span></span>
      </div>
    </button>
  );
}

// ═══════════════════════════════════════════════════
// PATTERN INTELLIGENCE (RIGHT COLUMN)
// ═══════════════════════════════════════════════════

function PatternIntelligence() {
  const [selectedPattern, setSelectedPattern] = useState("p1");
  const [patternName, setPatternName] = useState("Fractal_Prophet_G4");
  const [showPatternTemplates, setShowPatternTemplates] = useState(false);
  const [llmModel, setLlmModel] = useState("GPT-4");
  const [architecture, setArchitecture] = useState("Transformer");

  // ML Metric Controls - mockup values
  const [recursiveSelfImprove, setRecursiveSelfImprove] = useState(true);
  const [academicValidation, setAcademicValidation] = useState(94.5);
  const [sharpeRatio, setSharpeRatio] = useState(3.2);
  const [profitFactor, setProfitFactor] = useState(2.8);
  const [maxDrawdown, setMaxDrawdown] = useState(12);
  const [walkForwardEff, setWalkForwardEff] = useState(88);
  const [outOfSampleAcc, setOutOfSampleAcc] = useState(79);
  const [monteCarloCI, setMonteCarloCI] = useState("95%");
  const [patternComplexity, setPatternComplexity] = useState("Compound");
  const [swarmSize, setSwarmSize] = useState(50);

  // API data
  const { data: patternsData } = useApi("patterns", { pollIntervalMs: 30000 });

  return (
    <div className="flex flex-col gap-2 h-full">
      {/* Section Title - mockup: PATTERN INTELLIGENCE */}
      <div className="flex items-center gap-2 px-1">
        <Brain size={15} className="text-[#00D9FF]" />
        <span className="text-xs font-bold text-[#00D9FF] uppercase tracking-wider">PATTERN INTELLIGENCE</span>
      </div>

      {/* PATTERN AGENT FLEET - with filter icon */}
      <SectionBox title="PATTERN AGENT FLEET" icon={Cpu} headerRight={<Filter size={10} className="text-gray-400" />} windowControls className="flex-shrink-0">
        {/* Pattern Agent Cards - overlapping stack */}
        <div className="mb-2 relative">
          <div className="absolute top-1.5 left-1.5 right-1.5 h-16 bg-[#1e293b]/80 rounded border border-gray-700/50 -z-10 transform translate-x-1 translate-y-1" />
          <div className="absolute top-1 left-1 right-1 h-14 bg-[#1e293b]/60 rounded border border-gray-700/40 -z-10 transform translate-x-0.5 translate-y-0.5" />
          <div className="bg-[#1e293b] rounded border border-gray-700/50 overflow-hidden">
            <div className="flex items-center justify-between px-2 py-1 bg-[#0B0E14] border-b border-gray-700/40">
              <span className="text-[10px] text-gray-400">Pattern Agent Cards</span>
              <div className="flex items-center gap-0.5">
                <button className="p-0.5 text-gray-500 hover:text-gray-400 transition-colors" aria-label="Minimize"><Minimize2 size={10} /></button>
                <button className="p-0.5 text-gray-500 hover:text-gray-400 transition-colors" aria-label="Maximize"><Maximize2 size={10} /></button>
                <button className="p-0.5 text-gray-500 hover:text-red-400 transition-colors" aria-label="Close"><X size={10} /></button>
              </div>
            </div>
            <div className="p-2 space-y-2">
              {PATTERN_AGENTS.length > 0 && (
                <div className="flex flex-col gap-1 max-h-[60px] overflow-y-auto scrollbar-thin">
                  {PATTERN_AGENTS.map(a => (
                    <PatternAgentCard key={a.id} agent={a} selected={a.id === selectedPattern} onSelect={setSelectedPattern} />
                  ))}
                </div>
              )}
              {/* Name, LLM Model, ML Architecture - mockup */}
              <div className="grid grid-cols-1 gap-2">
                <div>
                  <label className="text-[9px] text-gray-500 block mb-0.5">Name:</label>
                  <select value={patternName} onChange={e => setPatternName(e.target.value)}
                    className="w-full bg-[#0B0E14] border border-gray-600 rounded px-1.5 py-0.5 text-[10px] text-cyan-200 focus:outline-none">
                    <option value="Fractal_Prophet_G4">[Fractal_Prophet_G4]</option>
                    <option value="Wyckoff_Agent_v2">[Wyckoff_Agent_v2]</option>
                    <option value="Elliott_Harmonic_G3">[Elliott_Harmonic_G3]</option>
                  </select>
                </div>
                <div>
                  <label className="text-[9px] text-gray-500 block mb-0.5">LLM Model:</label>
                  <select value={llmModel} onChange={e => setLlmModel(e.target.value)}
                    className="w-full bg-[#0B0E14] border border-gray-600 rounded px-1 py-0.5 text-[10px] text-cyan-200 focus:outline-none">
                    {LLM_MODELS.map(m => <option key={m} value={m}>[{m}]</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-[9px] text-gray-500 block mb-0.5">ML Architecture:</label>
                  <select value={architecture} onChange={e => setArchitecture(e.target.value)}
                    className="w-full bg-[#0B0E14] border border-gray-600 rounded px-1 py-0.5 text-[10px] text-cyan-200 focus:outline-none">
                    {ML_ARCHITECTURES.map(a => <option key={a} value={a}>[{a}]</option>)}
                  </select>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* ML METRIC CONTROLS - mockup */}
        <div className="border-t border-gray-700/40 pt-2 mt-2">
          <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-1.5">ML METRIC CONTROLS</div>
          <div className="space-y-1">
            <div className="flex items-center justify-between py-[3px]">
              <span className="text-[10px] text-gray-400">Recursive Self-Improvement</span>
              <div className="flex items-center gap-1">
                <Toggle value={recursiveSelfImprove} onChange={setRecursiveSelfImprove} />
                <span className="text-[10px] text-[#00D9FF]">{recursiveSelfImprove ? "ON" : "OFF"}</span>
              </div>
            </div>
            <Slider label="Academic Validation Score %" min={0} max={100} step={0.1} value={academicValidation} onChange={setAcademicValidation}
              suffix="%" formatValue={v => v.toFixed(1)} className="py-0.5" valueClassName="text-[10px] min-w-[3rem]" />
            <Slider label="Sharpe Ratio" min={0} max={5} step={0.1} value={sharpeRatio} onChange={setSharpeRatio}
              formatValue={v => v.toFixed(1)} className="py-0.5" valueClassName="text-[10px] min-w-[2rem]" />
            <Slider label="Profit Factor" min={0} max={5} step={0.1} value={profitFactor} onChange={setProfitFactor}
              formatValue={v => v.toFixed(1)} className="py-0.5" valueClassName="text-[10px] min-w-[2rem]" />
            <Slider label="Max Drawdown" min={0} max={30} step={1} value={maxDrawdown} onChange={setMaxDrawdown}
              suffix="" formatValue={v => `<${v}%`} className="py-0.5" valueClassName="text-[10px] text-red-400 min-w-[2.5rem]" />
            <Slider label="Walk-Forward Efficiency" min={0} max={100} step={1} value={walkForwardEff} onChange={setWalkForwardEff}
              suffix="%" className="py-0.5" valueClassName="text-[10px] min-w-[2.5rem]" />
            <Slider label="Out-of-Sample Accuracy" min={0} max={100} step={1} value={outOfSampleAcc} onChange={setOutOfSampleAcc}
              suffix="%" className="py-0.5" valueClassName="text-[10px] min-w-[2.5rem]" />
            <div className="flex items-center justify-between gap-2 py-[3px]">
              <span className="text-[10px] text-gray-400 shrink-0 w-40">Monte Carlo CI (90/95/99%)</span>
              <select value={monteCarloCI} onChange={e => setMonteCarloCI(e.target.value)}
                className="flex-1 bg-[#0B0E14] border border-gray-600 rounded px-1 py-0.5 text-[10px] text-cyan-200 focus:outline-none">
                <option value="90%">90%</option>
                <option value="95%">95%</option>
                <option value="99%">99%</option>
              </select>
            </div>
            <div className="flex items-center justify-between gap-2 py-[3px]">
              <span className="text-[10px] text-gray-400 shrink-0 w-40">Pattern Complexity</span>
              <select value={patternComplexity} onChange={e => setPatternComplexity(e.target.value)}
                className="flex-1 bg-[#0B0E14] border border-gray-600 rounded px-1 py-0.5 text-[10px] text-cyan-200 focus:outline-none">
                {PATTERN_COMPLEXITY_OPTS.map(p => <option key={p} value={p}>{p}</option>)}
              </select>
            </div>
            <div className="flex items-center justify-between gap-2 py-[3px]">
              <span className="text-[10px] text-gray-400 shrink-0 w-40">Sub-Agent Swarm Size</span>
              <input type="number" value={swarmSize} onChange={e => setSwarmSize(Number(e.target.value) || 0)}
                className="w-16 bg-[#0B0E14] border border-gray-600 rounded px-1 py-0.5 text-[10px] text-cyan-200 focus:outline-none text-right"
                placeholder="[50]" />
            </div>
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex flex-wrap gap-1.5 mt-2 pt-2 border-t border-gray-700/40">
          <TealButton icon={Plus} onClick={async () => { try { const r = await fetch(getApiUrl("agents"), { method: "POST", headers: { "Content-Type": "application/json", ...getAuthHeaders() }, body: JSON.stringify({ type: "pattern", action: "spawn" }) }); if (!r.ok) throw new Error(`HTTP ${r.status}`); toast.success("Pattern agent spawned"); } catch (e) { toast.error(`Spawn failed: ${e.message}`); } }}>+ Spawn New Pattern Agent</TealButton>
          <TealButton icon={Boxes} onClick={async () => { try { const r = await fetch(getApiUrl("agents"), { method: "POST", headers: { "Content-Type": "application/json", ...getAuthHeaders() }, body: JSON.stringify({ type: "pattern", action: "spawn_swarm" }) }); if (!r.ok) throw new Error(`HTTP ${r.status}`); toast.success("Discovery swarm spawned"); } catch (e) { toast.error(`Spawn swarm failed: ${e.message}`); } }} className="!text-emerald-400 !border-emerald-500/40 !bg-emerald-500/20">Spawn Discovery Swarm</TealButton>
          <div className="relative">
            <TealButton icon={Layers} variant="danger" onClick={() => setShowPatternTemplates(v => !v)}>Swarm Templates</TealButton>
            {showPatternTemplates && <SwarmTemplateDropdown type="pattern" onClose={() => setShowPatternTemplates(false)} />}
          </div>
          <TealButton icon={Trash2} variant="danger" onClick={async () => { if (!window.confirm("Kill ALL pattern agents?")) return; try { const r = await fetch(getApiUrl("agents") + "/batch/stop", { method: "POST", headers: { "Content-Type": "application/json", ...getAuthHeaders() }, body: JSON.stringify({ type: "pattern" }) }); if (!r.ok) throw new Error(`HTTP ${r.status}`); toast.success("All pattern agents killed"); } catch (e) { toast.error(`Kill failed: ${e.message}`); } }}>Kill All Pattern Agents</TealButton>
        </div>
      </SectionBox>
    </div>
  );
}

// ═══════════════════════════════════════════════════
// BOTTOM PANELS: Live Feed, Pattern Arsenal, Forming Detections
// ═══════════════════════════════════════════════════

function FormingDetectionCard({ pattern }) {
  const title = pattern.symbol
    ? `${pattern.symbol} | ${pattern.name} | ${pattern.confidence}% Confidence`
    : `${pattern.name} | ${pattern.confidence}% Confidence`;
  return (
    <div className="border border-gray-700/50 rounded bg-[#1e293b]/60 p-1.5">
      <div className="flex items-center justify-between mb-1">
        <span className="text-[9px] font-semibold text-cyan-200 truncate">{title}</span>
      </div>
      <ResponsiveContainer width="100%" height={40}>
        <AreaChart data={pattern.data || []}>
          <defs>
            <linearGradient id={`fd-${pattern.id}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#00D9FF" stopOpacity={0.3} />
              <stop offset="100%" stopColor="#00D9FF" stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <Area type="monotone" dataKey="y" stroke="#00D9FF" strokeWidth={1.2} fill={`url(#fd-${pattern.id})`} dot={false} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

// Consolidated Live Feed — pulls from /patterns/feed
function ConsolidatedLiveFeed() {
  const { data: feedData, loading, error } = useApi('patternFeed', { pollIntervalMs: 30000 });
  const feedEntries = feedData?.entries || feedData?.feed || [];
  const feedRef = useRef(null);

  return (
    <SectionBox title="Consolidated Live Feed" icon={Radio} windowControls className="flex-1 min-h-0 flex flex-col">
      <div ref={feedRef} className="flex-1 overflow-y-auto scrollbar-thin space-y-0 min-h-0 max-h-[200px]">
        {feedEntries.length === 0 ? (
          <div className="flex items-center justify-center h-full py-6">
            <span className="text-[10px] text-gray-600">
              {loading ? "Loading feed..." : error ? "Feed unavailable — retrying..." : "No feed data — awaiting pattern detections"}
            </span>
          </div>
        ) : feedEntries.map((entry, i) => (
          <div key={entry.id ?? i} className="flex items-start gap-2 py-[3px] border-b border-gray-800/30 hover:bg-cyan-950/20 px-1 text-[10px] font-mono">
            <span className="text-gray-600 whitespace-nowrap">{entry.timestamp ? new Date(entry.timestamp).toLocaleTimeString() : ""}</span>
            <span className="font-bold min-w-[36px] text-[#00D9FF]">{entry.symbol}</span>
            <span className={clsx("min-w-[12px]", entry.direction === "bullish" ? "text-emerald-400" : entry.direction === "bearish" ? "text-red-400" : "text-gray-400")}>
              {entry.direction === "bullish" ? "▲" : entry.direction === "bearish" ? "▼" : "●"}
            </span>
            <span className="text-gray-300 truncate">{entry.pattern || entry.action}</span>
            {entry.confidence > 0 && <span className="text-gray-500 ml-auto shrink-0">{entry.confidence}%</span>}
          </div>
        ))}
      </div>
    </SectionBox>
  );
}

// Pattern Arsenal — clickable pattern cards with detail view
function PatternArsenalPanel() {
  const [selectedPattern, setSelectedPattern] = useState(null);

  return (
    <SectionBox title="Pattern Arsenal" icon={Target} windowControls className="flex-1 min-h-0 flex flex-col">
      {selectedPattern ? (
        <div className="p-2">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[11px] font-semibold text-cyan-200">{selectedPattern.name}</span>
            <button onClick={() => setSelectedPattern(null)} className="text-gray-500 hover:text-gray-300"><X size={12} /></button>
          </div>
          <div className="space-y-1.5 text-[10px] text-gray-400">
            <p>{selectedPattern.name} is a classic chart pattern used to identify potential trend reversals or continuations.</p>
            <div className="flex items-center justify-between">
              <span>Category:</span>
              <span className="text-cyan-300">{["Wyckoff Accumulation", "Elliot Wave 3"].includes(selectedPattern.name) ? "Continuation" : "Reversal"}</span>
            </div>
            <div className="flex items-center justify-between">
              <span>Timeframes:</span>
              <span className="text-cyan-300">1H, 4H, D</span>
            </div>
            <div className="flex items-center justify-between">
              <span>Status:</span>
              <span className="text-emerald-400">Active</span>
            </div>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-3 gap-3 py-2">
          {PATTERNS_ARSENAL_DISPLAY.map(p => (
            <button key={p.id} onClick={() => setSelectedPattern(p)} className="flex flex-col items-center gap-1.5 group cursor-pointer">
              <div className="w-12 h-12 rounded-full bg-[#1e293b] border-2 border-[#00D9FF]/40 flex items-center justify-center text-white font-bold text-lg shadow-[0_0_8px_rgba(0,217,255,0.2)] group-hover:border-[#00D9FF] group-hover:shadow-[0_0_12px_rgba(0,217,255,0.4)] transition-all">
                {p.icon}
              </div>
              <span className="text-[10px] text-gray-300 text-center leading-tight group-hover:text-cyan-200 transition-colors">{p.name}</span>
            </button>
          ))}
        </div>
      )}
    </SectionBox>
  );
}

// Forming Detections — pulls from /patterns/forming
function FormingDetectionsPanel() {
  const { data: formingData, loading, error } = useApi('patternForming', { pollIntervalMs: 30000 });
  const forming = formingData?.detections || formingData?.forming || [];

  return (
    <SectionBox title="Forming Detections" icon={Crosshair} windowControls className="flex-1 min-h-0 flex flex-col">
      <div className="flex-1 overflow-y-auto scrollbar-thin space-y-1.5 max-h-[200px]">
        {forming.length === 0 ? (
          <div className="flex items-center justify-center h-full py-6">
            <span className="text-[10px] text-gray-600">
              {loading ? "Loading..." : error ? "Unavailable — retrying..." : "No forming detections — patterns below 70% confidence appear here"}
            </span>
          </div>
        ) : forming.map((f, i) => (
          <FormingDetectionCard key={f.id ?? i} pattern={f} />
        ))}
      </div>
    </SectionBox>
  );
}

// ═══════════════════════════════════════════════════
// MAIN PAGE
// ═══════════════════════════════════════════════════

export default function Patterns() {
  const { data: agentsData } = useApi("agents", { pollIntervalMs: 30000 });
  const { data: patternsData } = useApi("patterns", { pollIntervalMs: 30000 });
  const { data: statusData } = useApi("status", { pollIntervalMs: 30000 });

  const agentCount = agentsData?.agents?.length ?? "—";
  const patternCount = patternsData?.count ?? "—";
  const wsConnections = statusData?.websocket_connections ?? statusData?.connections ?? "—";

  return (
    <div className="flex flex-col h-full min-h-0 p-4 gap-3">
      {/* Page Title - centered per mockup */}
      <div className="flex flex-col items-center justify-center shrink-0 text-center">
        <h1 className="text-lg font-bold text-[#00D9FF] tracking-widest uppercase font-mono">
          SCREENER AND PATTERNS
        </h1>
      </div>

      {/* Two-column layout - top section */}
      <div className="flex-1 min-h-0 grid grid-cols-2 gap-3">
        {/* LEFT - Screening Engine */}
        <div className="min-h-0 overflow-y-auto scrollbar-thin pr-1">
          <ScreeningEngine />
        </div>

        {/* RIGHT - Pattern Intelligence */}
        <div className="min-h-0 overflow-y-auto scrollbar-thin pr-1">
          <PatternIntelligence />
        </div>
      </div>

      {/* Bottom section: 3 panels side by side */}
      <div className="flex-shrink-0 grid grid-cols-3 gap-2">
        <ConsolidatedLiveFeed />
        <PatternArsenalPanel />
        <FormingDetectionsPanel />
      </div>

      {/* Footer status bar — sourced from real API data */}
      <div className="flex-shrink-0 flex items-center justify-between px-3 py-1.5 bg-[#0B0E14] border border-[rgba(42,52,68,0.5)] rounded text-[9px] text-gray-500">
        <div className="flex items-center gap-3">
          <span>Connections: <span className="text-[#00D9FF]">{wsConnections}</span></span>
          <span className="text-gray-600">|</span>
          <span>Agents <span className="text-[#00D9FF]">{agentCount}</span></span>
          <span className="text-gray-600">|</span>
          <span>Patterns <span className="text-[#00D9FF]">{patternCount}</span></span>
          <span className="text-gray-600">|</span>
          <span>Scans <span className="text-[#00D9FF]">—</span></span>
        </div>
        <div className="flex items-center gap-2">
          <span>GPU <span className="text-gray-400">N/A</span></span>
          <div className="w-16 h-1.5 rounded-full bg-gray-700 overflow-hidden">
            <div className="h-full rounded-full bg-gray-600" style={{ width: "0%" }} />
          </div>
          <div className="flex items-center gap-1">
            <div className={clsx("w-1.5 h-1.5 rounded-full", agentsData ? "bg-emerald-400 animate-pulse" : "bg-gray-500")} />
            <span>{agentsData ? "Live" : "—"}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
