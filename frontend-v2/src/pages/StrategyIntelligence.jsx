import React, { useState } from 'react';

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

  const getStatusColor = (status) => {
    switch(status) {
      case 'Active': return 'text-green-500';
      case 'Paused': return 'text-yellow-500';
      case 'Error': return 'text-red-500';
      default: return 'text-secondary';
    }
  };

  const getStatusBg = (status) => {
    switch(status) {
      case 'Active': return 'bg-green-900/20 border-green-700';
      case 'Paused': return 'bg-yellow-900/20 border-yellow-700';
      case 'Error': return 'bg-red-900/20 border-red-700';
      default: return 'bg-secondary/20 border-secondary/50';
    }
  };

  return (
    <div className="min-h-screen bg-dark text-white p-6">
      {/* Emergency Controls */}
      <div className="bg-black border border-secondary/50 rounded-lg p-6 mb-6">
        <h2 className="text-xl font-bold mb-2">Emergency Controls</h2>
        <p className="text-sm text-gray-400 mb-6">Global settings to manage all active strategies and positions.</p>
        
        <div className="space-y-4">
          {/* Master Switch */}
          <div className="flex items-center justify-between">
            <span className="font-medium">Master Switch (ON/OFF)</span>
            <label className="relative inline-flex items-center cursor-pointer">
              <input 
                type="checkbox" 
                checked={masterSwitch}
                onChange={() => setMasterSwitch(!masterSwitch)}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-secondary/50 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-secondary after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
            </label>
          </div>

          {/* Pause All Strategies */}
          <div className="flex items-center justify-between">
            <span className="font-medium">Pause All Strategies</span>
            <label className="relative inline-flex items-center cursor-pointer">
              <input 
                type="checkbox" 
                checked={pauseAll}
                onChange={() => setPauseAll(!pauseAll)}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-secondary/50 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-secondary after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-secondary"></div>
            </label>
          </div>

          {/* Close All Positions */}
          <div className="flex items-center justify-between">
            <span className="font-medium text-red-400">Close All Positions</span>
            <label className="relative inline-flex items-center cursor-pointer">
              <input 
                type="checkbox" 
                checked={closeAllPositions}
                onChange={() => setCloseAllPositions(!closeAllPositions)}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-secondary/50 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-secondary after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-secondary"></div>
            </label>
          </div>
        </div>
      </div>

      {/* My Trading Strategies */}
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold">My Trading Strategies</h2>
        <button className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded flex items-center gap-2">
          <span>+</span> Add New Strategy
        </button>
      </div>

      {/* Strategy Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {strategies.map((strategy) => (
          <div 
            key={strategy.id}
            className={`bg-secondary/10 rounded-lg p-6 border-2 ${getStatusBg(strategy.status)}`}
          >
            <div className="flex items-start justify-between mb-4">
              <div>
                <h3 className="text-xl font-bold mb-1">{strategy.name}</h3>
                <div className="flex items-center gap-2">
                  <span className={`text-sm font-semibold ${getStatusColor(strategy.status)}`}>
                    ▶ {strategy.status}
                  </span>
                </div>
              </div>
            </div>

            <p className="text-sm text-gray-400 mb-4">{strategy.description}</p>

            <div className="grid grid-cols-3 gap-4 mb-4">
              <div>
                <p className="text-xs text-gray-400 mb-1">Daily P&L</p>
                <p className={`text-lg font-bold ${strategy.dailyPL >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                  {strategy.dailyPL >= 0 ? '+' : ''}{strategy.dailyPL}%
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-400 mb-1">Win Rate</p>
                <p className="text-lg font-bold">{strategy.winRate}%</p>
              </div>
              <div>
                <p className="text-xs text-gray-400 mb-1">Max Drawdown</p>
                <p className="text-lg font-bold text-red-500">{strategy.maxDrawdown}%</p>
              </div>
            </div>

            <div className="flex gap-3">
              <button className="flex-1 bg-secondary/50 hover:bg-secondary/80 py-2 rounded flex items-center justify-center gap-2">
                <span>ὄ1</span> View Details
              </button>
              <button className="flex-1 bg-secondary/50 hover:bg-secondary/80 py-2 rounded flex items-center justify-center gap-2">
                <span>✏</span> Edit
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default StrategyIntelligence;
