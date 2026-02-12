import React, { useState } from 'react';
import { runBacktest } from '../services/prediction.service';

export default function Backtest() {
  const [start, setStart] = useState('2023-01-01');
  const [end, setEnd] = useState('2024-12-31');
  const [modelId, setModelId] = useState('lstm_daily_latest');
  const [nStocks, setNStocks] = useState(20);
  const [minScore, setMinScore] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  const handleRun = () => {
    setLoading(true);
    setError(null);
    setResult(null);
    const params = { start, end, modelId, nStocks };
    if (minScore !== '') params.minScore = parseFloat(minScore);
    runBacktest(params)
      .then((data) => setResult(data))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  const metrics = result?.metrics;
  const curve = result?.equity_curve || [];

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">Strategy Backtest</h1>
      <p className="text-gray-600 dark:text-gray-400 mb-6">
        Top-N long-only daily backtest vs SPY. Requires daily_predictions populated for the chosen model_id and date range.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Start</label>
          <input
            type="date"
            value={start}
            onChange={(e) => setStart(e.target.value)}
            className="w-full rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">End</label>
          <input
            type="date"
            value={end}
            onChange={(e) => setEnd(e.target.value)}
            className="w-full rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Model ID</label>
          <input
            type="text"
            value={modelId}
            onChange={(e) => setModelId(e.target.value)}
            placeholder="lstm_daily_latest"
            className="w-full rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Top N stocks</label>
          <input
            type="number"
            min={1}
            max={100}
            value={nStocks}
            onChange={(e) => setNStocks(Number(e.target.value))}
            className="w-full rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Min score (optional)</label>
          <input
            type="number"
            step="0.01"
            min={0}
            max={1}
            value={minScore}
            onChange={(e) => setMinScore(e.target.value)}
            placeholder="e.g. 0.6"
            className="w-full rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm"
          />
        </div>
      </div>

      <button
        onClick={handleRun}
        disabled={loading}
        className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 font-medium"
      >
        {loading ? 'Running…' : 'Run backtest'}
      </button>

      {error && (
        <div className="mt-4 p-3 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 rounded-lg">
          {error}
        </div>
      )}

      {result && (
        <div className="mt-6 space-y-4">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Metrics</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {metrics && (
              <>
                <div className="p-3 bg-gray-100 dark:bg-gray-800 rounded-lg">
                  <div className="text-xs text-gray-500 dark:text-gray-400">Strategy ann. return</div>
                  <div className="text-lg font-semibold">{(metrics.strategy_annual_return * 100).toFixed(2)}%</div>
                </div>
                <div className="p-3 bg-gray-100 dark:bg-gray-800 rounded-lg">
                  <div className="text-xs text-gray-500 dark:text-gray-400">SPY ann. return</div>
                  <div className="text-lg font-semibold">{(metrics.spy_annual_return * 100).toFixed(2)}%</div>
                </div>
                <div className="p-3 bg-gray-100 dark:bg-gray-800 rounded-lg">
                  <div className="text-xs text-gray-500 dark:text-gray-400">Sharpe</div>
                  <div className="text-lg font-semibold">{metrics.sharpe.toFixed(3)}</div>
                </div>
                <div className="p-3 bg-gray-100 dark:bg-gray-800 rounded-lg">
                  <div className="text-xs text-gray-500 dark:text-gray-400">Max drawdown</div>
                  <div className="text-lg font-semibold">{(metrics.max_drawdown * 100).toFixed(2)}%</div>
                </div>
              </>
            )}
          </div>
          {curve.length > 0 && (
            <>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Equity curve (last 30 points)</h2>
              <div className="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-700">
                <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700 text-sm">
                  <thead className="bg-gray-50 dark:bg-gray-800">
                    <tr>
                      <th className="px-4 py-2 text-left font-medium text-gray-500 dark:text-gray-400">Date</th>
                      <th className="px-4 py-2 text-right font-medium text-gray-500 dark:text-gray-400">Strategy</th>
                      <th className="px-4 py-2 text-right font-medium text-gray-500 dark:text-gray-400">SPY</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
                    {curve.slice(-30).reverse().map((row, i) => (
                      <tr key={i}>
                        <td className="px-4 py-2 text-gray-700 dark:text-gray-300">{row.date}</td>
                        <td className="px-4 py-2 text-right font-mono">{row.strategy_equity?.toFixed(4)}</td>
                        <td className="px-4 py-2 text-right font-mono">{row.spy_equity?.toFixed(4)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
