import { useState } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { 
  faArrowUp, faArrowDown, faDownload, faChevronDown, faChevronUp,
  faChartLine, faChartArea
} from '@fortawesome/free-solid-svg-icons';

export default function PerformanceAnalytics() {
  const [selectedTimeframe, setSelectedTimeframe] = useState('1W');
  const [mlInsightsExpanded, setMlInsightsExpanded] = useState(false);
  const [riskShieldExpanded, setRiskShieldExpanded] = useState(false);

  // Market Overview Data
  const marketOverview = [
    { label: 'SPY (S&P 500 ETF)', value: '$498.75', change: '+0.85%', trend: 'up', color: 'green' },
    { label: 'VIX (Volatility Index)', value: '17.20', change: '-1.52%', trend: 'down', color: 'red' },
    { label: 'Market Breadth (Adv/Dec)', value: '+1,250', change: '+8.3%', trend: 'up', color: 'green' },
    { label: 'Sector Performance (Tech)', value: '+1.1%', change: 'Leading', trend: 'up', color: 'green' },
  ];

  // Performance Summary Data
  const performanceSummary = [
    { label: 'Total Return', value: '+15.3%', change: '+1.2% (last month)', trend: 'up', color: 'green' },
    { label: 'Annualized Return', value: '18.7%', change: '-0.5% (vs. avg)', trend: 'down', color: 'red' },
    { label: 'Sharpe Ratio', value: '1.25', change: '+0.03 (vs. benchmark)', trend: 'up', color: 'green' },
  ];

  // Monthly Returns Data (2023-2024)
  const monthlyReturns2023 = [3.5, 1.2, -0.8, 2.1, 4.0, 0.5, 1.8, -2.5, -1.0, 0.7];
  const monthlyReturns2024 = [4.1, 2.5, 0.1, 1.5, 3.2, 1.0];
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

  // Returns Decomposition
  const returnsDecomposition = [
    { factor: 'Equity Exposure', contribution: '+7.2%', color: 'green' },
    { factor: 'Fixed Income', contribution: '+1.8%', color: 'green' },
    { factor: 'Alternatives', contribution: '-0.5%', color: 'red' },
    { factor: 'Currency Hedging', contribution: '+0.3%', color: 'green' },
    { factor: 'Sector Rotation', contribution: '+1.5%', color: 'green' },
  ];

  const getHeatmapColor = (value) => {
    if (value >= 3) return 'bg-green-600 dark:bg-green-700';
    if (value >= 1.5) return 'bg-green-400 dark:bg-green-600';
    if (value >= 0.5) return 'bg-green-200 dark:bg-green-500';
    if (value >= 0) return 'bg-gray-200 dark:bg-gray-600';
    if (value >= -1) return 'bg-red-200 dark:bg-red-500';
    return 'bg-red-400 dark:bg-red-600';
  };

  return (
    <div className="p-6 space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Performance Analytics</h1>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">Last updated 1 minute ago</p>
        </div>
        <button className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors flex items-center gap-2">
          <FontAwesomeIcon icon={faDownload} />
          Export Report
        </button>
      </div>

      {/* Market Overview */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Market Overview</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {marketOverview.map((item, index) => (
            <div key={index} className="bg-gray-50 dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
              <div className="text-sm text-gray-600 dark:text-gray-400 mb-2">{item.label}</div>
              <div className="flex items-center justify-between">
                <div className="text-xl font-bold text-gray-900 dark:text-white">{item.value}</div>
                <div className={`flex items-center gap-1 text-sm font-medium ${
                  item.color === 'green' ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
                }`}>
                  <FontAwesomeIcon 
                    icon={item.trend === 'up' ? faArrowUp : faArrowDown} 
                    className="text-xs"
                  />
                  <span>{item.change}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Performance Summary */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Performance Summary</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {performanceSummary.map((item, index) => (
            <div key={index} className="bg-gray-50 dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
              <div className="text-sm text-gray-600 dark:text-gray-400 mb-2">{item.label}</div>
              <div className="flex items-center justify-between">
                <div className="text-xl font-bold text-gray-900 dark:text-white">{item.value}</div>
                <div className={`flex items-center gap-1 text-sm font-medium ${
                  item.color === 'green' ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
                }`}>
                  <FontAwesomeIcon 
                    icon={item.trend === 'up' ? faArrowUp : faArrowDown} 
                    className="text-xs"
                  />
                  <span>{item.change}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Portfolio Performance Chart */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Portfolio Performance</h2>
          <div className="flex gap-2">
            {['1H', '4H', '1D', '1W', '1M', '1Y', 'ALL'].map(tf => (
              <button
                key={tf}
                onClick={() => setSelectedTimeframe(tf)}
                className={`px-3 py-1 text-xs rounded font-medium transition ${
                  selectedTimeframe === tf
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                }`}
              >
                {tf}
              </button>
            ))}
          </div>
        </div>
        <div className="h-64 bg-gray-50 dark:bg-gray-900 rounded border border-gray-200 dark:border-gray-700 flex items-center justify-center">
          <div className="text-center">
            <FontAwesomeIcon icon={faChartLine} className="text-4xl text-gray-400 dark:text-gray-600 mb-2" />
            <p className="text-sm text-gray-500 dark:text-gray-400">Portfolio Performance Chart</p>
            <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">Portfolio Value (blue) vs Benchmark (dashed)</p>
          </div>
        </div>
      </div>

      {/* Drawdown Timeline Chart */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">Drawdown Timeline</h2>
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
          Shows percentage decline from peak equity over time.
        </p>
        <div className="h-48 bg-gray-50 dark:bg-gray-900 rounded border border-gray-200 dark:border-gray-700 flex items-center justify-center">
          <div className="text-center">
            <FontAwesomeIcon icon={faChartArea} className="text-4xl text-red-400 dark:text-red-600 mb-2" />
            <p className="text-sm text-gray-500 dark:text-gray-400">Drawdown Timeline Chart</p>
            <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">Red area showing drawdown periods</p>
          </div>
        </div>
      </div>

      {/* Monthly Returns Heatmap */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">Monthly Returns Heatmap (2023-2024)</h2>
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
          Color intensity indicates monthly performance.
        </p>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400">Month</th>
                {months.map(month => (
                  <th key={month} className="px-3 py-2 text-center text-xs font-medium text-gray-500 dark:text-gray-400">{month}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              <tr>
                <td className="px-4 py-2 text-sm font-medium text-gray-900 dark:text-white">2023</td>
                {months.map((month, idx) => (
                  <td key={`2023-${idx}`} className={`px-3 py-2 text-center text-sm font-medium ${
                    idx < monthlyReturns2023.length 
                      ? `${getHeatmapColor(monthlyReturns2023[idx])} text-gray-900 dark:text-white`
                      : 'bg-gray-100 dark:bg-gray-700 text-gray-400 dark:text-gray-500'
                  }`}>
                    {idx < monthlyReturns2023.length ? `${monthlyReturns2023[idx] > 0 ? '+' : ''}${monthlyReturns2023[idx]}%` : '-'}
                  </td>
                ))}
              </tr>
              <tr>
                <td className="px-4 py-2 text-sm font-medium text-gray-900 dark:text-white">2024</td>
                {months.map((month, idx) => (
                  <td key={`2024-${idx}`} className={`px-3 py-2 text-center text-sm font-medium ${
                    idx < monthlyReturns2024.length 
                      ? `${getHeatmapColor(monthlyReturns2024[idx])} text-gray-900 dark:text-white`
                      : 'bg-gray-100 dark:bg-gray-700 text-gray-400 dark:text-gray-500'
                  }`}>
                    {idx < monthlyReturns2024.length ? `${monthlyReturns2024[idx] > 0 ? '+' : ''}${monthlyReturns2024[idx]}%` : '-'}
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Returns Decomposition and Insights Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Returns Decomposition */}
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">Returns Decomposition</h2>
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
            Breakdown of portfolio returns by factor.
          </p>
          <div className="space-y-3">
            {returnsDecomposition.map((item, index) => (
              <div key={index} className="flex items-center justify-between">
                <span className="text-sm text-gray-600 dark:text-gray-400">{item.factor}</span>
                <span className={`text-sm font-medium ${
                  item.color === 'green' ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
                }`}>
                  {item.contribution}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* ML Insights */}
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">ML Insights</h2>
            <button
              onClick={() => setMlInsightsExpanded(!mlInsightsExpanded)}
              className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
            >
              <FontAwesomeIcon icon={mlInsightsExpanded ? faChevronUp : faChevronDown} />
            </button>
          </div>
          {mlInsightsExpanded && (
            <div className="space-y-3 text-sm text-gray-600 dark:text-gray-400">
              <p className="leading-relaxed">
                Our machine learning models predict a moderate uptrend for growth stocks in the next quarter, 
                driven by expected interest rate stability. Specific sectors to watch include renewable energy 
                and AI infrastructure. Consider tactical allocations to these areas for potential outperformance.
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-500">
                *Prediction accuracy: 78% for the next 30 days. Model last updated: 2024-07-20.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Risk Shield Summary */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Risk Shield Summary</h2>
          <button
            onClick={() => setRiskShieldExpanded(!riskShieldExpanded)}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          >
            <FontAwesomeIcon icon={riskShieldExpanded ? faChevronUp : faChevronDown} />
          </button>
        </div>
        {riskShieldExpanded && (
          <div className="space-y-3 text-sm text-gray-600 dark:text-gray-400">
            <div>
              <span className="font-medium text-gray-900 dark:text-white">Total Portfolio VaR (99%, 1-day):</span>{' '}
              <span className="text-red-600 dark:text-red-400">-2.5%</span>
            </div>
            <div>
              <span className="font-medium text-gray-900 dark:text-white">Current Beta vs. S&P 500:</span>{' '}
              1.15 (slightly aggressive)
            </div>
            <div>
              <span className="font-medium text-gray-900 dark:text-white">Concentration Risk (Top 5 Holdings):</span>{' '}
              35%
            </div>
            <div>
              <span className="font-medium text-gray-900 dark:text-white">Liquidity Profile:</span>{' '}
              High. Majority of holdings are highly liquid.
            </div>
            <div className="pt-2 border-t border-gray-200 dark:border-gray-700">
              <span className="font-medium text-gray-900 dark:text-white">Recommendations:</span>{' '}
              Diversify exposure in technology sector to mitigate concentration risk.
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
