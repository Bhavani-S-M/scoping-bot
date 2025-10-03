/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        //  Light mode palette
        primary: "#0d9488",   // Teal-600
        secondary: "#f97316", // Orange-500
        accent: "#14b8a6",    // Teal-500
        muted: "#64748b",     // Slate-500
        background: "#f1f5f9", // Slate-50
        surface: "#ffffff",   // White

        // Dark mode palette
        dark: {
          primary: "#2dd4bf",   // Teal-400
          secondary: "#fb923c", // Orange-400
          accent: "#5eead4",    // Teal-300
          muted: "#94a3b8",     // Slate-400
          background: "#0f172a", // Slate-900
          surface: "#1e293b",   // Slate-800
        },
      },
      fontFamily: {
        sans: ["'Nunito Sans'", "system-ui", "sans-serif"],
        heading: ["'Poppins'", "system-ui", "sans-serif"],
      },
      boxShadow: {
        soft: "0 4px 10px rgba(0,0,0,0.05)",
        dark: "0 4px 15px rgba(0,0,0,0.4)",
      },
      borderRadius: {
        xl: "1rem",
      },
    },
  },
  plugins: [],
};

