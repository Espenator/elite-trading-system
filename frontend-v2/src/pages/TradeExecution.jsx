import React, { useState } from 'react';
import Card from '../components/ui/Card';
import TextField from '../components/ui/TextField';
import Select from '../components/ui/Select';
import Button from '../components/ui/Button';

const TradeExecution = () => {
  const [symbol, setSymbol] = useState('TSLA');
  const [orderType, setOrderType] = useState('Limit');
  const [quantity, setQuantity] = useState(100);
  const [price, setPrice] = useState(150.25);
  const [timeframe, setTimeframe] = useState('1D');

  const estimatedCost = quantity * price;
  const requiredMargin = estimatedCost * 0.5;
  const potentialPL = 250.00;
  const riskStatus = 'Within Limits';

  const handleBuy = () => {
    console.log('Buy order placed:', { symbol, orderType, quantity, price });
  };

  const handleSell = () => {
    console.log('Sell order placed:', { symbol, orderType, quantity, price });
  };

  return (
    <div className="min-h-screen bg-dark text-white p-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-2">Trade Execution</h1>
        <p className="text-secondary">Execute and manage trades with real-time data and risk validation.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Chart Section */}
        <div className="lg:col-span-2">
          <Card title={`${symbol} Chart`}>
            <div className="flex justify-end gap-2 mb-4 -mt-1">
              {['15M', '1H', '4H', '1D'].map(tf => (
                <Button key={tf} variant={timeframe === tf ? 'primary' : 'secondary'} size="sm" onClick={() => setTimeframe(tf)}>{tf}</Button>
              ))}
            </div>
            <div className="h-96 flex items-center justify-center bg-dark rounded">
              <p className="text-secondary">Interactive Chart for {symbol}</p>
            </div>
          </Card>
        </div>

        <div className="space-y-6">
          <Card title={`Order Entry for ${symbol}`}>
            <div className="mb-4">
              <Select label="Order Type" value={orderType} onChange={e => setOrderType(e.target.value)} options={['Limit', 'Market', 'Stop', 'Stop Limit'].map(v => ({ value: v, label: v }))} />
            </div>
            <div className="mb-4">
              <TextField label="Quantity" type="number" value={quantity} onChange={e => setQuantity(parseFloat(e.target.value) || 0)} />
            </div>
            <div className="mb-4">
              <TextField label="Price" type="number" step="0.01" value={price} onChange={e => setPrice(parseFloat(e.target.value) || 0)} />
            </div>
            <div className="flex gap-3">
              <Button variant="success" fullWidth onClick={handleBuy}>↗ Buy</Button>
              <Button variant="danger" fullWidth onClick={handleSell}>↙ Sell</Button>
            </div>
          </Card>

          <Card title="Order Preview">
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-secondary">Estimated Cost:</span>
                <span className="font-semibold text-white">${estimatedCost.toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-secondary">Required Margin:</span>
                <span className="font-semibold text-white">${requiredMargin.toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-secondary">Potential P&L:</span>
                <span className="font-semibold text-success">+ ${potentialPL.toLocaleString()}</span>
              </div>
              <div className="pt-3 border-t border-secondary/50">
                <div className="flex justify-between items-center">
                  <span className="text-secondary">Risk Status:</span>
                  <span className="font-semibold text-success">{riskStatus}</span>
                </div>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default TradeExecution;
