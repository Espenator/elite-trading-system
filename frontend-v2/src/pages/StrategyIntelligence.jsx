import React, { useState } from 'react';
import Card from '../components/ui/Card';
import Toggle from '../components/ui/Toggle';
import Button from '../components/ui/Button';
import Badge from '../components/ui/Badge';

const StrategyIntelligence = () => {
  const [masterSwitch, setMasterSwitch] = useState(true);
  const [pauseAll, setPauseAll] = useState(false);
  const [closeAllPositions, setCloseAllPositions] = useState(false);

  const strategies = [
    {
      id: 1,
      name: 'Momentum Scalper v2',
      status: 'Active',
      description: 'Aggressive short-term momentum strategy with tight stop-losses.',
      dailyPL: 1.25,
      winRate: 68,
      maxDrawdown: -3.1
    },
    {
      id: 2,
      name: 'Trend Follower FX',
      status: 'Paused',
      description: 'Medium-term trend following strategy across major FX pairs.',
      dailyPL: 0.10,
      winRate: 55,
      maxDrawdown: -5.8
    },
    {
      id: 3,
      name: 'Arbitrage Crypto',
      status: 'Error',
      description: 'Cross-exchange cryptocurrency arbitrage with automated execution.',
      dailyPL: -0.50,
      winRate: 72,
      maxDrawdown: -1.2
    },
    {
      id: 4,
      name: 'Mean Reversion',
      status: 'Active',
      description: 'Statistical arbitrage on mean-reverting equity pairs.',
      dailyPL: 0.85,
      winRate: 61,
      maxDrawdown: -2.4
    }
  ];

  const getStatusVariant = (status) => {
    switch (status) {
      case 'Active': return 'success';
      case 'Paused': return 'warning';
      case 'Error': return 'danger';
      default: return 'secondary';
    }
  };

  const getStatusBorder = (status) => {
    switch (status) {
      case 'Active': return 'border-success/50';
      case 'Paused': return 'border-warning/50';
      case 'Error': return 'border-danger/50';
      default: return 'border-secondary/50';
    }
  };

  return (
    <div className="min-h-screen bg-dark text-white p-6">
      <Card title="Emergency Controls" subtitle="Global settings to manage all active strategies and positions." className="mb-6">
        <div className="space-y-4">
          <Toggle label="Master Switch (ON/OFF)" checked={masterSwitch} onChange={() => setMasterSwitch(!masterSwitch)} />
          <Toggle label="Pause All Strategies" checked={pauseAll} onChange={() => setPauseAll(!pauseAll)} />
          <Toggle label="Close All Positions" description="Danger: closes all open positions" checked={closeAllPositions} onChange={() => setCloseAllPositions(!closeAllPositions)} />
        </div>
      </Card>

      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold">My Trading Strategies</h2>
        <Button variant="primary">+ Add New Strategy</Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {strategies.map((strategy) => (
          <Card key={strategy.id} className={`border-2 ${getStatusBorder(strategy.status)}`} noPadding>
            <div className="p-6">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="text-xl font-bold mb-1 text-white">{strategy.name}</h3>
                  <Badge variant={getStatusVariant(strategy.status)}>▶ {strategy.status}</Badge>
                </div>
              </div>

              <p className="text-sm text-secondary mb-4">{strategy.description}</p>

              <div className="grid grid-cols-3 gap-4 mb-4">
                <div>
                  <p className="text-xs text-secondary mb-1">Daily P&L</p>
                  <p className={`text-lg font-bold ${strategy.dailyPL >= 0 ? 'text-success' : 'text-danger'}`}>
                    {strategy.dailyPL >= 0 ? '+' : ''}{strategy.dailyPL}%
                  </p>
                </div>
                <div>
                  <p className="text-xs text-secondary mb-1">Win Rate</p>
                  <p className="text-lg font-bold text-white">{strategy.winRate}%</p>
                </div>
                <div>
                  <p className="text-xs text-secondary mb-1">Max Drawdown</p>
                  <p className="text-lg font-bold text-danger">{strategy.maxDrawdown}%</p>
                </div>
              </div>

              <div className="flex gap-3">
                <Button variant="secondary" className="flex-1">View Details</Button>
                <Button variant="secondary" className="flex-1">Edit</Button>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
};

export default StrategyIntelligence;
