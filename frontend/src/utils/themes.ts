export const themes = {
  'elite-dark': {
    name: 'Elite Dark',
    background: '#0A0E1A',
    surface: '#1A1F2E',
    accent: '#00D9FF',
    accentSecondary: '#7C3AED',
    bull: '#10B981',
    bear: '#EF4444',
    textPrimary: '#F8FAFC',
    textSecondary: '#94A3B8',
  },
  'pure-black': {
    name: 'Pure Black',
    background: '#000000',
    surface: '#0D0D0D',
    accent: '#00FF88',
    accentSecondary: '#FF00FF',
    bull: '#00FF00',
    bear: '#FF0000',
    textPrimary: '#FFFFFF',
    textSecondary: '#888888',
  },
  'navy-blue': {
    name: 'Navy Blue',
    background: '#001233',
    surface: '#002855',
    accent: '#4A90E2',
    accentSecondary: '#50E3C2',
    bull: '#00D084',
    bear: '#FF3B30',
    textPrimary: '#E8F4FD',
    textSecondary: '#7FB3D5',
  },
  'terminal-green': {
    name: 'Terminal Green',
    background: '#0D1B0D',
    surface: '#1A2E1A',
    accent: '#00FF00',
    accentSecondary: '#00FFFF',
    bull: '#00FF00',
    bear: '#FF0000',
    textPrimary: '#00FF00',
    textSecondary: '#008800',
  },
  'high-contrast': {
    name: 'High Contrast',
    background: '#000000',
    surface: '#1A1A1A',
    accent: '#FFFF00',
    accentSecondary: '#FF00FF',
    bull: '#00FF00',
    bear: '#FF0000',
    textPrimary: '#FFFFFF',
    textSecondary: '#CCCCCC',
  },
};

export const applyTheme = (themeName: keyof typeof themes) => {
  const theme = themes[themeName];
  const root = document.documentElement;
  
  root.style.setProperty('--bg-primary', theme.background);
  root.style.setProperty('--bg-surface', theme.surface);
  root.style.setProperty('--accent-primary', theme.accent);
  root.style.setProperty('--accent-secondary', theme.accentSecondary);
  root.style.setProperty('--color-bull', theme.bull);
  root.style.setProperty('--color-bear', theme.bear);
  root.style.setProperty('--text-primary', theme.textPrimary);
  root.style.setProperty('--text-secondary', theme.textSecondary);
  
  localStorage.setItem('elite-theme', themeName);
};
