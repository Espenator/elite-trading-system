import React, { createContext, useContext, useEffect, useState } from 'react';

const ThemeContext = createContext();

// DARK THEME (original)
const DARK_COLORS = {
  '--bg-primary': '#0a0e27',
  '--bg-secondary': '#1a1f3a',
  '--bg-tertiary': '#252b4a',
  '--text-primary': '#e2e8f0',
  '--text-secondary': '#94a3b8',
  '--accent-primary': '#00d9ff',
  '--accent-secondary': '#a78bfa',
  '--success': '#10b981',
  '--danger': '#ef4444',
  '--warning': '#f59e0b',
};

// LIGHT THEME (new)
const LIGHT_COLORS = {
  '--bg-primary': '#ffffff',
  '--bg-secondary': '#f8fafc',
  '--bg-tertiary': '#e2e8f0',
  '--text-primary': '#1e293b',
  '--text-secondary': '#64748b',
  '--accent-primary': '#0ea5e9',
  '--accent-secondary': '#8b5cf6',
  '--success': '#10b981',
  '--danger': '#ef4444',
  '--warning': '#f59e0b',
};

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState('dark');
  const [mounted, setMounted] = useState(false);

  // Load from localStorage on mount
  useEffect(() => {
    const savedTheme = localStorage.getItem('elite-trader-theme');
    if (savedTheme) {
      setTheme(savedTheme);
      applyTheme(savedTheme);
    } else {
      // Check system preference
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      const initialTheme = prefersDark ? 'dark' : 'light';
      setTheme(initialTheme);
      applyTheme(initialTheme);
    }
    setMounted(true);
  }, []);

  // Apply theme to document
  const applyTheme = (themeName) => {
    const colors = themeName === 'dark' ? DARK_COLORS : LIGHT_COLORS;
    const root = document.documentElement;

    // Set CSS variables
    Object.entries(colors).forEach(([key, value]) => {
      root.style.setProperty(key, value);
    });

    // Set data attribute for Tailwind
    if (themeName === 'dark') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }

    // Save to localStorage
    localStorage.setItem('elite-trader-theme', themeName);
  };

  const toggleTheme = () => {
    const newTheme = theme === 'dark' ? 'light' : 'dark';
    setTheme(newTheme);
    applyTheme(newTheme);
  };

  const setThemeMode = (themeName) => {
    if (themeName === 'dark' || themeName === 'light') {
      setTheme(themeName);
      applyTheme(themeName);
    }
  };

  const value = {
    theme,
    toggleTheme,
    setTheme: setThemeMode,
    isDark: theme === 'dark',
    isLight: theme === 'light',
    colors: theme === 'dark' ? DARK_COLORS : LIGHT_COLORS,
  };

  // Prevent render until mounted (avoid hydration mismatch)
  if (!mounted) {
    return <>{children}</>;
  }

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider');
  }
  return context;
}
