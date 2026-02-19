import React, { useState } from "react";
import { Youtube } from "lucide-react";
import Card from "../components/ui/Card";
import TextField from "../components/ui/TextField";
import Button from "../components/ui/Button";
import Badge from "../components/ui/Badge";
import PageHeader from "../components/ui/PageHeader";
import { useApi } from "../hooks/useApi";

const YouTubeKnowledge = () => {
  const [videoUrl, setVideoUrl] = useState("");
  const { data, loading, error, refetch } = useApi("youtubeKnowledge", { pollIntervalMs: 60000 });
  const videos = Array.isArray(data?.videos) ? data.videos : [];
  const features = Array.isArray(data?.features) ? data.features : [];

  const handleAddVideo = (e) => {
    e.preventDefault();
    console.log("Add video:", videoUrl);
  };

  return (
    <div className="min-h-full bg-dark text-white space-y-6">
      <PageHeader
        icon={Youtube}
        title="YouTube Knowledge"
        description={error ? "Failed to load" : "Transcript ingestion and algo ideas extraction from financial videos."}
      >
        {error && (
          <span className="text-xs text-danger font-medium">Failed to load</span>
        )}
      </PageHeader>

      {/* Add Video (shell) */}
      <Card title="Add Video" className="mb-6">
        <form onSubmit={handleAddVideo} className="flex gap-3">
          <TextField
            type="url"
            value={videoUrl}
            onChange={(e) => setVideoUrl(e.target.value)}
            placeholder="Paste YouTube URL..."
            className="flex-1"
          />
          <Button type="submit" variant="primary">
            Add Video
          </Button>
        </form>
        <p className="text-xs text-secondary mt-2">
          POST /api/v1/youtube-knowledge when wired.
        </p>
      </Card>

      {/* Ingested Videos */}
      <Card title="Ingested Videos" className="mb-6">
        {loading && videos.length === 0 ? (
          <div className="py-8 text-center text-secondary">Loading...</div>
        ) : error && videos.length === 0 ? (
          <div className="py-8 text-center">
            <p className="text-secondary mb-2">Could not load. Check GET /api/v1/youtube-knowledge.</p>
            <Button variant="outline" size="sm" onClick={refetch}>Retry</Button>
          </div>
        ) : videos.length === 0 ? (
          <div className="py-8 text-center text-secondary">No videos ingested yet.</div>
        ) : (
        <div className="space-y-4">
          {videos.map((video) => (
            <div
              key={video.id}
              className="border border-secondary/50 rounded-xl p-4"
            >
              <h3 className="font-semibold text-white">{video.title}</h3>
              <p className="text-sm text-secondary">
                {video.channel} · {video.addedAt}
              </p>
              <div className="flex flex-wrap gap-2 mt-2">
                {(video.concepts || []).map((c) => (
                  <Badge key={c} variant="secondary">
                    {c}
                  </Badge>
                ))}
                <span className="text-xs text-primary">
                  {video.ideasCount ?? 0} ideas
                </span>
              </div>
            </div>
          ))}
        </div>
        )}
      </Card>

      {/* New ML Features from YouTube */}
      <Card title="New ML Features from YouTube">
        {features.length === 0 && !loading ? (
          <p className="text-secondary py-4">No extracted features yet.</p>
        ) : (
        <div className="space-y-3">
          {features.map((f) => (
            <div
              key={f.id}
              className="flex items-center justify-between py-2 border-b border-secondary/50 last:border-0"
            >
              <span className="text-sm">{f.name}</span>
              <span className="text-xs text-secondary">
                from {f.source} · {f.addedAt}
              </span>
            </div>
          ))}
        </div>
        )}
      </Card>
    </div>
  );
};

export default YouTubeKnowledge;
