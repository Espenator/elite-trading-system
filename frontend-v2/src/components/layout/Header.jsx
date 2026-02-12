import { 
  Activity, 
  Wifi, 
  WifiOff, 
  Clock, 
  Cpu,
  Bell
} from 'lucide-react';
import { mockSystemStatus, mockRegime } from '../../data/mockData';
import { format } from 'date-fns';

export default function Header() {
  const status = mockSystemStatus;
  const regime = mockRegime;
  
  const regimeColors = {
    GREEN: 'bg-regime-green',
    YELLOW: 'bg-regime-yellow',
    RED: 'bg-regime-red',
    RED_RECOVERY: 'bg-orange-500'
  };

  return (
    <header className="h-16 bg-dark-card border-b border-dark-border px-6 flex items-center justify-between">
      {/* Left: System status */}
      <div className="flex items-center gap-6">
        {/* Connection status */}
        <div className="flex items-center gap-2">
          {status.isConnected ? (
            <>
              <Wifi className="w-4 h-4 text-bullish" />
              <span className="text-sm text-bullish">Connected</span>
            </>
          ) : (
            <>
              <WifiOff className="w-4 h-4 text-bearish" />
              <span className="text-sm text-bearish">Disconnected</span>
            </>
          )}
        </div>

        {/* Market regime indicator */}
        <div className="flex items-center gap-2">
          <div className={`w-3 h-3 rounded-full ${regimeColors[regime.regime]} animate-pulse`} />
          <span className="text-sm font-medium">{regime.regime}</span>
          <span className="text-xs text-gray-400">VIX: {regime.vixLevel.toFixed(2)}</span>
        </div>

        {/* Active signals */}
        <div className="flex items-center gap-2 text-gray-400">
          <Activity className="w-4 h-4" />
          <span className="text-sm">{status.signalsGenerated} signals</span>
        </div>
      </div>

      {/* Center: Time info */}
      <div className="flex items-center gap-6">
        <div className="text-center">
          <div className="text-xs text-gray-400">Market Time</div>
          <div className="text-sm font-mono font-medium">
            {format(new Date(), 'HH:mm:ss')} EST
          </div>
        </div>
        <div className="text-center">
          <div className="text-xs text-gray-400">Next Inference</div>
          <div className="text-sm font-mono text-bullish">
            {format(status.nextInferenceCycle, 'HH:mm')}
          </div>
        </div>
      </div>

      {/* Right: Model & notifications */}
      <div className="flex items-center gap-6">
        {/* Model accuracy */}
        <div className="flex items-center gap-2">
          <Cpu className="w-4 h-4 text-gray-400" />
          <span className="text-sm">Model: {status.modelAccuracy}%</span>
        </div>

        {/* Last update */}
        <div className="flex items-center gap-2 text-gray-400">
          <Clock className="w-4 h-4" />
          <span className="text-sm">
            {format(status.lastUpdate, 'HH:mm:ss')}
          </span>
        </div>

        {/* Notifications */}
        <button className="relative p-2 hover:bg-dark-hover rounded-lg transition-colors">
          <Bell className="w-5 h-5 text-gray-400" />
          <span className="absolute top-1 right-1 w-2 h-2 bg-bullish rounded-full" />
        </button>
      </div>
    </header>
  );
}
