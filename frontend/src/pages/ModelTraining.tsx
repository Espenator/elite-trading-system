import React, { useState, useEffect, useRef, useMemo } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { 
  faUpload, faSearch, faEye, faDownload, faTrash,
  faPlay, faSave, faRocket, faChartLine, faCheckCircle,
  faArrowTrendUp, faSpinner, faStopCircle
} from '@fortawesome/free-solid-svg-icons';
import modelTrainingService from '../services/modelTraining.service';

interface Dataset {
  name: string;
  size: string;
  lastUpdated: string;
  status: 'Ready' | 'Processing' | 'Error';
}

interface TrainingProgress {
  epochsCompleted: number;
  totalEpochs: number;
  accuracy: number;
  loss: number;
}

interface Feature {
  name: string;
  importance: number;
}

interface PerformanceMetrics {
  accuracy: number;
  precision: number;
  recall: number;
  f1Score: number;
  confusionMatrix: {
    truePositive: number;
    falseNegative: number;
    falsePositive: number;
    trueNegative: number;
  };
}

interface ModelComparison {
  model: string;
  accuracy: number;
  precision: number;
  recall: number;
  f1Score: number;
  trainingTime: string;
  datasetSize: string;
}

interface TrainingHistory {
  runId: string;
  modelName: string;
  dataset: string;
  algorithm: string;
  startTime: string;
  endTime: string;
  status: 'Completed' | 'Failed' | 'Running';
  accuracy: string;
  loss: string;
}

