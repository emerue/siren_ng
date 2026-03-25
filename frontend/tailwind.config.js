/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // Brand
        primary: '#1B2A4A',  // Siren Navy — buttons, nav, headings
        accent: '#E8A020',  // Siren Amber — highlights, Guardian accents

        // Status (incidents only — never decorative)
        alert: '#DC2626',  // CRITICAL severity only
        warning: '#EA580C',  // HIGH severity
        caution: '#D97706',  // MEDIUM / VERIFYING
        success: '#16A34A',  // RESOLVED / SAFE / ARRIVED
        verified: '#2563EB',  // VERIFIED status
        agency: '#7C3AED',  // AGENCY_NOTIFIED
        rejected: '#9CA3AF',  // REJECTED

        // Feature identity
        guardian: '#0D9488',  // Guardian Mode UI
        commute: '#0284C7',  // Commute Shield UI

        // Surfaces
        bg: '#F8F7F5',  // Warm white background
        surface: '#FFFFFF',  // Cards

        // Text
        textPrimary: '#111827',
        textBody: '#374151',
        textMuted: '#6B7280',

        // Border
        border: '#E5E7EB',
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      },
    },
  },
  plugins: [],
}