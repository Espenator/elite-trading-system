// AGENT COMMAND CENTER - Embodier.ai Glass House Intelligence System
// Agent management: status, controls, logs, task queues
import { useState } from 'react';
import {
  Bot, Eye, Brain, ShieldCheck, Youtube, Play, Pause,
  RefreshCw, Activity, Clock, CheckCircle, AlertCircle, ToggleLeft, ToggleRight
} from 'lucide-react';

const AGENTS = [
  {
    id: 1, name: 'Market Scanner', icon: Eye, status: 'active', uptime: '72h 15m',
    tasksCompleted: 1420, tasksQueued: 8, lastAction: 'Scanned AAPL for breakout patterns',
    description: '24/7 multi-timeframe market scanning for trade opportunities',
    config: { scanInterval: 30, tickers: 'S&P 500', timeframes: '1m, 5m, 1H, 1D' }
  },
  {
    id: 2, name: 'Pattern AI', icon: Brain, status: 'active', uptime: '72h 15m',
    tasksCompleted: 890, tasksQueued: 3, lastAction: 'Detected Bull Flag on MSFT (87% conf)',
    description: 'AI-powered chart pattern recognition across all monitored assets',
    config: { minConfidence: 70, patterns: 'All', autoAlert: true }
  },
  {
    id: 3, name: 'Risk Manager', icon: ShieldCheck, status: 'active', uptime: '72h 15m',
    tasksCompleted: 560, tasksQueued: 1, lastAction: 'Adjusted stop-loss on NVDA position',
    description: 'Real-time portfolio risk monitoring and position management',
    config: { maxDrawdown: 5, circuitBreaker: true, positionLimit: 15 }
  },
  {
    id: 4, name: 'YouTube Ingestion', icon: Youtube, status: 'learning', uptime: '48h 30m',
    tasksCompleted: 145, tasksQueued: 12, lastAction: 'Processing: "Top 5 Swing Trade Setups"',
    description: 'Transcribes financial YouTube videos and extracts trading insights',
    config: { channels: 8, autoProcess: true, extractAlgos: true }
  },
];

const LOGS = [
  { time: '13:02:15', agent: 'Market Scanner', message: 'New bullish signal detected: AAPL breakout above $192', level: 'info' },
  { time: '13:01:48', agent: 'Pattern AI', message: 'Bull Flag pattern confirmed on MSFT (87% confidence)', level: 'success' },
  { time: '13:00:30', agent: 'Risk Manager', message: 'Position risk check passed - all within limits', level: 'info' },
  { time: '12:58:12', agent: 'YouTube Ingestion', message: 'Transcript extracted: 5 new trading ideas added to queue', level: 'success' },
  { time: '12:55:00', agent: 'Market Scanner', message: 'SPY approaching key resistance at $503.50', level: 'warning' },
  { time: '12:52:30', agent: 'Risk Manager', message: 'NVDA stop-loss tightened to $858 (trailing)', level: 'info' },
];

