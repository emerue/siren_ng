/** @type {import('tailwindcss').Config} */

/**
 * SIREN.NG DESIGN SYSTEM
 *
 * Principles (in order): Clarity → Trust → Action → Beauty.
 *
 * Colour doctrine for an emergency product:
 *   - Navy is the brand and the default action colour. It reads institutional
 *     and calm — the emotional target is confidence, not alarm.
 *   - Red is RESERVED for genuine criticality (critical severity, destructive
 *     actions, errors). It is never decorative, never a hover state, never a
 *     brand colour. A product that shouts everywhere cannot shout when it matters.
 *   - Status colours map to the real incident lifecycle and are the single
 *     source of truth for status rendering (see components/StatusPill).
 *   - Colour never carries meaning alone: every status pairs colour + icon + label.
 */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // ── Brand ───────────────────────────────────────────────────────────
        // Full ramp so hover/active/subtle states are systematic, not ad-hoc.
        primary: {
          50:  '#F2F5FA',
          100: '#E3E9F3',
          200: '#C2CEE3',
          300: '#93A7CA',
          400: '#5C77A6',
          500: '#365285',
          600: '#25406D',
          700: '#1B2A4A', // Siren Navy — canonical brand
          800: '#152039',
          900: '#0F1729',
          DEFAULT: '#1B2A4A',
        },
        accent: {
          50:  '#FEF8EC',
          100: '#FCEECC',
          300: '#F3CC7A',
          500: '#E8A020', // Siren Amber — sparing emphasis only
          600: '#C4820F',
          DEFAULT: '#E8A020',
        },

        // ── Incident status (lifecycle) ─────────────────────────────────────
        status: {
          detected:  '#8A6D2F', // awaiting human review — deliberately uncertain
          verifying: '#8A6D2F',
          verified:  '#1D4ED8', // a human confirmed it
          alerted:   '#0F766E', // neighbours notified
          notified:  '#6D28D9', // authorities notified
          resolved:  '#15803D', // closed
          rejected:  '#6B7280', // not an emergency
        },

        // ── Severity (only ever describes the incident itself) ──────────────
        severity: {
          low:      '#8A6D2F',
          medium:   '#B45309',
          high:     '#C2410C',
          critical: '#B91C1C', // the one true red
        },

        // ── Feedback ────────────────────────────────────────────────────────
        success:  '#15803D',
        warning:  '#B45309',
        critical: '#B91C1C',
        info:     '#1D4ED8',

        // ── Surfaces & text ─────────────────────────────────────────────────
        canvas:   '#F7F8FA', // page background
        surface:  '#FFFFFF', // cards / panels
        sunken:   '#F1F3F7', // wells, subtle grouping
        ink: {
          DEFAULT: '#111827', // primary text
          body:    '#3C4657', // body copy
          muted:   '#6B7280', // meta / captions — 4.83:1 on white
          /**
           * Timestamps, overlines, source attributions. Kept dark enough to
           * pass WCAG AA (5.17:1 on white, 4.65:1 on sunken); the earlier
           * #9AA3B2 was only 2.54:1 and failed for this small text.
           * De-emphasis is carried by size and weight, not by low contrast.
           */
          faint:   '#656E7A',
          invert:  '#FFFFFF',
        },
        line: {
          DEFAULT: '#E4E7EC', // hairline borders
          strong:  '#CDD3DC',
        },

        // Legacy aliases — keep older pages compiling during the migration.
        bg: '#F7F8FA',
        textPrimary: '#111827',
        textBody: '#3C4657',
        textMuted: '#6B7280',
        border: '#E4E7EC',
        alert: '#B91C1C',
        verified: '#1D4ED8',
        guardian: '#0F766E',
        commute: '#0284C7',
      },

      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
      },

      /**
       * Type scale. Display sizes carry negative tracking — the single biggest
       * lever between "template" and "designed" typography at large sizes.
       */
      fontSize: {
        'display-xl': ['3.5rem',  { lineHeight: '1.04', letterSpacing: '-0.033em', fontWeight: '700' }],
        'display-lg': ['2.75rem', { lineHeight: '1.08', letterSpacing: '-0.03em',  fontWeight: '700' }],
        'display':    ['2.25rem', { lineHeight: '1.12', letterSpacing: '-0.025em', fontWeight: '700' }],
        'h1':         ['1.875rem',{ lineHeight: '1.2',  letterSpacing: '-0.02em',  fontWeight: '700' }],
        'h2':         ['1.5rem',  { lineHeight: '1.25', letterSpacing: '-0.015em', fontWeight: '650' }],
        'h3':         ['1.125rem',{ lineHeight: '1.35', letterSpacing: '-0.01em',  fontWeight: '600' }],
        'body-lg':    ['1.0625rem',{ lineHeight: '1.6', letterSpacing: '-0.005em' }],
        'body':       ['0.9375rem',{ lineHeight: '1.6' }],
        'sm':         ['0.875rem', { lineHeight: '1.55' }],
        'caption':    ['0.8125rem',{ lineHeight: '1.45' }],
        'overline':   ['0.6875rem',{ lineHeight: '1.2', letterSpacing: '0.09em', fontWeight: '600' }],
      },

      // Restrained radii. Nothing is a pill unless it is genuinely a pill.
      borderRadius: {
        sm: '0.25rem',
        DEFAULT: '0.375rem',
        md: '0.5rem',
        lg: '0.75rem',
        xl: '1rem',
      },

      /**
       * Shadows are structural, not decorative. Two levels plus a focus ring.
       * Sophistication comes from spacing and type, not from glow.
       */
      boxShadow: {
        xs: '0 1px 2px 0 rgb(16 24 40 / 0.04)',
        sm: '0 1px 3px 0 rgb(16 24 40 / 0.06), 0 1px 2px -1px rgb(16 24 40 / 0.04)',
        md: '0 4px 12px -2px rgb(16 24 40 / 0.08), 0 2px 4px -2px rgb(16 24 40 / 0.04)',
        none: 'none',
      },

      maxWidth: {
        content: '68rem', // page shell
        prose: '42rem',   // readable measure (~70ch)
      },

      // Vertical rhythm for page sections.
      spacing: {
        section: '4.5rem',
        'section-lg': '6rem',
      },

      transitionDuration: {
        fast: '150ms',
        DEFAULT: '200ms',
      },

      keyframes: {
        'fade-up': {
          from: { opacity: '0', transform: 'translateY(4px)' },
          to:   { opacity: '1', transform: 'translateY(0)' },
        },
        shimmer: {
          '100%': { transform: 'translateX(100%)' },
        },
      },
      animation: {
        'fade-up': 'fade-up 200ms ease-out both',
        shimmer: 'shimmer 1.6s infinite',
      },
    },
  },
  plugins: [],
}
