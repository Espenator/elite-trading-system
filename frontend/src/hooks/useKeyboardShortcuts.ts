import { useEffect } from 'react';

export const useKeyboardShortcuts = () => {
  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      // Search focus
      if ((e.ctrlKey && e.key === 'k') || e.key === '/') {
        e.preventDefault();
        const searchInput = document.querySelector('.universal-search') as HTMLInputElement;
        searchInput?.focus();
      }

      // Clear/close on Escape
      if (e.key === 'Escape') {
        const searchInput = document.querySelector('.universal-search') as HTMLInputElement;
        if (searchInput) {
          searchInput.value = '';
          searchInput.blur();
        }
        // Close any open modals
        const modals = document.querySelectorAll('.settings-overlay');
        modals.forEach(modal => {
          (modal as HTMLElement).style.display = 'none';
        });
      }

      // Zone navigation with number keys
      if (e.key >= '1' && e.key <= '4' && !e.ctrlKey && !e.altKey) {
        const zones = ['.zone-1', '.zone-2', '.zone-3', '.zone-4'];
        const zoneIndex = parseInt(e.key) - 1;
        const zone = document.querySelector(zones[zoneIndex]) as HTMLElement;
        if (zone) {
          zone.scrollIntoView({ behavior: 'smooth', block: 'center' });
          zone.style.boxShadow = '0 0 32px rgba(0, 217, 255, 0.5)';
          setTimeout(() => {
            zone.style.boxShadow = '';
          }, 1000);
        }
      }

      // Pause auto-scroll with Space (when not in input)
      if (e.key === ' ' && e.target === document.body) {
        e.preventDefault();
        const pauseBtn = document.querySelector('.pause-btn') as HTMLButtonElement;
        pauseBtn?.click();
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, []);
};

export default useKeyboardShortcuts;
