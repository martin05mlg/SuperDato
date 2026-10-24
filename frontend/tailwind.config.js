/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        mercadona: {
          green: "#007A3D",
          lightGreen: "#00A651",
          yellow: "#FFB81C",
          dark: "#1B3624",
        }
      }
    },
  },
  plugins: [],
}

