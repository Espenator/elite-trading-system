import React from 'react';
import './Heatmap.css';

interface HeatmapProps {
  data: number[][];
  labels: string[];
  colorScale?: string[];
}

const Heatmap: React.FC<HeatmapProps> = ({ 
  data, 
  labels,
  colorScale = ['#1e3a8a', '#3b82f6', '#fbbf24', '#ef4444']
}) => {
  const getColor = (value: number) => {
    const normalized = Math.min(Math.max(value, 0), 1);
    const index = Math.floor(normalized * (colorScale.length - 1));
    return colorScale[index];
  };

  return (
    <div className="heatmap">
      <div className="heatmap-grid">
        {data.map((row, i) => (
          <div key={i} className="heatmap-row">
            <div className="heatmap-label">{labels[i]}</div>
            {row.map((value, j) => (
              <div
                key={j}
                className="heatmap-cell"
                style={{ backgroundColor: getColor(value) }}
                title={`${labels[i]}: ${(value * 100).toFixed(0)}%`}
              >
                {(value * 100).toFixed(0)}
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
};

export default Heatmap;
