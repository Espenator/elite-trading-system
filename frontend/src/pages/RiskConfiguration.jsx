import { useState } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { 
  faShieldAlt, faArrowUp, faArrowDown, faChartLine,
  faEnvelope, faComment
} from '@fortawesome/free-solid-svg-icons';

export default function RiskConfiguration() {
  // General Risk Parameters
  const [maxDailyDrawdown, setMaxDailyDrawdown] = useState(10);
  const [positionSizeLimit, setPositionSizeLimit] = useState(5);
  const [maxDailyLossLimit, setMaxDailyLossLimit] = useState(2);
  const [varLimit, setVarLimit] = useState(1.5);

  // Risk Scenario Simulator
  const [simulatedEquityDrop, setSimulatedEquityDrop] = useState(20);
  const [simulatedVolatilityIncrease, setSimulatedVolatilityIncrease] = useState(30);
  const [simulationResults, setSimulationResults] = useState(null);

  // Alert Configuration
  const [dailyPnLLossAlert, setDailyPnLLossAlert] = useState(5);
  const [maxDrawdownAlert, setMaxDrawdownAlert] = useState(10);
  const [autoPauseTrading, setAutoPauseTrading] = useState(true);

  // Real-time Risk Monitor Data
  const riskMetrics = [
    { label: 'Current Exposure', value: '$12,500', trend: 'up', color: 'green' },
    { label: 'VaR (95%)', value: '$350', trend: 'down', color: 'red' },
    { label: 'Expected Shortfall', value: '$520', trend: 'up', color: 'green' },
  ];

  const handleRunSimulation = () => {
    // Calculate estimated results based on inputs
    const estimatedMaxDrawdown = (maxDailyDrawdown * (1 + simulatedEquityDrop / 100)).toFixed(1);
    const potentialDailyLoss = (maxDailyLossLimit * (1 + simulatedVolatilityIncrease / 100)).toFixed(1);
    
    setSimulationResults({
      maxDrawdown: estimatedMaxDrawdown,
      dailyLoss: potentialDailyLoss,
    });
  };

  const handleTestEmailAlert = () => {
    // TODO: Implement email alert test
    alert('Email alert test sent!');
  };

  const handleTestSMSAlert = () => {
    // TODO: Implement SMS alert test
    alert('SMS alert test sent!');
  };

  return (
    <div className="p-6 space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Risk Configuration</h1>
      </div>

      {/* General Risk Parameters and Real-time Risk Monitor Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* General Risk Parameters */}
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">General Risk Parameters</h2>
          <div className="space-y-6">
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Maximum Daily Drawdown
                </label>
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    min="0"
                    max="100"
                    step="0.1"
                    value={maxDailyDrawdown}
                    onChange={(e) => setMaxDailyDrawdown(Number(e.target.value))}
                    className="w-20 px-2 py-1 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
                  />
                  <span className="text-sm text-gray-600 dark:text-gray-400">%</span>
                </div>
              </div>
              <input
                type="range"
                min="0"
                max="50"
                step="0.1"
                value={maxDailyDrawdown}
                onChange={(e) => setMaxDailyDrawdown(Number(e.target.value))}
                className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer"
              />
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Individual Position Size Limit
                </label>
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    min="0"
                    max="100"
                    step="0.1"
                    value={positionSizeLimit}
                    onChange={(e) => setPositionSizeLimit(Number(e.target.value))}
                    className="w-20 px-2 py-1 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
                  />
                  <span className="text-sm text-gray-600 dark:text-gray-400">%</span>
                </div>
              </div>
              <input
                type="range"
                min="0"
                max="20"
                step="0.1"
                value={positionSizeLimit}
                onChange={(e) => setPositionSizeLimit(Number(e.target.value))}
                className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer"
              />
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Maximum Daily Loss Limit (Account Equity)
                </label>
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    min="0"
                    max="100"
                    step="0.1"
                    value={maxDailyLossLimit}
                    onChange={(e) => setMaxDailyLossLimit(Number(e.target.value))}
                    className="w-20 px-2 py-1 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
                  />
                  <span className="text-sm text-gray-600 dark:text-gray-400">%</span>
                </div>
              </div>
              <input
                type="range"
                min="0"
                max="10"
                step="0.1"
                value={maxDailyLossLimit}
                onChange={(e) => setMaxDailyLossLimit(Number(e.target.value))}
                className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer"
              />
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Value at Risk (VaR) Limit
                </label>
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    min="0"
                    max="100"
                    step="0.1"
                    value={varLimit}
                    onChange={(e) => setVarLimit(Number(e.target.value))}
                    className="w-20 px-2 py-1 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
                  />
                  <span className="text-sm text-gray-600 dark:text-gray-400">%</span>
                </div>
              </div>
              <input
                type="range"
                min="0"
                max="10"
                step="0.1"
                value={varLimit}
                onChange={(e) => setVarLimit(Number(e.target.value))}
                className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer"
              />
            </div>
          </div>
        </div>

        {/* Real-time Risk Monitor */}
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Real-time Risk Monitor</h2>
          <div className="space-y-4">
            {riskMetrics.map((metric, index) => (
              <div key={index} className="bg-gray-50 dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <FontAwesomeIcon 
                      icon={faShieldAlt} 
                      className="text-gray-400 dark:text-gray-500"
                    />
                    <span className="text-sm text-gray-600 dark:text-gray-400">{metric.label}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-lg font-bold text-gray-900 dark:text-white">{metric.value}</span>
                    <div className={`flex items-center ${
                      metric.color === 'green' ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
                    }`}>
                      <FontAwesomeIcon 
                        icon={metric.trend === 'up' ? faArrowUp : faArrowDown} 
                        className="text-xs"
                      />
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Risk Scenario Simulator */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Risk Scenario Simulator</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Simulated Equity Drop
              </label>
              <div className="flex items-center gap-2">
                <input
                  type="range"
                  min="0"
                  max="100"
                  step="1"
                  value={simulatedEquityDrop}
                  onChange={(e) => setSimulatedEquityDrop(Number(e.target.value))}
                  className="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer"
                />
                <div className="flex items-center gap-1 w-20">
                  <input
                    type="number"
                    min="0"
                    max="100"
                    value={simulatedEquityDrop}
                    onChange={(e) => setSimulatedEquityDrop(Number(e.target.value))}
                    className="w-16 px-2 py-1 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
                  />
                  <span className="text-sm text-gray-600 dark:text-gray-400">%</span>
                </div>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Simulated Volatility Increase
              </label>
              <div className="flex items-center gap-2">
                <input
                  type="range"
                  min="0"
                  max="100"
                  step="1"
                  value={simulatedVolatilityIncrease}
                  onChange={(e) => setSimulatedVolatilityIncrease(Number(e.target.value))}
                  className="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer"
                />
                <div className="flex items-center gap-1 w-20">
                  <input
                    type="number"
                    min="0"
                    max="100"
                    value={simulatedVolatilityIncrease}
                    onChange={(e) => setSimulatedVolatilityIncrease(Number(e.target.value))}
                    className="w-16 px-2 py-1 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
                  />
                  <span className="text-sm text-gray-600 dark:text-gray-400">%</span>
                </div>
              </div>
            </div>

            <button
              onClick={handleRunSimulation}
              className="w-full px-4 py-2 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white rounded-lg font-medium transition-colors"
            >
              Run Simulation
            </button>
          </div>

          {simulationResults && (
            <div className="bg-gray-50 dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
              <div className="space-y-3">
                <div>
                  <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">Estimated Max Drawdown:</div>
                  <div className="text-xl font-bold text-red-600 dark:text-red-400">
                    {simulationResults.maxDrawdown}%
                  </div>
                </div>
                <div>
                  <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">Potential Daily Loss:</div>
                  <div className="text-xl font-bold text-red-600 dark:text-red-400">
                    {simulationResults.dailyLoss}%
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Risk History Chart */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Historical Risk Metrics</h2>
        <div className="h-64 bg-gray-50 dark:bg-gray-900 rounded border border-gray-200 dark:border-gray-700 flex items-center justify-center">
          <div className="text-center">
            <FontAwesomeIcon icon={faChartLine} className="text-4xl text-gray-400 dark:text-gray-600 mb-2" />
            <p className="text-sm text-gray-500 dark:text-gray-400">Risk History Chart</p>
            <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">Max Daily Loss (blue) and VaR (pink) over time</p>
          </div>
        </div>
      </div>

      {/* Alert Configuration */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Alert Configuration</h2>
        <div className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Alert on daily P&L loss greater than
            </label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                min="0"
                max="100"
                step="0.1"
                value={dailyPnLLossAlert}
                onChange={(e) => setDailyPnLLossAlert(Number(e.target.value))}
                className="w-24 px-3 py-2 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-600 dark:text-gray-400">%</span>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Alert on maximum drawdown greater than
            </label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                min="0"
                max="100"
                step="0.1"
                value={maxDrawdownAlert}
                onChange={(e) => setMaxDrawdownAlert(Number(e.target.value))}
                className="w-24 px-3 py-2 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-600 dark:text-gray-400">%</span>
            </div>
          </div>

          <div className="flex items-center justify-between pt-4 border-t border-gray-200 dark:border-gray-700">
            <div>
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Auto-pause trading on critical alerts
              </label>
            </div>
            <button
              onClick={() => setAutoPauseTrading(!autoPauseTrading)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                autoPauseTrading ? 'bg-blue-600' : 'bg-gray-300 dark:bg-gray-600'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  autoPauseTrading ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>

          <div className="flex gap-3 pt-2">
            <button
              onClick={handleTestEmailAlert}
              className="flex-1 px-4 py-2 bg-gray-900 dark:bg-gray-700 hover:bg-gray-800 dark:hover:bg-gray-600 text-white rounded-lg font-medium transition-colors flex items-center justify-center gap-2"
            >
              <FontAwesomeIcon icon={faEnvelope} />
              Test Email Alert
            </button>
            <button
              onClick={handleTestSMSAlert}
              className="flex-1 px-4 py-2 bg-gray-900 dark:bg-gray-700 hover:bg-gray-800 dark:hover:bg-gray-600 text-white rounded-lg font-medium transition-colors flex items-center justify-center gap-2"
            >
              <FontAwesomeIcon icon={faComment} />
              Test SMS Alert
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
