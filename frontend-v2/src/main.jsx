import React from 'react';
import ReactDOM from 'react-dom/client';

// Show loading indicator immediately — before any imports that could fail
const root = document.getElementById('root');
root.innerHTML = '<div style="color:#00D9FF;padding:2rem;font-family:monospace">Loading Embodier Trader...</div>';

// Wrap all imports in async IIFE so any crash is visible on screen (not silent blank page)
(async () => {
  try {
    const [{ default: App }, { initAuthFromElectron }] = await Promise.all([
      import('./App'),
      import('./config/api'),
    ]);
    await import('./index.css');

    // Load auth token from Electron preload bridge if running in desktop app
    initAuthFromElectron();

    ReactDOM.createRoot(root).render(
      <React.StrictMode>
        <App />
      </React.StrictMode>
    );
  } catch (err) {
    console.error('FATAL: App failed to load', err);
    root.innerHTML = `
      <div style="color:#EF4444;padding:2rem;font-family:monospace;max-width:800px">
        <h1 style="font-size:1.5rem;margin-bottom:1rem">Embodier Trader — Startup Error</h1>
        <pre style="white-space:pre-wrap;background:#1a1a2e;padding:1rem;border-radius:8px;font-size:0.85rem">${
          err?.stack || err?.message || String(err)
        }</pre>
        <button onclick="location.reload()" style="margin-top:1rem;padding:0.5rem 1rem;background:#00D9FF22;color:#00D9FF;border:1px solid #00D9FF44;border-radius:6px;cursor:pointer">
          Reload
        </button>
      </div>
    `;
  }
})();
