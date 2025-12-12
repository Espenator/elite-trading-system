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
        primary: '#5938CC',
        danger: '#ff0000',
        light: '#f2f2f2',
        gray: "#656565"
      },
      animation: {
        'spin-slow': 'spin 3s linear infinite',
      }
    },
  },
  plugins: [],
}