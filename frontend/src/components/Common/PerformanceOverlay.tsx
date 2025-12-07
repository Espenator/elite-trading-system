import React from 'react';
import React, { useState, useEffect } from 'react';
import './PerformanceOverlay.css';

const PerformanceOverlay = () => {
  const [fps, setFps] = useState(60);
  const [memory, setMemory] = useState(0);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    let frameCount = 0;
    let lastTime = performance.now();
    let animationId: number;

    const measurePerformance = () => {
      frameCount++;
      const currentTime = performance.now();
      
      if (currentTime >= lastTime + 1000) {
        setFps(frameCount);
        frameCount = 0;
        lastTime = currentTime;
        
        // Memory (Chrome only)
        if ('memory' in performance) {
          const mem = (performance as any).memory;
          setMemory(mem.usedJSHeapSize / 1048576);
        }
      }
      
      animationId = requestAnimationFrame(measurePerformance);
    };
    
    measurePerformance();
    return () => cancelAnimationFrame(animationId);
  }, []);

  // Toggle with Ctrl+Shift+P
  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.shiftKey && e.key === 'P') {
        setVisible(prev => !prev);
      }
    };
    
    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, []);

  if (!visible) return null;

  return (
    <div className="performance-overlay">
      <div className="perf-header">⚡ Performance</div>
      <div className="perf-metrics">
        <div className="perf-metric">
          <span className="perf-label">FPS</span>
          <span className={`perf-value ${fps < 30 ? 'bad' : fps < 50 ? 'ok' : 'good'}`}>
            {fps}
          </span>
        </div>
        {memory > 0 && (
          <div className="perf-metric">
            <span className="perf-label">Memory</span>
            <span className="perf-value">{memory.toFixed(0)}MB</span>
          </div>
        )}
      </div>
      <div className="perf-hint">Ctrl+Shift+P to hide</div>
    </div>
  );
};

export default PerformanceOverlay;

