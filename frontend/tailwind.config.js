/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{ts,tsx,js,jsx}',
  ],
  theme: {
    extend: {
      colors: {
        surface: '#0b0f1a',
        panel: '#11182a',
        accent: '#7dd3fc',
        muted: '#9ca3af',
      },
      boxShadow: {
        panel: '0 15px 30px rgba(0, 0, 0, 0.35)',
      },
    },
  },
  plugins: [],
};
