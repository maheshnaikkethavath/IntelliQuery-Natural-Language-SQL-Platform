export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"IBM Plex Sans"', "system-ui", "sans-serif"],
        mono: ['"IBM Plex Mono"', "ui-monospace", "monospace"],
      },
      colors: { ink: "#10202f", paper: "#f4f6f8", teal: { 600: "#0d7f74", 700: "#0a6860", 50: "#e8f5f3" } },
    },
  },
  plugins: [],
};
