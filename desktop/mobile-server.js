/**
 * Mobile Server — serves the iPhone PWA over local Wi-Fi.
 *
 * - Starts a lightweight HTTP server on port 8765 (configurable)
 * - Serves everything under desktop/mobile/ as static files
 * - Proxies /api/* calls to the FastAPI backend
 * - Displays QR code + URL in the Electron tray tooltip & notification
 * - Requires no internet — works purely on local network
 */

const http = require('http');
const https = require('https');
const fs = require('fs');
const path = require('path');
const os = require('os');

const log = {
  info: (...a) => console.log('[MobileServer]', ...a),
  warn: (...a) => console.warn('[MobileServer]', ...a),
  error: (...a) => console.error('[MobileServer]', ...a),
};

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js':   'application/javascript',
  '.css':  'text/css',
  '.json': 'application/json',
  '.png':  'image/png',
  '.ico':  'image/x-icon',
  '.svg':  'image/svg+xml',
  '.webmanifest': 'application/manifest+json',
};

class MobileServer {
  constructor(options = {}) {
    this._port      = options.port      || parseInt(process.env.MOBILE_SERVER_PORT || '8765');
    this._backendPort = options.backendPort || 8000;
    this._staticDir = options.staticDir || path.join(__dirname, 'mobile');
    this._server    = null;
    this._started   = false;
    this._localIp   = null;
  }

  /** Get primary LAN IPv4 address. */
  _getLanIp() {
    const ifaces = os.networkInterfaces();
    for (const name of Object.keys(ifaces)) {
      for (const iface of ifaces[name]) {
        if (iface.family === 'IPv4' && !iface.internal) {
          return iface.address;
        }
      }
    }
    return '127.0.0.1';
  }

  /** Start the HTTP server. */
  async start() {
    if (this._started) return this.getUrl();

    this._localIp = this._getLanIp();

    this._server = http.createServer((req, res) => {
      this._handleRequest(req, res);
    });

    await new Promise((resolve, reject) => {
      this._server.listen(this._port, '0.0.0.0', () => {
        this._started = true;
        log.info(`Mobile PWA server started at ${this.getUrl()}`);
        resolve();
      });
      this._server.on('error', (err) => {
        if (err.code === 'EADDRINUSE') {
          log.warn(`Port ${this._port} in use, trying ${this._port + 1}`);
          this._port += 1;
          this._server.listen(this._port, '0.0.0.0', () => {
            this._started = true;
            resolve();
          });
        } else {
          reject(err);
        }
      });
    });

    return this.getUrl();
  }

  /** Handle each incoming request. */
  _handleRequest(req, res) {
    const url = new URL(req.url, `http://${req.headers.host}`);

    // CORS preflight
    if (req.method === 'OPTIONS') {
      res.writeHead(204, this._corsHeaders(req));
      res.end();
      return;
    }

    // Proxy all /api/* requests to the FastAPI backend (requires Bearer token)
    if (url.pathname.startsWith('/api/')) {
      const authHeader = req.headers.authorization || '';
      if (!authHeader.startsWith('Bearer ')) {
        res.writeHead(401, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'Authorization required' }));
        return;
      }
      this._proxyToBackend(req, res);
      return;
    }

    // Serve static files
    let filePath = path.join(this._staticDir, url.pathname === '/' ? 'index.html' : url.pathname);

    // Security: prevent path traversal
    if (!filePath.startsWith(this._staticDir)) {
      res.writeHead(403);
      res.end('Forbidden');
      return;
    }

    if (!fs.existsSync(filePath)) {
      // SPA fallback — serve index.html for unknown paths
      filePath = path.join(this._staticDir, 'index.html');
    }

    try {
      const ext  = path.extname(filePath);
      const mime = MIME[ext] || 'application/octet-stream';
      const data = fs.readFileSync(filePath);

      res.writeHead(200, {
        'Content-Type': mime,
        'Cache-Control': ext === '.html' ? 'no-cache' : 'max-age=3600',
      });
      res.end(data);
    } catch (err) {
      res.writeHead(500);
      res.end('Server error: ' + err.message);
    }
  }

  /** Build CORS headers scoped to the LAN origin. */
  _corsHeaders(req) {
    const origin = req.headers.origin || `http://${this._localIp}:${this._port}`;
    return {
      'Access-Control-Allow-Origin': origin,
      'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
      'Access-Control-Allow-Headers': 'Authorization, Content-Type',
      'Access-Control-Max-Age': '86400',
    };
  }

  /** Proxy a request to the FastAPI backend. */
  _proxyToBackend(req, res) {
    const options = {
      hostname: '127.0.0.1',
      port: this._backendPort,
      path: req.url,
      method: req.method,
      headers: { ...req.headers, host: `127.0.0.1:${this._backendPort}` },
    };

    const proxy = http.request(options, (backendRes) => {
      res.writeHead(backendRes.statusCode, {
        ...backendRes.headers,
        ...this._corsHeaders(req),
      });
      backendRes.pipe(res, { end: true });
    });

    proxy.on('error', (err) => {
      log.error('Proxy error:', err.message);
      res.writeHead(502);
      res.end(JSON.stringify({ error: 'Backend unreachable', detail: err.message }));
    });

    req.pipe(proxy, { end: true });
  }

  /** Get the URL the phone should open. */
  getUrl() {
    return `http://${this._localIp}:${this._port}`;
  }

  /** Returns whether the server is running. */
  isRunning() {
    return this._started;
  }

  /** Get connection info for QR display. */
  getConnectionInfo() {
    return {
      url:     this.getUrl(),
      ip:      this._localIp,
      port:    this._port,
      running: this._started,
    };
  }

  /** Stop the server gracefully. */
  async stop() {
    if (!this._server) return;
    return new Promise((resolve) => {
      this._server.close(() => {
        this._started = false;
        log.info('Mobile server stopped');
        resolve();
      });
    });
  }
}

const mobileServer = new MobileServer();
module.exports = { mobileServer, MobileServer };
