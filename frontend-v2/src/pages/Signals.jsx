// SIGNALS PAGE - Embodier.ai Glass House Intelligence System
// GET /api/v1/signals - live signals; OpenClaw composite score + tier from /api/v1/openclaw/scan
// V3 Ultra-Dense: SHAP waterfalls, correlation matrix, accuracy table, decay curve,
//   composite breakdown, volume/options/darkpool, 15 filters, recursive improvement
import { useState, useMemo, useEffect, useCallback, useRef } from "react";
import { useNavigate } from "react-router-dom";
import {
  Zap,
  Clock,
  Target,
  Brain,
  Search,
  TrendingUp,
  TrendingDown,
  RefreshCw,
  ArrowUpRight,
  Sparkles,
  BarChart3,
  Activity,
  Eye,
  Shield,
  Layers,
  Filter,
  ChevronDown,
  ChevronUp,
  ChevronRight,
  Hash,
  Percent,
  LineChart,
  PieChart,
  AlertTriangle,
  Radio,
  Workflow,
  RefreshCcw,
  Flame,
  ArrowDown,
  ArrowUp,
  Settings,
  Grid3X3,
  Table2,
  GitBranch,
} from "lucide-react";
import Card from "../components/ui/Card";
import TextField from "../components/ui/TextField";
import Select from "../components/ui/Select";
import Button from "../components/ui/Button";
import Badge from "../components/ui/Badge";
import PageHeader from "../components/ui/PageHeader";
import { useApi } from "../hooks/useApi";
import { getApiUrl } from "../config/api";
import { toast } from "react-toastify";

/** Derive tier from composite score: SLAM 90+, HIGH 80+, TRADEABLE 70+, WATCH 50+ */
function getTier(score) {
  if (score == null || Number.isNaN(score)) return null;
  const s = Number(score);
  if (s >= 90) return { label: "SLAM", variant: "success" };
  if (s >= 80) return { label: "HIGH", variant: "success" };
  if (s >= 70) return { label: "TRADEABLE", variant: "primary" };
  if (s >= 50) return { label: "WATCH", variant: "warning" };
  return null;
}

function getTierVariantFromLabel(label) {
  if (!label) return "secondary";
  const L = String(label).toUpperCase();
  if (L === "SLAM" || L === "HIGH") return "success";
  if (L === "TRADEABLE") return "primary";
  if (L === "WATCH") return "warning";
  return "secondary";
}

/** Normalize backend signal { symbol, date, prob_up, action } to UI shape */
function normalizeSignals(backend) {
  if (!backend?.signals?.length) return [];
  return backend.signals.map((s, i) => ({
    id: s.id ?? i + 1,
    ticker: s.symbol || s.ticker || "—",
    type: s.type || "ML Signal",
    direction: s.action === "BUY" ? "long" : "short",
    score: Math.round((s.prob_up ?? 0.5) * 100),
    mlConfidence: Math.round((s.prob_up ?? 0.5) * 100),
    price: s.price ?? 0,
    target: s.target ?? 0,
    stop: s.stop ?? 0,
    timeframe: s.timeframe || "1D",
    time: s.date || s.timestamp || "—",
    source: s.source || "ML Engine",
    sector: s.sector || null,
    features: s.features || s.shap_values || null,
    decay: s.decay_curve || s.decay || null,
    sub_scores: s.sub_scores || s.components || null,
    volume_profile: s.volume_profile || null,
    options_flow: s.options_flow || null,
    dark_pool: s.dark_pool || null,
    accuracy_7d: s.accuracy_7d ?? null,
    accuracy_30d: s.accuracy_30d ?? null,
    accuracy_90d: s.accuracy_90d ?? null,
    total_count: s.total_count ?? null,
  }));
}

