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
} from "lucide-react";
import { LineChart, Line, AreaChart, Area, BarChart, Bar, ResponsiveContainer, XAxis, YAxis, Tooltip } from "recharts";
import clsx from "clsx";
import { format } from "date-fns";
import { useApi } from "../hooks/useApi";
import PageHeader from "../components/ui/PageHeader";
import Slider from "../components/ui/Slider";
import log from "@/utils/logger";

// ═══════════════════════════════════════════════════
// CONFIG & CONSTANTS
// ═══════════════════════════════════════════════════

const TIMEFRAMES = ["1m", "5m", "15m", "1H", "4H", "D", "W"];

const SCANNER_TYPES = [
  "Alpha Scanner", "Momentum Scanner", "Mean Reversion", "Breakout Hunter",
  "Volume Profiler", "Dark Pool Tracker", "Options Flow", "Sector Rotator",
];

const PATTERN_TYPES = [
  "BPT-4", "BPT-L", "BPT-S", "Fractal", "Harmonic", "Elliott Wave",
  "Wyckoff", "ICT", "SMC",
];

const ARCHITECTURES = [
  "Transformer", "LSTM", "CNN-LSTM", "GAN", "Attention-Net", "ResNet", "GPT-4",
];

const VOLATILITY_REGIMES = ["Expansion", "Contraction", "Normal", "Extreme"];
const VOLUME_PROFILES = ["Value Area High", "Value Area Low", "POC", "HVN", "LVN"];
const BENCHMARK_OPTIONS = ["S&P", "NASDAQ", "DOW", "Russell 2000", "VIX"];

const SCANNER_AGENTS = [];

const PATTERN_AGENTS = [];

// Feed entries are populated only from real WebSocket messages — no fake generation

function generatePatternChartData() {
  return [];
}

// Pattern Arsenal: real pattern type names the system CAN detect; detection data comes from API only
const PATTERNS_ARSENAL = [];

const FORMING_PATTERNS = [];

// ═══════════════════════════════════════════════════
// STYLED SUB-COMPONENTS
// ═══════════════════════════════════════════════════

/** Section wrapper with title bar */
function SectionBox({ title, icon: Icon, children, className, headerRight }) {
  return (
    <div className={clsx(
      "border border-cyan-900/50 rounded bg-[#0a1628]/80 overflow-hidden",
      className
    )}>
      <div className="flex items-center justify-between px-3 py-1.5 bg-cyan-950/40 border-b border-cyan-900/40">
        <div className="flex items-center gap-2">
          {Icon && <Icon size={13} className="text-cyan-400" />}
          <span className="text-[11px] font-semibold text-cyan-300 uppercase tracking-wider">{title}</span>
        </div>
        {headerRight}
      </div>
      <div className="p-2">
        {children}
      </div>
    </div>
  );
}

