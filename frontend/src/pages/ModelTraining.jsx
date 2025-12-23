import { useState } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { 
  faUpload, faSearch, faEye, faDownload, faTrash,
  faPlay, faSave, faRocket, faChartLine, faCheckCircle,
  faArrowTrendUp
} from '@fortawesome/free-solid-svg-icons';

export default function ModelTraining() {
  const [modelName, setModelName] = useState('XGBoost_V1_Financial');
  const [datasetSource, setDatasetSource] = useState('FinancialTimeSeries_V1');
  const [algorithm, setAlgorithm] = useState('XGBoost');
  const [epochs, setEpochs] = useState(100);
  const [validationSplit, setValidationSplit] = useState('20%');
  const [searchQuery, setSearchQuery] = useState('');

  const datasets = [
    { name: 'FinancialTimeSeries_V1', size: '1.2 GB', lastUpdated: '2023-11-20', status: 'Ready' },
    { name: 'MarketSentiment_V1', size: '850 MB', lastUpdated: '2023-11-18', status: 'Processing' },
    { name: 'AlternativeData_V3', size: '2.1 GB', lastUpdated: '2023-11-15', status: 'Error' },
    { name: 'TechnicalIndicators_V2', size: '650 MB', lastUpdated: '2023-11-12', status: 'Ready' },
  ];

  const trainingProgress = {
    epochsCompleted: 75,
    totalEpochs: 100,
    accuracy: 88.0,
    loss: 0.12,
  };

  const features = [
    { name: 'Volume', importance: 95 },
    { name: 'Change', importance: 82 },
    { name: 'RSIDivergence', importance: 75 },
    { name: 'MACDCrossover', importance: 68 },
    { name: 'VIXProximity', importance: 55 },
    { name: 'Market Regime', importance: 48 },
    { name: 'Historical Volatility', importance: 42 },
  ];

  const performanceMetrics = {
    accuracy: 92.5,
    precision: 88.1,
    recall: 90.3,
    f1Score: 89.2,
    confusionMatrix: {
      truePositive: 850,
      falseNegative: 50,
      falsePositive: 70,
      trueNegative: 930,
    },
  };

  const modelComparison = [
    { model: 'XGBoost_V1', accuracy: 92.5, precision: 88.1, recall: 90.3, f1Score: 89.2, trainingTime: '15m', datasetSize: '1.2 GB' },
    { model: 'RandomForest_V2', accuracy: 89.3, precision: 85.2, recall: 87.8, f1Score: 86.5, trainingTime: '22m', datasetSize: '1.2 GB' },
    { model: 'NeuralNet_V3', accuracy: 91.0, precision: 87.5, recall: 89.1, f1Score: 88.3, trainingTime: '45m', datasetSize: '1.2 GB' },
  ];

  const trainingHistory = [
    { runId: 'MT-001', modelName: 'XGBoost_V1', dataset: 'FinancialTimeSeries_V1', algorithm: 'XGBoost', startTime: '2023-12-10 10:00', endTime: '2023-12-10 10:15', status: 'Completed', accuracy: '92.5%', loss: '0.22' },
    { runId: 'MT-002', modelName: 'RandomForest_V2', dataset: 'FinancialTimeSeries_V1', algorithm: 'Random Forest', startTime: '2023-12-09 14:30', endTime: '2023-12-09 14:52', status: 'Completed', accuracy: '89.3%', loss: '0.28' },
    { runId: 'MT-003', modelName: 'NeuralNet_V3', dataset: 'FinancialTimeSeries_V1', algorithm: 'Neural Network', startTime: '2023-12-08 09:15', endTime: '2023-12-08 10:00', status: 'Completed', accuracy: '91.0%', loss: '0.25' },
    { runId: 'MT-004', modelName: 'XGBoost_V2', dataset: 'AlternativeData_V3', algorithm: 'XGBoost', startTime: '2023-12-07 11:00', endTime: '2023-12-07 11:05', status: 'Failed', accuracy: 'N/A', loss: '0.45' },
    { runId: 'MT-005', modelName: 'Ensemble_V1', dataset: 'MarketSentiment_V1', algorithm: 'Ensemble', startTime: '2023-12-06 16:00', endTime: '2023-12-06 16:10', status: 'Running', accuracy: '75.0%', loss: '0.35' },
  ];

  const getStatusColor = (status) => {
    switch (status) {
      case 'Ready':
      case 'Completed':
        return 'text-green-600 dark:text-green-400';
      case 'Processing':
      case 'Running':
        return 'text-blue-600 dark:text-blue-400';
      case 'Error':
      case 'Failed':
        return 'text-red-600 dark:text-red-400';
      default:
        return 'text-gray-600 dark:text-gray-400';
    }
  };

  const getStatusBg = (status) => {
    switch (status) {
      case 'Ready':
      case 'Completed':
        return 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300';
      case 'Processing':
      case 'Running':
        return 'bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300';
      case 'Error':
      case 'Failed':
        return 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-300';
      default:
        return 'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-300';
    }
  };

  return (
    <div className="p-6 space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Model Training & Metrics</h1>
        <p className="text-gray-600 dark:text-gray-400 mt-1">Train and evaluate machine learning models with comprehensive metrics tracking</p>
      </div>

      {/* Dataset Management */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">Dataset Management</h2>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Manage and oversee the datasets used for training your machine learning models. Ensure data quality and availability for optimal model performance.
          </p>
        </div>
        <div className="p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex-1 max-w-md relative">
              <FontAwesomeIcon icon={faSearch} className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                placeholder="Search datasets..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <button className="ml-4 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors flex items-center gap-2">
              <FontAwesomeIcon icon={faUpload} />
              Upload New Dataset
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 dark:bg-gray-900/50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Dataset Name</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Size</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Last Updated</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Status</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {datasets.map((dataset, index) => (
                  <tr key={index} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                    <td className="px-6 py-4 text-sm font-medium text-gray-900 dark:text-white">{dataset.name}</td>
                    <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-400">{dataset.size}</td>
                    <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-400">{dataset.lastUpdated}</td>
                    <td className="px-6 py-4 text-sm">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusBg(dataset.status)}`}>
                        {dataset.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm">
                      <div className="flex items-center gap-3">
                        <button className="text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors">
                          <FontAwesomeIcon icon={faEye} />
                        </button>
                        <button 
                          className={`transition-colors ${
                            dataset.status === 'Ready' 
                              ? 'text-gray-400 hover:text-green-600 dark:hover:text-green-400' 
                              : 'text-gray-300 dark:text-gray-600 cursor-not-allowed'
                          }`}
                          disabled={dataset.status !== 'Ready'}
                        >
                          <FontAwesomeIcon icon={faDownload} />
                        </button>
                        <button 
                          className={`transition-colors ${
                            dataset.status === 'Ready' 
                              ? 'text-gray-400 hover:text-red-600 dark:hover:text-red-400' 
                              : 'text-gray-300 dark:text-gray-600 cursor-not-allowed'
                          }`}
                          disabled={dataset.status !== 'Ready'}
                        >
                          <FontAwesomeIcon icon={faTrash} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Training Controls - 3 Column Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Training Run Configuration */}
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Training Run Configuration</h3>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Model Name</label>
              <input
                type="text"
                value={modelName}
                onChange={(e) => setModelName(e.target.value)}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Dataset Source</label>
              <select
                value={datasetSource}
                onChange={(e) => setDatasetSource(e.target.value)}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              >
                <option>FinancialTimeSeries_V1</option>
                <option>MarketSentiment_V1</option>
                <option>AlternativeData_V3</option>
                <option>TechnicalIndicators_V2</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Algorithm</label>
              <select
                value={algorithm}
                onChange={(e) => setAlgorithm(e.target.value)}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              >
                <option>XGBoost</option>
                <option>Random Forest</option>
                <option>Neural Network</option>
                <option>Ensemble</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Epochs</label>
              <input
                type="number"
                value={epochs}
                onChange={(e) => setEpochs(Number(e.target.value))}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Validation Split</label>
              <input
                type="text"
                value={validationSplit}
                onChange={(e) => setValidationSplit(e.target.value)}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div className="pt-2 space-y-2">
              <button className="w-full py-2 px-4 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors flex items-center justify-center gap-2">
                <FontAwesomeIcon icon={faPlay} />
                Start Training
              </button>
              <button className="w-full py-2 px-4 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-lg font-medium transition-colors flex items-center justify-center gap-2">
                <FontAwesomeIcon icon={faSave} />
                Save Configuration
              </button>
            </div>
          </div>
        </div>

        {/* Real-time Training Progress */}
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Real-time Training Progress</h3>
          <div className="space-y-4">
            <div>
              <div className="flex justify-between text-sm mb-2">
                <span className="text-gray-600 dark:text-gray-400">Epochs Completed</span>
                <span className="font-medium text-gray-900 dark:text-white">
                  {trainingProgress.epochsCompleted}/{trainingProgress.totalEpochs}
                </span>
              </div>
              <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2.5">
                <div 
                  className="bg-blue-600 h-2.5 rounded-full transition-all"
                  style={{ width: `${(trainingProgress.epochsCompleted / trainingProgress.totalEpochs) * 100}%` }}
                />
              </div>
            </div>
            <div>
              <div className="flex justify-between text-sm mb-2">
                <span className="text-gray-600 dark:text-gray-400">Accuracy</span>
                <span className="font-medium text-gray-900 dark:text-white">{trainingProgress.accuracy}%</span>
              </div>
              <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2.5">
                <div 
                  className="bg-green-600 h-2.5 rounded-full transition-all"
                  style={{ width: `${trainingProgress.accuracy}%` }}
                />
              </div>
            </div>
            <div>
              <div className="flex justify-between text-sm mb-2">
                <span className="text-gray-600 dark:text-gray-400">Loss</span>
                <span className="font-medium text-gray-900 dark:text-white">{trainingProgress.loss}</span>
              </div>
              <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2.5">
                <div 
                  className="bg-red-600 h-2.5 rounded-full transition-all"
                  style={{ width: `${(1 - trainingProgress.loss) * 100}%` }}
                />
              </div>
            </div>
            {/* Simple Line Chart Placeholder */}
            <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
              <div className="h-32 bg-gray-50 dark:bg-gray-900 rounded border border-gray-200 dark:border-gray-700 flex items-center justify-center">
                <div className="text-center">
                  <FontAwesomeIcon icon={faChartLine} className="text-4xl text-gray-400 dark:text-gray-600 mb-2" />
                  <p className="text-xs text-gray-500 dark:text-gray-400">Training Progress Chart</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Model Deployment */}
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">Model Deployment</h3>
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
            Deploy your trained models to production environments for live trading or paper trading simulations.
          </p>
          <div className="space-y-3 mb-4">
            <div className="flex items-center gap-2 text-green-600 dark:text-green-400">
              <FontAwesomeIcon icon={faCheckCircle} />
              <span className="text-sm font-medium">Model 'XGBoost_V1' Ready</span>
            </div>
            <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
              <span>Deployment Status:</span>
              <span className="font-medium text-green-600 dark:text-green-400 flex items-center gap-1">
                Live
                <FontAwesomeIcon icon={faArrowTrendUp} className="text-xs" />
              </span>
            </div>
            <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
              <span>API Endpoint:</span>
              <span className="font-mono text-xs text-gray-500 dark:text-gray-500 flex items-center gap-1">
                https://api...
                <FontAwesomeIcon icon={faArrowTrendUp} className="text-xs" />
              </span>
            </div>
          </div>
          <div className="pt-4 space-y-2">
            <button className="w-full py-2 px-4 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium transition-colors flex items-center justify-center gap-2">
              <FontAwesomeIcon icon={faRocket} />
              Deploy Model
            </button>
            <button className="w-full py-2 px-4 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-lg font-medium transition-colors flex items-center justify-center gap-2">
              <FontAwesomeIcon icon={faChartLine} />
              Monitor Live
            </button>
          </div>
        </div>
      </div>

      {/* Feature Importance Analysis */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">Feature Importance Analysis</h3>
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
          Understand which features are most influential in your model's decision-making process.
        </p>
        <div className="space-y-3">
          {features.map((feature, index) => (
            <div key={index} className="flex items-center gap-4">
              <div className="w-32 text-sm text-gray-600 dark:text-gray-400">{feature.name}</div>
              <div className="flex-1 bg-gray-200 dark:bg-gray-700 rounded-full h-6 relative">
                <div 
                  className="bg-blue-600 h-6 rounded-full flex items-center justify-end pr-2"
                  style={{ width: `${feature.importance}%` }}
                >
                  <span className="text-xs text-white font-medium">{feature.importance}%</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Model Performance Breakdown */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">Model Performance Breakdown</h3>
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
          Detailed breakdown of the selected model's performance metrics.
        </p>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Metrics Table */}
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 dark:bg-gray-900/50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Metric</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Value</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                <tr>
                  <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">Accuracy</td>
                  <td className="px-4 py-3 text-sm font-medium text-gray-900 dark:text-white bg-gray-50 dark:bg-gray-900">{performanceMetrics.accuracy}%</td>
                </tr>
                <tr>
                  <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">Precision</td>
                  <td className="px-4 py-3 text-sm font-medium text-gray-900 dark:text-white bg-gray-50 dark:bg-gray-900">{performanceMetrics.precision}%</td>
                </tr>
                <tr>
                  <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">Recall</td>
                  <td className="px-4 py-3 text-sm font-medium text-gray-900 dark:text-white bg-gray-50 dark:bg-gray-900">{performanceMetrics.recall}%</td>
                </tr>
                <tr>
                  <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">F1-Score</td>
                  <td className="px-4 py-3 text-sm font-medium text-gray-900 dark:text-white bg-gray-50 dark:bg-gray-900">{performanceMetrics.f1Score}%</td>
                </tr>
              </tbody>
            </table>
          </div>
          {/* Confusion Matrix */}
          <div>
            <div className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">Confusion Matrix</div>
            <div className="grid grid-cols-2 gap-2">
              <div className="bg-green-100 dark:bg-green-900/30 p-4 rounded-lg text-center border-2 border-green-300 dark:border-green-700">
                <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">True Positive</div>
                <div className="text-xl font-bold text-green-700 dark:text-green-300">{performanceMetrics.confusionMatrix.truePositive}</div>
              </div>
              <div className="bg-red-100 dark:bg-red-900/30 p-4 rounded-lg text-center border-2 border-red-300 dark:border-red-700">
                <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">False Negative</div>
                <div className="text-xl font-bold text-red-700 dark:text-red-300">{performanceMetrics.confusionMatrix.falseNegative}</div>
              </div>
              <div className="bg-red-100 dark:bg-red-900/30 p-4 rounded-lg text-center border-2 border-red-300 dark:border-red-700">
                <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">False Positive</div>
                <div className="text-xl font-bold text-red-700 dark:text-red-300">{performanceMetrics.confusionMatrix.falsePositive}</div>
              </div>
              <div className="bg-green-100 dark:bg-green-900/30 p-4 rounded-lg text-center border-2 border-green-300 dark:border-green-700">
                <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">True Negative</div>
                <div className="text-xl font-bold text-green-700 dark:text-green-300">{performanceMetrics.confusionMatrix.trueNegative}</div>
              </div>
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400 mt-2 text-center">Actual (Predicted)</div>
          </div>
        </div>
      </div>

      {/* Model Comparison */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">Model Comparison</h3>
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
          Compare different model versions or training runs side-by-side.
        </p>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 dark:bg-gray-900/50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Model</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Accuracy</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Precision</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Recall</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">F1-Score</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Training Time</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Dataset Size</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {modelComparison.map((model, index) => (
                <tr key={index} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                  <td className="px-4 py-3 text-sm font-medium text-gray-900 dark:text-white">{model.model}</td>
                  <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">{model.accuracy}%</td>
                  <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">{model.precision}%</td>
                  <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">{model.recall}%</td>
                  <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">{model.f1Score}%</td>
                  <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">{model.trainingTime}</td>
                  <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">{model.datasetSize}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        </div>

      {/* Training History & Metrics */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">Training History & Metrics</h3>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Review historical training runs and their key performance indicators.
          </p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 dark:bg-gray-900/50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Run ID</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Model Name</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Dataset</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Algorithm</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Start Time</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">End Time</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Status</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Accuracy</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Loss</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {trainingHistory.map((run, index) => (
                <tr key={index} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                  <td className="px-4 py-3 text-sm font-medium text-gray-900 dark:text-white">{run.runId}</td>
                  <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">{run.modelName}</td>
                  <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">{run.dataset}</td>
                  <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">{run.algorithm}</td>
                  <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">{run.startTime}</td>
                  <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">{run.endTime}</td>
                  <td className="px-4 py-3 text-sm">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusBg(run.status)}`}>
                      {run.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">{run.accuracy}</td>
                  <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">{run.loss}</td>
                  <td className="px-4 py-3 text-sm">
                    <button className="text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors">
                      <FontAwesomeIcon icon={faEye} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
