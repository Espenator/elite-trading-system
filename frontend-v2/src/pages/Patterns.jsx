// SCREENER AND PATTERNS - Embodier.ai Trading Intelligence System
// Mockup: 07-screener-and-patterns.png
// 3-column layout: Screening Engine (left) | Pattern Intelligence (center) | Coverage & Results (right)
// Bottom: Consolidated Live Feed | Pattern Arsenal | Forming Detections
// Backend: GET /api/v1/patterns, /api/v1/agents, /api/v1/signals; POST agents/spawn, clone, swarm, kill-all
// Uses: useApi, useSettings, Recharts, lucide-react, Aurora dark theme

import React, { useState, useEffect, useRef, useCallback, useMemo } from "react";
import {
  Filter, Brain, Copy, Trash2, Plus, Bot, Cpu, Layers, Settings,
  Radio, Radar, Crosshair, Boxes, Target,
} from "lucide-react";
import { AreaChart, Area, ResponsiveContainer } from "recharts";
import clsx from "clsx";
import { toast } from "react-toastify";
import { useApi } from "../hooks/useApi";
import { useSettings } from "../hooks/useSettings";
import Slider from "../components/ui/Slider";
import log from "@/utils/logger";
import { getApiUrl, getAuthHeaders } from "../config/api";

// ═══════════════════════════════════════════════════
// CONFIG & CONSTANTS (no mock data)
// ═══════════════════════════════════════════════════

const TIMEFRAMES = ["1M", "5M", "15M", "1H", "4H", "D", "W"];

const SCANNER_TYPES = [
  "Alpha Scanner", "Momentum Scanner", "Mean Reversion", "Breakout Hunter",
  "Volume Profiler", "Dark Pool Tracker", "Options Flow", "Sector Rotator",
];

const VOLATILITY_REGIMES = ["Expansion", "Contraction", "Normal", "Extreme"];
const VOLUME_PROFILES = ["Value Area High", "Value Area Low", "POC", "HVN", "LVN"];
const OPTIONS_FLOW_OPTS = ["Bullish Put Spreads", "Bearish Call Spreads", "Iron Condor", "Straddle", "Strangle"];
const ML_ARCHITECTURES = ["Transformer", "LSTM", "CNN-LSTM", "Attention-Net"];
const PATTERN_COMPLEXITY_OPTS = ["Simple", "Compound", "Multi-Timeframe"];
const PATTERN_ICON_MAP = { wyckoff: "W", elliott: "E", "head_shoulders": "H", cup_handle: "C", flag: "B", wedge: "R" };

// ═══════════════════════════════════════════════════
// STYLED SUB-COMPONENTS (Aurora: bg #0a0e1a, panels #111827, accent #00D9FF)
// ═══════════════════════════════════════════════════

