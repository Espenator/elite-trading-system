import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import { initAuthFromElectron } from './config/api';
import './index.css';

// Load auth token from Electron preload bridge if running in desktop app
initAuthFromElectron();

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
