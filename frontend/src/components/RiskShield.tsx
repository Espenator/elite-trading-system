import React from 'react';
import { Shield } from 'lucide-react';

export function RiskShield({ positionCount = 5, maxPositions = 15, positionSizePercent = 8.5, dailyLossPercent = 0.8, mlConfidence = 85 }) {
  const checks = [
    { name: 'Position Count', value: positionCount + '/' + maxPositions, passed: positionCount <= maxPositions },
    { name: 'Position Size', value: positionSizePercent + '%', passed: positionSizePercent <= 20 },
    { name: 'Daily Loss', value: dailyLossPercent + '%', passed: dailyLossPercent <= 3 },
    { name: 'ML Confidence', value: mlConfidence + '%', passed: mlConfidence >= 70 }
  ];
  const allPassed = checks.every(c => c.passed);

  return (
    <div className={'rounded-lg border p-4 ' + (allPassed ? 'bg-green-900/10 border-green-700' : 'bg-red-900/10 border-red-700')}>
      <div className="flex items-center gap-2 mb-4"><Shield size={20} className={allPassed ? 'text-green-400' : 'text-red-400'} /><h3 className="font-bold text-lg">{allPassed ? 'RISK SHIELD: PASS' : 'RISK SHIELD: ALERT'}</h3></div>
      <div className="grid grid-cols-2 gap-3">
        {checks.map((check, i) => (
          <div key={i} className={'p-2 rounded border ' + (check.passed ? 'bg-slate-800 border-slate-700' : 'bg-red-900/20 border-red-700')}>
            <div className="text-xs text-slate-400">{check.name}</div>
            <div className={'font-mono font-bold ' + (check.passed ? 'text-green-400' : 'text-red-400')}>{check.value}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