export default function ModelTraining() {
  const [modelName, setModelName] = useState('XGBoost_V1_Financial');
  const [datasetSource, setDatasetSource] = useState('FinancialTimeSeries_V1');
  const [algorithm, setAlgorithm] = useState('XGBoost');
  const [epochs, setEpochs] = useState(100);
  const [validationSplit, setValidationSplit] = useState('20%');
  const [searchQuery, setSearchQuery] = useState('');

  const [datasets, setDatasets] = useState([] as Dataset[]);
  const [trainingHistory, setTrainingHistory] = useState([] as TrainingHistory[]);
  const [modelComparison, setModelComparison] = useState([] as ModelComparison[]);
  const [activeProgress, setActiveProgress] = useState(null as { active: boolean; progress: TrainingProgress | null; runId?: string } | null);
  const [selectedRunId, setSelectedRunId] = useState(null as string | null);
  const [runDetails, setRunDetails] = useState(null as { performanceMetrics: PerformanceMetrics; featureImportance: Feature[] } | null);

  const [loading, setLoading] = useState({ datasets: true, runs: true, comparison: true });
  const [error, setError] = useState(null as string | null);
  const [actionLoading, setActionLoading] = useState(null as 'train' | 'save' | 'deploy' | 'stop' | null);
  const [actionMessage, setActionMessage] = useState(null as { type: 'success' | 'error'; text: string } | null);
  const progressPollRef = useRef(null as ReturnType<typeof setInterval> | null);

  const trainingProgress: TrainingProgress = activeProgress?.progress ?? {
    epochsCompleted: 0,
    totalEpochs: epochs,
    accuracy: 0,
    loss: 0,
  };

  const features: Feature[] = runDetails?.featureImportance ?? [];
  const performanceMetrics: PerformanceMetrics = runDetails?.performanceMetrics ?? {
    accuracy: 0,
    precision: 0,
    recall: 0,
    f1Score: 0,
    confusionMatrix: { truePositive: 0, falseNegative: 0, falsePositive: 0, trueNegative: 0 },
  };

  const filteredDatasets = useMemo(() => {
    if (!searchQuery.trim()) return datasets;
    const q = searchQuery.toLowerCase();
    return datasets.filter((d) => d.name.toLowerCase().includes(q));
  }, [datasets, searchQuery]);

  useEffect(() => {
    let cancelled = false;
    async function fetchInitial() {
      setError(null);
      try {
        const [ds, runs, comparison] = await Promise.all([
          modelTrainingService.getDatasets(),
          modelTrainingService.getTrainingRuns(),
          modelTrainingService.getModelComparison(),
        ]);
        if (!cancelled) {
          setDatasets(ds);
          setTrainingHistory(runs);
          setModelComparison(comparison);
          if (runs.length > 0 && !selectedRunId) setSelectedRunId(runs[0].runId);
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Failed to load data');
      } finally {
        if (!cancelled) setLoading({ datasets: false, runs: false, comparison: false });
      }
    }
    fetchInitial();
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function fetchProgress() {
      try {
        const res = await modelTrainingService.getActiveProgress();
        if (!cancelled) setActiveProgress(res);
      } catch {
        if (!cancelled) setActiveProgress({ active: false, progress: null });
      }
    }
    fetchProgress();
    const id = setInterval(fetchProgress, 2000);
    progressPollRef.current = id;
    return () => {
      cancelled = true;
      if (progressPollRef.current) clearInterval(progressPollRef.current);
    };
  }, []);

  useEffect(() => {
    if (!selectedRunId) {
      setRunDetails(null);
      return;
    }
    let cancelled = false;
    modelTrainingService.getRunDetails(selectedRunId).then((data) => {
      if (!cancelled)
        setRunDetails({
          performanceMetrics: data.performanceMetrics ?? {
            accuracy: 0, precision: 0, recall: 0, f1Score: 0,
            confusionMatrix: { truePositive: 0, falseNegative: 0, falsePositive: 0, trueNegative: 0 },
          },
          featureImportance: data.featureImportance ?? [],
        });
    }).catch(() => {
      if (!cancelled) setRunDetails(null);
    });
    return () => { cancelled = true; };
  }, [selectedRunId]);

  const handleStartTraining = async () => {
    setActionLoading('train');
    setActionMessage(null);
    try {
      await modelTrainingService.startTraining({
        modelName,
        datasetSource,
        algorithm,
        epochs,
        validationSplit,
      });
      setActionMessage({ type: 'success', text: 'Training started. Progress will update below.' });
      const res = await modelTrainingService.getActiveProgress();
      setActiveProgress(res);
      setTrainingHistory(await modelTrainingService.getTrainingRuns());
    } catch (e) {
      setActionMessage({ type: 'error', text: e instanceof Error ? e.message : 'Failed to start training' });
    } finally {
      setActionLoading(null);
    }
  };

  const handleStopTraining = async () => {
    if (!activeProgress?.runId) return;
    setActionLoading('stop');
    setActionMessage(null);
    try {
      await modelTrainingService.stopTraining(activeProgress.runId);
      setActionMessage({ type: 'success', text: 'Training stopped.' });
      setActiveProgress({ active: false, progress: null });
      setTrainingHistory(await modelTrainingService.getTrainingRuns());
    } catch (e) {
      setActionMessage({ type: 'error', text: e instanceof Error ? e.message : 'Failed to stop training' });
    } finally {
      setActionLoading(null);
    }
  };

  const handleSaveConfig = async () => {
    setActionLoading('save');
    setActionMessage(null);
    try {
      await modelTrainingService.saveConfig({
        modelName,
        datasetSource,
        algorithm,
        epochs,
        validationSplit,
      });
      setActionMessage({ type: 'success', text: 'Configuration saved.' });
    } catch (e) {
      setActionMessage({ type: 'error', text: e instanceof Error ? e.message : 'Failed to save config' });
    } finally {
      setActionLoading(null);
    }
  };

  const handleDeploy = async () => {
    setActionLoading('deploy');
    setActionMessage(null);
    try {
      const res = await modelTrainingService.deployModel();
      setActionMessage({ type: 'success', text: res.message || 'Deployment requested.' });
    } catch (e) {
      setActionMessage({ type: 'error', text: e instanceof Error ? e.message : 'Deployment failed' });
    } finally {
      setActionLoading(null);
    }
  };

  const getStatusBg = (status: string): string => {
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

      {/* Error / Action messages */}
      {error && (
        <div className="p-4 rounded-lg bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-300 text-sm">
          {error}
        </div>
      )}
      {actionMessage && (
        <div className={`p-4 rounded-lg text-sm ${actionMessage.type === 'success' ? 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300' : 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-300'}`}>
          {actionMessage.text}
        </div>
      )}

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
            {loading.datasets ? (
              <div className="flex items-center justify-center py-12 text-gray-500 dark:text-gray-400">
                <FontAwesomeIcon icon={faSpinner} spin className="mr-2" /> Loading datasets...
              </div>
            ) : (
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
                {filteredDatasets.map((dataset, index) => (
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
            )}
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
                {datasets.map((d) => (
                  <option key={d.name} value={d.name}>{d.name}</option>
                ))}
                {datasets.length === 0 && <option value={datasetSource}>{datasetSource}</option>}
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
              <button
                onClick={handleStartTraining}
                disabled={!!activeProgress?.active || actionLoading === 'train'}
                className="w-full py-2 px-4 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-colors flex items-center justify-center gap-2"
              >
                {actionLoading === 'train' ? <FontAwesomeIcon icon={faSpinner} spin /> : <FontAwesomeIcon icon={faPlay} />}
                {actionLoading === 'train' ? 'Starting...' : 'Start Training'}
              </button>
              <button
                onClick={handleSaveConfig}
                disabled={!!actionLoading}
                className="w-full py-2 px-4 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-lg font-medium transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
              >
                {actionLoading === 'save' ? <FontAwesomeIcon icon={faSpinner} spin /> : <FontAwesomeIcon icon={faSave} />}
                Save Configuration
              </button>
            </div>
          </div>
        </div>

        {/* Real-time Training Progress */}
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Real-time Training Progress</h3>
          {activeProgress?.active ? (
            <>
              <div className="flex items-center justify-between mb-4">
                <span className="text-sm text-gray-600 dark:text-gray-400">Run: {activeProgress.runId}</span>
                <button
                  onClick={handleStopTraining}
                  disabled={actionLoading === 'stop'}
                  className="px-3 py-1.5 text-sm bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white rounded-lg flex items-center gap-2"
                >
                  {actionLoading === 'stop' ? <FontAwesomeIcon icon={faSpinner} spin /> : <FontAwesomeIcon icon={faStopCircle} />}
                  Stop
                </button>
              </div>
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
                      style={{ width: `${trainingProgress.totalEpochs ? (trainingProgress.epochsCompleted / trainingProgress.totalEpochs) * 100 : 0}%` }}
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
                      style={{ width: `${Math.min(100, trainingProgress.accuracy)}%` }}
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
                      style={{ width: `${Math.min(100, (1 - trainingProgress.loss) * 100)}%` }}
                    />
                  </div>
                </div>
              </div>
            </>
          ) : (
            <div className="space-y-4">
              <p className="text-sm text-gray-500 dark:text-gray-400">No active training run. Start a run from the configuration panel.</p>
              <div className="flex justify-between text-sm text-gray-500 dark:text-gray-400">
                <span>Epochs</span>
                <span>0/{epochs}</span>
              </div>
              <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2.5">
                <div className="bg-gray-400 dark:bg-gray-600 h-2.5 rounded-full" style={{ width: '0%' }} />
              </div>
            </div>
          )}
          <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
            <div className="h-32 bg-gray-50 dark:bg-gray-900 rounded border border-gray-200 dark:border-gray-700 flex items-center justify-center">
              <div className="text-center">
                <FontAwesomeIcon icon={faChartLine} className="text-4xl text-gray-400 dark:text-gray-600 mb-2" />
                <p className="text-xs text-gray-500 dark:text-gray-400">Training Progress Chart</p>
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
            <button
              onClick={handleDeploy}
              disabled={!!actionLoading}
              className="w-full py-2 px-4 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white rounded-lg font-medium transition-colors flex items-center justify-center gap-2"
            >
              {actionLoading === 'deploy' ? <FontAwesomeIcon icon={faSpinner} spin /> : <FontAwesomeIcon icon={faRocket} />}
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
          Understand which features are most influential in your model's decision-making process. Select a run from Training History to view.
        </p>
        {!selectedRunId && (
          <p className="text-sm text-gray-500 dark:text-gray-400 py-4">Select a run from the table below to see feature importance.</p>
        )}
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
          Detailed breakdown of the selected model's performance metrics. {selectedRunId ? `Showing run ${selectedRunId}.` : 'Select a run from Training History to view metrics.'}
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
        {loading.comparison ? (
          <div className="flex items-center justify-center py-8 text-gray-500 dark:text-gray-400">
            <FontAwesomeIcon icon={faSpinner} spin className="mr-2" /> Loading...
          </div>
        ) : (
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
        )}
        </div>

      {/* Training History & Metrics */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">Training History & Metrics</h3>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Review historical training runs and their key performance indicators. Click View to see metrics for a run.
          </p>
        </div>
        {loading.runs ? (
          <div className="flex items-center justify-center py-12 text-gray-500 dark:text-gray-400">
            <FontAwesomeIcon icon={faSpinner} spin className="mr-2" /> Loading runs...
          </div>
        ) : (
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
                    <button
                      onClick={() => setSelectedRunId(run.runId)}
                      className={`transition-colors ${selectedRunId === run.runId ? 'text-blue-600 dark:text-blue-400' : 'text-gray-400 hover:text-blue-600 dark:hover:text-blue-400'}`}
                      title="View metrics"
                    >
                      <FontAwesomeIcon icon={faEye} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        )}
      </div>
    </div>
  );
}
