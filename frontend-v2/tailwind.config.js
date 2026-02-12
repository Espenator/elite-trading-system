/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Trading-specific colors
        'bullish': '#10b981',
        'bearish': '#ef4444',
        'neutral': '#6b7280',
        // Regime colors
        'regime-green': '#22c55e',
        'regime-yellow': '#eab308',
        'regime-red': '#ef4444',
        // Dark theme
        'dark': {
          'bg': '#0f1117',
          'card': '#1a1d26',
          'border': '#2d3748',
          'hover': '#252a36',
        }
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
      },
      keyframes: {
        glow: {
          '0%': { boxShadow: '0 0 5px rgb(34 197 94 / 0.2)' },
          '100%': { boxShadow: '0 0 20px rgb(34 197 94 / 0.4)' },
        }
      }
    },
  },
  plugins: [],
}
