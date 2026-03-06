import { useMemo } from 'react';
import {
  Brain, Activity, Zap, Target, Gauge, Clock,
  TrendingUp, TrendingDown, Minus, Shuffle,
  BarChart3, PieChart as PieChartIcon
} from 'lucide-react';
import { useApi } from '../hooks/useApi';
import Card from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import PageHeader from '../components/ui/PageHeader';

// --- FALLBACK DATA ---
const FALLBACK = {
  total_evaluations: 0,
  metrics: { avg_hypothesis_diversity: 0, avg_agent_agreement: 0, avg_memory_precision: 0, avg_latency_ms: 0 },
  mode_distribution: { exploit: 1.0 },
  mode_switches_24h: 0,
  latency_profile: {},
  calibration: { brier_score: null, total_predictions: 0 },
  exploration_outcomes: {},
  recent_snapshots: [],
  time_series: [],
};

// --- COLORS ---
const CYAN = '#00D9FF';
const EMERALD = '#10b981';
const RED = '#ef4444';
const AMBER = '#f59e0b';
const PURPLE = '#a78bfa';

// --- KPI Card ---
function KpiCard({ icon: Icon, label, value, sub, color = CYAN }) {
  return (
    <Card noPadding>
      <div className="p-3 flex flex-col gap-1">
        <div className="flex items-center gap-1.5">
          <Icon size={13} style={{ color }} />
          <span className="text-[10px] text-gray-400 uppercase tracking-wider">{label}</span>
        </div>
        <span className="text-xl font-bold text-white" style={{ color }}>{value}</span>
        {sub && <span className="text-[10px] text-gray-500">{sub}</span>}
      </div>
    </Card>
  );
}

