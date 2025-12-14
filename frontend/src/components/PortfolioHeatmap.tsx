import React, { useState } from 'react';

export function PortfolioHeatmap() {
  const [sectors] = useState([
    { name: 'Technology', value: 45.2, color: 'bg-cyan-600', positions: 8 },
    { name: 'Healthcare', value: 22.8, color: 'bg-green-600', positions: 4 },
    { name: 'Finance', value: 18.5, color: 'bg-blue-600', positions: 3 },
    { name: 'Energy', value: 13.5, color: 'bg-yellow-600', positions: 2 }
  ]);

  return (
    <div className="bg-slate-900 rounded-lg border border-slate-700 p-4">
      <h3 className="font-bold text-cyan-400 mb-4">Sector Exposure</h3>
      <div className="grid grid-cols-2 gap-2 mb-4">
        {sectors.map((sector, i) => (
          <div key={i} className={sector.color + ' rounded p-3 text-white text-center cursor-pointer hover:opacity-80 transition'}>
            <div className="font-bold text-sm">{sector.name}</div>
            <div className="text-lg font-bold">{sector.value}%</div>
            <div className="text-xs opacity-75">{sector.positions} positions</div>
          </div>
        ))}
      </div>
    </div>
  );
}
