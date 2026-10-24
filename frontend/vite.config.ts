import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor-charts': ['recharts'],
          'vendor-icons': ['lucide-react'],
          'vendor-query': ['@tanstack/react-query'],
        },
      },
    },
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,
    watch: {
      usePolling: true,
      interval: 1000,
    },
  },
  preview: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,
  },
});
