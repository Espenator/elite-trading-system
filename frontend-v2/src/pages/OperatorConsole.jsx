// OPERATOR CONSOLE - Embodier.ai Glass House Intelligence System
// PURPOSE: Master command view - see everything the AI sees, all agent activity, profit impact
// PROFIT FOCUS: Every action shows P&L impact, risk exposure, and trade opportunity cost
// BACKEND: /api/v1/system - system logs, agent states, performance metrics

import { useState, useEffect } from 'react';
import {
  Terminal,
  Activity,
  AlertTriangle,
  CheckCircle,
  Clock,
  DollarSign,
  TrendingUp,
  TrendingDown,
  Eye,
  Pause,
  Play,
  RefreshCw
} from 'lucide-react';

// Mock real-time system logs with P&L context
const MOCK_LOGS = [
  { id: 1, timestamp: '14:32:15', agent: 'SignalAgent', action: 'BUY signal generated', ticker: 'NVDA', confidence: 0.87, pnlImpact: '+$2,450', type: 'signal' },
  { id: 2, timestamp: '14:32:14', agent: 'RiskAgent', action: 'Position size approved', ticker: 'NVDA', confidence: 0.92, pnlImpact: 'Risk: $500 max', type: 'risk' },
  { id: 3, timestamp: '14:32:12', agent: 'MLAgent', action: 'Pattern detected: Bull Flag', ticker: 'NVDA', confidence: 0.84, pnlImpact: 'Hist. win rate: 72%', type: 'ml' },
  { id: 4, timestamp: '14:31:58', agent: 'DataAgent', action: 'Unusual volume spike', ticker: 'AAPL', confidence: 0.78, pnlImpact: 'Watching...', type: 'data' },
  { id: 5, timestamp: '14:31:45', agent: 'SentimentAgent', action: 'Bullish sentiment surge', ticker: 'TSLA', confidence: 0.81, pnlImpact: '+15% sentiment', type: 'sentiment' },
];

const MOCK_AGENTS = [
  { name: 'SignalAgent', status: 'running', signals: 47, profitToday: 2450, winRate: 0.68, lastAction: '2s ago' },
  { name: 'RiskAgent', status: 'running', signals: 23, profitToday: 0, winRate: 0.95, lastAction: '5s ago' },
  { name: 'MLAgent', status: 'running', signals: 156, profitToday: 1200, winRate: 0.72, lastAction: '12s ago' },
  { name: 'SentimentAgent', status: 'running', signals: 89, profitToday: 800, winRate: 0.64, lastAction: '8s ago' },
  { name: 'ExecutionAgent', status: 'paused', signals: 12, profitToday: 3100, winRate: 0.75, lastAction: '1m ago' },
];