function ScoreRing({ score, size = 56, showGlow = false }) {
  const r = (size - 6) / 2;
  const circ = 2 * Math.PI * r;
  const offset = circ - (score / 100) * circ;
  const isHigh = score >= 75;
  const isMid = score >= 55 && score < 75;
  const stroke = isHigh ? "#22c55e" : isMid ? "#eab308" : "#ef4444";
  return (
    <div className="relative inline-flex items-center justify-center">
      {showGlow && isHigh && (
        <div
          className="absolute inset-0 rounded-full opacity-40 blur-md"
          style={{
            background:
              "radial-gradient(circle, #22c55e40 0%, transparent 70%)",
          }}
        />
      )}
      <svg width={size} height={size} className="-rotate-90 shrink-0">
        ircle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="rgba(30,41,59,0.6)"
          strokeWidth={4}
        />
        ircle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={stroke}
          strokeWidth={4}
          strokeDasharray={circ}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className="transition-all duration-700 ease-out"
        />
      </svg>
      <span
        className="absolute inset-0 flex items-center justify-center text-sm font-bold text-white"
        style={{ fontSize: size * 0.28 }}
      >
        {score}
      </span>
    </div>
  );
}

function ScoreBar({ score }) {
  const width = Math.min(100, Math.max(0, score));
  const bg =
    score >= 75
      ? "from-emerald-500 to-green-400"
      : score >= 55
        ? "from-amber-500 to-yellow-400"
        : "from-red-500 to-rose-400";
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-secondary/30">
      <div
        className={`h-full rounded-full bg-gradient-to-r ${bg} transition-all duration-500`}
        style={{ width: `${width}%` }}
      />
    </div>
  );
}

// ─── V3: SHAP Waterfall Bar (horizontal stacked from real signal.features) ───
function ShapWaterfall({ features, onClick }) {
  if (!features || typeof features !== "object") return null;
  const entries = Array.isArray(features)
    ? features
    : Object.entries(features).map(([k, v]) => ({ name: k, value: Number(v) || 0 }));
  if (entries.length === 0) return null;
  const maxVal = Math.max(...entries.map((e) => Math.abs(e.value || 0)), 1);
  return (
    <div
      className="mt-2 space-y-1 cursor-pointer"
      onClick={onClick || (() => toast.info("Opening SHAP analysis"))}
    >
      <div className="text-[9px] text-secondary uppercase font-mono tracking-wider flex items-center gap-1">
        <BarChart3 className="w-3 h-3 text-cyan-500" /> SHAP Importance
      </div>
      {entries.slice(0, 5).map((f, i) => {
        const val = f.value || 0;
        const pct = (Math.abs(val) / maxVal) * 100;
        return (
          <div key={f.name || i} className="flex items-center gap-2">
            <span className="text-[9px] text-secondary font-mono w-16 truncate shrink-0">
              {f.name || `F${i}`}
            </span>
            <div className="flex-1 h-1.5 bg-secondary/20 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-500 ${val >= 0 ? "bg-cyan-500" : "bg-red-500"}`}
                style={{ width: `${pct}%` }}
              />
            </div>
            <span
              className={`text-[9px] font-mono w-8 text-right shrink-0 ${val >= 0 ? "text-cyan-400" : "text-red-400"}`}
            >
              {val >= 0 ? "+" : ""}
              {val.toFixed(1)}
            </span>
          </div>
        );
      })}
    </div>
  );
}