// --- Donut Chart (inline SVG) ---
function ModeDonut({ distribution }) {
  const modes = [
    { key: 'explore', label: 'Explore', color: PURPLE },
    { key: 'exploit', label: 'Exploit', color: CYAN },
    { key: 'defensive', label: 'Defensive', color: RED },
  ];

  const total = modes.reduce((s, m) => s + (distribution[m.key] || 0), 0) || 1;
  const r = 50;
  const cx = 60;
  const cy = 60;
  const strokeWidth = 18;
  const circumference = 2 * Math.PI * r;

  let cumulativeOffset = 0;
  const segments = modes.map((m) => {
    const pct = (distribution[m.key] || 0) / total;
    const dashArray = `${pct * circumference} ${circumference}`;
    const rotation = cumulativeOffset * 360 - 90;
    cumulativeOffset += pct;
    return { ...m, pct, dashArray, rotation };
  });

  return (
    <div className="flex items-center gap-4">
      <svg width={120} height={120} viewBox="0 0 120 120">
        {segments.map((seg) => (
          <circle
            key={seg.key}
            cx={cx}
            cy={cy}
            r={r}
            fill="none"
            stroke={seg.color}
            strokeWidth={strokeWidth}
            strokeDasharray={seg.dashArray}
            strokeDashoffset={0}
            transform={`rotate(${seg.rotation} ${cx} ${cy})`}
            strokeLinecap="butt"
            opacity={seg.pct > 0 ? 1 : 0}
          />
        ))}
        <text x={cx} y={cy - 4} textAnchor="middle" className="text-[10px]" fill="#9CA3AF">MODE</text>
        <text x={cx} y={cy + 10} textAnchor="middle" className="text-xs font-bold" fill="white">DIST</text>
      </svg>
      <div className="flex flex-col gap-1.5">
        {segments.map((seg) => (
          <div key={seg.key} className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: seg.color }} />
            <span className="text-[10px] text-gray-400 uppercase w-16">{seg.label}</span>
            <span className="text-xs font-semibold text-white">{(seg.pct * 100).toFixed(1)}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// --- Horizontal Bar Chart ---
function LatencyBars({ profile }) {
  const stages = ['stage1', 'stage2', 'stage3', 'stage4', 'stage5', 'stage6', 'total'];
  const entries = stages.filter((s) => profile[s] != null).map((s) => ({ stage: s, ms: profile[s] }));
  const maxMs = Math.max(...entries.map((e) => e.ms), 1);

  function barColor(ms) {
    if (ms < 200) return EMERALD;
    if (ms <= 500) return AMBER;
    return RED;
  }

  return (
    <div className="flex flex-col gap-1.5">
      {entries.map((e) => (
        <div key={e.stage} className="flex items-center gap-2">
          <span className="text-[10px] text-gray-400 w-12 text-right font-mono">{e.stage}</span>
          <div className="flex-1 h-3 bg-gray-800 rounded-sm overflow-hidden">
            <div
              className="h-full rounded-sm transition-all"
              style={{ width: `${(e.ms / maxMs) * 100}%`, backgroundColor: barColor(e.ms) }}
            />
          </div>
          <span className="text-[10px] text-gray-300 w-14 text-right font-mono">{e.ms.toFixed(0)}ms</span>
        </div>
      ))}
    </div>
  );
}

// --- Sparkline Mini Chart ---
function Sparkline({ data, dataKey, color = CYAN, height = 48 }) {
  const points = useMemo(() => {
    if (!data?.length) return '';
    const values = data.map((d) => d[dataKey]).filter((v) => v != null);
    if (!values.length) return '';
    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = max - min || 1;
    const w = 160;
    const h = height - 4;
    return values.map((v, i) => `${(i / (values.length - 1)) * w},${h - ((v - min) / range) * h + 2}`).join(' ');
  }, [data, dataKey, height]);

  const values = data?.map((d) => d[dataKey]).filter((v) => v != null) || [];
  const latest = values.length ? values[values.length - 1] : null;

  return (
    <div className="flex items-center gap-2">
      <svg width={160} height={height} viewBox={`0 0 160 ${height}`} className="flex-shrink-0">
        {points && (
          <polyline
            points={points}
            fill="none"
            stroke={color}
            strokeWidth={1.5}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        )}
        {!points && (
          <text x={80} y={height / 2 + 4} textAnchor="middle" className="text-[10px]" fill="#4B5563">No data</text>
        )}
      </svg>
      {latest != null && (
        <span className="text-xs font-semibold text-white">{typeof latest === 'number' ? latest.toFixed(2) : latest}</span>
      )}
    </div>
  );
}

// --- Exploration vs Exploitation ---
function ExploreExploitCard({ outcomes }) {
  const explore = outcomes?.explore || { win_rate: 0, count: 0, avg_r_multiple: 0 };
  const exploit = outcomes?.exploit || { win_rate: 0, count: 0, avg_r_multiple: 0 };

  function Side({ label, data, color }) {
    return (
      <div className="flex-1 flex flex-col items-center gap-1 p-3">
        <span className="text-[10px] text-gray-400 uppercase tracking-wider">{label}</span>
        <span className="text-2xl font-bold" style={{ color }}>{(data.win_rate * 100).toFixed(1)}%</span>
        <span className="text-[10px] text-gray-500">Win Rate</span>
        <div className="flex gap-3 mt-1">
          <div className="text-center">
            <span className="text-xs font-semibold text-white">{data.count}</span>
            <span className="text-[10px] text-gray-500 block">Trades</span>
          </div>
          <div className="text-center">
            <span className="text-xs font-semibold text-white">{data.avg_r_multiple?.toFixed(2) || '0.00'}</span>
            <span className="text-[10px] text-gray-500 block">Avg R</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex divide-x divide-cyan-500/20">
      <Side label="Explore" data={explore} color={PURPLE} />
      <Side label="Exploit" data={exploit} color={CYAN} />
    </div>
  );
}

// --- Snapshots Table ---
function SnapshotsTable({ snapshots }) {
  function dirColor(dir) {
    if (!dir) return 'text-gray-500';
    const d = dir.toLowerCase();
    if (d === 'buy' || d === 'long') return 'text-emerald-400';
    if (d === 'sell' || d === 'short') return 'text-red-400';
    return 'text-gray-400';
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-[11px]">
        <thead>
          <tr className="text-gray-500 uppercase tracking-wider border-b border-cyan-500/10">
            <th className="text-left py-1.5 px-2 font-medium">Time</th>
            <th className="text-left py-1.5 px-2 font-medium">Symbol</th>
            <th className="text-left py-1.5 px-2 font-medium">Dir</th>
            <th className="text-right py-1.5 px-2 font-medium">Conf</th>
            <th className="text-left py-1.5 px-2 font-medium">Mode</th>
            <th className="text-right py-1.5 px-2 font-medium">Diversity</th>
            <th className="text-right py-1.5 px-2 font-medium">Latency</th>
          </tr>
        </thead>
        <tbody>
          {snapshots.length === 0 && (
            <tr>
              <td colSpan={7} className="text-center py-4 text-gray-600">No recent evaluations</td>
            </tr>
          )}
          {snapshots.map((s, i) => (
            <tr key={i} className="border-b border-cyan-500/5 hover:bg-white/[0.02] transition-colors">
              <td className="py-1.5 px-2 text-gray-400 font-mono">{s.time || '—'}</td>
              <td className="py-1.5 px-2 text-white font-semibold">{s.symbol || '—'}</td>
              <td className={`py-1.5 px-2 font-semibold ${dirColor(s.direction)}`}>{s.direction || '—'}</td>
              <td className="py-1.5 px-2 text-right text-cyan-300 font-mono">{s.confidence != null ? s.confidence.toFixed(2) : '—'}</td>
              <td className="py-1.5 px-2">
                {s.mode ? (
                  <Badge variant={s.mode === 'exploit' ? 'cyan' : s.mode === 'explore' ? 'purple' : 'red'}>
                    {s.mode}
                  </Badge>
                ) : '—'}
              </td>
              <td className="py-1.5 px-2 text-right text-gray-300 font-mono">{s.diversity != null ? s.diversity.toFixed(2) : '—'}</td>
              <td className="py-1.5 px-2 text-right text-gray-300 font-mono">{s.latency_ms != null ? `${s.latency_ms.toFixed(0)}ms` : '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// --- MAIN COMPONENT ---
export default function CognitiveDashboard() {
  const { data: dashboard } = useApi('cognitiveDashboard', { pollIntervalMs: 10000 });

  const d = dashboard || FALLBACK;
  const m = d.metrics || FALLBACK.metrics;
  const cal = d.calibration || FALLBACK.calibration;
  const modeDist = d.mode_distribution || FALLBACK.mode_distribution;
  const latency = d.latency_profile || FALLBACK.latency_profile;
  const outcomes = d.exploration_outcomes || FALLBACK.exploration_outcomes;
  const snapshots = (d.recent_snapshots || []).slice(0, 10);
  const timeSeries = d.time_series || [];

  function metricColor(val, good, threshold) {
    if (val == null) return CYAN;
    return good === 'high'
      ? val > threshold ? EMERALD : AMBER
      : val < threshold ? EMERALD : RED;
  }

  return (
    <div className="space-y-4 pb-8">
      <PageHeader
        title="COGNITIVE TELEMETRY"
        subtitle="Embodier Trader Being Intelligence — Research Dashboard"
      />

      {/* KPI Strip */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <KpiCard
          icon={Brain}
          label="Total Evaluations"
          value={d.total_evaluations.toLocaleString()}
          color={CYAN}
        />
        <KpiCard
          icon={Shuffle}
          label="Hypothesis Diversity"
          value={m.avg_hypothesis_diversity.toFixed(2)}
          sub="Avg (0-1)"
          color={metricColor(m.avg_hypothesis_diversity, 'high', 0.5)}
        />
        <KpiCard
          icon={Target}
          label="Agent Agreement"
          value={m.avg_agent_agreement.toFixed(2)}
          sub="Avg (0-1)"
          color={metricColor(m.avg_agent_agreement, 'high', 0.7)}
        />
        <KpiCard
          icon={Gauge}
          label="Memory Precision"
          value={m.avg_memory_precision.toFixed(2)}
          sub="Avg (0-1)"
          color={CYAN}
        />
        <KpiCard
          icon={Target}
          label="Brier Score"
          value={cal.brier_score != null ? cal.brier_score.toFixed(3) : 'N/A'}
          sub={`${cal.total_predictions} predictions`}
          color={cal.brier_score != null ? metricColor(cal.brier_score, 'low', 0.25) : CYAN}
        />
        <KpiCard
          icon={Zap}
          label="Mode Switches (24h)"
          value={d.mode_switches_24h}
          color={AMBER}
        />
      </div>

      {/* Middle Row: Mode Distribution | Latency Profile | Explore vs Exploit */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <Card noPadding>
          <div className="p-4">
            <div className="flex items-center gap-1.5 mb-3">
              <PieChartIcon size={13} className="text-purple-400" />
              <span className="text-[10px] text-gray-400 uppercase tracking-wider">Mode Distribution</span>
            </div>
            <ModeDonut distribution={modeDist} />
          </div>
        </Card>

        <Card noPadding>
          <div className="p-4">
            <div className="flex items-center gap-1.5 mb-3">
              <BarChart3 size={13} className="text-cyan-400" />
              <span className="text-[10px] text-gray-400 uppercase tracking-wider">Latency Profile</span>
            </div>
            {Object.keys(latency).length > 0 ? (
              <LatencyBars profile={latency} />
            ) : (
              <div className="text-[10px] text-gray-600 py-4 text-center">No latency data</div>
            )}
          </div>
        </Card>

        <Card noPadding>
          <div className="p-4">
            <div className="flex items-center gap-1.5 mb-3">
              <Activity size={13} className="text-emerald-400" />
              <span className="text-[10px] text-gray-400 uppercase tracking-wider">Explore vs Exploit Outcomes</span>
            </div>
            <ExploreExploitCard outcomes={outcomes} />
          </div>
        </Card>
      </div>

      {/* Time Series Sparklines */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
        {[
          { key: 'diversity', label: 'Diversity', color: PURPLE },
          { key: 'agreement', label: 'Agreement', color: CYAN },
          { key: 'confidence', label: 'Confidence', color: EMERALD },
          { key: 'latency_ms', label: 'Latency', color: AMBER },
        ].map((chart) => (
          <Card noPadding key={chart.key}>
            <div className="p-3">
              <div className="flex items-center gap-1.5 mb-2">
                <TrendingUp size={11} style={{ color: chart.color }} />
                <span className="text-[10px] text-gray-400 uppercase tracking-wider">{chart.label} Over Time</span>
              </div>
              <Sparkline data={timeSeries} dataKey={chart.key} color={chart.color} />
            </div>
          </Card>
        ))}
      </div>

      {/* Recent Snapshots Table */}
      <Card noPadding>
        <div className="p-4">
          <div className="flex items-center gap-1.5 mb-3">
            <Clock size={13} className="text-cyan-400" />
            <span className="text-[10px] text-gray-400 uppercase tracking-wider">Recent Evaluations</span>
            <span className="text-[10px] text-gray-600 ml-auto">Last 10</span>
          </div>
          <SnapshotsTable snapshots={snapshots} />
        </div>
      </Card>
    </div>
  );
}
