import React, { useEffect, useState } from 'react';
import { fetchSignals, getDataStatus } from '../services/prediction.service';

export default function Signals() {
  const [signals, setSignals] = useState([]);
  const [asOf, setAsOf] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [dataStatus, setDataStatus] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchSignals(asOf || undefined)
      .then((data) => {
        if (!cancelled) setSignals(data.signals || []);
      })
      .catch((e) => {
        if (!cancelled) {
          setError(e.message);
          setSignals([]);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [asOf]);

  useEffect(() => {
    getDataStatus().then(setDataStatus).catch(() => setDataStatus(null));
  }, []);

  const buySignals = signals.filter((s) => s.action === 'BUY');

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">ML Signals</h1>
      <p className="text-gray-600 dark:text-gray-400 mb-4">
        Daily direction signals (P(up)) from the LSTM model. Run data pipeline and train a model to see live signals.
      </p>

      {dataStatus && (
        <div className="mb-4 p-3 bg-gray-100 dark:bg-gray-800 rounded-lg text-sm">
          <span className="font-medium">Data status:</span> {dataStatus.connected ? 'Connected' : 'Not connected'}
          {dataStatus.daily_features_last_date && (
            <span className="ml-4">Features through {dataStatus.daily_features_last_date}</span>
          )}
        </div>
      )}

      <div className="mb-4 flex items-center gap-4">
        <label className="text-sm text-gray-600 dark:text-gray-400">As of date (optional)</label>
        <input
          type="date"
          value={asOf}
          onChange={(e) => setAsOf(e.target.value)}
          className="rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-1.5 text-sm"
        />
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 rounded-lg">
          {error}
        </div>
      )}

      {loading ? (
        <p className="text-gray-500">Loading signals…</p>
      ) : (
        <>
          <p className="text-sm text-gray-500 mb-2">
            {signals.length} symbols · {buySignals.length} BUY
          </p>
          <div className="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-700">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-800">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Symbol</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Date</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">P(up)</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Action</th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
                {signals.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="px-4 py-6 text-center text-gray-500">
                      No signals. Ensure daily_features are populated and an LSTM model is trained (see backend jobs).
                    </td>
                  </tr>
                ) : (
                  signals.map((s) => (
                    <tr key={`${s.symbol}-${s.date}`}>
                      <td className="px-4 py-2 font-medium text-gray-900 dark:text-white">{s.symbol}</td>
                      <td className="px-4 py-2 text-gray-600 dark:text-gray-300">{s.date}</td>
                      <td className="px-4 py-2">{(s.prob_up ?? 0).toFixed(3)}</td>
                      <td className="px-4 py-2">
                        <span className={s.action === 'BUY' ? 'text-green-600 dark:text-green-400 font-medium' : 'text-gray-500'}>
                          {s.action}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
