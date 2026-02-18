import React, { useState } from 'react';
import Card from '../components/ui/Card';
import TextField from '../components/ui/TextField';
import Button from '../components/ui/Button';

const RiskIntelligence = () => {
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
    <div className="min-h-screen bg-dark text-white p-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold">Risk Configuration</h1>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <Card title="General Risk Parameters">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-white mb-3">Maximum Daily Drawdown</label>
                <div className="flex items-center gap-4">
                  <input
                    type="range"
                    min="0"
                    max="20"
                    value={maxDrawdown}
                    onChange={(e) => setMaxDrawdown(parseFloat(e.target.value))}
                    className="flex-1 accent-primary"
                  />
                  <TextField type="number" value={maxDrawdown} onChange={(e) => setMaxDrawdown(parseFloat(e.target.value) || 0)} suffix="%" className="w-20" inputClassName="text-right w-16" />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-white mb-3">Individual Position Size Limit</label>
                <div className="flex items-center gap-4">
                  <input
                    type="range"
                    min="0"
                    max="10"
                    value={positionSizeLimit}
                    onChange={(e) => setPositionSizeLimit(parseFloat(e.target.value))}
                    className="flex-1 accent-primary"
                  />
                  <TextField type="number" value={positionSizeLimit} onChange={(e) => setPositionSizeLimit(parseFloat(e.target.value) || 0)} suffix="%" className="w-20" inputClassName="text-right w-16" />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-white mb-3">Maximum Daily Loss Limit (Account Equity)</label>
                <div className="flex items-center gap-4">
                  <input
                    type="range"
                    min="0"
                    max="5"
                    step="0.5"
                    value={maxDailyLoss}
                    onChange={(e) => setMaxDailyLoss(parseFloat(e.target.value))}
                    className="flex-1 accent-primary"
                  />
                  <TextField type="number" value={maxDailyLoss} onChange={(e) => setMaxDailyLoss(parseFloat(e.target.value) || 0)} step="0.1" suffix="%" className="w-20" inputClassName="text-right w-16" />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-white mb-3">Value at Risk (VaR) Limit</label>
                <div className="flex items-center gap-4">
                  <input
                    type="range"
                    min="0"
                    max="3"
                    step="0.1"
                    value={varLimit}
                    onChange={(e) => setVarLimit(parseFloat(e.target.value))}
                    className="flex-1 accent-primary"
                  />
                  <TextField type="number" value={varLimit} onChange={(e) => setVarLimit(parseFloat(e.target.value) || 0)} step="0.1" suffix="%" className="w-20" inputClassName="text-right w-16" />
                </div>
              </div>
            </div>
          </Card>

          <Card title="Risk Scenario Simulator">
            <div className="space-y-4">
              <TextField label="Simulated Equity Drop" type="number" value={equityDrop} onChange={(e) => setEquityDrop(parseFloat(e.target.value) || 0)} suffix="%" className="max-w-[8rem]" />
              <TextField label="Simulated Volatility Increase" type="number" value={volatilityIncrease} onChange={(e) => setVolatilityIncrease(parseFloat(e.target.value) || 0)} suffix="%" className="max-w-[8rem]" />
              <Button variant="primary" fullWidth onClick={handleRunSimulation} className="mt-4">Run Simulation</Button>
              <div className="mt-4 pt-4 border-t border-secondary/50">
                <div className="flex justify-between mb-2">
                  <span className="text-sm text-secondary">Estimated Max Drawdown:</span>
                  <span className="text-sm font-semibold text-danger">10.0%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-secondary">Potential Daily Loss:</span>
                  <span className="text-sm font-semibold text-danger">1.5%</span>
                </div>
              </div>
            </div>
          </Card>

          <Card title="Risk History Chart">
            <div className="h-64 flex items-center justify-center bg-dark/50 rounded">
              <p className="text-secondary">Historical Risk Metrics Chart (Placeholder)</p>
            </div>
          </Card>
        </div>

        <div className="lg:col-span-1">
          <Card title="Real-time Risk Monitor" className="sticky top-6">
            
            <div className="space-y-6">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-secondary">$ Current Exposure</span>
                  <span className="text-2xl font-bold text-white">$12,500</span>
                </div>
                <span className="text-success">↑</span>
              </div>
              <div className="border-t border-secondary/50 pt-6">
                <div className="flex items-center justify-between mb-4">
                  <span className="text-sm text-secondary">○ VaR (95%, 1-day)</span>
                  <span className="text-xl font-bold text-white">$350</span>
                </div>
                <span className="text-danger">↓</span>
              </div>
              <div className="border-t border-secondary/50 pt-6">
                <div className="flex items-center justify-between mb-4">
                  <span className="text-sm text-secondary">○ Expected Shortfall</span>
                  <span className="text-xl font-bold text-white">$520</span>
                </div>
                <span className="text-success">↑</span>
              </div>
              <div className="mt-6 p-4 bg-success/20 border border-success/50 rounded-xl">
                <p className="text-sm text-success">✓ All risk parameters are within acceptable limits</p>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default RiskIntelligence;
