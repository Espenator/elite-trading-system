/** Tailwind config (CJS) — ensures loadable when package.json has "type": "module". */
module.exports = {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}", "./src/**/*.css"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "Cascadia Code", "monospace"],
      },
      colors: {
        primary: "#00D9FF",
        success: "#10B981",
        danger: "#EF4444",
        warning: "#F59E0B",
        dark: "#0B0E14",
        surface: "#111827",
        "surface-alt": "#1F2937",
        secondary: "#64748B",
        "card-border": "rgba(42,52,68,0.5)",
        aurora: {
          bg: "#0B0E1A",
          card: "#111827",
          "card-to": "#1F2937",
          border: "rgba(42,52,68,0.5)",
          primary: "#00D9FF",
          success: "#10B981",
          warning: "#F59E0B",
          danger: "#EF4444",
          text: "#F9FAFB",
          subtext: "#9CA3AF",
          muted: "#374151",
        },
        regime: {
          green: "#10B981",
          yellow: "#F59E0B",
          red: "#EF4444",
        },
      },
      borderRadius: { aurora: "8px" },
      boxShadow: {
        glow: "0 0 20px rgba(0,217,255,0.3)",
        "glow-hover": "0 0 20px rgba(0,217,255,0.5)",
        glass: "0 8px 32px rgba(0,0,0,0.3)",
      },
      backdropBlur: { glass: "16px" },
      backgroundImage: {
        "aurora-card": "linear-gradient(145deg, #111827, #1F2937)",
        "aurora-card-hover": "linear-gradient(145deg, #1a2236, #252f3f)",
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        glow: "glow 2s ease-in-out infinite alternate",
        blink: "blink 1.5s infinite",
        ticker: "ticker-scroll 60s linear infinite",
      },
      keyframes: {
        glow: {
          "0%": { boxShadow: "0 0 5px rgba(0,217,255,0.2)" },
          "100%": { boxShadow: "0 0 20px rgba(0,217,255,0.4)" },
        },
        blink: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.3" },
        },
        "ticker-scroll": {
          "0%": { transform: "translateX(0)" },
          "100%": { transform: "translateX(-50%)" },
        },
      },
      gridTemplateColumns: { 14: "repeat(14, minmax(0, 1fr))" },
      fontSize: { "2xs": ["0.65rem", { lineHeight: "0.85rem" }] },
    },
  },
  plugins: [],
};
