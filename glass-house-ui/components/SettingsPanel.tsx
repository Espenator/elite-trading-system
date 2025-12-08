'use client';

import { useEliteStore } from '@/lib/store';

interface SettingsPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function SettingsPanel({ isOpen, onClose }: SettingsPanelProps) {
  const { soundEnabled, toggleSound, minConfidence, setMinConfidence } = useEliteStore();

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center">
      <div className="glass-card w-full max-w-2xl p-6 m-4 animate-scale-in">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold cyan-glow-text">SYSTEM SETTINGS</h2>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white transition-colors text-2xl"
          >
            ?
          </button>
        </div>

        <div className="space-y-6">
          {/* Sound Settings */}
          <div>
            <h3 className="text-sm font-bold text-cyan-400 mb-3">AUDIO ALERTS</h3>
            <div className="flex items-center justify-between p-4 bg-slate-800/50 rounded-lg">
              <div>
                <div className="font-bold text-white">Sound Notifications</div>
                <div className="text-xs text-slate-400">Play audio alerts for new signals</div>
              </div>
              <button
                onClick={toggleSound}
                className={`w-14 h-8 rounded-full transition-all `}
              >
                <div className={`w-6 h-6 bg-white rounded-full transition-transform `}></div>
              </button>
            </div>
          </div>

          {/* Filter Settings */}
          <div>
            <h3 className="text-sm font-bold text-cyan-400 mb-3">SIGNAL FILTERS</h3>
            <div className="p-4 bg-slate-800/50 rounded-lg">
              <label className="block mb-2">
                <span className="text-white font-bold">Minimum Confidence: {minConfidence}%</span>
              </label>
              <input
                type="range"
                min="0"
                max="100"
                value={minConfidence}
                onChange={(e) => setMinConfidence(Number(e.target.value))}
                className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer slider"
              />
              <div className="flex justify-between text-xs text-slate-400 mt-1">
                <span>0%</span>
                <span>50%</span>
                <span>100%</span>
              </div>
            </div>
          </div>

          {/* Display Settings */}
          <div>
            <h3 className="text-sm font-bold text-cyan-400 mb-3">DISPLAY</h3>
            <div className="grid grid-cols-2 gap-3">
              <button className="p-4 bg-slate-800/50 rounded-lg text-left hover:bg-slate-700/50 transition-colors">
                <div className="font-bold text-white">Theme</div>
                <div className="text-xs text-slate-400">Dark Military (Active)</div>
              </button>
              <button className="p-4 bg-slate-800/50 rounded-lg text-left hover:bg-slate-700/50 transition-colors">
                <div className="font-bold text-white">Refresh Rate</div>
                <div className="text-xs text-slate-400">Real-time</div>
              </button>
            </div>
          </div>

          {/* About */}
          <div className="p-4 bg-gradient-to-r from-cyan-500/10 to-purple-500/10 border border-cyan-500/30 rounded-lg">
            <div className="text-sm font-bold text-cyan-400 mb-1">ELITE TRADER TERMINAL</div>
            <div className="text-xs text-slate-400">Version 1.0.0 | Build 2025.12.07</div>
            <div className="text-xs text-slate-500 mt-2">
              AI-Powered Trading Intelligence Platform
            </div>
          </div>
        </div>

        <div className="mt-6 flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 px-6 py-3 bg-gradient-to-r from-cyan-500 to-purple-500 rounded-lg font-bold text-white hover:opacity-90 transition-opacity"
          >
            SAVE SETTINGS
          </button>
          <button
            onClick={onClose}
            className="px-6 py-3 border border-slate-600 rounded-lg font-bold text-slate-400 hover:text-white hover:border-slate-500 transition-colors"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