/** Section wrapper with panel title (no window controls) */
function SectionBox({ title, icon: Icon, children, className, headerRight }) {
  return (
    <div className={clsx(
      "border border-[rgba(42,52,68,0.5)] rounded-lg bg-[#111827] overflow-hidden shadow-lg",
      className
    )}>
      <div className="flex items-center justify-between px-3 py-1.5 bg-[#1e293b] border-b border-[rgba(42,52,68,0.5)]">
        <div className="flex items-center gap-2">
          {Icon && <Icon size={13} className="text-[#00D9FF]" />}
          <span className="text-[11px] font-semibold text-gray-200">{title}</span>
        </div>
        {headerRight && <div className="flex items-center gap-2">{headerRight}</div>}
      </div>
      <div className="p-2">
        {children}
      </div>
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
  const type = agent.type ?? agent.config?.sources?.[0] ?? agent.name;
  const hits = agent.hits ?? (agent.last_actions?.length ?? 0);
  return (
    <button
      onClick={() => onSelect?.(agent.id)}
      className={clsx(
        "w-full text-left p-2 rounded border transition-all",
        selected
          ? "border-[#00D9FF]/50 bg-cyan-950/40 shadow-[0_0_8px_rgba(6,182,212,0.15)]"
          : "border-gray-800/60 bg-gray-900/40 hover:border-cyan-800/40"
      )}
    >
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-1.5">
          <StatusDot status={agent.status} />
          <span className="text-[11px] font-semibold text-cyan-200">{agent.name}</span>
        </div>
        <span className="text-[9px] text-gray-500">{agent.uptime ?? "—"}</span>
      </div>
      <div className="flex items-center gap-3 text-[9px] text-gray-400">
        <span>Type: <span className="text-[#00D9FF]">{type}</span></span>
        <span>Hits: <span className="text-emerald-400">{hits}</span></span>
      </div>
    </button>
  );
}

// ═══════════════════════════════════════════════════
// SCREENING ENGINE (LEFT COLUMN)
// ═══════════════════════════════════════════════════

function ScreeningEngine({ onOpenTemplates, onKillAllConfirm }) {
  const { data: agentsData, refetch: refetchAgents } = useApi("agents", { pollIntervalMs: 15000 });
  const { settings, updateField, saveCategory } = useSettings();
  const category = "screener";
  const screener = settings?.[category] ?? {};

  const [selectedScanner, setSelectedScanner] = useState(null);
  const [scannerName, setScannerName] = useState(screener.scannerName ?? "");
  const [scannerType, setScannerType] = useState(screener.scannerType ?? "Alpha Scanner");
  const [activeTimeframe, setActiveTimeframe] = useState(screener.activeTimeframe ?? "1M");
  const [betaThreshold, setBetaThreshold] = useState(screener.betaThreshold ?? 1.2);
  const [alphaTarget, setAlphaTarget] = useState(screener.alphaTarget ?? 15);
  const [mfi, setMfi] = useState(screener.mfi ?? 70);
  const [shortInterest, setShortInterest] = useState(screener.shortInterest ?? 10);
  const [relativeStrength, setRelativeStrength] = useState(screener.relativeStrength ?? 1.5);
  const [optionsFlowFilter, setOptionsFlowFilter] = useState(screener.optionsFlowFilter ?? "Bullish Put Spreads");
  const [volatilityRegime, setVolatilityRegime] = useState(screener.volatilityRegime ?? "Expansion");
  const [volumeProfile, setVolumeProfile] = useState(screener.volumeProfile ?? "Value Area High");
  const [darkPoolActivity, setDarkPoolActivity] = useState(screener.darkPoolActivity !== false);
  const [institutionalAccum, setInstitutionalAccum] = useState(screener.institutionalAccum !== false);
  const [sectorMomentum, setSectorMomentum] = useState(screener.sectorMomentum !== false);
  const [pendingSave, setPendingSave] = useState(false);

  useEffect(() => {
    if (!settings?.[category]) return;
    const s = settings[category];
    setScannerName(s.scannerName ?? "");
    setScannerType(s.scannerType ?? "Alpha Scanner");
    setActiveTimeframe(s.activeTimeframe ?? "1M");
    setBetaThreshold(s.betaThreshold ?? 1.2);
    setAlphaTarget(s.alphaTarget ?? 15);
    setMfi(s.mfi ?? 70);
    setShortInterest(s.shortInterest ?? 10);
    setRelativeStrength(s.relativeStrength ?? 1.5);
    setOptionsFlowFilter(s.optionsFlowFilter ?? "Bullish Put Spreads");
    setVolatilityRegime(s.volatilityRegime ?? "Expansion");
    setVolumeProfile(s.volumeProfile ?? "Value Area High");
    setDarkPoolActivity(s.darkPoolActivity !== false);
    setInstitutionalAccum(s.institutionalAccum !== false);
    setSectorMomentum(s.sectorMomentum !== false);
  }, [settings, category]);

  const scannerAgents = useMemo(() => {
    const list = agentsData?.agents ?? [];
    return list.filter(a => a.name && (a.config?.sources || a.name.toLowerCase().includes("market") || a.name.toLowerCase().includes("signal") || a.name.toLowerCase().includes("scanner")));
  }, [agentsData]);
  const scannerNames = useMemo(() => [...new Set([...(scannerAgents.map(a => a.name)), scannerName].filter(Boolean))], [scannerAgents, scannerName]);

  const settingsBase = getApiUrl("settings");
  const handleSaveScannerConfig = useCallback(async () => {
    const payload = { ...(settings?.[category] ?? {}), scannerName, scannerType, activeTimeframe };
    try {
      const res = await fetch(`${settingsBase}/${category}`, { method: "PUT", headers: { "Content-Type": "application/json", ...getAuthHeaders() }, body: JSON.stringify(payload) });
      if (res.ok) setPendingSave(false);
    } catch { /* no-op */ }
  }, [category, scannerName, scannerType, activeTimeframe, settings, settingsBase]);

  const handleSaveTradingMetrics = useCallback(async () => {
    const payload = { ...(settings?.[category] ?? {}), betaThreshold, alphaTarget, mfi, shortInterest, relativeStrength, optionsFlowFilter, volatilityRegime, volumeProfile, darkPoolActivity, institutionalAccum, sectorMomentum };
    try {
      const res = await fetch(`${settingsBase}/${category}`, { method: "PUT", headers: { "Content-Type": "application/json", ...getAuthHeaders() }, body: JSON.stringify(payload) });
      if (res.ok) setPendingSave(false);
    } catch { /* no-op */ }
  }, [category, betaThreshold, alphaTarget, mfi, shortInterest, relativeStrength, optionsFlowFilter, volatilityRegime, volumeProfile, darkPoolActivity, institutionalAccum, sectorMomentum, settings, settingsBase]);

  const postSpawn = useCallback(async () => {
    try {
      const res = await fetch(getApiUrl("agents/spawn"), { method: "POST", headers: { "Content-Type": "application/json", ...getAuthHeaders() }, body: JSON.stringify({ name: scannerName || "Scanner", type: scannerType }) });
      if (res.ok) {
        refetchAgents();
        toast.success("Scanner agent spawned");
      } else {
        const err = await res.json().catch(() => ({}));
        toast.error(err?.detail ?? `Spawn failed (${res.status})`);
      }
    } catch (e) {
      toast.error("Spawn failed: " + (e?.message || "network error"));
    }
  }, [scannerName, scannerType, refetchAgents]);
  const postClone = useCallback(async () => {
    if (selectedScanner == null) return;
    try {
      const res = await fetch(getApiUrl("agents/clone"), { method: "POST", headers: { "Content-Type": "application/json", ...getAuthHeaders() }, body: JSON.stringify({ agent_id: selectedScanner }) });
      if (res.ok) {
        refetchAgents();
        toast.success("Agent cloned");
      } else {
        const err = await res.json().catch(() => ({}));
        toast.error(err?.detail ?? `Clone failed (${res.status})`);
      }
    } catch (e) {
      toast.error("Clone failed: " + (e?.message || "network error"));
    }
  }, [selectedScanner, refetchAgents]);
  const postSwarmSpawn = useCallback(async () => {
    try {
      const res = await fetch(getApiUrl("agents/swarm/spawn"), { method: "POST", headers: { "Content-Type": "application/json", ...getAuthHeaders() }, body: JSON.stringify({}) });
      if (res.ok) {
        refetchAgents();
        toast.success("Swarm spawn requested");
      } else {
        const err = await res.json().catch(() => ({}));
        toast.error(err?.detail ?? `Swarm spawn failed (${res.status})`);
      }
    } catch (e) {
      toast.error("Swarm spawn failed: " + (e?.message || "network error"));
    }
  }, [refetchAgents]);

  return (
    <div className="flex flex-col gap-2 h-full">
      <div className="flex items-center gap-2 px-1">
        <Radar size={15} className="text-[#00D9FF]" />
        <span className="text-xs font-bold text-[#00D9FF] uppercase tracking-wider">SCREENING ENGINE</span>
      </div>

      <SectionBox title="SCAN AGENT FLEET" icon={Bot} headerRight={<Filter size={10} className="text-gray-400" />} className="flex-shrink-0">
        <div className="mb-2 relative">
          <div className="absolute top-1.5 left-1.5 right-1.5 h-16 bg-[#1e293b]/80 rounded border border-gray-700/50 -z-10 transform translate-x-1 translate-y-1" />
          <div className="absolute top-1 left-1 right-1 h-14 bg-[#1e293b]/60 rounded border border-gray-700/40 -z-10 transform translate-x-0.5 translate-y-0.5" />
          <div className="bg-[#1e293b] rounded border border-gray-700/50 overflow-hidden">
            <div className="px-2 py-1 bg-[#0B0E14] border-b border-gray-700/40">
              <span className="text-[10px] text-gray-400">Scanner Agent Cards</span>
            </div>
            <div className="p-2 space-y-2">
              {scannerAgents.length > 0 ? (
                <div className="flex flex-col gap-1 max-h-[80px] overflow-y-auto scrollbar-thin">
                  {scannerAgents.map(a => (
                    <ScannerAgentCard key={a.id} agent={a} selected={a.id === selectedScanner} onSelect={setSelectedScanner} />
                  ))}
                </div>
              ) : (
                <p className="text-[10px] text-gray-500 py-1">No scanner agents active. Start scanners from Agent Command Center.</p>
              )}
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[9px] text-gray-500 block mb-0.5">Name:</label>
                  <select value={scannerName} onChange={e => { setScannerName(e.target.value); setPendingSave(true); }} className="w-full bg-[#0B0E14] border border-gray-600 rounded px-1.5 py-0.5 text-[10px] text-cyan-200 focus:outline-none focus:border-cyan-600/60">
                    {scannerNames.map(n => <option key={n} value={n}>{n}</option>)}
                    {!scannerNames.includes(scannerName) && scannerName && <option value={scannerName}>{scannerName}</option>}
                  </select>
                </div>
                <div>
                  <label className="text-[9px] text-gray-500 block mb-0.5">Type:</label>
                  <select value={scannerType} onChange={e => { setScannerType(e.target.value); setPendingSave(true); }} className="w-full bg-[#0B0E14] border border-gray-600 rounded px-1 py-0.5 text-[10px] text-cyan-200 focus:outline-none focus:border-cyan-600/60">
                    {SCANNER_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
              </div>
              <div>
                <div className="flex gap-0.5 flex-wrap">
                  {TIMEFRAMES.map(tf => (
                    <button key={tf} onClick={() => { setActiveTimeframe(tf); setPendingSave(true); }} className={clsx("px-1.5 py-0.5 rounded text-[8px] font-medium transition-colors", activeTimeframe === tf ? "bg-[#00D9FF] text-white" : "bg-gray-700 text-gray-400 hover:bg-gray-600")}>{tf}</button>
                  ))}
                </div>
                {pendingSave && <TealButton onClick={handleSaveScannerConfig} className="mt-1">Save config</TealButton>}
              </div>
            </div>
          </div>
        </div>

        <div className="border-t border-gray-700/40 pt-2 mt-2">
          <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-1.5 flex items-center gap-1"><Settings size={10} /> TRADING METRIC CONTROLS</div>
          <div className="space-y-1">
            <Slider label="Beta Threshold 0-3" min={0} max={3} step={0.1} value={betaThreshold} onChange={v => { setBetaThreshold(v); setPendingSave(true); }} formatValue={v => v.toFixed(1)} className="py-0.5" valueClassName="text-[10px] min-w-[2rem]" />
            <Slider label="Alpha Target" min={0} max={50} step={1} value={alphaTarget} onChange={v => { setAlphaTarget(v); setPendingSave(true); }} suffix="%" formatValue={v => `+${v}%`} className="py-0.5" valueClassName="text-[10px] min-w-[2.5rem]" />
            <Slider label="MFI 0-100" min={0} max={100} step={1} value={mfi} onChange={v => { setMfi(v); setPendingSave(true); }} className="py-0.5" valueClassName="text-[10px] min-w-[2rem]" />
            <Slider label="Short Interest" min={0} max={100} step={1} value={shortInterest} onChange={v => { setShortInterest(v); setPendingSave(true); }} suffix="%" formatValue={v => `>${v}%`} className="py-0.5" valueClassName="text-[10px] min-w-[2.5rem]" />
            <Slider label="Relative Strength vs SPX" min={0.5} max={3} step={0.1} value={relativeStrength} onChange={v => { setRelativeStrength(v); setPendingSave(true); }} formatValue={v => `>${v.toFixed(1)}`} className="py-0.5" valueClassName="text-[10px] min-w-[2.5rem]" />
            <div className="flex items-center justify-between gap-2 py-[3px]">
              <span className="text-[10px] text-gray-400 shrink-0 w-40">Options Flow Filter</span>
              <select value={optionsFlowFilter} onChange={e => { setOptionsFlowFilter(e.target.value); setPendingSave(true); }} className="flex-1 bg-[#0B0E14] border border-gray-600 rounded px-1 py-0.5 text-[10px] text-cyan-200 focus:outline-none">{OPTIONS_FLOW_OPTS.map(o => <option key={o} value={o}>{o}</option>)}</select>
            </div>
            <div className="flex items-center justify-between gap-2 py-[3px]">
              <span className="text-[10px] text-gray-400 shrink-0 w-40">Volatility Regime</span>
              <select value={volatilityRegime} onChange={e => { setVolatilityRegime(e.target.value); setPendingSave(true); }} className="flex-1 bg-[#0B0E14] border border-gray-600 rounded px-1 py-0.5 text-[10px] text-cyan-200 focus:outline-none">{VOLATILITY_REGIMES.map(v => <option key={v} value={v}>{v}</option>)}</select>
            </div>
            <div className="flex items-center justify-between gap-2 py-[3px]">
              <span className="text-[10px] text-gray-400 shrink-0 w-40">Volume Profile</span>
              <select value={volumeProfile} onChange={e => { setVolumeProfile(e.target.value); setPendingSave(true); }} className="flex-1 bg-[#0B0E14] border border-gray-600 rounded px-1 py-0.5 text-[10px] text-cyan-200 focus:outline-none">{VOLUME_PROFILES.map(v => <option key={v} value={v}>{v}</option>)}</select>
            </div>
            <div className="flex items-center justify-between py-[3px]">
              <span className="text-[10px] text-gray-400">Dark Pool Activity</span>
              <div className="flex items-center gap-1">
                <Toggle value={darkPoolActivity} onChange={v => { setDarkPoolActivity(v); setPendingSave(true); }} />
                <span className="text-[10px] text-[#00D9FF]">{darkPoolActivity ? "ON" : "OFF"}</span>
              </div>
            </div>
            <div className="flex items-center justify-between py-[3px]">
              <span className="text-[10px] text-gray-400">Institutional Accumulation</span>
              <div className="flex items-center gap-1">
                <Toggle value={institutionalAccum} onChange={v => { setInstitutionalAccum(v); setPendingSave(true); }} />
                <span className="text-[10px] text-[#00D9FF]">{institutionalAccum ? "ON" : "OFF"}</span>
              </div>
            </div>
            <div className="flex items-center justify-between py-[3px]">
              <span className="text-[10px] text-gray-400">Sector Momentum</span>
              <div className="flex items-center gap-1">
                <Toggle value={sectorMomentum} onChange={v => { setSectorMomentum(v); setPendingSave(true); }} />
                <span className="text-[10px] text-[#00D9FF]">{sectorMomentum ? "ON" : "OFF"}</span>
              </div>
            </div>
            {pendingSave && <TealButton onClick={handleSaveTradingMetrics}>Save metrics</TealButton>}
          </div>
        </div>

        <div className="flex flex-wrap gap-1.5 mt-2 pt-2 border-t border-gray-700/40">
          <TealButton icon={Plus} onClick={postSpawn}>+ Spawn New Scanner Agent</TealButton>
          <TealButton icon={Copy} onClick={postClone} disabled={selectedScanner == null} className="!text-emerald-400 !border-emerald-500/40 !bg-emerald-500/20">Clone Agent</TealButton>
          <TealButton icon={Boxes} onClick={postSwarmSpawn} className="!text-emerald-400 !border-emerald-500/40 !bg-emerald-500/20">Spawn Swarm</TealButton>
          <TealButton icon={Layers} variant="danger" onClick={onOpenTemplates}>Swarm Templates</TealButton>
          <TealButton icon={Trash2} variant="danger" onClick={onKillAllConfirm}>Kill All Agents</TealButton>
        </div>
      </SectionBox>
    </div>
  );
}

// ═══════════════════════════════════════════════════
// PATTERN AGENT CARD
// ═══════════════════════════════════════════════════

function PatternAgentCard({ agent, selected, onSelect }) {
  const type = agent.type ?? agent.name;
  const arch = agent.architecture ?? "—";
  const found = agent.patternsFound ?? agent.last_actions?.length ?? 0;
  const accuracy = agent.accuracy ?? "—";
  return (
    <button
      onClick={() => onSelect?.(agent.id)}
      className={clsx(
        "w-full text-left p-2 rounded border transition-all",
        selected ? "border-[#00D9FF]/50 bg-cyan-950/40 shadow-[0_0_8px_rgba(6,182,212,0.15)]" : "border-gray-800/60 bg-gray-900/40 hover:border-cyan-800/40"
      )}
    >
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-1.5">
          <StatusDot status={agent.status} />
          <span className="text-[11px] font-semibold text-cyan-200">{agent.name}</span>
        </div>
        <span className="text-[9px] text-emerald-400">{accuracy}%</span>
      </div>
      <div className="flex items-center gap-3 text-[9px] text-gray-400">
        <span>Type: <span className="text-[#00D9FF]">{type}</span></span>
        <span>Arch: <span className="text-purple-400">{arch}</span></span>
        <span>Found: <span className="text-emerald-400">{found}</span></span>
      </div>
    </button>
  );
}

// ═══════════════════════════════════════════════════
// PATTERN INTELLIGENCE (CENTER COLUMN)
// ═══════════════════════════════════════════════════

function PatternIntelligence({ onOpenTemplates, onKillAllConfirm }) {
  const { data: agentsData, refetch: refetchAgents } = useApi("agents", { pollIntervalMs: 15000 });
  const { settings, updateField, saveCategory } = useSettings();
  const category = "pattern_config";
  const patternConfig = settings?.[category] ?? {};

  const [selectedPattern, setSelectedPattern] = useState(null);
  const [patternName, setPatternName] = useState(patternConfig.patternName ?? "");
  const [llmModel, setLlmModel] = useState(patternConfig.llmModel ?? "");
  const [architecture, setArchitecture] = useState(patternConfig.architecture ?? "Transformer");
  const [recursiveSelfImprove, setRecursiveSelfImprove] = useState(patternConfig.recursiveSelfImprove !== false);
  const [academicValidation, setAcademicValidation] = useState(patternConfig.academicValidation ?? 94.5);
  const [sharpeRatio, setSharpeRatio] = useState(patternConfig.sharpeRatio ?? 3.2);
  const [profitFactor, setProfitFactor] = useState(patternConfig.profitFactor ?? 2.8);
  const [maxDrawdown, setMaxDrawdown] = useState(patternConfig.maxDrawdown ?? 12);
  const [walkForwardEff, setWalkForwardEff] = useState(patternConfig.walkForwardEff ?? 88);
  const [outOfSampleAcc, setOutOfSampleAcc] = useState(patternConfig.outOfSampleAcc ?? 79);
  const [monteCarloCI, setMonteCarloCI] = useState(patternConfig.monteCarloCI ?? "95%");
  const [patternComplexity, setPatternComplexity] = useState(patternConfig.patternComplexity ?? "Compound");
  const [swarmSize, setSwarmSize] = useState(patternConfig.swarmSize ?? 50);

  useEffect(() => {
    if (!settings?.[category]) return;
    const s = settings[category];
    setPatternName(s.patternName ?? "");
    setLlmModel(s.llmModel ?? "");
    setArchitecture(s.architecture ?? "Transformer");
    setRecursiveSelfImprove(s.recursiveSelfImprove !== false);
    setAcademicValidation(s.academicValidation ?? 94.5);
    setSharpeRatio(s.sharpeRatio ?? 3.2);
    setProfitFactor(s.profitFactor ?? 2.8);
    setMaxDrawdown(s.maxDrawdown ?? 12);
    setWalkForwardEff(s.walkForwardEff ?? 88);
    setOutOfSampleAcc(s.outOfSampleAcc ?? 79);
    setMonteCarloCI(s.monteCarloCI ?? "95%");
    setPatternComplexity(s.patternComplexity ?? "Compound");
    setSwarmSize(s.swarmSize ?? 50);
  }, [settings, category]);

  const patternAgents = useMemo(() => {
    const list = agentsData?.agents ?? [];
    const patternLike = list.filter(a => a.name && (a.name.toLowerCase().includes("ml") || a.name.toLowerCase().includes("pattern") || a.name.toLowerCase().includes("sentiment") || a.name.toLowerCase().includes("youtube")));
    return patternLike.length > 0 ? patternLike : list;
  }, [agentsData]);
  const patternNames = useMemo(() => [...new Set([...(patternAgents.map(a => a.name)), patternName].filter(Boolean))], [patternAgents, patternName]);
  const llmModels = useMemo(() => {
    const fromSettings = settings?.llm?.models ?? settings?.models ?? settings?.llm_models;
    return Array.isArray(fromSettings) ? fromSettings : (fromSettings ? Object.keys(fromSettings) : []);
  }, [settings]);

  const settingsBase = getApiUrl("settings");
  const handleApplyMlMetrics = useCallback(async () => {
    const payload = { ...(settings?.[category] ?? {}), recursiveSelfImprove, academicValidation, sharpeRatio, profitFactor, maxDrawdown, walkForwardEff, outOfSampleAcc, monteCarloCI, patternComplexity, swarmSize, patternName, llmModel, architecture };
    try {
      const res = await fetch(`${settingsBase}/${category}`, { method: "PUT", headers: { "Content-Type": "application/json", ...getAuthHeaders() }, body: JSON.stringify(payload) });
      if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    } catch (e) {
      toast.error("Apply ML metrics failed: " + (e?.message || "network error"));
    }
  }, [category, settings, settingsBase, recursiveSelfImprove, academicValidation, sharpeRatio, profitFactor, maxDrawdown, walkForwardEff, outOfSampleAcc, monteCarloCI, patternComplexity, swarmSize, patternName, llmModel, architecture]);

  const postSpawnPattern = useCallback(async () => {
    try {
      const res = await fetch(getApiUrl("agents/spawn"), { method: "POST", headers: { "Content-Type": "application/json", ...getAuthHeaders() }, body: JSON.stringify({ name: patternName || "PatternAgent", type: "pattern" }) });
      if (res.ok) {
        refetchAgents();
        toast.success("Pattern agent spawned");
      } else {
        const err = await res.json().catch(() => ({}));
        toast.error(err?.detail ?? `Spawn failed (${res.status})`);
      }
    } catch (e) {
      toast.error("Spawn failed: " + (e?.message || "network error"));
    }
  }, [patternName, refetchAgents]);
  const postSwarmSpawn = useCallback(async () => {
    try {
      const res = await fetch(getApiUrl("agents/swarm/spawn"), { method: "POST", headers: { "Content-Type": "application/json", ...getAuthHeaders() }, body: JSON.stringify({}) });
      if (res.ok) {
        refetchAgents();
        toast.success("Discovery swarm spawn requested");
      } else {
        const err = await res.json().catch(() => ({}));
        toast.error(err?.detail ?? `Swarm spawn failed (${res.status})`);
      }
    } catch (e) {
      toast.error("Swarm spawn failed: " + (e?.message || "network error"));
    }
  }, [refetchAgents]);

  return (
    <div className="flex flex-col gap-2 h-full">
      <div className="flex items-center gap-2 px-1">
        <Brain size={15} className="text-[#00D9FF]" />
        <span className="text-xs font-bold text-[#00D9FF] uppercase tracking-wider">PATTERN INTELLIGENCE</span>
      </div>

      <SectionBox title="PATTERN AGENT FLEET" icon={Cpu} headerRight={<Filter size={10} className="text-gray-400" />} className="flex-shrink-0">
        <div className="mb-2 relative">
          <div className="absolute top-1.5 left-1.5 right-1.5 h-16 bg-[#1e293b]/80 rounded border border-gray-700/50 -z-10 transform translate-x-1 translate-y-1" />
          <div className="absolute top-1 left-1 right-1 h-14 bg-[#1e293b]/60 rounded border border-gray-700/40 -z-10 transform translate-x-0.5 translate-y-0.5" />
          <div className="bg-[#1e293b] rounded border border-gray-700/50 overflow-hidden">
            <div className="px-2 py-1 bg-[#0B0E14] border-b border-gray-700/40">
              <span className="text-[10px] text-gray-400">Pattern Agent Cards</span>
            </div>
            <div className="p-2 space-y-2">
              {patternAgents.length > 0 ? (
                <div className="flex flex-col gap-1 max-h-[80px] overflow-y-auto scrollbar-thin">
                  {patternAgents.map(a => (
                    <PatternAgentCard key={a.id} agent={a} selected={a.id === selectedPattern} onSelect={setSelectedPattern} />
                  ))}
                </div>
              ) : (
                <p className="text-[10px] text-gray-500 py-1">No pattern agents. Spawn from controls below.</p>
              )}
              <div className="grid grid-cols-1 gap-2">
                <div>
                  <label className="text-[9px] text-gray-500 block mb-0.5">Name:</label>
                  <select value={patternName} onChange={e => setPatternName(e.target.value)} className="w-full bg-[#0B0E14] border border-gray-600 rounded px-1.5 py-0.5 text-[10px] text-cyan-200 focus:outline-none">
                    {patternNames.map(n => <option key={n} value={n}>{n}</option>)}
                    {!patternNames.includes(patternName) && patternName && <option value={patternName}>{patternName}</option>}
                  </select>
                </div>
                <div>
                  <label className="text-[9px] text-gray-500 block mb-0.5">LLM Model:</label>
                  <select value={llmModel} onChange={e => setLlmModel(e.target.value)} className="w-full bg-[#0B0E14] border border-gray-600 rounded px-1 py-0.5 text-[10px] text-cyan-200 focus:outline-none">
                    {llmModels.map(m => <option key={m} value={m}>{m}</option>)}
                    {llmModels.length === 0 && <option value="">—</option>}
                  </select>
                </div>
                <div>
                  <label className="text-[9px] text-gray-500 block mb-0.5">ML Architecture:</label>
                  <select value={architecture} onChange={e => setArchitecture(e.target.value)} className="w-full bg-[#0B0E14] border border-gray-600 rounded px-1 py-0.5 text-[10px] text-cyan-200 focus:outline-none">
                    {ML_ARCHITECTURES.map(a => <option key={a} value={a}>{a}</option>)}
                  </select>
                </div>
              </div>
            </div>
          </div>
        </div>

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
            <Slider label="Academic Validation Score %" min={0} max={100} step={0.1} value={academicValidation} onChange={setAcademicValidation} suffix="%" formatValue={v => v.toFixed(1)} className="py-0.5" valueClassName="text-[10px] min-w-[3rem]" />
            <Slider label="Sharpe Ratio" min={0} max={5} step={0.1} value={sharpeRatio} onChange={setSharpeRatio} formatValue={v => v.toFixed(1)} className="py-0.5" valueClassName="text-[10px] min-w-[2rem]" />
            <Slider label="Profit Factor" min={0} max={5} step={0.1} value={profitFactor} onChange={setProfitFactor} formatValue={v => v.toFixed(1)} className="py-0.5" valueClassName="text-[10px] min-w-[2rem]" />
            <Slider label="Max Drawdown" min={0} max={30} step={1} value={maxDrawdown} onChange={setMaxDrawdown} formatValue={v => `<${v}%`} className="py-0.5" valueClassName="text-[10px] text-red-400 min-w-[2.5rem]" />
            <Slider label="Walk-Forward Efficiency" min={0} max={100} step={1} value={walkForwardEff} onChange={setWalkForwardEff} suffix="%" className="py-0.5" valueClassName="text-[10px] min-w-[2.5rem]" />
            <Slider label="Out-of-Sample Accuracy" min={0} max={100} step={1} value={outOfSampleAcc} onChange={setOutOfSampleAcc} suffix="%" className="py-0.5" valueClassName="text-[10px] min-w-[2.5rem]" />
            <div className="flex items-center justify-between gap-2 py-[3px]">
              <span className="text-[10px] text-gray-400 shrink-0 w-40">Monte Carlo CI</span>
              <select value={monteCarloCI} onChange={e => setMonteCarloCI(e.target.value)} className="flex-1 bg-[#0B0E14] border border-gray-600 rounded px-1 py-0.5 text-[10px] text-cyan-200 focus:outline-none">
                <option value="90%">90%</option>
                <option value="95%">95%</option>
                <option value="99%">99%</option>
              </select>
            </div>
            <div className="flex items-center justify-between gap-2 py-[3px]">
              <span className="text-[10px] text-gray-400 shrink-0 w-40">Pattern Complexity</span>
              <select value={patternComplexity} onChange={e => setPatternComplexity(e.target.value)} className="flex-1 bg-[#0B0E14] border border-gray-600 rounded px-1 py-0.5 text-[10px] text-cyan-200 focus:outline-none">
                {PATTERN_COMPLEXITY_OPTS.map(p => <option key={p} value={p}>{p}</option>)}
              </select>
            </div>
            <div className="flex items-center justify-between gap-2 py-[3px]">
              <span className="text-[10px] text-gray-400 shrink-0 w-40">Sub-Agent Swarm Size</span>
              <input type="number" value={swarmSize} onChange={e => setSwarmSize(Number(e.target.value) || 0)} className="w-16 bg-[#0B0E14] border border-gray-600 rounded px-1 py-0.5 text-[10px] text-cyan-200 focus:outline-none text-right" />
            </div>
            <TealButton onClick={handleApplyMlMetrics} className="mt-1">Apply</TealButton>
          </div>
        </div>

        <div className="flex flex-wrap gap-1.5 mt-2 pt-2 border-t border-gray-700/40">
          <TealButton icon={Plus} onClick={postSpawnPattern}>+ Spawn New Pattern Agent</TealButton>
          <TealButton icon={Boxes} onClick={postSwarmSpawn} className="!text-emerald-400 !border-emerald-500/40 !bg-emerald-500/20">Spawn Discovery Swarm</TealButton>
          <TealButton icon={Layers} variant="danger" onClick={onOpenTemplates}>Swarm Templates</TealButton>
          <TealButton icon={Trash2} variant="danger" onClick={onKillAllConfirm}>Kill All Pattern Agents</TealButton>
        </div>
      </SectionBox>
    </div>
  );
}

// ═══════════════════════════════════════════════════
// BOTTOM PANELS: Live Feed, Pattern Arsenal, Forming Detections
// ═══════════════════════════════════════════════════

function FormingDetectionCard({ pattern }) {
  const ticker = pattern.ticker ?? pattern.symbol ?? "—";
  const name = pattern.pattern ?? pattern.name ?? "—";
  const confidence = pattern.confidence ?? 0;
  const title = `${ticker} | ${name} | ${confidence}%`;
  const chartData = pattern.data ?? [];
  return (
    <div className="border border-gray-700/50 rounded bg-[#1e293b]/60 p-1.5">
      <div className="flex items-center justify-between mb-1">
        <span className="text-[9px] font-semibold text-cyan-200 truncate">{title}</span>
      </div>
      {chartData.length > 0 ? (
        <ResponsiveContainer width="100%" height={40}>
          <AreaChart data={chartData}>
            <defs>
              <linearGradient id={`fd-${pattern.id}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#00D9FF" stopOpacity={0.3} />
                <stop offset="100%" stopColor="#00D9FF" stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <Area type="monotone" dataKey="y" stroke="#00D9FF" strokeWidth={1.2} fill={`url(#fd-${pattern.id})`} dot={false} />
          </AreaChart>
        </ResponsiveContainer>
      ) : null}
    </div>
  );
}

function ConsolidatedLiveFeed() {
  const { data: alertsData } = useApi("systemAlerts", { pollIntervalMs: 20000 });
  const feedEntries = useMemo(() => {
    const raw = alertsData?.alerts ?? alertsData ?? [];
    return Array.isArray(raw) ? raw.slice(0, 50).map((a, i) => ({ id: String(i), timestamp: a.time ?? a.timestamp ?? "", symbol: a.symbol ?? "", agent: a.agent ?? a.source ?? "", action: a.message ?? a.action ?? "" })) : [];
  }, [alertsData]);

  return (
    <SectionBox title="Consolidated Live Feed" icon={Radio} className="flex-1 min-h-0 flex flex-col">
      <div className="flex-1 overflow-y-auto scrollbar-thin space-y-0 min-h-0 max-h-[200px]">
        {feedEntries.length === 0 ? (
          <div className="flex items-center justify-center h-full py-6">
            <span className="text-[10px] text-gray-600">No feed data</span>
          </div>
        ) : feedEntries.map(entry => (
          <div key={entry.id} className="flex items-start gap-2 py-[3px] border-b border-gray-800/30 hover:bg-cyan-950/20 px-1 text-[10px] font-mono">
            <span className="text-gray-600 whitespace-nowrap">{entry.timestamp}</span>
            <span className="font-bold min-w-[36px] text-[#00D9FF]">{entry.symbol}</span>
            <span className="text-gray-500">{entry.agent}</span>
            <span className="text-gray-300 truncate">{entry.action}</span>
          </div>
        ))}
      </div>
    </SectionBox>
  );
}

function PatternArsenalPanel() {
  const { data: patternsData } = useApi("patterns", { pollIntervalMs: 30000 });
  const arsenalDisplay = useMemo(() => {
    const list = patternsData?.patterns ?? [];
    const byType = {};
    list.forEach(p => {
      const key = (p.pattern ?? p.name ?? "Other").replace(/\s+/g, "_").toLowerCase();
      if (!byType[key]) byType[key] = { id: key, name: p.pattern ?? p.name ?? "Other", icon: ((PATTERN_ICON_MAP[key] ?? (p.pattern || "?")[0]) || "P") };
    });
    return Object.values(byType);
  }, [patternsData]);

  return (
    <SectionBox title="Pattern Arsenal" icon={Target} className="flex-1 min-h-0 flex flex-col">
      <div className="grid grid-cols-3 gap-3 py-2">
        {arsenalDisplay.length === 0 ? (
          <div className="col-span-3 flex items-center justify-center py-4">
            <span className="text-[10px] text-gray-600">No patterns yet</span>
          </div>
        ) : arsenalDisplay.map(p => (
          <div key={p.id} className="flex flex-col items-center gap-1.5">
            <div className="w-12 h-12 rounded-full bg-[#1e293b] border-2 border-[#00D9FF]/40 flex items-center justify-center text-white font-bold text-lg shadow-[0_0_8px_rgba(0,217,255,0.2)]">
              {p.icon}
            </div>
            <span className="text-[10px] text-gray-300 text-center leading-tight">{p.name}</span>
          </div>
        ))}
      </div>
    </SectionBox>
  );
}

function FormingDetectionsPanel() {
  const { data: patternsData } = useApi("patterns", { pollIntervalMs: 30000 });
  const forming = useMemo(() => (patternsData?.patterns ?? []).slice(0, 20), [patternsData]);

  return (
    <SectionBox title="Forming Detections" icon={Crosshair} className="flex-1 min-h-0 flex flex-col">
      <div className="flex-1 overflow-y-auto scrollbar-thin space-y-1.5 max-h-[200px]">
        {forming.length === 0 ? (
          <div className="flex items-center justify-center h-full py-6">
            <span className="text-[10px] text-gray-600">No forming detections</span>
          </div>
        ) : forming.map(f => (
          <FormingDetectionCard key={f.id ?? `${f.ticker}-${f.pattern}`} pattern={f} />
        ))}
      </div>
    </SectionBox>
  );
}

// ═══════════════════════════════════════════════════
// MAIN PAGE (3-col layout, Aurora theme)
// ═══════════════════════════════════════════════════

export default function Patterns() {
  const [templatesOpen, setTemplatesOpen] = useState(false);
  const [templatesList, setTemplatesList] = useState([]);
  const [templatesLoading, setTemplatesLoading] = useState(false);
  const [killAllOpen, setKillAllOpen] = useState(false);
  const [killAllPending, setKillAllPending] = useState(false);

  const { data: agentsData, refetch: refetchAgents } = useApi("agents", { pollIntervalMs: 15000 });
  const { data: patternsData } = useApi("patterns", { pollIntervalMs: 30000 });
  const { data: healthData } = useApi("system/health", { pollIntervalMs: 30000 });

  const agentCount = (agentsData?.agents ?? []).length;
  const patternCount = patternsData?.count ?? (patternsData?.patterns ?? []).length;
  const gpuPct = healthData?.gpuPercent ?? healthData?.gpu ?? null;
  const connections = healthData?.connections ?? null;

  const openTemplates = useCallback(async () => {
    setTemplatesOpen(true);
    setTemplatesLoading(true);
    try {
      const res = await fetch(getApiUrl("agents/swarm/templates"), { headers: getAuthHeaders() });
      const json = res.ok ? await res.json() : {};
      setTemplatesList(Array.isArray(json.templates) ? json.templates : (json?.data ?? []));
      if (!res.ok) toast.error("Failed to load swarm templates");
    } catch {
      setTemplatesList([]);
      toast.error("Failed to load swarm templates");
    } finally {
      setTemplatesLoading(false);
    }
  }, []);

  const confirmKillAll = useCallback(async () => {
    setKillAllPending(true);
    try {
      const res = await fetch(getApiUrl("agents/kill-all"), { method: "POST", headers: { "Content-Type": "application/json", ...getAuthHeaders() }, body: JSON.stringify({}) });
      setKillAllOpen(false);
      if (res.ok) {
        refetchAgents();
        toast.success("All agents paused");
      } else {
        const err = await res.json().catch(() => ({}));
        toast.error(err?.detail ?? `Kill all failed (${res.status})`);
      }
    } catch (e) {
      setKillAllOpen(false);
      toast.error("Kill all failed: " + (e?.message || "network error"));
    } finally {
      setKillAllPending(false);
    }
  }, [refetchAgents]);

  return (
    <div className="flex flex-col h-full min-h-0 p-4 gap-3 bg-[#0a0e1a]">
      <div className="flex flex-col items-center justify-center shrink-0 text-center">
        <h1 className="text-lg font-bold text-[#00D9FF] tracking-widest uppercase font-mono">
          SCREENER AND PATTERNS
        </h1>
      </div>

      {/* 3-column layout: Screening (30%) | Pattern Intelligence (30%) | Coverage & Results (40%) */}
      <div className="flex-1 min-h-0 grid grid-cols-12 gap-3">
        <div className="col-span-4 min-h-0 overflow-y-auto scrollbar-thin pr-1">
          <ScreeningEngine onOpenTemplates={openTemplates} onKillAllConfirm={() => setKillAllOpen(true)} />
        </div>
        <div className="col-span-4 min-h-0 overflow-y-auto scrollbar-thin pr-1">
          <PatternIntelligence onOpenTemplates={openTemplates} onKillAllConfirm={() => setKillAllOpen(true)} />
        </div>
        <div className="col-span-4 min-h-0 overflow-y-auto scrollbar-thin">
          <SectionBox title="Coverage & Results" icon={Target} className="h-full">
            <div className="space-y-2 text-[10px] text-gray-400">
              <p>Agents: <span className="text-[#00D9FF]">{agentCount}</span></p>
              <p>Patterns: <span className="text-[#00D9FF]">{patternCount}</span></p>
              <p className="pt-2 border-t border-gray-700/40">Screener and pattern results appear in the panels below.</p>
            </div>
          </SectionBox>
        </div>
      </div>

      <div className="flex-shrink-0 grid grid-cols-3 gap-2">
        <ConsolidatedLiveFeed />
        <PatternArsenalPanel />
        <FormingDetectionsPanel />
      </div>

      <div className="flex-shrink-0 flex items-center justify-between px-3 py-1.5 bg-[#111827] border border-[rgba(42,52,68,0.5)] rounded text-[9px] text-gray-500">
        <div className="flex items-center gap-3">
          <span>Connections: <span className="text-[#00D9FF]">{connections ?? "—"}</span></span>
          <span className="text-gray-600">|</span>
          <span>Agents <span className="text-[#00D9FF]">{agentCount}</span></span>
          <span className="text-gray-600">|</span>
          <span>Patterns <span className="text-[#00D9FF]">{patternCount}</span></span>
        </div>
        <div className="flex items-center gap-2">
          <span>GPU <span className="text-emerald-400">{gpuPct != null ? `${gpuPct}%` : "—"}</span></span>
          {gpuPct != null && (
            <div className="w-16 h-1.5 rounded-full bg-gray-700 overflow-hidden">
              <div className="h-full rounded-full bg-emerald-500" style={{ width: `${Math.min(100, gpuPct)}%` }} />
            </div>
          )}
          <div className="flex items-center gap-1">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span>Live</span>
          </div>
        </div>
      </div>

      {/* Swarm Templates modal */}
      {templatesOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={() => setTemplatesOpen(false)}>
          <div className="bg-[#111827] border border-gray-700 rounded-lg p-4 max-w-md w-full shadow-xl" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-[#00D9FF]">Swarm Templates</h3>
              <button className="text-gray-400 hover:text-white" onClick={() => setTemplatesOpen(false)}>×</button>
            </div>
            {templatesLoading ? <p className="text-[10px] text-gray-500">Loading…</p> : templatesList.length === 0 ? <p className="text-[10px] text-gray-500">No templates available.</p> : (
              <ul className="space-y-1 max-h-60 overflow-y-auto">
                {templatesList.map((t, i) => <li key={i} className="text-[10px] text-gray-300">{typeof t === "string" ? t : (t.name ?? t.id ?? JSON.stringify(t))}</li>)}
              </ul>
            )}
          </div>
        </div>
      )}

      {/* Kill All confirmation modal */}
      {killAllOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={() => !killAllPending && setKillAllOpen(false)}>
          <div className="bg-[#111827] border border-red-900/50 rounded-lg p-4 max-w-sm w-full shadow-xl" onClick={e => e.stopPropagation()}>
            <h3 className="text-sm font-semibold text-red-300 mb-2">Kill All Agents?</h3>
            <p className="text-[10px] text-gray-400 mb-4">This will stop all scanner and pattern agents. Continue?</p>
            <div className="flex gap-2 justify-end">
              <TealButton variant="secondary" onClick={() => setKillAllOpen(false)} disabled={killAllPending}>Cancel</TealButton>
              <TealButton variant="danger" onClick={confirmKillAll} disabled={killAllPending}>{killAllPending ? "…" : "Kill All"}</TealButton>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
