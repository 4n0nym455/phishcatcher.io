/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        heading: ['Syne', 'system-ui', 'sans-serif'],
        body:    ['DM Sans', 'system-ui', 'sans-serif'],
      },
      fontWeight: {
        300: '300',
        400: '400',
        500: '500',
        600: '600',
        700: '700',
        800: '800',
      },
      colors: {
        /* CSS-variable mapped colors — use these in Tailwind classes */
        brand: {
          DEFAULT: 'var(--brand)',
          hover:   'var(--brand-hover)',
          subtle:  'var(--brand-subtle)',
          dim:     'var(--brand-dim)',
        },
        threat: {
          DEFAULT: 'var(--threat)',
          hover:   'var(--threat-hover)',
          subtle:  'var(--threat-subtle)',
          dim:     'var(--threat-dim)',
        },
        danger: {
          DEFAULT: 'var(--danger)',
          subtle:  'var(--danger-subtle)',
          dim:     'var(--danger-dim)',
        },
        success: {
          DEFAULT: 'var(--success)',
          subtle:  'var(--success-subtle)',
          dim:     'var(--success-dim)',
        },
        surface:   'var(--bg-surface)',
        elevated:  'var(--bg-elevated)',
        base:      'var(--bg-base)',
        primary:   'var(--text-primary)',
        secondary: 'var(--text-secondary)',
        muted:     'var(--text-muted)',
        border:    'var(--border)',
      },
      borderRadius: {
        xl:  '12px',
        '2xl': '16px',
        '3xl': '20px',
        '4xl': '24px',
      },
      boxShadow: {
        sm:   'var(--shadow-sm)',
        md:   'var(--shadow-md)',
        lg:   'var(--shadow-lg)',
        glow: 'var(--shadow-glow)',
      },
      animation: {
        'fade-in':  'fadeIn 0.35s ease both',
        'slide-up': 'slideUp 0.4s ease both',
        'spin':     'spin 1s linear infinite',
      },
      keyframes: {
        fadeIn: {
          from: { opacity: '0', transform: 'translateY(6px)' },
          to:   { opacity: '1', transform: 'translateY(0)' },
        },
        slideUp: {
          from: { opacity: '0', transform: 'translateY(16px)' },
          to:   { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
};