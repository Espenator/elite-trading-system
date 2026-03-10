/**
 * Ollama Fallback Manager (process/health only)
 *
 * CONTRACT: This module manages Ollama process lifecycle and health only.
 * Trading intelligence (signals, council, inference) is backend-managed:
 * backend calls brain_service (PC2) or backend-owned Ollama (PC1) via
 * app.services.brain_client / HyperSwarm / llm_router. Electron does NOT
 * implement trading logic; it only starts Ollama, checks /api/tags, and
 * reports status. The chat()/embed() methods exist for non-trading use
 * (e.g. local UI experiments) and must not be used for signal/council path.
 */

const { exec, spawn } = require('child_process');
const http = require('http');
const path = require('path');
const { app } = require('electron');

const log = {
    info: (...args) => console.log('[OllamaFallback]', ...args),
    warn: (...args) => console.warn('[OllamaFallback]', ...args),
    error: (...args) => console.error('[OllamaFallback]', ...args),
};

// Default configuration
const DEFAULT_CONFIG = {
    ollamaHost: 'http://127.0.0.1:11434',
    preferredModel: 'llama3.2',
    fallbackModel: 'mistral:7b',
    healthCheckInterval: 30000,
    requestTimeout: 120000,
    maxRetries: 3,
    autoStart: true,
};

class OllamaFallback {
    constructor(config = {}) {
        this._config = { ...DEFAULT_CONFIG, ...config };
        this._available = false;
        this._activeModel = null;
        this._ollamaProcess = null;
        this._healthTimer = null;
        this._stats = {
            requestsHandled: 0,
            errors: 0,
            avgResponseTime: 0,
        };
    }

    /**
     * Initialize Ollama fallback - check availability and warm up model.
     */
    async initialize() {
        log.info('Initializing Ollama fallback...');
        
        // Check if Ollama is already running
        const running = await this._isOllamaRunning();
        
        if (!running && this._config.autoStart) {
            log.info('Ollama not running, attempting to start...');
            await this._startOllama();
        }
        
        if (await this._isOllamaRunning()) {
            this._available = true;
            await this._selectModel();
            this._startHealthCheck();
            log.info(`Ollama fallback ready with model: ${this._activeModel}`);
        } else {
            log.warn('Ollama not available - fallback disabled');
            this._available = false;
        }
        
        return this._available;
    }

    /**
     * Check if Ollama server is running.
     */
    async _isOllamaRunning() {
        return new Promise((resolve) => {
            const url = new URL('/api/tags', this._config.ollamaHost);
            const req = http.get(url, { timeout: 5000 }, (res) => {
                resolve(res.statusCode === 200);
            });
            req.on('error', () => resolve(false));
            req.on('timeout', () => { req.destroy(); resolve(false); });
        });
    }

    /**
     * Attempt to start Ollama server.
     */
    async _startOllama() {
        return new Promise((resolve) => {
            try {
                const isWin = process.platform === 'win32';
                const cmd = isWin ? 'ollama' : '/usr/local/bin/ollama';
                
                this._ollamaProcess = spawn(cmd, ['serve'], {
                    detached: true,
                    stdio: 'ignore',
                });
                
                this._ollamaProcess.unref();
                
                // Wait for server to start
                setTimeout(async () => {
                    const running = await this._isOllamaRunning();
                    if (running) {
                        log.info('Ollama server started successfully');
                    } else {
                        log.warn('Ollama server failed to start');
                    }
                    resolve(running);
                }, 3000);
            } catch (err) {
                log.error('Failed to start Ollama:', err.message);
                resolve(false);
            }
        });
    }

    /**
     * Select the best available model.
     */
    async _selectModel() {
        try {
            const models = await this._listModels();
            const modelNames = models.map(m => m.name);
            
            if (modelNames.includes(this._config.preferredModel)) {
                this._activeModel = this._config.preferredModel;
            } else if (modelNames.includes(this._config.fallbackModel)) {
                this._activeModel = this._config.fallbackModel;
            } else if (models.length > 0) {
                this._activeModel = models[0].name;
                log.warn(`Using available model: ${this._activeModel}`);
            } else {
                log.warn('No models available, attempting to pull preferred model...');
                await this._pullModel(this._config.preferredModel);
                this._activeModel = this._config.preferredModel;
            }
        } catch (err) {
            log.error('Model selection failed:', err.message);
        }
    }

    /**
     * List available Ollama models.
     */
    async _listModels() {
        return new Promise((resolve, reject) => {
            const url = new URL('/api/tags', this._config.ollamaHost);
            const req = http.get(url, { timeout: 10000 }, (res) => {
                let data = '';
                res.on('data', chunk => data += chunk);
                res.on('end', () => {
                    try {
                        const parsed = JSON.parse(data);
                        resolve(parsed.models || []);
                    } catch { resolve([]); }
                });
            });
            req.on('error', (err) => reject(err));
            req.on('timeout', () => { req.destroy(); reject(new Error('Timeout')); });
        });
    }

