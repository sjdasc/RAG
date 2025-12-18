/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        space: {
          dark: "#000000", // Pure Black
          light: "#111111", // Dark Gray for cards/sidebars
          accent: "#FFFFFF", // White for accents/buttons
          text: "#EDEDED", // Off-white for text
          border: "#333333", // Subtle border
        },
      },
      backgroundImage: {
        "space-gradient": "none", // Remove gradient
      },
      keyframes: {
        "fade-in-up": {
          "0%": {
            opacity: "0",
            transform: "translateY(10px)",
          },
          "100%": {
            opacity: "1",
            transform: "translateY(0)",
          },
        },
      },
      animation: {
        "fade-in-up": "fade-in-up 0.5s ease-out",
      },
    },
  },
  plugins: [],
};
