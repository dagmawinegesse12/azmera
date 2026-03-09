import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/features/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Azmera dark palette — matches existing Streamlit brand
        background: {
          DEFAULT: "#05080f",
          surface: "#080e1a",
          elevated: "#0f1623",
          border: "#1e2a3d",
          subtle: "#0a0e18",
        },
        text: {
          primary: "#e0e8f0",
          secondary: "#c8d8e8",
          muted: "#7a90a8",
          faint: "#4a6080",
        },
        accent: {
          green: "#27ae60",
          "green-light": "#4a9060",
          "green-dark": "#1a6b40",
        },
        forecast: {
          below: "#e74c3c",   // Below Normal / drought
          near: "#d4a017",    // Near Normal
          above: "#27ae60",   // Above Normal
          "below-bg": "rgba(231, 76, 60, 0.12)",
          "near-bg": "rgba(212, 160, 23, 0.12)",
          "above-bg": "rgba(39, 174, 96, 0.12)",
        },
        tier: {
          full: "#27ae60",          // Full — green
          "full-bg": "rgba(39, 174, 96, 0.10)",
          experimental: "#d4a017", // Experimental — amber
          "experimental-bg": "rgba(212, 160, 23, 0.10)",
          suppressed: "#e74c3c",   // Suppressed — red
          "suppressed-bg": "rgba(231, 76, 60, 0.10)",
        },
      },
      fontFamily: {
        sans: ["Sora", "system-ui", "sans-serif"],
        serif: ["Playfair Display", "Georgia", "serif"],
        ethiopic: ["Noto Sans Ethiopic", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },
      borderRadius: {
        lg: "14px",
        xl: "20px",
        "2xl": "28px",
      },
      animation: {
        "fade-up": "fadeUp 0.6s ease both",
        "pulse-soft": "pulseSoft 2s ease-in-out infinite",
        shimmer: "shimmer 1.5s infinite",
      },
      keyframes: {
        fadeUp: {
          from: { opacity: "0", transform: "translateY(20px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        pulseSoft: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.6" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
