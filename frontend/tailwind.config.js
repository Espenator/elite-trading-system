/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx}"
  ],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        rubik: ['Rubik', 'sans-serif'],
        'league-spartan': ['League Spartan', 'sans-serif'],
        'league-spartan-bold': ['LeagueSpartan-Bold', 'sans-serif'],
      },
      colors: {
        // Legacy colors (backward compatibility)
        primary: '#5938CC',
        danger: '#ff0000',
        light: '#f2f2f2',
        gray: "#656565",
        
        // Theme system CSS variables
        'bg-primary': 'var(--bg-primary)',
        'bg-secondary': 'var(--bg-secondary)',
        'bg-tertiary': 'var(--bg-tertiary)',
        'text-primary': 'var(--text-primary)',
        'text-secondary': 'var(--text-secondary)',
        'accent-primary': 'var(--accent-primary)',
        'accent-secondary': 'var(--accent-secondary)',
        'success': 'var(--success)',
        'danger-theme': 'var(--danger)',
        'warning': 'var(--warning)',
      },
      animation: {
        'spin-slow': 'spin 3s linear infinite',
      }
    },
  },
  plugins: [],
}
