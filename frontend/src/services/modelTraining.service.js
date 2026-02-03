/**
 * Model Training API service.
 * Calls backend /api/v1/training endpoints for datasets, runs, progress, and metrics.
 */
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001/api/v1';

class ModelTrainingService {
  async getDatasets() {
    const response = await fetch(`${API_BASE_URL}/training/datasets`);
    if (!response.ok) throw new Error(`API Error: ${response.status} ${response.statusText}`);
    return response.json();
  }

  async getTrainingRuns() {
    const response = await fetch(`${API_BASE_URL}/training/runs`);
    if (!response.ok) throw new Error(`API Error: ${response.status} ${response.statusText}`);
    return response.json();
  }

  async getActiveProgress() {
    const response = await fetch(`${API_BASE_URL}/training/runs/active/progress`);
    if (!response.ok) throw new Error(`API Error: ${response.status} ${response.statusText}`);
    return response.json();
  }

  async getRunDetails(runId) {
    const response = await fetch(`${API_BASE_URL}/training/runs/${encodeURIComponent(runId)}`);
    if (!response.ok) throw new Error(`API Error: ${response.status} ${response.statusText}`);
    return response.json();
  }

  async startTraining({ modelName, datasetSource, algorithm, epochs, validationSplit }) {
    const response = await fetch(`${API_BASE_URL}/training/runs`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        modelName,
        datasetSource,
        algorithm,
        epochs: Number(epochs) || 100,
        validationSplit: validationSplit || '20%',
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || `API Error: ${response.status}`);
    return data;
  }

  async stopTraining(runId) {
    const response = await fetch(`${API_BASE_URL}/training/runs/${encodeURIComponent(runId)}/stop`, {
      method: 'POST',
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || `API Error: ${response.status}`);
    return data;
  }

  async getModelComparison() {
    const response = await fetch(`${API_BASE_URL}/training/models/compare`);
    if (!response.ok) throw new Error(`API Error: ${response.status} ${response.statusText}`);
    return response.json();
  }

  async saveConfig({ modelName, datasetSource, algorithm, epochs, validationSplit }) {
    const response = await fetch(`${API_BASE_URL}/training/config`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        modelName,
        datasetSource,
        algorithm,
        epochs: Number(epochs) || 100,
        validationSplit: validationSplit || '20%',
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || `API Error: ${response.status}`);
    return data;
  }

  async deployModel() {
    const response = await fetch(`${API_BASE_URL}/training/deploy`, { method: 'POST' });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || `API Error: ${response.status}`);
    return data;
  }
}

export const modelTrainingService = new ModelTrainingService();
export default modelTrainingService;