export default function OperatorConsole() {
  const [logs, setLogs] = useState(MOCK_LOGS);
  const [agents, setAgents] = useState(MOCK_AGENTS);
  const [isPaused, setIsPaused] = useState(false);
  const [filter, setFilter] = useState('all');

  const totalProfitToday = agents.reduce((sum, a) => sum + a.profitToday, 0);
  const activeAgents = agents.filter(a => a.status === 'running').length;

  const getLogTypeColor = (type) => {
    switch(type) {
      case 'signal': return 'text-cyan-400 bg-cyan-500/10';
      case 'risk': return 'text-amber-400 bg-amber-500/10';
      case 'ml': return 'text-purple-400 bg-purple-500/10';
      case 'data': return 'text-blue-400 bg-blue-500/10';
      case 'sentiment': return 'text-emerald-400 bg-emerald-500/10';
      default: return 'text-gray-400 bg-gray-500/10';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header with P&L Summary */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <Terminal className="w-7 h-7 text-cyan-400" />
            Operator Console
          </h1>
          <p className="text-gray-400 text-sm mt-1">Glass House view - see everything, control everything</p>
        </div>
        <div className="flex items-center gap-4">
          <div className="bg-gray-800/50 rounded-lg px-4 py-2 border border-gray-700/50">
            <div className="text-xs text-gray-500">TODAY'S P&L</div>
            <div className={`text-xl font-bold ${totalProfitToday >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
              {totalProfitToday >= 0 ? '+' : ''}${totalProfitToday.toLocaleString()}
            </div>
          </div>
          <button
            onClick={() => setIsPaused(!isPaused)}
            className={`p-3 rounded-lg transition-all ${
              isPaused 
                ? 'bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30' 
                : 'bg-amber-500/20 text-amber-400 hover:bg-amber-500/30'
            }`}
          >
            {isPaused ? <Play className="w-5 h-5" /> : <Pause className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Agent Status Grid */}
      <div className="grid grid-cols-5 gap-4">
        {agents.map((agent) => (
          <div
            key={agent.name}
            className={`bg-gray-800/30 rounded-xl p-4 border ${
              agent.status === 'running' ? 'border-emerald-500/30' : 'border-amber-500/30'
            }`}
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm font-medium text-white">{agent.name}</span>
              <div className={`w-2 h-2 rounded-full ${
                agent.status === 'running' ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'
              }`} />
            </div>
            <div className="space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-gray-500">Signals</span>
                <span className="text-gray-300">{agent.signals}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Profit</span>
                <span className={agent.profitToday >= 0 ? 'text-emerald-400' : 'text-red-400'}>
                  +${agent.profitToday.toLocaleString()}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Win Rate</span>
                <span className="text-cyan-400">{(agent.winRate * 100).toFixed(0)}%</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Live Activity Feed */}
      <div className="bg-gray-800/30 rounded-xl border border-gray-700/50">
        <div className="p-4 border-b border-gray-700/50 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <Activity className="w-5 h-5 text-cyan-400" />
            Live Activity Feed
            <span className="text-xs bg-emerald-500/20 text-emerald-400 px-2 py-0.5 rounded-full ml-2">
              {isPaused ? 'PAUSED' : 'LIVE'}
            </span>
          </h2>
          <div className="flex items-center gap-2">
            {['all', 'signal', 'risk', 'ml', 'sentiment'].map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-3 py-1 text-xs rounded-lg transition-all ${
                  filter === f
                    ? 'bg-cyan-500/20 text-cyan-400'
                    : 'text-gray-500 hover:text-gray-300'
                }`}
              >
                {f.toUpperCase()}
              </button>
            ))}
          </div>
        </div>
        <div className="divide-y divide-gray-700/30 max-h-96 overflow-y-auto">
          {logs
            .filter(log => filter === 'all' || log.type === filter)
            .map((log) => (
            <div key={log.id} className="p-3 hover:bg-gray-800/30 transition-colors">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="text-xs text-gray-500 w-16">{log.timestamp}</span>
                  <span className={`text-xs px-2 py-0.5 rounded ${getLogTypeColor(log.type)}`}>
                    {log.agent}
                  </span>
                  <span className="text-sm text-gray-300">{log.action}</span>
                  <span className="text-sm font-medium text-white">{log.ticker}</span>
                </div>
                <div className="flex items-center gap-4">
                  <div className="text-xs text-gray-500">
                    Confidence: <span className="text-cyan-400">{(log.confidence * 100).toFixed(0)}%</span>
                  </div>
                  <div className={`text-xs font-medium ${
                    log.pnlImpact.includes('+') ? 'text-emerald-400' : 'text-gray-400'
                  }`}>
                    {log.pnlImpact}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-gray-800/30 rounded-xl p-4 border border-gray-700/50">
          <div className="flex items-center gap-2 text-gray-400 text-sm mb-2">
            <Eye className="w-4 h-4" />
            Active Agents
          </div>
          <div className="text-2xl font-bold text-white">{activeAgents}/{agents.length}</div>
        </div>
        <div className="bg-gray-800/30 rounded-xl p-4 border border-gray-700/50">
          <div className="flex items-center gap-2 text-gray-400 text-sm mb-2">
            <TrendingUp className="w-4 h-4" />
            Signals Today
          </div>
          <div className="text-2xl font-bold text-cyan-400">{agents.reduce((s, a) => s + a.signals, 0)}</div>
        </div>
        <div className="bg-gray-800/30 rounded-xl p-4 border border-gray-700/50">
          <div className="flex items-center gap-2 text-gray-400 text-sm mb-2">
            <CheckCircle className="w-4 h-4" />
            Avg Win Rate
          </div>
          <div className="text-2xl font-bold text-emerald-400">
            {(agents.reduce((s, a) => s + a.winRate, 0) / agents.length * 100).toFixed(0)}%
          </div>
        </div>
        <div className="bg-gray-800/30 rounded-xl p-4 border border-gray-700/50">
          <div className="flex items-center gap-2 text-gray-400 text-sm mb-2">
            <Clock className="w-4 h-4" />
            System Uptime
          </div>
          <div className="text-2xl font-bold text-white">99.9%</div>
        </div>
      </div>
    </div>
  );
}
