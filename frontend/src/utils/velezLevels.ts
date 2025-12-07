import { IChartApi, IPriceLine } from 'lightweight-charts';

export interface VelezLevels {
  mlTarget: number;
  atrStop: number;
  profitZone: number;
  entryPrice: number;
  rrRatio: number;
}

export const addVelezLevels = (chart: IChartApi, levels: VelezLevels): IPriceLine[] => {
  const lines: IPriceLine[] = [];

  // Entry price (reference)
  const entryLine = {
    price: levels.entryPrice,
    color: '#64748b',
    lineWidth: 1,
    lineStyle: 2, // Dashed
    axisLabelVisible: true,
    title: `ENTRY: $${levels.entryPrice.toFixed(2)}`,
  };

  // ML Target (AI prediction)
  const targetLine = {
    price: levels.mlTarget,
    color: '#00d9ff',
    lineWidth: 2,
    lineStyle: 0, // Solid
    axisLabelVisible: true,
    title: `🤖 AI TARGET: $${levels.mlTarget.toFixed(2)}`,
  };

  // ATR-based Stop Loss (Velez system)
  const stopLine = {
    price: levels.atrStop,
    color: '#ef4444',
    lineWidth: 2,
    lineStyle: 0,
    axisLabelVisible: true,
    title: `🛡️ ATR STOP: $${levels.atrStop.toFixed(2)}`,
  };

  // Profit Zone (2:1 R/R minimum)
  const profitLine = {
    price: levels.profitZone,
    color: '#10b981',
    lineWidth: 2,
    lineStyle: 0,
    axisLabelVisible: true,
    title: `💰 PROFIT ZONE: $${levels.profitZone.toFixed(2)} (${levels.rrRatio.toFixed(1)}:1)`,
  };

  lines.push(
    chart.addPriceLine(entryLine) as IPriceLine,
    chart.addPriceLine(targetLine) as IPriceLine,
    chart.addPriceLine(stopLine) as IPriceLine,
    chart.addPriceLine(profitLine) as IPriceLine
  );

  return lines;
};

export const removeVelezLevels = (chart: IChartApi, lines: IPriceLine[]) => {
  lines.forEach(line => {
    try {
      chart.removePriceLine(line);
    } catch (e) {
      // Line already removed
    }
  });
};

export const calculateVelezLevels = (
  entryPrice: number,
  mlPrediction: number,
  atr: number
): VelezLevels => {
  // ATR-based stop (2x ATR below entry)
  const atrStop = entryPrice - (atr * 2);
  
  // ML target from prediction model
  const mlTarget = mlPrediction;
  
  // Profit zone (2:1 minimum R/R)
  const risk = entryPrice - atrStop;
  const profitZone = entryPrice + (risk * 2);
  
  // Calculate actual R/R ratio
  const reward = mlTarget - entryPrice;
  const rrRatio = reward / risk;

  return {
    mlTarget,
    atrStop,
    profitZone,
    entryPrice,
    rrRatio
  };
};
