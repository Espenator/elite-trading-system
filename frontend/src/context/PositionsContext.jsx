import React, { createContext, useContext, useState, useCallback } from 'react';

const PositionsContext = createContext();

export function PositionsProvider({ children }) {
  const [positions, setPositions] = useState([
    {
      id: 1,
      ticker: 'YUM',
      quantity: 100,
      entryPrice: 148.0,
      currentPrice: 149.5,
      stopPrice: 145.0,
      targetPrice: 152.0,
      entryTime: new Date(Date.now() - 5 * 60000),
      status: 'open',
      pnlDollars: 150,
      pnlPercent: 1.01,
    },
    {
      id: 2,
      ticker: 'NVDA',
      quantity: 500,
      entryPrice: 189.0,
      currentPrice: 187.25,
      stopPrice: 185.0,
      targetPrice: 197.0,
      entryTime: new Date(Date.now() - 12 * 60000),
      status: 'open',
      pnlDollars: -875,
      pnlPercent: -0.93,
    },
    {
      id: 3,
      ticker: 'AAPL',
      quantity: 250,
      entryPrice: 195.5,
      currentPrice: 195.75,
      stopPrice: 193.0,
      targetPrice: 200.0,
      entryTime: new Date(Date.now() - 3 * 60000),
      status: 'open',
      pnlDollars: 62.5,
      pnlPercent: 0.13,
    },
  ]);

  // Add a new position
  const addPosition = useCallback(
    (positionData) => {
      const newPosition = {
        id: Math.max(...positions.map(p => p.id), 0) + 1,
        entryTime: new Date(),
        status: 'open',
        pnlDollars: 0,
        pnlPercent: 0,
        ...positionData,
      };
      setPositions(prev => [...prev, newPosition]);
      return newPosition;
    },
    [positions]
  );

  // Update a position's current price
  const updatePositionPrice = useCallback((positionId, newPrice) => {
    setPositions(prev =>
      prev.map(pos => {
        if (pos.id === positionId) {
          const pnlDollars = (newPrice - pos.entryPrice) * pos.quantity;
          const pnlPercent = ((newPrice - pos.entryPrice) / pos.entryPrice) * 100;
          return {
            ...pos,
            currentPrice: newPrice,
            pnlDollars,
            pnlPercent,
          };
        }
        return pos;
      })
    );
  }, []);

  // Close a position
  const closePosition = useCallback((positionId) => {
    setPositions(prev => prev.filter(p => p.id !== positionId));
  }, []);

  // Close all positions
  const closeAllPositions = useCallback(() => {
    setPositions([]);
  }, []);

  // Update position stop/target
  const updatePositionLevels = useCallback(
    (positionId, stopPrice, targetPrice) => {
      setPositions(prev =>
        prev.map(pos => {
          if (pos.id === positionId) {
            return {
              ...pos,
              stopPrice: stopPrice !== undefined ? stopPrice : pos.stopPrice,
              targetPrice: targetPrice !== undefined ? targetPrice : pos.targetPrice,
            };
          }
          return pos;
        })
      );
    },
    []
  );

  // Calculate statistics
  const getStatistics = useCallback(() => {
    const stats = {
      totalPositions: positions.length,
      totalPnlDollars: 0,
      totalPnlPercent: 0,
      totalValue: 0,
      winning: 0,
      losing: 0,
      breakeven: 0,
      winRate: 0,
      avgPnl: 0,
      maxGain: null,
      maxLoss: null,
    };

    if (positions.length === 0) {
      return stats;
    }

    let maxGain = -Infinity;
    let maxLoss = Infinity;

    positions.forEach(pos => {
      stats.totalPnlDollars += pos.pnlDollars;
      stats.totalValue += pos.entryPrice * pos.quantity;

      if (pos.pnlDollars > 0) {
        stats.winning++;
        maxGain = Math.max(maxGain, pos.pnlDollars);
      } else if (pos.pnlDollars < 0) {
        stats.losing++;
        maxLoss = Math.min(maxLoss, pos.pnlDollars);
      } else {
        stats.breakeven++;
      }
    });

    stats.totalPnlPercent = (stats.totalPnlDollars / stats.totalValue) * 100;
    stats.winRate = ((stats.winning / positions.length) * 100).toFixed(1);
    stats.avgPnl = (stats.totalPnlDollars / positions.length).toFixed(2);
    stats.maxGain = maxGain === -Infinity ? null : maxGain;
    stats.maxLoss = maxLoss === Infinity ? null : maxLoss;

    return stats;
  }, [positions]);

  const value = {
    positions,
    addPosition,
    updatePositionPrice,
    closePosition,
    closeAllPositions,
    updatePositionLevels,
    getStatistics,
  };

  return (
    <PositionsContext.Provider value={value}>
      {children}
    </PositionsContext.Provider>
  );
}

export function usePositions() {
  const context = useContext(PositionsContext);
  if (!context) {
    throw new Error('usePositions must be used within PositionsProvider');
  }
  return context;
}
