import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Backend origin for `npm run dev`. Override with:
//   VITE_BACKEND_ORIGIN=http://localhost:9005 npm run dev
const backendOrigin = process.env.VITE_BACKEND_ORIGIN || 'http://127.0.0.1:9005';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: backendOrigin, changeOrigin: true },
      '/ws': { target: backendOrigin, ws: true, changeOrigin: true },
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    rollupOptions: {
      output: {
        manualChunks: {
          react: ['react', 'react-dom'],
          recharts: ['recharts'],
        },
      },
    },
  },
});
