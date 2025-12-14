import React, { useState, useEffect } from 'react';
import { Command } from 'lucide-react';

/**
 * Keyboard Shortcuts Overlay - Bloomberg Terminal-style hotkeys
 */

const ShortcutItem = ({ keys, description }) => (
  <div className="flex items-center justify-between py-2 border-b border-slate-700/50 last:border-0">
    <span className="text-sm text-gray-300">{description}</span>
    <div className="flex gap-1">
      {keys.map((key, idx) => (
        <kbd key={idx} className="px-2 py-1 bg-slate-700 text-teal-400 rounded text-xs font-mono">
          {key}
        </kbd>
      ))}
    </div>
  </div>
);

export default function KeyboardShortcuts() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const handleKeyPress = (e) => {
      // Show/hide help overlay
      if (e.key === '?' && !e.shiftKey) {
        e.preventDefault();
        setVisible(prev => !prev);
        return;
      }
      
      // Don't trigger shortcuts if typing in input
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return;
      }

      const shortcuts = {
        's': () => window.location.href = '/signals',
        'p': () => window.location.href = '/positions',
        'r': () => window.location.reload(),
        'Escape': () => setVisible(false)
      };
      
      const action = shortcuts[e.key];
      if (action) {
        e.preventDefault();
        action();
      }
    };
    
    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, []);

  if (!visible) {
    return (
      <button
        onClick={() => setVisible(true)}
        className="fixed bottom-4 right-4 p-3 bg-teal-500/20 hover:bg-teal-500/30 border border-teal-500/50 rounded-full shadow-lg transition-colors z-40"
        title="Keyboard Shortcuts (?)"
      >
        <Command className="text-teal-400" size={20} />
      </button>
    );
  }

  return (
    <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center">
      <div className="bg-slate-900 border border-slate-700 rounded-lg p-6 max-w-2xl w-full mx-4">
        <h2 className="text-2xl font-bold mb-6 flex items-center gap-2">
          <Command className="text-teal-400" size={24} />
          Keyboard Shortcuts
        </h2>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <h3 className="text-sm font-semibold text-gray-400 mb-2">Navigation</h3>
            <ShortcutItem keys={['?']} description="Show/hide this help" />
            <ShortcutItem keys={['S']} description="Open Signals view" />
            <ShortcutItem keys={['P']} description="View Positions" />
            <ShortcutItem keys={['R']} description="Refresh data" />
            <ShortcutItem keys={['ESC']} description="Close modals" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-gray-400 mb-2">Trading</h3>
            <ShortcutItem keys={['1-9']} description="Quick select signal" />
            <ShortcutItem keys={['B']} description="Buy 100 shares" />
            <ShortcutItem keys={['Shift', 'B']} description="Buy 500 shares" />
            <ShortcutItem keys={['C']} description="Close position" />
          </div>
        </div>
        <button 
          onClick={() => setVisible(false)}
          className="mt-6 w-full py-2 bg-teal-500 hover:bg-teal-600 rounded transition-colors"
        >
          Close (Press ? again)
        </button>
      </div>
    </div>
  );
}