/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      boxShadow: {
        glow: "0 0 40px rgba(244, 63, 94, 0.35)",
        glowcyan: "0 0 36px rgba(34, 211, 238, 0.35)",
      },
      keyframes: {
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        siren: {
          "0%,100%": { opacity: "1", filter: "brightness(1.2)" },
          "50%": { opacity: "0.85", filter: "brightness(1.8)" },
        },
        pulseGlow: {
          "0%,100%": { boxShadow: "0 0 20px rgba(244,63,94,0.5)" },
          "50%": { boxShadow: "0 0 55px rgba(244,63,94,0.95)" },
        },
      },
      animation: {
        shimmer: "shimmer 2.2s linear infinite",
        siren: "siren 1.1s ease-in-out infinite",
        pulseGlow: "pulseGlow 2s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
