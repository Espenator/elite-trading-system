import React from 'react';
import React, { useState, useEffect, useRef } from 'react';
import './ContextMenu.css';

interface ContextMenuProps {
  x: number;
  y: number;
  ticker?: string;
  onClose: () => void;
}

const ContextMenu: React.FC<ContextMenuProps> = ({ x, y, ticker, onClose }) => {
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        onClose();
      }
    };

    document.addEventListener('click', handleClickOutside);
    return () => document.removeEventListener('click', handleClickOutside);
  }, [onClose]);

  return (
    <div 
      ref={menuRef}
      className="context-menu"
      style={{ left: x, top: y }}
    >
      <div className="context-menu-header">{ticker}</div>
      
      <button className="context-menu-item" onClick={() => console.log('Load chart', ticker)}>
        <span className="menu-icon">📈</span>
        Load in Chart
      </button>
      
      <button className="context-menu-item" onClick={() => console.log('Add to watchlist', ticker)}>
        <span className="menu-icon">⭐</span>
        Add to Watchlist
      </button>
      
      <button className="context-menu-item" onClick={() => console.log('View news', ticker)}>
        <span className="menu-icon">📰</span>
        Latest News
      </button>
      
      <button className="context-menu-item" onClick={() => console.log('View financials', ticker)}>
        <span className="menu-icon">💰</span>
        Financials
      </button>
      
      <div className="context-menu-divider"></div>
      
      <button className="context-menu-item trade-action buy" onClick={() => console.log('Quick buy', ticker)}>
        <span className="menu-icon">🟢</span>
        Quick Buy
      </button>
      
      <button className="context-menu-item trade-action sell" onClick={() => console.log('Quick sell', ticker)}>
        <span className="menu-icon">🔴</span>
        Quick Sell
      </button>
    </div>
  );
};

export default ContextMenu;

