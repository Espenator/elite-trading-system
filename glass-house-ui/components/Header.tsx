'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useStore } from '@/lib/store';
import { PriceData } from '@/lib/types';

/**
 * HEADER COMPONENT - Navigation + Live Market Ticker
 * Data: Real prices from backend via store
 */

export default function Header() {
  const store = useStore();
  const [btcPrice, setBtcPrice] = useState<PriceData | null>(null);
  const [ethPrice, setEthPrice] = useState<PriceData | null>(null);
  const [wsStatus, setWsStatus] = useState<'connected' | 'disconnected' | 'connecting'>(
    'disconnected'
  );

  // Update prices from store
  useEffect(() => {
    const btc = store.getPriceBySymbol('BTC');
    const eth = store.getPriceBySymbol('ETH');
    setBtcPrice(btc);
    setEthPrice(eth);
  }, [store.prices]);

  // Update WebSocket status
  useEffect(() => {
    if (store.wsConnected) {
      setWsStatus('connected');
    } else if (store.wsReconnectAttempts > 0) {
      setWsStatus('connecting');
    } else {
      setWsStatus('disconnected');
    }
  }, [store.wsConnected, store.wsReconnectAttempts]);

  return (
    <header className="sticky top-0 z-50 border-b border-slate-700/50 bg-gradient-to-r from-slate-900/95 to-slate-800/95 backdrop-blur-sm">
      <div className="container mx-auto px-6 py-4">
        <div className="flex items-center justify-between gap-8">
          {/* Logo + Brand */}
          <Link href="/" className="flex items-center gap-3 shrink-0">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center font-bold text-white text-lg shadow-lg">
              ⚡
            </div>
            <div>
              <h1 className="text-xl font-bold text-white leading-tight">Elite</h1>
              <p className="text-xs text-blue-400">Trading System</p>
            </div>
          </Link>

          {/* Live Market Ticker - Real data from backend */}
          <div className="flex-1 flex items-center gap-8 px-8 border-l border-r border-slate-700/50">
            {/* BTC Price */}
            <div className="flex flex-col">
              <p className="text-xs text-slate-400 uppercase tracking-widest">BTC</p>
              <p className="text-sm font-bold text-white">
                ${btcPrice?.price.toLocaleString('en-US', { maximumFractionDigits: 0 }) || '---'}
              </p>
              <p
                className={`text-xs font-semibold ${
                  btcPrice && btcPrice.change_percent_24h >= 0
                    ? 'text-green-400'
                    : 'text-red-400'
                }`}
              >
                {btcPrice ? (
                  <>
                    {btcPrice.change_percent_24h >= 0 ? '↑' : '↓'}
                    {Math.abs(btcPrice.change_percent_24h).toFixed(2)}%
                  </>
                ) : (
                  '---'
                )}
              </p>
            </div>

            {/* ETH Price */}
            <div className="flex flex-col">
              <p className="text-xs text-slate-400 uppercase tracking-widest">ETH</p>
              <p className="text-sm font-bold text-white">
                ${ethPrice?.price.toLocaleString('en-US', { maximumFractionDigits: 0 }) || '---'}
              </p>
              <p
                className={`text-xs font-semibold ${
                  ethPrice && ethPrice.change_percent_24h >= 0
                    ? 'text-green-400'
                    : 'text-red-400'
                }`}
              >
                {ethPrice ? (
                  <>
                    {ethPrice.change_percent_24h >= 0 ? '↑' : '↓'}
                    {Math.abs(ethPrice.change_percent_24h).toFixed(2)}%
                  </>
                ) : (
                  '---'
                )}
              </p>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="flex items-center gap-6">
            <Link
              href="/dashboard"
              className="text-sm font-semibold text-slate-300 hover:text-white transition-colors"
            >
              Dashboard
            </Link>
            <Link
              href="/signals"
              className="text-sm font-semibold text-slate-300 hover:text-white transition-colors"
            >
              Signals
            </Link>
            <Link
              href="/analysis"
              className="text-sm font-semibold text-slate-300 hover:text-white transition-colors"
            >
              Analysis
            </Link>
            <Link
              href="/watchlist"
              className="text-sm font-semibold text-slate-300 hover:text-white transition-colors"
            >
              Watchlist
            </Link>
          </nav>

          {/* Status Indicators */}
          <div className="flex items-center gap-3">
            {/* Backend Status */}
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-800/50 border border-slate-700/50">
              <div
                className={`w-2 h-2 rounded-full ${
                  store.backendOnline ? 'bg-green-500' : 'bg-red-500'
                }`}
              />
              <span className="text-xs text-slate-400">
                {store.backendOnline ? 'Backend OK' : 'Backend Offline'}
              </span>
            </div>

            {/* WebSocket Status */}
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-800/50 border border-slate-700/50">
              <div
                className={`w-2 h-2 rounded-full animate-pulse ${
                  wsStatus === 'connected'
                    ? 'bg-blue-500'
                    : wsStatus === 'connecting'
                    ? 'bg-yellow-500'
                    : 'bg-slate-500'
                }`}
              />
              <span className="text-xs text-slate-400">
                {wsStatus === 'connected' ? 'Live' : wsStatus === 'connecting' ? 'Connecting' : 'Offline'}
              </span>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
