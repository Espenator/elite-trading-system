/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}", "./src/**/*.css"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "Cascadia Code", "monospace"],
      },
      colors: {
        primary: "#06b6d4",
        success: "#10b981",
        danger: "#ef4444",
        warning: "#f59e0b",
        dark: "#0B0E14",
        surface: "#111827",
        "surface-alt": "#1a1e2f",
        secondary: "#64748b",
        "card-border": "#1e293b",
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        glow: "glow 2s ease-in-out infinite alternate",
        "blink": "blink 1.5s infinite",
      },
      keyframes: {
        glow: {
          "0%": { boxShadow: "0 0 5px rgb(6 182 212 / 0.2)" },
          "100%": { boxShadow: "0 0 20px rgb(6 182 212 / 0.4)" },
        },
        blink: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.3" },
        },
      },
      fontSize: {
        "2xs": ["0.65rem", { lineHeight: "0.85rem" }],
      },
    },
  },
  plugins: [],
};