import React, { useState } from 'react';

// Mock: transcript / extracted ideas from YouTube financial content
const MOCK_VIDEOS = [
  { id: 1, title: 'S&P 500 Sector Rotation Strategy', channel: 'Trading Alpha', addedAt: '2h ago', concepts: ['sector rotation', 'momentum'], ideasCount: 3 },
  { id: 2, title: 'Options Greeks Explained', channel: 'Options Lab', addedAt: '5h ago', concepts: ['delta', 'gamma', 'IV'], ideasCount: 5 },
  { id: 3, title: 'Macro Monday: Fed and Rates', channel: 'Macro Edge', addedAt: '1d ago', concepts: ['Fed', 'rates', 'regime'], ideasCount: 2 },
];

const MOCK_FEATURES = [
  { id: 1, name: 'sector_rotation_score', source: 'S&P 500 Sector Rotation Strategy', addedAt: '2h ago' },
  { id: 2, name: 'iv_regime_filter', source: 'Options Greeks Explained', addedAt: '5h ago' },
];

const YouTubeKnowledge = () => {
  const [videoUrl, setVideoUrl] = useState('');

  const handleAddVideo = (e) => {
    e.preventDefault();
    console.log('Add video:', videoUrl);
  };

  return (
    <div className="min-h-screen bg-dark text-white p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold">YouTube Knowledge</h1>
        <p className="text-secondary mt-1">Transcript ingestion and algo ideas extraction from financial videos.</p>
      </div>

      {/* Add Video (shell) */}
      <div className="bg-secondary/10 rounded-lg p-6 mb-6">
        <h2 className="text-xl font-bold mb-4">Add Video</h2>
        <form onSubmit={handleAddVideo} className="flex gap-3">
          <input
            type="url"
            value={videoUrl}
            onChange={(e) => setVideoUrl(e.target.value)}
            placeholder="Paste YouTube URL..."
            className="flex-1 bg-dark border border-secondary/50 rounded px-4 py-2 focus:outline-none focus:ring-1 focus:ring-primary"
          />
          <button type="submit" className="bg-cyan-600 hover:bg-cyan-700 px-4 py-2 rounded font-medium">
            Add Video
          </button>
        </form>
        <p className="text-xs text-secondary mt-2">POST /api/v1/youtube-knowledge when wired.</p>
      </div>

      {/* Ingested Videos (mock list) */}
      <div className="bg-secondary/10 rounded-lg p-6 mb-6">
        <h2 className="text-xl font-bold mb-4">Ingested Videos</h2>
        <div className="space-y-4">
          {MOCK_VIDEOS.map((video) => (
            <div key={video.id} className="border border-secondary/50 rounded p-4">
              <h3 className="font-semibold">{video.title}</h3>
              <p className="text-sm text-secondary">{video.channel} · {video.addedAt}</p>
              <div className="flex flex-wrap gap-2 mt-2">
                {video.concepts.map((c) => (
                  <span key={c} className="text-xs bg-secondary/50 px-2 py-0.5 rounded">{c}</span>
                ))}
                <span className="text-xs text-cyan-400">{video.ideasCount} ideas</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* New ML Features from YouTube (mock) */}
      <div className="bg-secondary/10 rounded-lg p-6">
        <h2 className="text-xl font-bold mb-4">New ML Features from YouTube</h2>
        <div className="space-y-3">
          {MOCK_FEATURES.map((f) => (
            <div key={f.id} className="flex items-center justify-between py-2 border-b border-secondary/50 last:border-0">
              <span className="font-mono text-sm">{f.name}</span>
              <span className="text-xs text-secondary">from {f.source} · {f.addedAt}</span>
            </div>
          ))}
        </div>
        <p className="text-xs text-secondary mt-4">Connect GET /api/v1/youtube-knowledge for live data.</p>
      </div>
    </div>
  );
};

export default YouTubeKnowledge;
