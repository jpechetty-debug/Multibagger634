/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  corePlugins: {
    // Disabled to match the previous CDN config (cdn.tailwindcss.com with
    // corePlugins.preflight=false) — index.css already ships its own
    // reset/base styles that Tailwind's preflight would otherwise conflict with.
    preflight: false,
  },
  theme: {
    extend: {
      colors: {
        'brand-base': 'var(--surface)',
        'brand-card': 'var(--surface-container-lowest)',
        'brand-border': 'var(--wire)',
        'brand-accent': 'var(--primary)',
        'brand-positive': 'var(--secondary)',
        'brand-negative': 'var(--error)',
        white: 'var(--on-surface)',
        black: 'var(--surface-container-lowest)',
        slate: {
          300: 'var(--on-surface)',
          400: 'var(--on-surface-variant)',
          500: 'var(--outline)',
          700: 'var(--surface-container-high)',
          800: 'var(--surface-container)',
          900: 'var(--surface-container-low)',
        },
        emerald: {
          400: 'var(--secondary)',
          500: 'var(--secondary-container)',
        },
        rose: {
          400: 'var(--error)',
        },
        red: {
          300: 'var(--on-error-container)',
          400: 'var(--error)',
          500: 'var(--error-container)',
        },
        amber: {
          400: '#b8860b',
        }
      }
    },
  },
  plugins: [],
};
