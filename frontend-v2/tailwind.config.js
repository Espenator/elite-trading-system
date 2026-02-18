/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
    "./src/**/*.css",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Sarala', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      colors: {
        primary: '#06b6d4',
        success: '#22c55e',
        danger: '#ef4444',
        warning: '#eab308',
        dark: '#0f1117',
        secondary: '#6b7280',
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
