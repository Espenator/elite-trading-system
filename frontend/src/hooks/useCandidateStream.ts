import { useState, useEffect } from 'react';
import { Candidate } from '../types/candidate';

interface Progress {
  current: number;
  total: number;
  tier3Passed: number;
  tier4Approved: number;
}

// Mock data generator for development
const generateMockCandidate = (index: number): Candidate => {
  const tickers = ['AAPL', 'TSLA', 'NVDA', 'AMD', 'GOOGL', 'MSFT', 'META', 'AMZN'];
  const tiers: Array<'Core' | 'Hot' | 'Liquid'> = ['Core', 'Hot', 'Liquid'];
  
  return {
    id: `candidate-${Date.now()}-${index}`,
    ticker: tickers[index % tickers.length],
    companyName: `Company ${index + 1}`,
    price: 100 + Math.random() * 400,
    change: (Math.random() - 0.3) * 10,
    volume: Math.floor(Math.random() * 50000000),
    rvol: 0.5 + Math.random() * 3,
    score: 70 + Math.random() * 25,
    aiConfidence: 75 + Math.floor(Math.random() * 20),
    modelAgreement: 80 + Math.floor(Math.random() * 15),
    tier: tiers[Math.floor(Math.random() * tiers.length)],
    structure: Math.random() > 0.5 ? 'HHHL' : 'LLLH',
    timestamp: Date.now(),
    priceHistory: Array.from({ length: 20 }, () => Math.random() * 100),
    velezScores: {
      weekly: 60 + Math.floor(Math.random() * 20),
      daily: 60 + Math.floor(Math.random() * 20),
      fourHour: 60 + Math.floor(Math.random() * 20),
      oneHour: 60 + Math.floor(Math.random() * 20),
    },
    darkPoolBlocks: Math.floor(Math.random() * 50),
    catalyst: 'Volume surge + breakout',
  };
};

export const useCandidateStream = () => {
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [progress, setProgress] = useState<Progress>({
    current: 0,
    total: 25,
    tier3Passed: 0,
    tier4Approved: 0,
  });
  const [isAnalyzing, setIsAnalyzing] = useState(true);

  useEffect(() => {
    // Simulate streaming candidates
    let count = 0;
    const interval = setInterval(() => {
      if (count < 25) {
        const newCandidate = generateMockCandidate(count);
        setCandidates((prev) => [...prev, newCandidate].sort((a, b) => b.score - a.score));
        
        setProgress({
          current: count + 1,
          total: 25,
          tier3Passed: Math.floor((count + 1) * 0.95),
          tier4Approved: count + 1,
        });
        
        count++;
      } else {
        setIsAnalyzing(false);
        clearInterval(interval);
      }
    }, 1500); // New candidate every 1.5 seconds

    return () => clearInterval(interval);
  }, []);

  return {
    candidates,
    progress,
    isAnalyzing,
  };
};
