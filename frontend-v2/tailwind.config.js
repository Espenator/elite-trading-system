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
        // ── Core accent (was #06b6d4 — CRITICAL FIX: now matches mockups exactly)
        primary: "#00D9FF",

        // ── Semantic status colors (exact mockup values)
        success: "#10B981",
        danger:  "#EF4444",
        warning: "#F59E0B",

        // ── Surface / background hierarchy
        dark:         "#0B0E14",  // outermost shell / page bg
        surface:      "#111827",  // sidebar, header, cards
        "surface-alt": "#1F2937", // card gradient endpoint, secondary panels
        secondary:    "#64748B",  // muted text, inactive icons

        // ── Border token (updated to match mockup rgba value)
        "card-border": "rgba(42,52,68,0.5)",

        // ── Aurora design language — full token set
        aurora: {
          bg:       "#0B0E1A",             // deepest background
          card:     "#111827",             // card base colour
          "card-to":"#1F2937",             // gradient endpoint
          border:   "rgba(42,52,68,0.5)",  // card border
          primary:  "#00D9FF",             // cyan accent — same as top-level primary
          success:  "#10B981",
          warning:  "#F59E0B",
          danger:   "#EF4444",
          text:     "#F9FAFB",             // primary text
          subtext:  "#9CA3AF",             // secondary / label text
          muted:    "#374151",             // muted / disabled
        },

        // ── Regime badge colours
        regime: {
          green:  "#10B981",
          yellow: "#F59E0B",
          red:    "#EF4444",
        },
      },

      borderRadius: {
        aurora: "8px",
      },

      boxShadow: {
        glow:  "0 0 20px rgba(0,217,255,0.3)",
        "glow-hover": "0 0 20px rgba(0,217,255,0.5)",
        glass: "0 8px 32px rgba(0,0,0,0.3)",
      },

      backdropBlur: {
        glass: "16px",
      },

      backgroundImage: {
        "aurora-card": "linear-gradient(145deg, #111827, #1F2937)",
        "aurora-card-hover": "linear-gradient(145deg, #1a2236, #252f3f)",
      },

      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        glow:         "glow 2s ease-in-out infinite alternate",
        blink:        "blink 1.5s infinite",
        "ticker":     "ticker-scroll 60s linear infinite",
      },

      keyframes: {
        glow: {
          "0%":   { boxShadow: "0 0 5px rgba(0,217,255,0.2)" },
          "100%": { boxShadow: "0 0 20px rgba(0,217,255,0.4)" },
        },
        blink: {
          "0%, 100%": { opacity: "1" },
          "50%":      { opacity: "0.3" },
        },
        "ticker-scroll": {
          "0%":   { transform: "translateX(0)" },
          "100%": { transform: "translateX(-50%)" },
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
