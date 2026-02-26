/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#0f172a", // Dark blue/slate background
        surface: "#1e293b",    // Lighter surface for cards
        primary: "#0ea5e9",    // Cyan/Blue
        secondary: "#10b981",  // Green
        accent: "#f43f5e",     // Red/Pink for loss
        muted: "#64748b",      // Muted text
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      }
    },
  },
  plugins: [],
}