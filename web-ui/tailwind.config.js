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
    extend: {},
  },
  plugins: [],
};
