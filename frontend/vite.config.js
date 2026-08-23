import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Requests to /api are proxied to the Flask server, so the browser sees a single
// origin during development and no CORS preflight is involved.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
      },
    },
  },
})
