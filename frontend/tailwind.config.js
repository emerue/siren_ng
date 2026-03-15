/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        primary:     '#C0392B',
        success:     '#1A6B3C',
        warning:     '#D35400',
        bg:          '#FAFAFA',
        surface:     '#FFFFFF',
        textPrimary: '#0D0D0D',
        textBody:    '#4A4A4A',
        textMuted:   '#9E9E9E',
        border:      '#E8E8E8',
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
