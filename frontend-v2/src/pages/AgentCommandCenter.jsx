// AGENT COMMAND CENTER - Embodier.ai Glass House Intelligence System
// Agent management: status, controls, logs, task queues
import { useState } from 'react';
import { Eye, Brain, ShieldCheck, Youtube, Play, Pause, RefreshCw, Activity, CheckCircle, AlertCircle } from 'lucide-react';
import Card from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';

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

  const getStatusVariant = (status) => {
    switch (status) {
      case 'active': return 'success';
      case 'learning': return 'warning';
      case 'paused': return 'secondary';
      case 'error': return 'danger';
      default: return 'secondary';
    }
  };

  const getLevelColor = (level) => {
    switch (level) {
      case 'success': return 'text-success';
      case 'warning': return 'text-warning';
      case 'error': return 'text-danger';
      default: return 'text-primary';
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Agent Command Center</h1>
          <p className="text-sm text-secondary mt-1">Monitor and control your AI agents</p>
        </div>
        <Badge variant="success" size="lg" className="gap-2">
          <span className="w-2 h-2 rounded-full bg-current animate-pulse" />
          {AGENTS.filter(a => a.status === 'active').length}/{AGENTS.length} Active
        </Badge>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {AGENTS.map(agent => {
          const Icon = agent.icon;
          return (
            <Card
              key={agent.id}
              noPadding
              className={`p-5 transition-all cursor-pointer ${selectedAgent === agent.id ? 'border-primary/50 ring-1 ring-primary/20' : 'hover:border-primary/30'}`}
              onClick={() => setSelectedAgent(selectedAgent === agent.id ? null : agent.id)}
            >
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
                    <Icon className="w-5 h-5 text-primary" />
                  </div>
                  <div>
                    <div className="text-lg font-semibold text-white">{agent.name}</div>
                    <div className="text-xs text-secondary">{agent.description}</div>
                  </div>
                </div>
                <Badge variant={getStatusVariant(agent.status)}>{agent.status}</Badge>
              </div>
              <div className="grid grid-cols-3 gap-3 mb-4">
                <div className="text-center p-2 bg-secondary/10 rounded-xl">
                  <div className="text-lg font-bold text-white">{agent.tasksCompleted.toLocaleString()}</div>
                  <div className="text-xs text-secondary">Completed</div>
                </div>
                <div className="text-center p-2 bg-secondary/10 rounded-xl">
                  <div className="text-lg font-bold text-warning">{agent.tasksQueued}</div>
                  <div className="text-xs text-secondary">Queued</div>
                </div>
                <div className="text-center p-2 bg-secondary/10 rounded-xl">
                  <div className="text-sm font-bold text-white">{agent.uptime}</div>
                  <div className="text-xs text-secondary">Uptime</div>
                </div>
              </div>
              <div className="text-xs text-secondary mb-3">
                <span className="text-white">Last: </span>{agent.lastAction}
              </div>
              <div className="flex items-center gap-2 pt-3 border-t border-secondary/30">
                <Button variant="success" size="sm" leftIcon={Play}>Start</Button>
                <Button variant="warning" size="sm" leftIcon={Pause}>Pause</Button>
                <Button variant="secondary" size="sm" leftIcon={RefreshCw}>Restart</Button>
              </div>
            </Card>
          );
        })}
      </div>

      <Card title="Activity Log" bodyClassName="p-0">
        <div className="flex justify-end px-4 -mt-2 mb-2"><span className="text-xs text-secondary">Real-time</span></div>
        <div className="divide-y divide-secondary/30 max-h-80 overflow-y-auto">
          {LOGS.map((log, i) => (
            <div key={i} className="flex items-start gap-3 px-4 py-3 hover:bg-secondary/5 transition-colors">
              <span className="text-xs font-mono text-secondary shrink-0 mt-0.5">{log.time}</span>
              <span className={`shrink-0 mt-0.5 ${getLevelColor(log.level)}`}>
                {log.level === 'success' ? <CheckCircle className="w-3.5 h-3.5 inline" /> : log.level === 'warning' ? <AlertCircle className="w-3.5 h-3.5 inline" /> : <Activity className="w-3.5 h-3.5 inline" />}
              </span>
              <div className="flex-1 min-w-0">
                <span className="text-xs font-medium text-primary">[{log.agent}]</span>
                <span className="text-xs text-secondary ml-2">{log.message}</span>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