// ─── V3: Mini SVG Line for decay/improvement curves ───
function MiniSvgLine({ points, color, height = 40, width = 160, label, onClick }) {
  const vals = Array.isArray(points) && points.length > 0 ? points.map(Number) : [];
  if (vals.length < 2) {
    return (
      <div
        className="bg-[#0B0E14] border border-secondary/20 rounded-lg p-2 cursor-pointer hover:border-cyan-500/40 transition-colors"
        onClick={onClick}
      >
        {label && (
          <span className="text-[9px] text-secondary font-mono uppercase tracking-wider">
            {label}
          </span>
        )}
        <div className="text-[10px] text-secondary/50 font-mono mt-1">
          Awaiting data
        </div>
      </div>
    );
  }
  const min = Math.min(...vals);
  const max = Math.max(...vals);
  const range = max - min || 1;
  const polyline = vals
    .map(
      (v, i) =>
        `${(i / (vals.length - 1)) * width},${height - ((v - min) / range) * height}`
    )
    .join(" ");
  return (
    <div
      className="bg-[#0B0E14] border border-secondary/20 rounded-lg p-2 cursor-pointer hover:border-cyan-500/40 transition-colors"
      onClick={onClick || (() => toast.info(`Expanding ${label || "chart"}`))}
    >
      {label && (
        <div className="flex items-center justify-between mb-1">
          <span className="text-[9px] text-secondary font-mono uppercase tracking-wider">
            {label}
          </span>
          <span
            className={`text-[9px] font-mono font-bold ${vals[vals.length - 1] >= vals[0] ? "text-emerald-400" : "text-red-400"}`}
          >
            {vals[vals.length - 1] >= vals[0] ? "+" : ""}
            {(
              ((vals[vals.length - 1] - vals[0]) / (vals[0] || 1)) *
              100
            ).toFixed(1)}
            %
          </span>
        </div>
      )}
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full" style={{ height }}>
        <polyline
          points={polyline}
          fill="none"
          stroke={color || "#06B6D4"}
          strokeWidth="2"
          strokeLinejoin="round"
          strokeLinecap="round"
        />
      </svg>
    </div>
  );
}

// ─── V3: Composite Score Breakdown (stacked horizontal bar from sub_scores) ───
function CompositeBreakdown({ subScores, onClick }) {
  if (!subScores || typeof subScores !== "object") return null;
  const entries = Array.isArray(subScores)
    ? subScores
    : Object.entries(subScores).map(([k, v]) => ({ name: k, value: Number(v) || 0 }));
  if (entries.length === 0) return null;
  const total = entries.reduce((sum, e) => sum + Math.abs(e.value || 0), 0) || 1;
  const colors = [
    "bg-cyan-500",
    "bg-amber-500",
    "bg-emerald-500",
    "bg-purple-500",
    "bg-red-500",
    "bg-blue-500",
    "bg-pink-500",
    "bg-teal-500",
  ];
  return (
    <div
      className="mt-2 cursor-pointer"
      onClick={onClick || (() => toast.info("Opening composite breakdown"))}
    >
      <div className="text-[9px] text-secondary uppercase font-mono tracking-wider flex items-center gap-1 mb-1">
        <Layers className="w-3 h-3 text-amber-500" /> Score Breakdown
      </div>
      <div className="flex w-full h-2 rounded-full overflow-hidden bg-secondary/20">
        {entries.map((e, i) => (
          <div
            key={e.name || i}
            className={`${colors[i % colors.length]} hover:brightness-125 transition-all`}
            style={{ width: `${(Math.abs(e.value || 0) / total) * 100}%` }}
            title={`${e.name}: ${(e.value || 0).toFixed(1)}`}
          />
        ))}
      </div>
      <div className="flex flex-wrap gap-x-3 gap-y-0.5 mt-1">
        {entries.slice(0, 4).map((e, i) => (
          <span key={e.name || i} className="text-[8px] text-secondary/70 font-mono flex items-center gap-1">
            <span
              className={`inline-block w-1.5 h-1.5 rounded-full ${colors[i % colors.length]}`}
            />
            {e.name}
          </span>
        ))}
      </div>
    </div>
  );
}

// ─── V3: Volume/Options/DarkPool Indicators ───
function FlowIndicators({ signal, onClick }) {
  const hasVolume = signal.volume_profile != null;
  const hasOptions = signal.options_flow != null;
  const hasDarkPool = signal.dark_pool != null;
  if (!hasVolume && !hasOptions && !hasDarkPool) return null;
  return (
    <div className="mt-2 flex flex-wrap gap-2">
      {hasVolume && (
        <span
          className="inline-flex items-center gap-1 text-[9px] font-mono px-1.5 py-0.5 rounded bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 cursor-pointer hover:bg-cyan-500/