export default function AgentCommandCenter() {
  const [selectedAgent, setSelectedAgent] = useState(null);

  const getStatusColor = (status) => {
    switch(status) {
      case 'active': return 'bg-emerald-400';
      case 'learning': return 'bg-amber-400';
      case 'paused': return 'bg-gray-400';
      case 'error': return 'bg-red-400';
      default: return 'bg-gray-400';
    }
  };

  const getLevelColor = (level) => {
    switch(level) {
      case 'success': return 'text-emerald-400';
      case 'warning': return 'text-amber-400';
      case 'error': return 'text-red-400';
      default: return 'text-blue-400';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Agent Command Center</h1>
          <p className="text-sm text-gray-400 mt-1">Monitor and control your AI agents</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
            <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-sm text-emerald-400">{AGENTS.filter(a => a.status === 'active').length}/{AGENTS.length} Active</span>
          </div>
        </div>
      </div>

      {/* Agent cards grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {AGENTS.map(agent => (
          <div key={agent.id}
            className={`bg-slate-800/30 border rounded-2xl p-5 transition-all cursor-pointer ${
              selectedAgent === agent.id ? 'border-blue-500/50 shadow-lg shadow-blue-500/10' : 'border-white/10 hover:border-white/20'
            }`}
            onClick={() => setSelectedAgent(selectedAgent === agent.id ? null : agent.id)}
          >
            {/* Agent header */}
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-purple-500/10 flex items-center justify-center">
                  <agent.icon className="w-5 h-5 text-purple-400" />
                </div>
                <div>
                  <div className="text-lg font-semibold text-white">{agent.name}</div>
                  <div className="text-xs text-gray-500">{agent.description}</div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <div className={`w-2.5 h-2.5 rounded-full ${getStatusColor(agent.status)} animate-pulse`} />
                <span className="text-xs text-gray-400 capitalize">{agent.status}</span>
              </div>
            </div>

            {/* Stats row */}
            <div className="grid grid-cols-3 gap-3 mb-4">
              <div className="text-center p-2 bg-slate-800/40 rounded-xl">
                <div className="text-lg font-bold text-white">{agent.tasksCompleted.toLocaleString()}</div>
                <div className="text-xs text-gray-500">Completed</div>
              </div>
              <div className="text-center p-2 bg-slate-800/40 rounded-xl">
                <div className="text-lg font-bold text-amber-400">{agent.tasksQueued}</div>
                <div className="text-xs text-gray-500">Queued</div>
              </div>
              <div className="text-center p-2 bg-slate-800/40 rounded-xl">
                <div className="text-sm font-bold text-white">{agent.uptime}</div>
                <div className="text-xs text-gray-500">Uptime</div>
              </div>
            </div>

            {/* Last action */}
            <div className="text-xs text-gray-500 mb-3">
              <span className="text-gray-400">Last: </span>{agent.lastAction}
            </div>

            {/* Controls */}
            <div className="flex items-center gap-2 pt-3 border-t border-white/5">
              <button className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-500/20 text-emerald-400 rounded-lg text-xs font-medium hover:bg-emerald-500/30 transition-colors">
                <Play className="w-3 h-3" /> Start
              </button>
              <button className="flex items-center gap-1.5 px-3 py-1.5 bg-amber-500/20 text-amber-400 rounded-lg text-xs font-medium hover:bg-amber-500/30 transition-colors">
                <Pause className="w-3 h-3" /> Pause
              </button>
              <button className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-500/20 text-blue-400 rounded-lg text-xs font-medium hover:bg-blue-500/30 transition-colors">
                <RefreshCw className="w-3 h-3" /> Restart
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Activity Log */}
      <div className="bg-slate-800/30 border border-white/10 rounded-2xl overflow-hidden">
        <div className="flex items-center justify-between px-5 py-4 border-b border-white/5">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-gray-400" />
            <h3 className="text-sm font-semibold text-white">Activity Log</h3>
          </div>
          <span className="text-xs text-gray-500">Real-time</span>
        </div>
        <div className="divide-y divide-white/5 max-h-80 overflow-y-auto">
          {LOGS.map((log, i) => (
            <div key={i} className="flex items-start gap-3 px-5 py-3 hover:bg-white/5 transition-colors">
              <span className="text-xs font-mono text-gray-600 shrink-0 mt-0.5">{log.time}</span>
              <span className={`text-xs font-medium shrink-0 mt-0.5 ${getLevelColor(log.level)}`}>
                {log.level === 'success' ? <CheckCircle className="w-3.5 h-3.5 inline" /> : log.level === 'warning' ? <AlertCircle className="w-3.5 h-3.5 inline" /> : <Activity className="w-3.5 h-3.5 inline" />}
              </span>
              <div className="flex-1 min-w-0">
                <span className="text-xs font-medium text-purple-400">[{log.agent}]</span>
                <span className="text-xs text-gray-400 ml-2">{log.message}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
