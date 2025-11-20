import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1', // Explicitly bind to 127.0.0.1
    port: 5173,
    proxy: {
      '/auth': {
        target: 'http://127.0.0.1:3001',
        changeOrigin: true,
        cookieDomainRewrite: ''
      },
      '/api': {
        target: 'http://127.0.0.1:3001',
        changeOrigin: true,
        cookieDomainRewrite: ''
      }
    }
  }
})
