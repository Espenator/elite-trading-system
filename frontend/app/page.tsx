'use client';

import { useEffect, useState } from 'react';
import CommandBar from '@/components/CommandBar';
import IntelligenceRadar from '@/components/IntelligenceRadar';
import TacticalChart from '@/components/TacticalChart';
import ExecutionDeck from '@/components/ExecutionDeck';
import LiveSignalFeed from '@/components/LiveSignalFeed';

export default function EliteTraderTerminal() {
  const [selectedSymbol, setSelectedSymbol] = useState<string>('SPY');
  const [wsConnected, setWsConnected] = useState(false);

  // WebSocket connection with reconnection logic
  useEffect(() => {
    let ws: WebSocket | null = null;
    let reconnectTimeout: NodeJS.Timeout;
    
    const connect = () => {
      try {
        ws = new WebSocket('ws://localhost:8000/ws');
        
        ws.onopen = () => {
          console.log('✅ WebSocket Connected');
          setWsConnected(true);
        };
        
        ws.onclose = () => {
          console.log('❌ WebSocket Disconnected');
          setWsConnected(false);
          // Attempt to reconnect after 3 seconds
          reconnectTimeout = setTimeout(() => {
            console.log('🔄 Attempting to reconnect...');
            connect();
          }, 3000);
        };
        
        ws.onerror = (error) => {
          console.error('WebSocket Error:', error);
          setWsConnected(false);
        };
      } catch (error) {
        console.error('Failed to create WebSocket:', error);
        setWsConnected(false);
      }
    };

    connect();

    return () => {
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      if (ws) ws.close();
    };
  }, []);

  return (
    <div className="elite-terminal-grid">
      {/* ZONE 0: Command Bar */}
      <CommandBar 
        selectedSymbol={selectedSymbol}
        wsConnected={wsConnected}
      />

      {/* ZONE 1: Intelligence Radar (Left Panel) */}
      <IntelligenceRadar 
        onSelectSymbol={setSelectedSymbol}
      />

      {/* ZONE 2: Tactical Chart (Center) */}
      <TacticalChart 
        symbol={selectedSymbol}
      />

      {/* ZONE 3: Execution Deck (Right Panel) */}
      <ExecutionDeck 
        symbol={selectedSymbol}
      />

      {/* ZONE 4: Live Signal Feed (Bottom) */}
      <LiveSignalFeed 
        onSelectSymbol={setSelectedSymbol}
      />
    </div>
  );
}
