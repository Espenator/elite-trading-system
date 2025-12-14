import React, { useState } from 'react';
import { TrendingUp, TrendingDown, AlertTriangle } from 'lucide-react';

export function ExecutionPanel({ selectedSignal }) {
  const [quantity, setQuantity] = useState(100);
  const [orderType, setOrderType] = useState('MARKET');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const symbol = selectedSignal?.symbol || 'NVDA';
  const currentPrice = 188.5; const stopLoss = currentPrice * 0.98; const positionValue = quantity * currentPrice;

  const handleTrade = async (side) => { setIsSubmitting(true); await new Promise(resolve => setTimeout(resolve, 1000)); alert(side + ' order: ' + quantity + ' ' + symbol + ' @ ' + currentPrice); setIsSubmitting(false); };

  return (
    <div className="bg-slate-900 rounded-lg border border-slate-700 flex flex-col h-full">
      <div className="p-3 border-b border-slate-700"><h3 className="font-bold text-cyan-400 mb-1">ORDER ENTRY</h3><div className="text-xs text-slate-400">{symbol}</div></div>
      <div className="p-3 space-y-3 flex-1 overflow-y-auto">
        <div><label className="text-xs text-slate-400 block mb-1">Quantity</label><input type="number" value={quantity} onChange={(e) => setQuantity(Number(e.target.value))} className="w-full px-2 py-1 bg-slate-800 border border-slate-600 rounded text-sm font-mono text-slate-100" /></div>
        <div className="grid grid-cols-3 gap-1">
          <button onClick={() => setQuantity(50)} className="px-2 py-1 bg-slate-700 hover:bg-slate-600 rounded text-xs font-bold">50</button>
          <button onClick={() => setQuantity(100)} className="px-2 py-1 bg-slate-700 hover:bg-slate-600 rounded text-xs font-bold">100</button>
          <button onClick={() => setQuantity(200)} className="px-2 py-1 bg-slate-700 hover:bg-slate-600 rounded text-xs font-bold">200</button>
        </div>
        <div><label className="text-xs text-slate-400 block mb-1">Order Type</label><select value={orderType} onChange={(e) => setOrderType(e.target.value)} className="w-full px-2 py-1 bg-slate-800 border border-slate-600 rounded text-sm text-slate-100"><option>MARKET</option><option>LIMIT</option><option>STOP</option></select></div>
        <div className="bg-slate-800 rounded p-2 space-y-1 text-xs">
          <div className="flex justify-between"><span className="text-slate-400">Entry</span><span className="font-mono font-bold">{currentPrice}</span></div>
          <div className="flex justify-between"><span className="text-slate-400">Stop Loss</span><span className="font-mono font-bold text-red-400">{stopLoss.toFixed(2)}</span></div>
          <div className="flex justify-between"><span className="text-slate-400">Value</span><span className="font-mono font-bold"
@"
import React, { useState, useEffect } from 'react';
import { AlertCircle, CheckCircle, AlertTriangle, X } from 'lucide-react';

export function NotificationCenter() {
  const [notifications, setNotifications] = useState([]);

  useEffect(() => {
    const interval = setInterval(() => {
      const types = ['success', 'error', 'warning', 'info'];
      const type = types[Math.floor(Math.random() * types.length)];
      const titles = { success: 'Order Executed', error: 'Connection Lost', warning: 'Position at Risk', info: 'Market Alert' };
      const messages = { success: 'BUY 100 NVDA @ 188.50', error: 'WebSocket disconnected', warning: 'TSLA down 5%', info: 'New T1 signal: AAPL' };
      const newNotif = { id: Date.now().toString(), type, title: titles[type], message: messages[type] };
      setNotifications(prev => [newNotif, ...prev].slice(0, 5));
    }, 8000);
    return () => clearInterval(interval);
  }, []);

  const removeNotification = (id) => { setNotifications(prev => prev.filter(n => n.id !== id)); };
  const getBgColor = (type) => { if (type === 'success') return 'bg-green-900/20 border-green-700'; if (type === 'error') return 'bg-red-900/20 border-red-700'; if (type === 'warning') return 'bg-yellow-900/20 border-yellow-700'; return 'bg-cyan-900/20 border-cyan-700'; };

  return (
    <div className="fixed top-20 right-6 z-50 space-y-2 w-80">
      {notifications.map(notif => (
        <div key={notif.id} className={'rounded border p-3 flex items-start gap-3 ' + getBgColor(notif.type)}>
          <CheckCircle size={18} className="text-green-400" />
          <div className="flex-1"><div className="font-bold text-sm">{notif.title}</div><div className="text-xs text-slate-300">{notif.message}</div></div>
          <button onClick={() => removeNotification(notif.id)} className="text-slate-400 hover:text-slate-200"><X size={16} /></button>
        </div>
      ))}
    </div>
  );
}
