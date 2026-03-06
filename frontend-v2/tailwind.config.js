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
        aurora: {
          bg: "#0B0E1A",
          card: "#111827",
          border: "rgba(42,52,68,0.5)",
          primary: "#00D9FF",
          success: "#10B981",
          warning: "#F59E0B",
          danger: "#EF4444",
          text: "#F9FAFB",
          subtext: "#9CA3AF",
          muted: "#374151",
        },
      },
      borderRadius: {
        aurora: "8px",
      },
      boxShadow: {
        glow: "0 0 20px rgba(0,217,255,0.3)",
        glass: "0 8px 32px rgba(0,0,0,0.3)",
      },
      backdropBlur: {
        glass: "16px",
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
      gridTemplateColumns: {
        14: "repeat(14, minmax(0, 1fr))",
      },
      fontSize: {
        "2xs": ["0.65rem", { lineHeight: "0.85rem" }],
      },
    },
  },
  plugins: [],
};