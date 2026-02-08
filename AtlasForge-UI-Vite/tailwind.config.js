/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        mongodb: {
          green: '#00684A',
          'green-dark': '#00463E',
          'green-light': '#00A35C',
          forest: '#001E2B',
          spring: '#00ED64',
          slate: '#889397',
          'slate-light': '#B8C4C2',
          'gray-light': '#F9FBFA',
        },
      },
    },
  },
  plugins: [],
}
