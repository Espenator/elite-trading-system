import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faChartBar } from '@fortawesome/free-solid-svg-icons';

export default function PerformanceAnalytics() {
  return (
    <div className="p-6 h-full flex items-center justify-center">
      <div className="text-center max-w-2xl">
        <div className="w-24 h-24 mx-auto bg-gradient-to-br from-green-500 to-emerald-500 rounded-2xl flex items-center justify-center mb-6">
          <FontAwesomeIcon icon={faChartBar} className="text-white text-4xl" />
        </div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-4">Performance Analytics</h1>
        <p className="text-lg text-gray-600 dark:text-gray-400 mb-6">
          Deep dive into your trading performance with advanced analytics including Sharpe ratio, 
          max drawdown, win rates, profit factors, and detailed trade statistics over time.
        </p>
        <div className="inline-flex items-center px-6 py-3 bg-gray-100 dark:bg-gray-800 rounded-lg border border-gray-300 dark:border-gray-700">
          <span className="text-sm text-gray-600 dark:text-gray-400">Coming Soon</span>
        </div>
      </div>
    </div>
  );
}

