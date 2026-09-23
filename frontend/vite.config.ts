import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    // In dev the backend runs on :8000; in prod FastAPI serves frontend/dist itself (same origin).
    proxy: { '/api': 'http://localhost:8000' },
  },
})
