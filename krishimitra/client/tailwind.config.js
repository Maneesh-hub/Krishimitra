export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: { extend: {
    colors: { leaf: { DEFAULT: "#1F6B45", dark: "#17523a", light: "#e4f1ea" }, cream: "#F7F8F2", ink: "#1F2933", amber: { DEFAULT: "#E6A23C", light: "#fdf1dc" } },
    screens: { sm: "640px", lg: "1024px" },
    fontFamily: { sans: ["Noto Sans", "Noto Sans Telugu", "Noto Sans Devanagari", "system-ui", "Segoe UI", "Roboto", "sans-serif"] },
  } },
  plugins: [],
};