    /**
     * Pull a model from Ollama registry.
     */
    async _pullModel(modelName) {
        return new Promise((resolve, reject) => {
            log.info(`Pulling model: ${modelName}...`);
            exec(`ollama pull ${modelName}`, { timeout: 600000 }, (err) => {
                if (err) {
                    log.error(`Failed to pull ${modelName}:`, err.message);
                    reject(err);
                } else {
                    log.info(`Model ${modelName} pulled successfully`);
                    resolve();
                }
            });
        });
    }

    /**
     * Send a chat completion request to Ollama.
     * This is the main API used by the brain service fallback.
     */
    async chat(messages, options = {}) {
        if (!this._available || !this._activeModel) {
            throw new Error('Ollama fallback not available');
        }

        const startTime = Date.now();
        const body = JSON.stringify({
            model: options.model || this._activeModel,
            messages,
            stream: false,
            options: {
                temperature: options.temperature || 0.7,
                num_predict: options.maxTokens || 2048,
            },
        });

        for (let attempt = 0; attempt < this._config.maxRetries; attempt++) {
            try {
                const result = await this._postRequest('/api/chat', body);
                const elapsed = Date.now() - startTime;
                this._updateStats(elapsed);
                return {
                    content: result.message?.content || '',
                    model: result.model,
                    totalDuration: result.total_duration,
                    promptTokens: result.prompt_eval_count,
                    completionTokens: result.eval_count,
                };
            } catch (err) {
                if (attempt === this._config.maxRetries - 1) {
                    this._stats.errors++;
                    throw err;
                }
                log.warn(`Chat attempt ${attempt + 1} failed, retrying...`);
                await this._delay(1000 * (attempt + 1));
            }
        }
    }

    /**
     * Generate embeddings via Ollama.
     */
    async embed(text, model = 'nomic-embed-text') {
        if (!this._available) {
            throw new Error('Ollama fallback not available');
        }

        const body = JSON.stringify({ model, prompt: text });
        const result = await this._postRequest('/api/embeddings', body);
        return result.embedding;
    }

    /**
     * HTTP POST helper.
     */
    async _postRequest(endpoint, body) {
        return new Promise((resolve, reject) => {
            const url = new URL(endpoint, this._config.ollamaHost);
            const options = {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                timeout: this._config.requestTimeout,
            };

            const req = http.request(url, options, (res) => {
                let data = '';
                res.on('data', chunk => data += chunk);
                res.on('end', () => {
                    try {
                        resolve(JSON.parse(data));
                    } catch (err) {
                        reject(new Error(`Invalid JSON response: ${data.substring(0, 100)}`));
                    }
                });
            });

            req.on('error', reject);
            req.on('timeout', () => { req.destroy(); reject(new Error('Request timeout')); });
            req.write(body);
            req.end();
        });
    }

    /**
     * Update performance stats.
     */
    _updateStats(elapsed) {
        this._stats.requestsHandled++;
        const n = this._stats.requestsHandled;
        this._stats.avgResponseTime = 
            ((this._stats.avgResponseTime * (n - 1)) + elapsed) / n;
    }

    /**
     * Start periodic health checks.
     */
    _startHealthCheck() {
        if (this._healthTimer) clearInterval(this._healthTimer);
        this._healthTimer = setInterval(async () => {
            const running = await this._isOllamaRunning();
            if (this._available && !running) {
                log.warn('Ollama became unavailable');
                this._available = false;
            } else if (!this._available && running) {
                log.info('Ollama recovered');
                this._available = true;
                await this._selectModel();
            }
        }, this._config.healthCheckInterval);
    }

    /**
     * Get current status.
     */
    getStatus() {
        return {
            available: this._available,
            activeModel: this._activeModel,
            stats: { ...this._stats },
        };
    }

    /**
     * Activate fallback (called by service-orchestrator when peer is lost).
     */
    async activate() {
        log.info('Activating Ollama fallback...');
        if (!this._available) {
            await this.initialize();
        }
    }

    /**
     * Deactivate fallback (called by service-orchestrator when peer recovers).
     */
    async deactivate() {
        log.info('Deactivating Ollama fallback...');
        if (this._healthTimer) {
            clearInterval(this._healthTimer);
            this._healthTimer = null;
        }
        this._available = false;
    }

    /**
     * Graceful shutdown.
     */
    async shutdown() {
        log.info('Shutting down Ollama fallback...');
        if (this._healthTimer) {
            clearInterval(this._healthTimer);
            this._healthTimer = null;
        }
        // Don't kill Ollama process - user may want it running
        this._available = false;
    }

    _delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

const ollamaFallback = new OllamaFallback();

module.exports = { ollamaFallback, OllamaFallback };