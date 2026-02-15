// AGENT COMMAND CENTER - Glass House micro-control for every agent
// OLEH: Full operator visibility into agent internals, manual overrides
// Backend: GET /api/v1/agents, POST /api/v1/agents/:id/config
// WebSocket: 'agents' channel for real-time agent state
// Every agent parameter is exposed with inline sliders/toggles

import { useState, useEffect, useCallback } from 'react';
import { getApiUrl } from '../config/api';

// ============================================================
// CONFIGURABLE PANEL - Reusable scrollable/collapsible wrapper
// ============================================================
function ConfigPanel({ title, icon, collapsed, onToggle, maxHeight = '400px', children, badge, headerActions }) {
  return (
    <div className="bg-gray-900 border border-gray-700 rounded-lg overflow-hidden">
      <div
        className="flex items-center justify-between px-4 py-3 bg-gray-800 cursor-pointer hover:bg-gray-750 transition-colors"
        onClick={onToggle}
      >
        <div className="flex items-center gap-2">
          <span className="text-lg">{icon}</span>
          <h3 className="text-sm font-semibold text-white">{title}</h3>
          {badge && <span className="px-2 py-0.5 text-xs rounded-full bg-cyan-900 text-cyan-300">{badge}</span>}
        </div>
        <div className="flex items-center gap-2">
          {headerActions}
          <svg className={`w-4 h-4 text-gray-400 transition-transform ${collapsed ? '' : 'rotate-180'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </div>
      {!collapsed && (
        <div className="overflow-y-auto custom-scrollbar" style={{ maxHeight }}>
          {children}
        </div>
      )}
    </div>
  );
}

// ============================================================
// INLINE SLIDER - Micro-control for numeric parameters
// ============================================================
function InlineSlider({ label, value, onChange, min = 0, max = 100, step = 1, unit = '', helpText }) {
  return (
    <div className="flex items-center gap-3 py-1">
      <span className="text-xs text-gray-400 w-32 shrink-0">{label}</span>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => { e.stopPropagation(); onChange(parseFloat(e.target.value)); }}
        className="flex-1 h-1.5 accent-cyan-400 cursor-pointer"
      />
      <span className="text-xs text-cyan-300 w-16 text-right font-mono">{value}{unit}</span>
      {helpText && <span className="text-xs text-gray-500" title={helpText}>?</span>}
    </div>
  );
}

// ============================================================
// TOGGLE SWITCH - For boolean agent parameters
// ============================================================
function ToggleSwitch({ label, checked, onChange, helpText }) {
  return (
    <div className="flex items-center justify-between py-1">
      <div className="flex items-center gap-2">
        <span className="text-xs text-gray-400">{label}</span>
        {helpText && <span className="text-xs text-gray-500" title={helpText}>?</span>}
      </div>
      <button
        onClick={(e) => { e.stopPropagation(); onChange(!checked); }}
        className={`w-8 h-4 rounded-full transition-colors ${checked ? 'bg-cyan-500' : 'bg-gray-600'} relative`}
      >
        <span className={`absolute top-0.5 w-3 h-3 rounded-full bg-white transition-transform ${checked ? 'left-4' : 'left-0.5'}`} />
      </button>
    </div>
  );
}

// ============================================================
// AGENT DETAIL CARD - Expandable card for each agent
// Shows status, metrics, config, logs, manual overrides
// ============================================================
function AgentDetailCard({ agent, onConfigChange, onAction, expanded, onToggleExpand }) {
  const statusColors = {
    running: 'bg-emerald-500',
    paused: 'bg-yellow-500',
    stopped: 'bg-red-500',
    error: 'bg-red-600 animate-pulse',
    idle: 'bg-gray-500',
    learning: 'bg-purple-500 animate-pulse',
  };

  const statusColor = statusColors[agent.status] || 'bg-gray-500';

  return (
    <div className="bg-gray-900 border border-gray-700 rounded-lg overflow-hidden mb-3">
      {/* Agent Header - always visible */}
      <div
        className="flex items-center justify-between px-4 py-3 cursor-pointer hover:bg-gray-800 transition-colors"
        onClick={onToggleExpand}
      >
        <div className="flex items-center gap-3">
          <div className={`w-3 h-3 rounded-full ${statusColor}`} />
          <div>
            <h4 className="text-sm font-semibold text-white">{agent.name}</h4>
            <p className="text-xs text-gray-400">{agent.type} | PID: {agent.pid || 'N/A'}</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          {/* Quick stats */}
          <div className="text-right hidden sm:block">
            <p className="text-xs text-gray-400">CPU: <span className="text-cyan-300 font-mono">{agent.cpu || 0}%</span></p>
            <p className="text-xs text-gray-400">Mem: <span className="text-cyan-300 font-mono">{agent.memory || 0}MB</span></p>
          </div>
          <div className="text-right hidden sm:block">
            <p className="text-xs text-gray-400">Tasks: <span className="text-emerald-300 font-mono">{agent.tasksCompleted || 0}</span></p>
            <p className="text-xs text-gray-400">Errors: <span className="text-red-300 font-mono">{agent.errors || 0}</span></p>
          </div>
          {/* Quick action buttons */}
          <div className="flex gap-1">
            <button
              onClick={(e) => { e.stopPropagation(); onAction(agent.id, agent.status === 'running' ? 'pause' : 'resume'); }}
              className={`px-2 py-1 text-xs rounded ${agent.status === 'running' ? 'bg-yellow-600 hover:bg-yellow-500' : 'bg-emerald-600 hover:bg-emerald-500'} text-white transition-colors`}
            >
              {agent.status === 'running' ? 'Pause' : 'Resume'}
            </button>
            <button
              onClick={(e) => { e.stopPropagation(); onAction(agent.id, 'restart'); }}
              className="px-2 py-1 text-xs rounded bg-blue-600 hover:bg-blue-500 text-white transition-colors"
            >
              Restart
            </button>
            <button
              onClick={(e) => { e.stopPropagation(); onAction(agent.id, 'stop'); }}
              className="px-2 py-1 text-xs rounded bg-red-600 hover:bg-red-500 text-white transition-colors"
            >
              Stop
            </button>
          </div>
          <svg className={`w-4 h-4 text-gray-400 transition-transform ${expanded ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </div>

      {/* Expanded Detail View - Glass House internals */}
      {expanded && (
        <div className="border-t border-gray-700 p-4 space-y-4">
          {/* === SECTION 1: Live Metrics === */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="bg-gray-800 rounded p-2">
              <p className="text-xs text-gray-400">Uptime</p>
              <p className="text-sm text-white font-mono">{agent.uptime || '0h 0m'}</p>
            </div>
            <div className="bg-gray-800 rounded p-2">
              <p className="text-xs text-gray-400">Last Action</p>
              <p className="text-sm text-white font-mono">{agent.lastAction || 'None'}</p>
            </div>
            <div className="bg-gray-800 rounded p-2">
              <p className="text-xs text-gray-400">Queue Depth</p>
              <p className="text-sm text-white font-mono">{agent.queueDepth || 0}</p>
            </div>
            <div className="bg-gray-800 rounded p-2">
              <p className="text-xs text-gray-400">Avg Latency</p>
              <p className="text-sm text-white font-mono">{agent.avgLatency || 0}ms</p>
            </div>
            <div className="bg-gray-800 rounded p-2">
              <p className="text-xs text-gray-400">Success Rate</p>
              <p className="text-sm text-emerald-300 font-mono">{agent.successRate || 0}%</p>
            </div>
            <div className="bg-gray-800 rounded p-2">
              <p className="text-xs text-gray-400">API Calls/min</p>
              <p className="text-sm text-cyan-300 font-mono">{agent.apiCallsPerMin || 0}</p>
            </div>
            <div className="bg-gray-800 rounded p-2">
              <p className="text-xs text-gray-400">Data Processed</p>
              <p className="text-sm text-white font-mono">{agent.dataProcessed || '0 KB'}</p>
            </div>
            <div className="bg-gray-800 rounded p-2">
              <p className="text-xs text-gray-400">Last Error</p>
              <p className="text-sm text-red-300 font-mono truncate" title={agent.lastError}>{agent.lastError || 'None'}</p>
            </div>
          </div>

          {/* === SECTION 2: Granular Parameter Controls === */}
          <div className="bg-gray-800 rounded-lg p-3">
            <h5 className="text-xs font-semibold text-cyan-300 mb-2 uppercase tracking-wider">Agent Parameters</h5>
            <div className="space-y-1">
              <InlineSlider
                label="Poll Interval"
                value={agent.config?.pollInterval || 5}
                onChange={(v) => onConfigChange(agent.id, 'pollInterval', v)}
                min={1} max={60} step={1} unit="s"
                helpText="How often this agent polls for new data"
              />
              <InlineSlider
                label="Batch Size"
                value={agent.config?.batchSize || 10}
                onChange={(v) => onConfigChange(agent.id, 'batchSize', v)}
                min={1} max={100} step={1}
                helpText="Number of items to process per batch"
              />
              <InlineSlider
                label="Confidence Threshold"
                value={agent.config?.confidenceThreshold || 0.7}
                onChange={(v) => onConfigChange(agent.id, 'confidenceThreshold', v)}
                min={0} max={1} step={0.05}
                helpText="Minimum confidence for agent to act"
              />
              <InlineSlider
                label="Max Retries"
                value={agent.config?.maxRetries || 3}
                onChange={(v) => onConfigChange(agent.id, 'maxRetries', v)}
                min={0} max={10} step={1}
                helpText="Maximum retry attempts on failure"
              />
              <InlineSlider
                label="Timeout"
                value={agent.config?.timeout || 30}
                onChange={(v) => onConfigChange(agent.id, 'timeout', v)}
                min={5} max={120} step={5} unit="s"
                helpText="Maximum time to wait for response"
              />
              <InlineSlider
                label="Priority Level"
                value={agent.config?.priority || 5}
                onChange={(v) => onConfigChange(agent.id, 'priority', v)}
                min={1} max={10} step={1}
                helpText="Processing priority (1=low, 10=critical)"
              />
              <ToggleSwitch
                label="Auto-Recovery"
                checked={agent.config?.autoRecover !== false}
                onChange={(v) => onConfigChange(agent.id, 'autoRecover', v)}
                helpText="Automatically restart on crash"
              />
              <ToggleSwitch
                label="Verbose Logging"
                checked={agent.config?.verboseLog || false}
                onChange={(v) => onConfigChange(agent.id, 'verboseLog', v)}
                helpText="Enable detailed debug logging"
              />
              <ToggleSwitch
                label="Rate Limiting"
                checked={agent.config?.rateLimiting !== false}
                onChange={(v) => onConfigChange(agent.id, 'rateLimiting', v)}
                helpText="Respect API rate limits"
              />
            </div>
          </div>

          {/* === SECTION 3: Agent-Specific Config (varies by agent type) === */}
          {agent.type === 'data-ingestion' && (
            <div className="bg-gray-800 rounded-lg p-3">
              <h5 className="text-xs font-semibold text-emerald-300 mb-2 uppercase tracking-wider">Data Ingestion Config</h5>
              <div className="space-y-1">
                <InlineSlider label="Feed Refresh" value={agent.config?.feedRefresh || 10} onChange={(v) => onConfigChange(agent.id, 'feedRefresh', v)} min={1} max={300} step={5} unit="s" />
                <InlineSlider label="Max Sources" value={agent.config?.maxSources || 20} onChange={(v) => onConfigChange(agent.id, 'maxSources', v)} min={1} max={50} step={1} />
                <InlineSlider label="Dedup Window" value={agent.config?.dedupWindow || 60} onChange={(v) => onConfigChange(agent.id, 'dedupWindow', v)} min={10} max={600} step={10} unit="s" />
                <ToggleSwitch label="FRED API" checked={agent.config?.fredEnabled !== false} onChange={(v) => onConfigChange(agent.id, 'fredEnabled', v)} />
                <ToggleSwitch label="SEC Edgar" checked={agent.config?.secEdgarEnabled !== false} onChange={(v) => onConfigChange(agent.id, 'secEdgarEnabled', v)} />
                <ToggleSwitch label="News API" checked={agent.config?.newsApiEnabled !== false} onChange={(v) => onConfigChange(agent.id, 'newsApiEnabled', v)} />
                <ToggleSwitch label="Stockgeist" checked={agent.config?.stockgeistEnabled || false} onChange={(v) => onConfigChange(agent.id, 'stockgeistEnabled', v)} />
                <ToggleSwitch label="Discord Feed" checked={agent.config?.discordEnabled || false} onChange={(v) => onConfigChange(agent.id, 'discordEnabled', v)} />
                <ToggleSwitch label="X/Twitter Feed" checked={agent.config?.xEnabled || false} onChange={(v) => onConfigChange(agent.id, 'xEnabled', v)} />
                <ToggleSwitch label="YouTube Transcripts" checked={agent.config?.youtubeEnabled || false} onChange={(v) => onConfigChange(agent.id, 'youtubeEnabled', v)} />
              </div>
            </div>
          )}

          {agent.type === 'signal-generation' && (
            <div className="bg-gray-800 rounded-lg p-3">
              <h5 className="text-xs font-semibold text-blue-300 mb-2 uppercase tracking-wider">Signal Generation Config</h5>
              <div className="space-y-1">
                <InlineSlider label="Min Score" value={agent.config?.minScore || 60} onChange={(v) => onConfigChange(agent.id, 'minScore', v)} min={0} max={100} step={5} />
                <InlineSlider label="Lookback Period" value={agent.config?.lookback || 20} onChange={(v) => onConfigChange(agent.id, 'lookback', v)} min={5} max={200} step={5} unit=" bars" />
                <InlineSlider label="Signal Cooldown" value={agent.config?.cooldown || 300} onChange={(v) => onConfigChange(agent.id, 'cooldown', v)} min={30} max={3600} step={30} unit="s" />
                <InlineSlider label="Max Signals/Hour" value={agent.config?.maxSignals || 10} onChange={(v) => onConfigChange(agent.id, 'maxSignals', v)} min={1} max={50} step={1} />
                <ToggleSwitch label="Technical Analysis" checked={agent.config?.taEnabled !== false} onChange={(v) => onConfigChange(agent.id, 'taEnabled', v)} />
                <ToggleSwitch label="Sentiment Analysis" checked={agent.config?.sentimentEnabled !== false} onChange={(v) => onConfigChange(agent.id, 'sentimentEnabled', v)} />
                <ToggleSwitch label="Pattern Recognition" checked={agent.config?.patternEnabled !== false} onChange={(v) => onConfigChange(agent.id, 'patternEnabled', v)} />
                <ToggleSwitch label="Volume Profile" checked={agent.config?.volumeEnabled || false} onChange={(v) => onConfigChange(agent.id, 'volumeEnabled', v)} />
                <ToggleSwitch label="Options Flow" checked={agent.config?.optionsFlowEnabled || false} onChange={(v) => onConfigChange(agent.id, 'optionsFlowEnabled', v)} />
              </div>
            </div>
          )}

          {agent.type === 'ml-flywheel' && (
            <div className="bg-gray-800 rounded-lg p-3">
              <h5 className="text-xs font-semibold text-purple-300 mb-2 uppercase tracking-wider">ML Flywheel Config</h5>
              <div className="space-y-1">
                <InlineSlider label="Learning Rate" value={agent.config?.learningRate || 0.001} onChange={(v) => onConfigChange(agent.id, 'learningRate', v)} min={0.0001} max={0.1} step={0.0001} />
                <InlineSlider label="Training Batch" value={agent.config?.trainingBatch || 32} onChange={(v) => onConfigChange(agent.id, 'trainingBatch', v)} min={8} max={256} step={8} />
                <InlineSlider label="Epochs/Cycle" value={agent.config?.epochsPerCycle || 5} onChange={(v) => onConfigChange(agent.id, 'epochsPerCycle', v)} min={1} max={50} step={1} />
                <InlineSlider label="Validation Split" value={agent.config?.validationSplit || 0.2} onChange={(v) => onConfigChange(agent.id, 'validationSplit', v)} min={0.05} max={0.5} step={0.05} />
                <InlineSlider label="Min Improvement" value={agent.config?.minImprovement || 0.01} onChange={(v) => onConfigChange(agent.id, 'minImprovement', v)} min={0.001} max={0.1} step={0.001} />
                <ToggleSwitch label="Auto-Retrain" checked={agent.config?.autoRetrain !== false} onChange={(v) => onConfigChange(agent.id, 'autoRetrain', v)} />
                <ToggleSwitch label="Feature Selection" checked={agent.config?.featureSelection || false} onChange={(v) => onConfigChange(agent.id, 'featureSelection', v)} />
                <ToggleSwitch label="Sunday Backtest" checked={agent.config?.sundayBacktest || false} onChange={(v) => onConfigChange(agent.id, 'sundayBacktest', v)} />
                <ToggleSwitch label="YouTube Learning" checked={agent.config?.ytLearning || false} onChange={(v) => onConfigChange(agent.id, 'ytLearning', v)} />
              </div>
            </div>
          )}

          {agent.type === 'risk-management' && (
            <div className="bg-gray-800 rounded-lg p-3">
              <h5 className="text-xs font-semibold text-red-300 mb-2 uppercase tracking-wider">Risk Management Config</h5>
              <div className="space-y-1">
                <InlineSlider label="Max Position %" value={agent.config?.maxPosition || 5} onChange={(v) => onConfigChange(agent.id, 'maxPosition', v)} min={0.5} max={25} step={0.5} unit="%" />
                <InlineSlider label="Max Daily Loss" value={agent.config?.maxDailyLoss || 2} onChange={(v) => onConfigChange(agent.id, 'maxDailyLoss', v)} min={0.5} max={10} step={0.5} unit="%" />
                <InlineSlider label="Stop Loss Default" value={agent.config?.defaultStopLoss || 2} onChange={(v) => onConfigChange(agent.id, 'defaultStopLoss', v)} min={0.5} max={10} step={0.25} unit="%" />
                <InlineSlider label="Take Profit Default" value={agent.config?.defaultTakeProfit || 4} onChange={(v) => onConfigChange(agent.id, 'defaultTakeProfit', v)} min={1} max={20} step={0.5} unit="%" />
                <InlineSlider label="Max Correlation" value={agent.config?.maxCorrelation || 0.7} onChange={(v) => onConfigChange(agent.id, 'maxCorrelation', v)} min={0} max={1} step={0.05} />
                <InlineSlider label="Max Open Trades" value={agent.config?.maxOpenTrades || 5} onChange={(v) => onConfigChange(agent.id, 'maxOpenTrades', v)} min={1} max={20} step={1} />
                <ToggleSwitch label="Auto Kill Switch" checked={agent.config?.autoKillSwitch !== false} onChange={(v) => onConfigChange(agent.id, 'autoKillSwitch', v)} />
                <ToggleSwitch label="Trailing Stops" checked={agent.config?.trailingStops || false} onChange={(v) => onConfigChange(agent.id, 'trailingStops', v)} />
              </div>
            </div>
          )}

          {/* === SECTION 4: Live Activity Log === */}
          <div className="bg-gray-800 rounded-lg p-3">
            <h5 className="text-xs font-semibold text-yellow-300 mb-2 uppercase tracking-wider">Activity Log (Last 20)</h5>
            <div className="max-h-40 overflow-y-auto custom-scrollbar space-y-1">
              {(agent.recentLogs || []).slice(0, 20).map((log, i) => (
                <div key={i} className="flex items-start gap-2 py-0.5">
                  <span className="text-xs text-gray-500 font-mono shrink-0">{log.time}</span>
                  <span className={`text-xs shrink-0 px-1 rounded ${log.level === 'error' ? 'text-red-400 bg-red-900/30' : log.level === 'warn' ? 'text-yellow-400 bg-yellow-900/30' : 'text-gray-400'}`}>{log.level}</span>
                  <span className="text-xs text-gray-300 flex-1">{log.msg}</span>
                </div>
              ))}
              {(!agent.recentLogs || agent.recentLogs.length === 0) && (
                <p className="text-xs text-gray-500 italic">No recent activity</p>
              )}
            </div>
          </div>

          {/* === SECTION 5: Manual Command Input === */}
          <div className="bg-gray-800 rounded-lg p-3">
            <h5 className="text-xs font-semibold text-cyan-300 mb-2 uppercase tracking-wider">Manual Command</h5>
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="Send command to agent..."
                className="flex-1 bg-gray-900 border border-gray-600 rounded px-3 py-1.5 text-sm text-white focus:outline-none focus:border-cyan-500"
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && e.target.value) {
                    onAction(agent.id, 'command', e.target.value);
                    e.target.value = '';
                  }
                }}
              />
              <button className="px-3 py-1.5 text-xs bg-cyan-600 hover:bg-cyan-500 text-white rounded transition-colors">Send</button>
            </div>
            <div className="flex gap-2 mt-2 flex-wrap">
              <button onClick={() => onAction(agent.id, 'command', 'status')} className="px-2 py-0.5 text-xs bg-gray-700 hover:bg-gray-600 text-gray-300 rounded">status</button>
              <button onClick={() => onAction(agent.id, 'command', 'flush')} className="px-2 py-0.5 text-xs bg-gray-700 hover:bg-gray-600 text-gray-300 rounded">flush</button>
              <button onClick={() => onAction(agent.id, 'command', 'reset-stats')} className="px-2 py-0.5 text-xs bg-gray-700 hover:bg-gray-600 text-gray-300 rounded">reset-stats</button>
              <button onClick={() => onAction(agent.id, 'command', 'dump-config')} className="px-2 py-0.5 text-xs bg-gray-700 hover:bg-gray-600 text-gray-300 rounded">dump-config</button>
              <button onClick={() => onAction(agent.id, 'command', 'force-run')} className="px-2 py-0.5 text-xs bg-gray-700 hover:bg-gray-600 text-gray-300 rounded">force-run</button>
            </div>
          </div>

        </div>
      )}
    </div>
  );
}

