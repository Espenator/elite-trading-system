import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faThLarge } from '@fortawesome/free-solid-svg-icons';

export default function PortfolioHeatmap() {
  return (
    <div className="p-6 h-full flex items-center justify-center">
      <div className="text-center max-w-2xl">
        <div className="w-24 h-24 mx-auto bg-gradient-to-br from-purple-500 to-pink-500 rounded-2xl flex items-center justify-center mb-6">
          <FontAwesomeIcon icon={faThLarge} className="text-white text-4xl" />
        </div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-4">Portfolio Heatmap</h1>
        <p className="text-lg text-gray-600 dark:text-gray-400 mb-6">
          Visualize your portfolio performance with interactive heatmaps showing sector allocation, 
          position performance, and risk exposure across your holdings.
        </p>
        <div className="inline-flex items-center px-6 py-3 bg-gray-100 dark:bg-gray-800 rounded-lg border border-gray-300 dark:border-gray-700">
          <span className="text-sm text-gray-600 dark:text-gray-400">Coming Soon</span>
        </div>
      </div>
    </div>
  );
}

