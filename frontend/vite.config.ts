import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

// Use localhost for local dev, Docker service name is handled by nginx in production
const API_TARGET = process.env.VITE_API_URL || 'http://localhost:8000'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    port: 5173,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: API_TARGET,
        changeOrigin: true,
      }
    }
  },
  build: {
    target: 'es2022',
    minify: 'esbuild',
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor': ['vue', 'vue-router', 'pinia'],
          'charts': ['chart.js', 'vue-chartjs'],
        }
      }
    }
  }
})
