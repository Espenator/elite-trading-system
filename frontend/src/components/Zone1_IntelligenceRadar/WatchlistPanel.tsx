import { useState } from 'react';
import './WatchlistPanel.css';

interface WatchlistItem {
  ticker: string;
  price: number;
  change: number;
}

const WatchlistPanel = () => {
  const [watchlists, setWatchlists] = useState([
    {
      name: 'Swing Trades',
      items: [
        { ticker: 'AAPL', price: 195.43, change: 1.2 },
        { ticker: 'TSLA', price: 412.34, change: 2.1 }
      ]
    }
  ]);

  return (
    <div className="watchlist-panel">
      <div className="watchlist-header">
        <h3>⭐ My Watchlists</h3>
        <button className="add-btn">+ New</button>
      </div>

      {watchlists.map((list) => (
        <div key={list.name} className="watchlist-group">
          <h4 className="list-name">📁 {list.name} ({list.items.length})</h4>
          
          {list.items.map((item) => (
            <div key={item.ticker} className="watchlist-item">
              <span className="item-ticker">{item.ticker}</span>
              <span className="item-price">${item.price.toFixed(2)}</span>
              <span className={`item-change ${item.change >= 0 ? 'positive' : 'negative'}`}>
                {item.change >= 0 ? '+' : ''}{item.change.toFixed(2)}%
              </span>
              <button className="remove-btn">×</button>
            </div>
          ))}
        </div>
      ))}

      <div className="watchlist-actions">
        <button>Import CSV</button>
        <button>Export</button>
      </div>
    </div>
  );
};

export default WatchlistPanel;