// ============================================================
// MAIN EXPORT: Agent Command Center
// ============================================================
export default function AgentCommandCenter() {
  const [agents, setAgents] = useState([]);
  const [expandedAgents, setExpandedAgents] = useState({});
  const [panels, setPanels] = useState({
    overview: true,
    agents: true,
    orchestrator: true,
    systemResources: false,
    agentComms: false,
  });
  const [filterStatus, setFilterStatus] = useState('ALL');
  const [filterType, setFilterType] = useState('ALL');
  const [refreshRate, setRefreshRate] = useState(3);
  const [systemStats, setSystemStats] = useState({});
  const [orchestratorLog, setOrchestratorLog] = useState([]);

  const togglePanel = useCallback((key) => {
    setPanels(prev => ({ ...prev, [key]: !prev[key] }));
  }, []);

  // Fetch agents from backend
  useEffect(() => {
    const fetchAgents = async () => {
      try {
        const res = await fetch(`${getApiUrl()}/api/v1/agents`);
        if (res.ok) {
          const data = await res.json();
          setAgents(data.agents || []);
          setSystemStats(data.system || {});
          setOrchestratorLog(data.orchestratorLog || []);
        }
      } catch (err) {
        console.error('Failed to fetch agents:', err);
      }
    };
    fetchAgents();
    const interval = setInterval(fetchAgents, refreshRate * 1000);
    return () => clearInterval(interval);
  }, [refreshRate]);

  // Mock agents for dev - OLEH: Replace with real WebSocket data
  useEffect(() => {
    if (agents.length === 0) {
      setAgents([
        { id: 'agent-data-1', name: 'Data Ingestion Master', type: 'data-ingestion', status: 'running', pid: 12847, cpu: 12, memory: 256, tasksCompleted: 1847, errors: 3, uptime: '14h 32m', lastAction: 'Fetched FRED data', queueDepth: 5, avgLatency: 45, successRate: 99.2, apiCallsPerMin: 24, dataProcessed: '2.4 GB', lastError: null, config: { pollInterval: 10, batchSize: 25, confidenceThreshold: 0.7, maxRetries: 3, timeout: 30, priority: 8, autoRecover: true, verboseLog: false, rateLimiting: true, feedRefresh: 15, maxSources: 30, dedupWindow: 120, fredEnabled: true, secEdgarEnabled: true, newsApiEnabled: true, stockgeistEnabled: true, discordEnabled: false, xEnabled: true, youtubeEnabled: true }, recentLogs: [{ time: '14:32:01', level: 'info', msg: 'FRED API: 15 new indicators fetched' }, { time: '14:31:45', level: 'info', msg: 'SEC Edgar: AAPL 10-K filing processed' }, { time: '14:31:12', level: 'warn', msg: 'NewsAPI rate limit approaching (85%)' }] },
        { id: 'agent-signal-1', name: 'Signal Generator Alpha', type: 'signal-generation', status: 'running', pid: 12848, cpu: 28, memory: 512, tasksCompleted: 342, errors: 1, uptime: '14h 32m', lastAction: 'Generated NVDA buy signal', queueDepth: 2, avgLatency: 120, successRate: 94.7, apiCallsPerMin: 8, dataProcessed: '890 MB', lastError: null, config: { pollInterval: 5, batchSize: 10, confidenceThreshold: 0.75, maxRetries: 2, timeout: 60, priority: 9, autoRecover: true, minScore: 65, lookback: 30, cooldown: 300, maxSignals: 15, taEnabled: true, sentimentEnabled: true, patternEnabled: true, volumeEnabled: true, optionsFlowEnabled: true }, recentLogs: [{ time: '14:32:05', level: 'info', msg: 'BUY signal: NVDA score=82 confidence=0.89' }, { time: '14:31:30', level: 'info', msg: 'Scanning 150 symbols for patterns' }] },
        { id: 'agent-risk-1', name: 'Risk Guardian', type: 'risk-management', status: 'running', pid: 12849, cpu: 8, memory: 128, tasksCompleted: 2100, errors: 0, uptime: '14h 32m', lastAction: 'Portfolio risk check OK', queueDepth: 0, avgLatency: 15, successRate: 100, apiCallsPerMin: 40, dataProcessed: '450 MB', lastError: null, config: { pollInterval: 2, batchSize: 5, confidenceThreshold: 0.9, maxRetries: 5, timeout: 10, priority: 10, autoRecover: true, maxPosition: 5, maxDailyLoss: 2, defaultStopLoss: 2, defaultTakeProfit: 4, maxCorrelation: 0.7, maxOpenTrades: 5, autoKillSwitch: true, trailingStops: true }, recentLogs: [{ time: '14:32:08', level: 'info', msg: 'Portfolio exposure: 23% (within limits)' }, { time: '14:32:00', level: 'info', msg: 'Correlation check passed for all positions' }] },
        { id: 'agent-ml-1', name: 'ML Flywheel Engine', type: 'ml-flywheel', status: 'learning', pid: 12850, cpu: 65, memory: 1024, tasksCompleted: 45, errors: 2, uptime: '14h 32m', lastAction: 'Training epoch 3/5', queueDepth: 12, avgLatency: 2500, successRate: 91.1, apiCallsPerMin: 2, dataProcessed: '5.2 GB', lastError: 'Gradient overflow in layer 4', config: { pollInterval: 30, batchSize: 32, confidenceThreshold: 0.8, maxRetries: 3, timeout: 120, priority: 7, autoRecover: true, learningRate: 0.001, trainingBatch: 64, epochsPerCycle: 5, validationSplit: 0.2, minImprovement: 0.01, autoRetrain: true, featureSelection: true, sundayBacktest: true, ytLearning: true }, recentLogs: [{ time: '14:32:10', level: 'info', msg: 'Epoch 3/5: loss=0.0234 val_loss=0.0289' }, { time: '14:30:00', level: 'warn', msg: 'Gradient overflow in layer 4, clipping applied' }] },
        { id: 'agent-youtube-1', name: 'YouTube Transcript Digester', type: 'data-ingestion', status: 'paused', pid: 12851, cpu: 0, memory: 64, tasksCompleted: 28, errors: 0, uptime: '8h 12m', lastAction: 'Processed 3 videos', queueDepth: 0, avgLatency: 5000, successRate: 100, apiCallsPerMin: 0, dataProcessed: '120 MB', lastError: null, config: { pollInterval: 300, batchSize: 3, confidenceThreshold: 0.5, maxRetries: 2, timeout: 60, priority: 3, youtubeEnabled: true }, recentLogs: [{ time: '12:00:00', level: 'info', msg: 'Paused by operator - scheduled for next scan' }] },
        { id: 'agent-exec-1', name: 'Trade Executor', type: 'execution', status: 'running', pid: 12852, cpu: 4, memory: 96, tasksCompleted: 67, errors: 0, uptime: '14h 32m', lastAction: 'Executed AAPL limit buy', queueDepth: 1, avgLatency: 25, successRate: 100, apiCallsPerMin: 1, dataProcessed: '15 MB', lastError: null, config: { pollInterval: 1, batchSize: 1, confidenceThreshold: 0.95, maxRetries: 0, timeout: 5, priority: 10, autoRecover: false }, recentLogs: [{ time: '14:31:50', level: 'info', msg: 'AAPL limit buy @$185.50 x 50 shares - FILLED' }] },
      ]);
    }
  }, []);

  // Handler: Update agent config parameter
  const handleConfigChange = useCallback(async (agentId, key, value) => {
    setAgents(prev => prev.map(a =>
      a.id === agentId ? { ...a, config: { ...a.config, [key]: value } } : a
    ));
    try {
      await fetch(`${getApiUrl()}/api/v1/agents/${agentId}/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ [key]: value }),
      });
    } catch (err) { console.error('Config update failed:', err); }
  }, []);

  // Handler: Agent actions (pause/resume/stop/restart/command)
  const handleAgentAction = useCallback(async (agentId, action, payload) => {
    try {
      await fetch(`${getApiUrl()}/api/v1/agents/${agentId}/action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, payload }),
      });
    } catch (err) { console.error('Agent action failed:', err); }
  }, []);

  // Handler: Global actions
  const handleGlobalAction = useCallback(async (action) => {
    try {
      await fetch(`${getApiUrl()}/api/v1/agents/global`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action }),
      });
    } catch (err) { console.error('Global action failed:', err); }
  }, []);

  // Filter agents
  const filteredAgents = agents
    .filter(a => filterStatus === 'ALL' || a.status === filterStatus)
    .filter(a => filterType === 'ALL' || a.type === filterType);

  // Derived stats
  const runningCount = agents.filter(a => a.status === 'running').length;
  const errorCount = agents.filter(a => a.status === 'error').length;
  const totalCpu = agents.reduce((sum, a) => sum + (a.cpu || 0), 0);
  const totalMem = agents.reduce((sum, a) => sum + (a.memory || 0), 0);
  const totalTasks = agents.reduce((sum, a) => sum + (a.tasksCompleted || 0), 0);
  const totalErrors = agents.reduce((sum, a) => sum + (a.errors || 0), 0);

  return (
    <div className="space-y-4">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Agent Command Center</h1>
          <p className="text-gray-400 text-sm">Glass House micro-control over every AI agent</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-400">Refresh:</span>
            <input type="range" min={1} max={30} value={refreshRate} onChange={(e) => setRefreshRate(parseInt(e.target.value))} className="w-20 h-1.5 accent-cyan-400" />
            <span className="text-xs text-cyan-300 font-mono">{refreshRate}s</span>
          </div>
          <button onClick={() => handleGlobalAction('pause-all')} className="px-3 py-1.5 text-xs bg-yellow-600 hover:bg-yellow-500 text-white rounded transition-colors">Pause All</button>
          <button onClick={() => handleGlobalAction('resume-all')} className="px-3 py-1.5 text-xs bg-emerald-600 hover:bg-emerald-500 text-white rounded transition-colors">Resume All</button>
          <button onClick={() => handleGlobalAction('emergency-stop')} className="px-3 py-1.5 text-xs bg-red-600 hover:bg-red-500 text-white rounded transition-colors font-bold">EMERGENCY STOP</button>
        </div>
      </div>

      {/* ===== PANEL 1: Fleet Overview Dashboard ===== */}
      <ConfigPanel
        title="Fleet Overview"
        icon="\u{1F6F8}"
        collapsed={!panels.overview}
        onToggle={() => togglePanel('overview')}
        badge={`${runningCount}/${agents.length} active`}
        maxHeight="300px"
      >
        <div className="p-4">
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
            <div className="bg-gradient-to-br from-gray-800/80 to-gray-900/80 backdrop-blur border border-cyan-500/20 rounded-xl p-3 shadow-lg shadow-cyan-500/5">
              <p className="text-xs text-cyan-400/70 uppercase tracking-wider">Active Agents</p>
              <p className="text-2xl font-bold text-cyan-300 font-mono mt-1">{runningCount}<span className="text-sm text-gray-500">/{agents.length}</span></p>
            </div>
            <div className="bg-gradient-to-br from-gray-800/80 to-gray-900/80 backdrop-blur border border-emerald-500/20 rounded-xl p-3 shadow-lg shadow-emerald-500/5">
              <p className="text-xs text-emerald-400/70 uppercase tracking-wider">Tasks Done</p>
              <p className="text-2xl font-bold text-emerald-300 font-mono mt-1">{totalTasks.toLocaleString()}</p>
            </div>
            <div className="bg-gradient-to-br from-gray-800/80 to-gray-900/80 backdrop-blur border border-red-500/20 rounded-xl p-3 shadow-lg shadow-red-500/5">
              <p className="text-xs text-red-400/70 uppercase tracking-wider">Errors</p>
              <p className="text-2xl font-bold text-red-300 font-mono mt-1">{totalErrors}</p>
            </div>
            <div className="bg-gradient-to-br from-gray-800/80 to-gray-900/80 backdrop-blur border border-purple-500/20 rounded-xl p-3 shadow-lg shadow-purple-500/5">
              <p className="text-xs text-purple-400/70 uppercase tracking-wider">CPU Total</p>
              <p className="text-2xl font-bold text-purple-300 font-mono mt-1">{totalCpu}%</p>
            </div>
            <div className="bg-gradient-to-br from-gray-800/80 to-gray-900/80 backdrop-blur border border-blue-500/20 rounded-xl p-3 shadow-lg shadow-blue-500/5">
              <p className="text-xs text-blue-400/70 uppercase tracking-wider">Memory</p>
              <p className="text-2xl font-bold text-blue-300 font-mono mt-1">{totalMem}MB</p>
            </div>
            <div className="bg-gradient-to-br from-gray-800/80 to-gray-900/80 backdrop-blur border border-yellow-500/20 rounded-xl p-3 shadow-lg shadow-yellow-500/5">
              <p className="text-xs text-yellow-400/70 uppercase tracking-wider">Error Agents</p>
              <p className="text-2xl font-bold text-yellow-300 font-mono mt-1">{errorCount}</p>
            </div>
          </div>
        </div>
      </ConfigPanel>

      {/* ===== PANEL 2: Agent Fleet - Filters + All Agent Cards ===== */}
      <ConfigPanel
        title="Agent Fleet"
        icon="\u{1F916}"
        collapsed={!panels.agents}
        onToggle={() => togglePanel('agents')}
        badge={`${filteredAgents.length} shown`}
        maxHeight="800px"
        headerActions={
          <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
            <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)} className="bg-gray-700 border border-gray-600 text-xs text-gray-200 rounded px-2 py-1">
              <option value="ALL">All Status</option>
              <option value="running">Running</option>
              <option value="paused">Paused</option>
              <option value="stopped">Stopped</option>
              <option value="error">Error</option>
              <option value="learning">Learning</option>
            </select>
            <select value={filterType} onChange={(e) => setFilterType(e.target.value)} className="bg-gray-700 border border-gray-600 text-xs text-gray-200 rounded px-2 py-1">
              <option value="ALL">All Types</option>
              <option value="data-ingestion">Data Ingestion</option>
              <option value="signal-generation">Signal Gen</option>
              <option value="risk-management">Risk Mgmt</option>
              <option value="ml-flywheel">ML Flywheel</option>
              <option value="execution">Execution</option>
            </select>
          </div>
        }
      >
        <div className="p-3 space-y-2">
          {filteredAgents.map(agent => (
            <AgentDetailCard
              key={agent.id}
              agent={agent}
              expanded={!!expandedAgents[agent.id]}
              onToggleExpand={() => setExpandedAgents(prev => ({ ...prev, [agent.id]: !prev[agent.id] }))}
              onConfigChange={handleConfigChange}
              onAction={handleAgentAction}
            />
          ))}
          {filteredAgents.length === 0 && (
            <p className="text-sm text-gray-500 italic text-center py-8">No agents match filters</p>
          )}
        </div>
      </ConfigPanel>

      {/* ===== PANEL 3: Orchestrator Intelligence Log ===== */}
      <ConfigPanel
        title="Orchestrator Intelligence"
        icon="\u{1F9E0}"
        collapsed={!panels.orchestrator}
        onToggle={() => togglePanel('orchestrator')}
        badge={`${orchestratorLog.length} events`}
        maxHeight="400px"
      >
        <div className="p-3">
          <p className="text-xs text-gray-400 mb-2">Real-time decisions made by the orchestrator agent - the brain coordinating all other agents</p>
          <div className="space-y-1">
            {(orchestratorLog.length > 0 ? orchestratorLog : [
              { time: '14:32:10', type: 'decision', msg: 'Increased Signal Generator priority after detecting high-vol market conditions' },
              { time: '14:31:55', type: 'coordination', msg: 'Routed FRED macro data to both Signal Gen and Risk Guardian agents' },
              { time: '14:31:40', type: 'learning', msg: 'ML Flywheel training cycle 3/5 - val_loss improving, continuing training' },
              { time: '14:31:20', type: 'alert', msg: 'NewsAPI rate limit at 85% - throttled Data Ingestion agent to 1 req/5s' },
              { time: '14:31:00', type: 'decision', msg: 'YouTube Transcript agent paused - no new financial videos in watch queue' },
              { time: '14:30:45', type: 'signal', msg: 'NVDA buy signal from Signal Gen approved by Risk Guardian - forwarded to Executor' },
              { time: '14:30:30', type: 'coordination', msg: 'Correlation matrix updated - all open positions within 0.7 threshold' },
              { time: '14:30:15', type: 'system', msg: 'System health check: all 6 agents responsive, avg latency 45ms' },
            ]).map((log, i) => {
              const typeColors = { decision: 'text-cyan-400 bg-cyan-900/30', coordination: 'text-blue-400 bg-blue-900/30', learning: 'text-purple-400 bg-purple-900/30', alert: 'text-yellow-400 bg-yellow-900/30', signal: 'text-emerald-400 bg-emerald-900/30', system: 'text-gray-400 bg-gray-700/30' };
              return (
                <div key={i} className="flex items-start gap-2 py-1 border-b border-gray-800/50">
                  <span className="text-xs text-gray-500 font-mono shrink-0 w-16">{log.time}</span>
                  <span className={`text-xs shrink-0 px-1.5 py-0.5 rounded ${typeColors[log.type] || 'text-gray-400'}`}>{log.type}</span>
                  <span className="text-xs text-gray-300 flex-1">{log.msg}</span>
                </div>
              );
            })}
          </div>
        </div>
      </ConfigPanel>

      {/* ===== PANEL 4: System Resources ===== */}
      <ConfigPanel
        title="System Resources"
        icon="\u{1F5A5}"
        collapsed={!panels.systemResources}
        onToggle={() => togglePanel('systemResources')}
        maxHeight="300px"
      >
        <div className="p-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="space-y-2">
              <p className="text-xs text-gray-400 uppercase">CPU Usage</p>
              <div className="w-full bg-gray-700 rounded-full h-3">
                <div className="bg-gradient-to-r from-cyan-500 to-blue-500 h-3 rounded-full transition-all shadow-lg shadow-cyan-500/20" style={{ width: `${Math.min(totalCpu, 100)}%` }} />
              </div>
              <p className="text-xs text-cyan-300 font-mono">{totalCpu}% / 100%</p>
            </div>
            <div className="space-y-2">
              <p className="text-xs text-gray-400 uppercase">Memory</p>
              <div className="w-full bg-gray-700 rounded-full h-3">
                <div className="bg-gradient-to-r from-purple-500 to-pink-500 h-3 rounded-full transition-all shadow-lg shadow-purple-500/20" style={{ width: `${Math.min((totalMem / 4096) * 100, 100)}%` }} />
              </div>
              <p className="text-xs text-purple-300 font-mono">{totalMem}MB / 4096MB</p>
            </div>
            <div className="space-y-2">
              <p className="text-xs text-gray-400 uppercase">Network I/O</p>
              <div className="w-full bg-gray-700 rounded-full h-3">
                <div className="bg-gradient-to-r from-emerald-500 to-teal-500 h-3 rounded-full transition-all shadow-lg shadow-emerald-500/20" style={{ width: '35%' }} />
              </div>
              <p className="text-xs text-emerald-300 font-mono">142 Mbps / 400 Mbps</p>
            </div>
            <div className="space-y-2">
              <p className="text-xs text-gray-400 uppercase">Disk I/O</p>
              <div className="w-full bg-gray-700 rounded-full h-3">
                <div className="bg-gradient-to-r from-yellow-500 to-orange-500 h-3 rounded-full transition-all shadow-lg shadow-yellow-500/20" style={{ width: '18%' }} />
              </div>
              <p className="text-xs text-yellow-300 font-mono">18% utilization</p>
            </div>
          </div>
          <div className="mt-4 grid grid-cols-3 gap-3">
            <div className="bg-gray-800/50 rounded-lg p-2 border border-gray-700/50">
              <p className="text-xs text-gray-400">API Rate Limits</p>
              <p className="text-sm text-cyan-300 font-mono">Alpaca: 45/200 | News: 85/100</p>
            </div>
            <div className="bg-gray-800/50 rounded-lg p-2 border border-gray-700/50">
              <p className="text-xs text-gray-400">WebSocket Connections</p>
              <p className="text-sm text-emerald-300 font-mono">5/5 active channels</p>
            </div>
            <div className="bg-gray-800/50 rounded-lg p-2 border border-gray-700/50">
              <p className="text-xs text-gray-400">DB Queue</p>
              <p className="text-sm text-purple-300 font-mono">12 pending writes</p>
            </div>
          </div>
        </div>
      </ConfigPanel>

      {/* ===== PANEL 5: Inter-Agent Communication Log ===== */}
      <ConfigPanel
        title="Agent Communications"
        icon="\u{1F4E1}"
        collapsed={!panels.agentComms}
        onToggle={() => togglePanel('agentComms')}
        badge="live"
        maxHeight="350px"
      >
        <div className="p-3">
          <p className="text-xs text-gray-400 mb-2">Messages passing between agents in real-time</p>
          <div className="space-y-1">
            {[
              { from: 'Data Ingestion', to: 'Signal Generator', msg: 'New batch: 45 price updates, 12 news items, 3 SEC filings', time: '14:32:08' },
              { from: 'Signal Generator', to: 'Risk Guardian', msg: 'Signal proposal: NVDA BUY score=82 conf=0.89 - requesting approval', time: '14:32:05' },
              { from: 'Risk Guardian', to: 'Signal Generator', msg: 'APPROVED: NVDA BUY within risk params (position 3.2%, correlation 0.45)', time: '14:32:06' },
              { from: 'Risk Guardian', to: 'Trade Executor', msg: 'Execute: NVDA BUY 50 shares limit $875.00 SL=$857.50 TP=$910.00', time: '14:32:06' },
              { from: 'Trade Executor', to: 'Risk Guardian', msg: 'FILLED: NVDA 50 shares @$874.80 - order ID #4821', time: '14:32:07' },
              { from: 'ML Flywheel', to: 'Orchestrator', msg: 'Training progress: epoch 3/5 complete, val_loss=0.0289 (improving)', time: '14:31:40' },
              { from: 'Orchestrator', to: 'All Agents', msg: 'Market regime update: HIGH_VOLATILITY - adjust parameters accordingly', time: '14:31:35' },
              { from: 'Data Ingestion', to: 'ML Flywheel', msg: 'New training data available: 1,247 labeled samples from last 24h', time: '14:31:30' },
            ].map((comm, i) => (
              <div key={i} className="flex items-start gap-2 py-1.5 border-b border-gray-800/30">
                <span className="text-xs text-gray-500 font-mono shrink-0 w-16">{comm.time}</span>
                <span className="text-xs text-cyan-400 shrink-0">{comm.from}</span>
                <span className="text-xs text-gray-500">-&gt;</span>
                <span className="text-xs text-emerald-400 shrink-0">{comm.to}</span>
                <span className="text-xs text-gray-300 flex-1">{comm.msg}</span>
              </div>
            ))}
          </div>
        </div>
      </ConfigPanel>

    </div>
  );
}
