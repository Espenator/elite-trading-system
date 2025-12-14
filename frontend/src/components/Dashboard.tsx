import React, { useState } from 'react';
import { LeftSidebar } from './LeftSidebar';
import { SignalsPanel } from './SignalsPanel';
import { ChartArea } from './ChartArea';
import { MLInsightsPanel } from './MLInsightsPanel';
import { PositionsPanel } from './PositionsPanel';
import { ExecutionPanel } from './ExecutionPanel';
import { Header } from './Header';
import { NotificationCenter } from './NotificationCenter';

export function Dashboard() {
  const [selectedSignal, setSelectedSignal] = useState(null);
  const [positions, setPositions] = useState([]);
  const [signals, setSignals] = useState([]);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <Header />
      <NotificationCenter />
      <div className="flex h-[calc(100vh-64px)]">
        <div className="w-72 border-r border-slate-700 bg-slate-900 overflow-y-auto">
          <LeftSidebar />
        </div>
        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="flex flex-1 overflow-hidden gap-2 p-2">
            <div className="w-96 overflow-hidden">
              <SignalsPanel signals={signals} setSignals={setSignals} onSelectSignal={setSelectedSignal} />
            </div>
            <div className="flex-1 overflow-hidden">
              <ChartArea selectedSignal={selectedSignal} />
            </div>
          </div>
          <div className="flex gap-2 p-2 h-1/3 overflow-hidden">
            <div className="w-80 overflow-hidden"><MLInsightsPanel /></div>
            <div className="flex-1 overflow-hidden"><PositionsPanel positions={positions} setPositions={setPositions} /></div>
            <div className="w-72 overflow-hidden"><ExecutionPanel selectedSignal={selectedSignal} /></div>
          </div>
        </div>
      </div>
    </div>
  );
}
