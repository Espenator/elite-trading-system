export default function Home() {
  return (
    <div className="min-h-screen bg-slate-950 text-white p-8">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-4xl font-bold text-cyan-400 mb-8">
          ?? Elite Trader Terminal
        </h1>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {/* Status Card */}
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
            <h2 className="text-xl font-bold text-cyan-400 mb-4">System Status</h2>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-slate-400">Frontend:</span>
                <span className="text-green-400">? Running</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Backend:</span>
                <span className="text-yellow-400">? Not Connected</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Database:</span>
                <span className="text-yellow-400">? Not Connected</span>
              </div>
            </div>
          </div>

          {/* Quick Stats */}
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
            <h2 className="text-xl font-bold text-cyan-400 mb-4">Quick Stats</h2>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-slate-400">Active Signals:</span>
                <span className="text-white font-mono">0</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Watchlist:</span>
                <span className="text-white font-mono">0</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Trades Today:</span>
                <span className="text-white font-mono">0</span>
              </div>
            </div>
          </div>

          {/* Next Steps */}
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
            <h2 className="text-xl font-bold text-cyan-400 mb-4">Next Steps</h2>
            <ol className="space-y-2 text-sm text-slate-400">
              <li>1. Start backend server</li>
              <li>2. Connect database</li>
              <li>3. Run signal scanner</li>
              <li>4. Monitor live feed</li>
            </ol>
          </div>
        </div>

        {/* Market Indices */}
        <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-4">
            <div className="text-xs text-slate-500 mb-1">S&P 500</div>
            <div className="text-2xl font-bold font-mono">6,850.69</div>
            <div className="text-sm text-green-400">+0.51%</div>
          </div>
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-4">
            <div className="text-xs text-slate-500 mb-1">DOW JONES</div>
            <div className="text-2xl font-bold font-mono">47,950</div>
            <div className="text-sm text-red-400">-0.01%</div>
          </div>
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-4">
            <div className="text-xs text-slate-500 mb-1">NASDAQ</div>
            <div className="text-2xl font-bold font-mono">21,180</div>
            <div className="text-sm text-green-400">+0.12%</div>
          </div>
        </div>

        {/* Footer */}
        <div className="mt-8 text-center text-slate-500 text-sm">
          Elite Trader Terminal v1.0.0 | Ready for configuration
        </div>
      </div>
    </div>
  )
}
