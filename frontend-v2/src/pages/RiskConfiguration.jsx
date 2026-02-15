import React, { useState } from 'react';

const RiskConfiguration = () => {
  const [maxDrawdown, setMaxDrawdown] = useState(10);
  const [positionSizeLimit, setPositionSizeLimit] = useState(5);
  const [maxDailyLoss, setMaxDailyLoss] = useState(2);
  const [varLimit, setVarLimit] = useState(1.5);
  const [equityDrop, setEquityDrop] = useState(20);
  const [volatilityIncrease, setVolatilityIncrease] = useState(30);

  const handleRunSimulation = () => {
    console.log('Running risk simulation with:', { equityDrop, volatilityIncrease });
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold">Risk Configuration</h1>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* General Risk Parameters */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-gray-800/50 rounded-lg p-6">
            <h2 className="text-xl font-bold mb-6">General Risk Parameters</h2>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Maximum Daily Drawdown */}
              <div>
                <label className="block text-sm font-medium mb-3">Maximum Daily Drawdown</label>
                <div className="flex items-center gap-4">
                  <input 
                    type="range" 
                    min="0" 
                    max="20" 
                    value={maxDrawdown}
                    onChange={(e) => setMaxDrawdown(parseFloat(e.target.value))}
                    className="flex-1"
                  />
                  <div className="flex items-center gap-1">
                    <input 
                      type="number" 
                      value={maxDrawdown}
                      onChange={(e) => setMaxDrawdown(parseFloat(e.target.value))}
                      className="w-16 bg-gray-900 border border-gray-700 rounded px-2 py-1 text-right"
                    />
                    <span className="text-gray-400">%</span>
                  </div>
                </div>
              </div>

              {/* Individual Position Size Limit */}
              <div>
                <label className="block text-sm font-medium mb-3">Individual Position Size Limit</label>
                <div className="flex items-center gap-4">
                  <input 
                    type="range" 
                    min="0" 
                    max="10" 
                    value={positionSizeLimit}
                    onChange={(e) => setPositionSizeLimit(parseFloat(e.target.value))}
                    className="flex-1"
                  />
                  <div className="flex items-center gap-1">
                    <input 
                      type="number" 
                      value={positionSizeLimit}
                      onChange={(e) => setPositionSizeLimit(parseFloat(e.target.value))}
                      className="w-16 bg-gray-900 border border-gray-700 rounded px-2 py-1 text-right"
                    />
                    <span className="text-gray-400">%</span>
                  </div>
                </div>
              </div>

              {/* Maximum Daily Loss Limit */}
              <div>
                <label className="block text-sm font-medium mb-3">Maximum Daily Loss Limit (Account Equity)</label>
                <div className="flex items-center gap-4">
                  <input 
                    type="range" 
                    min="0" 
                    max="5" 
                    step="0.5"
                    value={maxDailyLoss}
                    onChange={(e) => setMaxDailyLoss(parseFloat(e.target.value))}
                    className="flex-1"
                  />
                  <div className="flex items-center gap-1">
                    <input 
                      type="number" 
                      value={maxDailyLoss}
                      onChange={(e) => setMaxDailyLoss(parseFloat(e.target.value))}
                      step="0.1"
                      className="w-16 bg-gray-900 border border-gray-700 rounded px-2 py-1 text-right"
                    />
                    <span className="text-gray-400">%</span>
                  </div>
                </div>
              </div>

              {/* Value at Risk Limit */}
              <div>
                <label className="block text-sm font-medium mb-3">Value at Risk (VaR) Limit</label>
                <div className="flex items-center gap-4">
                  <input 
                    type="range" 
                    min="0" 
                    max="3" 
                    step="0.1"
                    value={varLimit}
                    onChange={(e) => setVarLimit(parseFloat(e.target.value))}
                    className="flex-1"
                  />
                  <div className="flex items-center gap-1">
                    <input 
                      type="number" 
                      value={varLimit}
                      onChange={(e) => setVarLimit(parseFloat(e.target.value))}
                      step="0.1"
                      className="w-16 bg-gray-900 border border-gray-700 rounded px-2 py-1 text-right"
                    />
                    <span className="text-gray-400">%</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Risk Scenario Simulator */}
          <div className="bg-gray-800/50 rounded-lg p-6">
            <h2 className="text-xl font-bold mb-6">Risk Scenario Simulator</h2>
            
            <div className="space-y-4">
              {/* Simulated Equity Drop */}
              <div>
                <label className="block text-sm font-medium mb-2">Simulated Equity Drop</label>
                <div className="flex items-center gap-3">
                  <input 
                    type="number" 
                    value={equityDrop}
                    onChange={(e) => setEquityDrop(parseFloat(e.target.value))}
                    className="w-24 bg-gray-900 border border-gray-700 rounded px-3 py-2"
                  />
                  <span className="text-gray-400">%</span>
                </div>
              </div>

              {/* Simulated Volatility Increase */}
              <div>
                <label className="block text-sm font-medium mb-2">Simulated Volatility Increase</label>
                <div className="flex items-center gap-3">
                  <input 
                    type="number" 
                    value={volatilityIncrease}
                    onChange={(e) => setVolatilityIncrease(parseFloat(e.target.value))}
                    className="w-24 bg-gray-900 border border-gray-700 rounded px-3 py-2"
                  />
                  <span className="text-gray-400">%</span>
                </div>
              </div>

              <button 
                onClick={handleRunSimulation}
                className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 rounded mt-4"
              >
                Run Simulation
              </button>

              <div className="mt-4 pt-4 border-t border-gray-700">
                <div className="flex justify-between mb-2">
                  <span className="text-sm text-gray-400">Estimated Max Drawdown:</span>
                  <span className="text-sm font-semibold text-red-500">10.0%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-400">Potential Daily Loss:</span>
                  <span className="text-sm font-semibold text-red-500">1.5%</span>
                </div>
              </div>
            </div>
          </div>

          {/* Risk History Chart */}
          <div className="bg-gray-800/50 rounded-lg p-6">
            <h2 className="text-xl font-bold mb-4">Risk History Chart</h2>
            <div className="h-64 flex items-center justify-center bg-gray-900/50 rounded">
              <p className="text-gray-500">Historical Risk Metrics Chart (Placeholder)</p>
            </div>
          </div>
        </div>

        {/* Real-time Risk Monitor */}
        <div className="lg:col-span-1">
          <div className="bg-gray-800/50 rounded-lg p-6 sticky top-6">
            <h2 className="text-xl font-bold mb-6">Real-time Risk Monitor</h2>
            
            <div className="space-y-6">
              {/* Current Exposure */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-gray-400">$ Current Exposure</span>
                  <span className="text-2xl font-bold">$12,500</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-green-500">↑</span>
                </div>
              </div>

              <div className="border-t border-gray-700 pt-6">
                {/* VaR (95%) */}
                <div className="flex items-center justify-between mb-4">
                  <span className="text-sm text-gray-400">○ VaR (95%, 1-day)</span>
                  <span className="text-xl font-bold">$350</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-red-500">↓</span>
                </div>
              </div>

              <div className="border-t border-gray-700 pt-6">
                {/* Expected Shortfall */}
                <div className="flex items-center justify-between mb-4">
                  <span className="text-sm text-gray-400">○ Expected Shortfall</span>
                  <span className="text-xl font-bold">$520</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-green-500">↑</span>
                </div>
              </div>

              <div className="mt-6 p-4 bg-green-900/20 border border-green-700 rounded">
                <p className="text-sm text-green-400">✓ All risk parameters are within acceptable limits</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RiskConfiguration;
