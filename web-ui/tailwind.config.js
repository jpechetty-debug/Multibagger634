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
        'brand-base': '#0B0F14',
        'brand-card': '#111827',
        'brand-border': '#1F2937',
        'brand-accent': '#00E5FF',
        'brand-positive': '#00FF88',
        'brand-negative': '#FF4D4F',
      }
    },
  },
  plugins: [],
};
