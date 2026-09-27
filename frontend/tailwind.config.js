/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        poke: {
          red: "#CC0000",
          yellow: "#FFCB05",
          blue: "#3B4CCA",
          dark: "#0f1117",
          card: "#1a1d26",
          border: "#2a2d3a",
          muted: "#6b7280",
        },
      },
    },
  },
  plugins: [],
};
