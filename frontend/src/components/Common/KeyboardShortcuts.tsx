import React from 'react';
import React, { useState, useEffect } from 'react';
import { useKeyboardShortcuts } from '../../hooks/useKeyboardShortcuts';
import './KeyboardShortcuts.css';

const KeyboardShortcuts = () => {
  const [isOpen, setIsOpen] = useState(false);
  useKeyboardShortcuts();

  useEffect(() => {
    const handleQuestionMark = (e: KeyboardEvent) => {
      if (e.key === '?' && e.shiftKey) {
        setIsOpen(prev => !prev);
      }
    };

    window.addEventListener('keydown', handleQuestionMark);
    return () => window.removeEventListener('keydown', handleQuestionMark);
  }, []);

  if (!isOpen) return null;

  return (
    <div className="shortcuts-overlay" onClick={() => setIsOpen(false)}>
      <div className="shortcuts-panel" onClick={(e) => e.stopPropagation()}>
        <div className="shortcuts-header">
          <h3>⌨️ Keyboard Shortcuts</h3>
          <button className="close-btn" onClick={() => setIsOpen(false)}>✕</button>
        </div>

        <div className="shortcuts-grid">
          <div className="shortcut-item">
            <kbd>Ctrl</kbd> + <kbd>K</kbd> or <kbd>/</kbd>
            <span>Focus search</span>
          </div>
          <div className="shortcut-item">
            <kbd>Esc</kbd>
            <span>Clear search / Close modals</span>
          </div>
          <div className="shortcut-item">
            <kbd>?</kbd>
            <span>Show this panel</span>
          </div>
          <div className="shortcut-item">
            <kbd>Space</kbd>
            <span>Pause/Resume auto-scroll</span>
          </div>
          <div className="shortcut-item">
            <kbd>1</kbd> - <kbd>4</kbd>
            <span>Jump to Zone 1-4</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default KeyboardShortcuts;

