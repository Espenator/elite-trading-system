import { useState, useEffect } from 'react';
import { Prediction } from '../types/chart';

export const usePredictions = (symbol: string) => {
  const [predictions, setPredictions] = useState<Prediction[]>([]);

  useEffect(() => {
    const generatePredictions = (): Prediction[] => {
      const now = Date.now();
      const preds: Prediction[] = [];
      let baseValue = 155;

      for (let i = 0; i < 24; i++) {
        const time = Math.floor((now + (i * 3600000)) / 1000);
        const value = baseValue + (Math.random() - 0.3) * 5;
        const confidence = 0.7 + Math.random() * 0.25;
        const spread = (1 - confidence) * 10;

        preds.push({
          time,
          value,
          upper: value + spread,
          lower: value - spread,
          confidence
        });

        baseValue = value;
      }
      return preds;
    };

    setPredictions(generatePredictions());
  }, [symbol]);

  return predictions;
};