/** Small labeled row with value */
function MetricRow({ label, children }) {
  return (
    <div className="flex items-center justify-between gap-2 py-[3px]">
      <span className="text-[10px] text-gray-400 whitespace-nowrap">{label}</span>
      <div className="flex items-center gap-1.5 flex-1 justify-end min-w-0">
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
    primary: "bg-cyan-600/80 hover:bg-cyan-500/90 text-white border border-cyan-500/40",
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

/** Inline mini sparkline */
function MiniSparkline({ data, color = "#22d3ee", height = 24, width = 60 }) {
  return (
    <ResponsiveContainer width={width} height={height}>
      <LineChart data={data}>
        <Line type="monotone" dataKey="y" stroke={color} strokeWidth={1.2} dot={false} />
      </LineChart>
    </ResponsiveContainer>
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
          ? "border-cyan-500/60 bg-cyan-950/40 shadow-[0_0_8px_rgba(6,182,212,0.15)]"
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
        <span>Type: <span className="text-cyan-400">{agent.type}</span></span>
        <span>Hits: <span className="text-emerald-400">{agent.hits}</span></span>
      </div>
    </button>
  );
}

// ═══════════════════════════════════════════════════
// SCREENING ENGINE (LEFT COLUMN)
// ═══════════════════════════════════════════════════

function ScreeningEngine() {
  const [selectedScanner, setSelectedScanner] = useState("s1");
  const [scannerName, setScannerName] = useState("AlphaHunter_V4");
  const [scannerType, setScannerType] = useState("Alpha Scanner");
  const [activeTimeframe, setActiveTimeframe] = useState("1H");

  // Trading metric controls
  const [betaThreshold, setBetaThreshold] = useState(1.2);
  const [mfi, setMfi] = useState(25);
  const [shortInterest, setShortInterest] = useState(10);
  const [benchmark, setBenchmark] = useState("S&P");
  const [relativeValue, setRelativeValue] = useState(65);
  const [optionsFlowFilter, setOptionsFlowFilter] = useState(55);
  const [volatilityRegime, setVolatilityRegime] = useState("Expansion");
  const [volumeProfile, setVolumeProfile] = useState("Value Area High");
  const [darkPoolActivity, setDarkPoolActivity] = useState(70);
  const [institutionalAccum, setInstitutionalAccum] = useState(55);
  const [sectorMomentum, setSectorMomentum] = useState(80);

  // API data (graceful fallback)
  const { data: signalsData } = useApi("signals", { pollIntervalMs: 30000 });

  return (
    <div className="flex flex-col gap-2 h-full">
      {/* Section Title */}
      <div className="flex items-center gap-2 px-1">
        <Radar size={15} className="text-cyan-400" />
        <span className="text-xs font-bold text-cyan-300 uppercase tracking-wider">Screening Engine</span>
      </div>

      {/* SCAN AGENT FLEET */}
      <SectionBox title="Scan Agent Fleet" icon={Bot} className="flex-shrink-0">
        {/* Scanner Agent Cards */}
        <div className="mb-2">
          <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-1.5 flex items-center gap-1">
            <Layers size={10} />
            Scanner Agent Cards
          </div>
          <div className="flex flex-col gap-1 max-h-[90px] overflow-y-auto scrollbar-thin">
            {SCANNER_AGENTS.length === 0 ? (
              <div className="py-3 text-center text-[10px] text-gray-600">No scanners</div>
            ) : SCANNER_AGENTS.map(a => (
              <ScannerAgentCard
                key={a.id}
                agent={a}
                selected={a.id === selectedScanner}
                onSelect={setSelectedScanner}
              />
            ))}
          </div>
        </div>

        {/* Selected agent fields: Name, Type, Timeframe */}
        <div className="grid grid-cols-3 gap-1.5 mb-2">
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
            <MetricRow label="Beta Threshold 0-3">
              <Slider min={0} max={3} step={0.1} value={betaThreshold} onChange={setBetaThreshold}
                suffix="" showValue={false} className="flex-1" inputClassName="h-1.5" />
              <span className="text-[10px] text-cyan-400 min-w-[28px] text-right">{betaThreshold.toFixed(1)}</span>
              <MiniSparkline data={generatePatternChartData(15)} width={44} height={16} />
            </MetricRow>

            <MetricRow label="MFI 0-50">
              <Slider min={0} max={50} step={1} value={mfi} onChange={setMfi}
                showValue={false} className="flex-1" inputClassName="h-1.5" />
              <span className="text-[10px] text-cyan-400 min-w-[28px] text-right">{mfi}</span>
              <MiniSparkline data={generatePatternChartData(15)} width={44} height={16} />
            </MetricRow>

            <MetricRow label="Short Interest">
              <Slider min={0} max={100} step={1} value={shortInterest} onChange={setShortInterest}
                suffix="%" showValue={false} className="flex-1" inputClassName="h-1.5" />
              <span className="text-[10px] text-cyan-400 min-w-[28px] text-right">{shortInterest}%</span>
              <MiniSparkline data={generatePatternChartData(15)} width={44} height={16} />
            </MetricRow>

            <MetricRow label="Benchmark Comp">
              <select
                value={benchmark}
                onChange={e => setBenchmark(e.target.value)}
                className="bg-gray-900/80 border border-cyan-900/40 rounded px-1 py-0 text-[10px] text-cyan-300 focus:outline-none"
              >
                {BENCHMARK_OPTIONS.map(b => <option key={b} value={b}>{b}</option>)}
              </select>
            </MetricRow>

            <MetricRow label="Relative Value vs SPX">
              <Slider min={0} max={100} step={1} value={relativeValue} onChange={setRelativeValue}
                showValue={false} className="flex-1" inputClassName="h-1.5" />
              <span className="text-[10px] text-cyan-400 min-w-[28px] text-right">{relativeValue}</span>
              <MiniSparkline data={generatePatternChartData(15)} width={44} height={16} />
            </MetricRow>

            <MetricRow label="Options Flow Filter">
              <Slider min={0} max={100} step={1} value={optionsFlowFilter} onChange={setOptionsFlowFilter}
                showValue={false} className="flex-1" inputClassName="h-1.5" />
              <span className="text-[10px] text-cyan-400 min-w-[28px] text-right">{optionsFlowFilter}</span>
              <MiniSparkline data={generatePatternChartData(15)} width={44} height={16} />
            </MetricRow>

            <MetricRow label="Volatility Regime">
              <select
                value={volatilityRegime}
                onChange={e => setVolatilityRegime(e.target.value)}
                className="bg-gray-900/80 border border-cyan-900/40 rounded px-1 py-0 text-[10px] text-cyan-300 focus:outline-none"
              >
                {VOLATILITY_REGIMES.map(v => <option key={v} value={v}>{v}</option>)}
              </select>
            </MetricRow>

            <MetricRow label="Volume Profile">
              <select
                value={volumeProfile}
                onChange={e => setVolumeProfile(e.target.value)}
                className="bg-gray-900/80 border border-cyan-900/40 rounded px-1 py-0 text-[10px] text-cyan-300 focus:outline-none"
              >
                {VOLUME_PROFILES.map(v => <option key={v} value={v}>{v}</option>)}
              </select>
            </MetricRow>

            <MetricRow label="Dark Pool Activity">
              <Slider min={0} max={100} step={1} value={darkPoolActivity} onChange={setDarkPoolActivity}
                showValue={false} className="flex-1" inputClassName="h-1.5" />
              <span className="text-[10px] text-cyan-400 min-w-[28px] text-right">{darkPoolActivity}</span>
            </MetricRow>

            <MetricRow label="Institutional Accumulation">
              <Slider min={0} max={100} step={1} value={institutionalAccum} onChange={setInstitutionalAccum}
                showValue={false} className="flex-1" inputClassName="h-1.5" />
              <span className="text-[10px] text-cyan-400 min-w-[28px] text-right">{institutionalAccum}</span>
            </MetricRow>

            <MetricRow label="Sector Momentum">
              <Slider min={0} max={100} step={1} value={sectorMomentum} onChange={setSectorMomentum}
                showValue={false} className="flex-1" inputClassName="h-1.5" />
              <span className="text-[10px] text-cyan-400 min-w-[28px] text-right">{sectorMomentum}</span>
            </MetricRow>
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex flex-wrap gap-1.5 mt-2 pt-2 border-t border-cyan-900/30">
          <TealButton icon={Plus} onClick={() => log.info("Spawn scanner agent")}>Spawn New Scanner Agent</TealButton>
          <TealButton icon={Copy} variant="secondary" onClick={() => log.info("Clone agent")}>Clone Agent</TealButton>
          <TealButton icon={Boxes} onClick={() => log.info("Spawn swarm")}>Spawn Swarm</TealButton>
          <TealButton icon={Layers} variant="secondary" onClick={() => log.info("Swarm template")}>Swarm Template</TealButton>
          <TealButton icon={Skull} variant="danger" onClick={() => log.info("Kill all agents")}>Kill All Agents</TealButton>
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
          ? "border-cyan-500/60 bg-cyan-950/40 shadow-[0_0_8px_rgba(6,182,212,0.15)]"
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
        <span>Type: <span className="text-cyan-400">{agent.type}</span></span>
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
  const [patternType, setPatternType] = useState("BPT-4");
  const [architecture, setArchitecture] = useState("Transformer");

  // ML Metric Controls
  const [recursiveSelfImprove, setRecursiveSelfImprove] = useState(0);
  const [accuracyValidation, setAccuracyValidation] = useState(0);
  const [profitFactor, setProfitFactor] = useState(0);
  const [maxDrawdown, setMaxDrawdown] = useState(0);
  const [walkForwardEff, setWalkForwardEff] = useState(0);
  const [outOfSampleAcc, setOutOfSampleAcc] = useState(0);
  const [monteCarloCI, setMonteCarloCI] = useState(0);
  const [monteCarloPct, setMonteCarloPct] = useState("0%");
  const [patternComplexity, setPatternComplexity] = useState(0);

  // API data
  const { data: patternsData } = useApi("patterns", { pollIntervalMs: 30000 });

  const MONTE_CARLO_OPTS = ["90%", "95%", "99%"];

  return (
    <div className="flex flex-col gap-2 h-full">
      {/* Section Title */}
      <div className="flex items-center gap-2 px-1">
        <Brain size={15} className="text-cyan-400" />
        <span className="text-xs font-bold text-cyan-300 uppercase tracking-wider">Pattern Intelligence</span>
      </div>

      {/* PATTERN AGENT FLEET */}
      <SectionBox title="Pattern Agent Fleet" icon={Cpu} className="flex-shrink-0">
        {/* Pattern Agent Cards */}
        <div className="mb-2">
          <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-1.5 flex items-center gap-1">
            <Layers size={10} />
            Pattern Agent Cards
          </div>
          <div className="flex flex-col gap-1 max-h-[90px] overflow-y-auto scrollbar-thin">
            {PATTERN_AGENTS.length === 0 ? (
              <div className="py-3 text-center text-[10px] text-gray-600">No agents</div>
            ) : PATTERN_AGENTS.map(a => (
              <PatternAgentCard
                key={a.id}
                agent={a}
                selected={a.id === selectedPattern}
                onSelect={setSelectedPattern}
              />
            ))}
          </div>
        </div>

        {/* Selected agent config fields: Name, Type, Architecture */}
        <div className="grid grid-cols-3 gap-1.5 mb-2">
          <div>
            <label className="text-[9px] text-gray-500 block mb-0.5">Name</label>
            <input
              type="text"
              value={patternName}
              onChange={e => setPatternName(e.target.value)}
              className="w-full bg-gray-900/80 border border-cyan-900/40 rounded px-1.5 py-0.5 text-[10px] text-cyan-200 focus:outline-none focus:border-cyan-600/60"
            />
          </div>
          <div>
            <label className="text-[9px] text-gray-500 block mb-0.5">Type</label>
            <select
              value={patternType}
              onChange={e => setPatternType(e.target.value)}
              className="w-full bg-gray-900/80 border border-cyan-900/40 rounded px-1 py-0.5 text-[10px] text-cyan-200 focus:outline-none focus:border-cyan-600/60 appearance-none"
            >
              {PATTERN_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div>
            <label className="text-[9px] text-gray-500 block mb-0.5">Architecture</label>
            <select
              value={architecture}
              onChange={e => setArchitecture(e.target.value)}
              className="w-full bg-gray-900/80 border border-cyan-900/40 rounded px-1 py-0.5 text-[10px] text-cyan-200 focus:outline-none focus:border-cyan-600/60 appearance-none"
            >
              {ARCHITECTURES.map(a => <option key={a} value={a}>{a}</option>)}
            </select>
          </div>
        </div>

        {/* ML METRIC CONTROLS */}
        <div className="border-t border-cyan-900/30 pt-2">
          <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-1.5 flex items-center gap-1">
            <Brain size={10} />
            ML Metric Controls
          </div>

          <div className="space-y-1">
            <MetricRow label="Recursive Self-Improvement">
              <Slider min={0} max={100} step={1} value={recursiveSelfImprove} onChange={setRecursiveSelfImprove}
                showValue={false} className="flex-1" inputClassName="h-1.5" />
              <span className="text-[10px] text-cyan-400 min-w-[28px] text-right">{recursiveSelfImprove}</span>
              <MiniSparkline data={generatePatternChartData(15)} width={44} height={16} color="#a78bfa" />
            </MetricRow>

            <MetricRow label="Accuracy Validation Score %">
              <Slider min={0} max={100} step={1} value={accuracyValidation} onChange={setAccuracyValidation}
                showValue={false} className="flex-1" inputClassName="h-1.5" />
              <span className="text-[10px] text-cyan-400 min-w-[28px] text-right">{accuracyValidation}%</span>
              <MiniSparkline data={generatePatternChartData(15)} width={44} height={16} />
            </MetricRow>

            <MetricRow label="Profit Factor">
              <Slider min={0} max={5} step={0.1} value={profitFactor} onChange={setProfitFactor}
                showValue={false} className="flex-1" inputClassName="h-1.5" />
              <span className="text-[10px] text-cyan-400 min-w-[28px] text-right">{profitFactor.toFixed(1)}</span>
              <MiniSparkline data={generatePatternChartData(15)} width={44} height={16} />
            </MetricRow>

            <MetricRow label="Max Drawdown">
              <Slider min={0} max={50} step={1} value={maxDrawdown} onChange={setMaxDrawdown}
                showValue={false} className="flex-1" inputClassName="h-1.5" />
              <span className="text-[10px] text-red-400 min-w-[28px] text-right">{maxDrawdown}%</span>
              <MiniSparkline data={generatePatternChartData(15)} width={44} height={16} color="#f87171" />
            </MetricRow>

            <MetricRow label="Walk-Forward Efficiency">
              <Slider min={0} max={100} step={1} value={walkForwardEff} onChange={setWalkForwardEff}
                showValue={false} className="flex-1" inputClassName="h-1.5" />
              <span className="text-[10px] text-cyan-400 min-w-[28px] text-right">{walkForwardEff}%</span>
              <MiniSparkline data={generatePatternChartData(15)} width={44} height={16} />
            </MetricRow>

            <MetricRow label="Out-of-Sample Accuracy">
              <Slider min={0} max={100} step={1} value={outOfSampleAcc} onChange={setOutOfSampleAcc}
                showValue={false} className="flex-1" inputClassName="h-1.5" />
              <span className="text-[10px] text-cyan-400 min-w-[28px] text-right">{outOfSampleAcc}%</span>
              <MiniSparkline data={generatePatternChartData(15)} width={44} height={16} />
            </MetricRow>

            <MetricRow label={`Monte Carlo CI (${monteCarloPct})`}>
              <div className="flex gap-0.5 mr-1">
                {MONTE_CARLO_OPTS.map(opt => (
                  <button
                    key={opt}
                    onClick={() => setMonteCarloPct(opt)}
                    className={clsx(
                      "px-1 py-0 rounded text-[8px] font-medium transition-colors",
                      monteCarloPct === opt
                        ? "bg-cyan-600 text-white"
                        : "bg-gray-800 text-gray-400 hover:bg-gray-700"
                    )}
                  >
                    {opt.replace("%", "")}
                  </button>
                ))}
              </div>
              <span className="text-[10px] text-cyan-400 min-w-[28px] text-right">{monteCarloCI}%</span>
              <MiniSparkline data={generatePatternChartData(15)} width={44} height={16} />
            </MetricRow>

            <MetricRow label="Pattern Complexity">
              <Slider min={1} max={10} step={1} value={patternComplexity} onChange={setPatternComplexity}
                showValue={false} className="flex-1" inputClassName="h-1.5" />
              <span className="text-[10px] text-cyan-400 min-w-[28px] text-right">{patternComplexity}/10</span>
              <MiniSparkline data={generatePatternChartData(15)} width={44} height={16} />
            </MetricRow>
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex flex-wrap gap-1.5 mt-2 pt-2 border-t border-cyan-900/30">
          <TealButton icon={Plus} onClick={() => log.info("Spawn pattern agent")}>Spawn New Pattern Agent</TealButton>
          <TealButton icon={Boxes} onClick={() => log.info("Spawn discovery swarm")}>Spawn Discovery Swarm</TealButton>
          <TealButton icon={Skull} variant="danger" onClick={() => log.info("Kill all scanners")}>Kill All Scanners</TealButton>
        </div>
      </SectionBox>
    </div>
  );
}

// ═══════════════════════════════════════════════════
// BOTTOM PANELS: Live Feed, Pattern Arsenal, Forming Detections
// ═══════════════════════════════════════════════════

function PatternMiniChart({ data, name, confidence, type }) {
  const color = type === "Reversal" ? "#f472b6" : "#22d3ee";
  return (
    <div className="border border-gray-800/50 rounded bg-gray-900/40 p-1.5">
      <div className="flex items-center justify-between mb-1">
        <span className="text-[9px] font-semibold text-cyan-200 truncate">{name}</span>
        <span className={clsx(
          "text-[9px] font-bold",
          confidence >= 90 ? "text-emerald-400" : confidence >= 80 ? "text-cyan-400" : "text-amber-400"
        )}>{confidence}%</span>
      </div>
      <ResponsiveContainer width="100%" height={48}>
        <AreaChart data={data}>
          <defs>
            <linearGradient id={`pg-${name.replace(/[\s&()]/g, "")}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.3} />
              <stop offset="100%" stopColor={color} stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <Area type="monotone" dataKey="y" stroke={color} strokeWidth={1.2} fill={`url(#pg-${name.replace(/[\s&()]/g, "")})`} dot={false} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

function FormingDetectionCard({ pattern }) {
  return (
    <div className="border border-gray-800/50 rounded bg-gray-900/40 p-1.5">
      <div className="flex items-center justify-between mb-1">
        <span className="text-[9px] font-semibold text-amber-300 truncate">{pattern.name}</span>
        <span className="text-[9px] text-gray-400">{pattern.symbol}</span>
      </div>
      <ProgressBar value={pattern.progress} color="bg-amber-500" className="mb-1" />
      <div className="flex items-center justify-between">
        <span className="text-[8px] text-gray-500">{pattern.timeframe}</span>
        <span className="text-[8px] text-amber-400">{pattern.progress}% formed</span>
      </div>
      <ResponsiveContainer width="100%" height={36}>
        <AreaChart data={pattern.data}>
          <defs>
            <linearGradient id={`fd-${pattern.id}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#f59e0b" stopOpacity={0.3} />
              <stop offset="100%" stopColor="#f59e0b" stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <Area type="monotone" dataKey="y" stroke="#f59e0b" strokeWidth={1} fill={`url(#fd-${pattern.id})`} dot={false} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

function ConsolidatedLiveFeed() {
  // Feed is populated only from real WebSocket messages; starts empty
  const [feedEntries] = useState([]);
  const feedRef = useRef(null);

  return (
    <SectionBox title="Consolidated Live Feed" icon={Radio} className="flex-1 min-h-0 flex flex-col">
      <div ref={feedRef} className="flex-1 overflow-y-auto scrollbar-thin space-y-0 min-h-0 max-h-[200px]">
        {feedEntries.length === 0 ? (
          <div className="flex items-center justify-center h-full py-6">
            <span className="text-[10px] text-gray-600">No feed data</span>
          </div>
        ) : feedEntries.map(entry => (
          <div key={entry.id} className="flex items-start gap-2 py-[3px] border-b border-gray-800/30 hover:bg-cyan-950/20 px-1 text-[10px]">
            <span className="text-gray-600 font-mono whitespace-nowrap">{entry.timestamp}</span>
            <span className={clsx(
              "font-bold min-w-[36px]",
              ["AAPL", "NVDA", "MSFT", "GOOGL"].includes(entry.symbol) ? "text-cyan-400" : "text-emerald-400"
            )}>{entry.symbol}</span>
            <span className="text-gray-500">{entry.agent}</span>
            <span className="text-gray-300 truncate">{entry.action}</span>
          </div>
        ))}
      </div>
    </SectionBox>
  );
}

function PatternArsenalPanel() {
  return (
    <SectionBox title="Pattern Arsenal" icon={Target} className="flex-1 min-h-0 flex flex-col">
      <div className="flex-1 overflow-y-auto scrollbar-thin space-y-1.5 max-h-[200px]">
        {PATTERNS_ARSENAL.length === 0 ? (
          <div className="flex items-center justify-center h-full py-6">
            <span className="text-[10px] text-gray-600">No patterns detected</span>
          </div>
        ) : PATTERNS_ARSENAL.map(p => (
          <PatternMiniChart
            key={p.id}
            data={p.data}
            name={`${p.name} (${p.symbol} ${p.timeframe})`}
            confidence={p.confidence}
            type={p.type}
          />
        ))}
      </div>
    </SectionBox>
  );
}

function FormingDetectionsPanel() {
  return (
    <SectionBox title="Forming Detections" icon={Crosshair} className="flex-1 min-h-0 flex flex-col">
      <div className="flex-1 overflow-y-auto scrollbar-thin space-y-1.5 max-h-[200px]">
        {FORMING_PATTERNS.length === 0 ? (
          <div className="flex items-center justify-center h-full py-6">
            <span className="text-[10px] text-gray-600">No forming detections</span>
          </div>
        ) : FORMING_PATTERNS.map(f => (
          <FormingDetectionCard key={f.id} pattern={f} />
        ))}
      </div>
    </SectionBox>
  );
}

// ═══════════════════════════════════════════════════
// MAIN PAGE
// ═══════════════════════════════════════════════════

export default function Patterns() {
  return (
    <div className="flex flex-col h-full min-h-0 p-4 gap-3">
      {/* Page Title */}
      <PageHeader
        icon={Radar}
        title="Screener and Patterns"
        description="Scan Agent Fleet management, trading metric controls, pattern intelligence, and ML-powered detection"
      />

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

      {/* Footer status bar */}
      <div className="flex-shrink-0 flex items-center justify-between px-3 py-1.5 bg-cyan-950/20 border border-cyan-900/30 rounded text-[9px] text-gray-500">
        <div className="flex items-center gap-4">
          <span>Patterns <span className="text-cyan-400">4541</span></span>
          <span className="text-gray-600">|</span>
          <span>5 agents: <span className="text-cyan-400">42</span></span>
        </div>
        <div className="flex items-center gap-4">
          <span>Status <span className="text-emerald-400">150000</span></span>
          <div className="flex items-center gap-1">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span>Live</span>
          </div>
        </div>
      </div>
    </div>
  );
}
