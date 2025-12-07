import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './lib/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Dark theme for trading dashboard
        'slate-950': '#0f172a',
        'slate-900': '#0f172a',
        'slate-800': '#1e293b',
        'slate-700': '#334155',
        'slate-600': '#475569',
        'slate-400': '#cbd5e1',
        'slate-300': '#e2e8f0',

        // Trading colors
        'bullish': '#10b981',
        'bearish': '#ef4444',
        'neutral': '#64748b',
        'signal-compression': '#f59e0b',
        'signal-ignition': '#ef4444',
      },
      backgroundColor: {
        'glass': 'rgba(15, 23, 42, 0.6)',
        'glass-light': 'rgba(30, 41, 59, 0.5)',
      },
      backdropBlur: {
        'glass': '10px',
      },
      borderColor: {
        'glass': 'rgba(71, 85, 105, 0.3)',
      },
      boxShadow: {
        'glass': '0 8px 32px 0 rgba(31, 38, 135, 0.37)',
        'chart': '0 4px 6px rgba(0, 0, 0, 0.1)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'pulse-fast': 'pulse 1s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      keyframes: {
        'signal-flash': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.5' },
        },
      },
    },
  },
  plugins: [],
  darkMode: 'class',
};

export default config;
