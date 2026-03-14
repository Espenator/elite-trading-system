import { useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';

/**
 * Global keyboard shortcuts for power trading.
 * Disabled when focus is in input/textarea/select.
 */
export default function useKeyboardShortcuts() {
  const navigate = useNavigate();

  const handleKeyDown = useCallback((e) => {
    // Skip if user is typing in an input
    const tag = document.activeElement?.tagName;
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
    if (document.activeElement?.contentEditable === 'true') return;

    const key = e.key;
    const ctrl = e.ctrlKey || e.metaKey;

    // Navigation: Ctrl+1-9
    if (ctrl && key >= '1' && key <= '9') {
      e.preventDefault();
      const routes = [
        '/dashboard',              // Ctrl+1
        '/agents',                 // Ctrl+2
        '/signal-intelligence-v3', // Ctrl+3
        '/trades',                 // Ctrl+4
        '/risk',                   // Ctrl+5
        '/performance',            // Ctrl+6
        '/market-regime',          // Ctrl+7
        '/settings',               // Ctrl+8
        '/ml-brain',               // Ctrl+9
      ];
      const idx = parseInt(key) - 1;
      if (routes[idx]) navigate(routes[idx]);
      return;
    }

    // Refresh all: R (no modifier)
    if (key === 'r' && !ctrl && !e.altKey) {
      // Dispatch a custom event that useApi hooks can listen to
      window.dispatchEvent(new CustomEvent('app:refresh'));
      return;
    }

    // Escape: close any modal/panel
    if (key === 'Escape') {
      window.dispatchEvent(new CustomEvent('app:escape'));
      return;
    }

    // ? : Toggle shortcut help
    if (key === '?' && !ctrl) {
      window.dispatchEvent(new CustomEvent('app:toggle-shortcuts'));
      return;
    }
  }, [navigate]);

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);
}
