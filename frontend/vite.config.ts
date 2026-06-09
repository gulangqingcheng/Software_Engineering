import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': '/src'
    }
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8010',
        changeOrigin: true
      },
      '/uploads': {
        target: 'http://localhost:8010',
        changeOrigin: true
      }
    }
  }
})
