import React, { useEffect, useState } from 'react';
import './KeyboardShortcuts.css';

const KeyboardShortcuts: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      // Show shortcuts panel with ?
      if (e.key === '?' && !e.ctrlKey && !e.metaKey) {
        e.preventDefault();
        setIsOpen(true);
      }

      // Close with Escape
      if (e.key === 'Escape') {
        setIsOpen(false);
      }

      // Add other shortcuts here
      if (e.key === '/' || (e.ctrlKey && e.key === 'k')) {
        e.preventDefault();
        const searchInput = document.querySelector('.universal-search') as HTMLInputElement;
        searchInput?.focus();
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, []);

  if (!isOpen) return null;

  return (
    <div className="shortcuts-overlay" onClick={() => setIsOpen(false)}>
      <div className="shortcuts-panel" onClick={(e) => e.stopPropagation()}>
        <div className="shortcuts-header">
          <h3>⌨️ Keyboard Shortcuts</h3>
          <button className="close-btn" onClick={() => setIsOpen(false)}>✕</button>
        </div>

        <div className="shortcuts-content">
          <div className="shortcut-group">
            <h4>Navigation</h4>
            <div className="shortcut-item">
              <kbd>/</kbd>
              <span>Focus search</span>
            </div>
            <div className="shortcut-item">
              <kbd>Ctrl</kbd> + <kbd>K</kbd>
              <span>Focus search (alternate)</span>
            </div>
            <div className="shortcut-item">
              <kbd>Esc</kbd>
              <span>Clear/close</span>
            </div>
            <div className="shortcut-item">
              <kbd>?</kbd>
              <span>Show this help</span>
            </div>
          </div>

          <div className="shortcut-group">
            <h4>Actions</h4>
            <div className="shortcut-item">
              <kbd>Space</kbd>
              <span>Pause auto-scroll</span>
            </div>
            <div className="shortcut-item">
              <kbd>1</kbd> - <kbd>4</kbd>
              <span>Jump to zone</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default KeyboardShortcuts;
