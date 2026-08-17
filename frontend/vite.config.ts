import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

/**
 * The API is served by Django. Proxying /api during dev and preview means the
 * frontend can run against a local backend without CORS or a rebuild, and
 * production keeps using same-origin relative URLs.
 */
const API_TARGET = process.env.VITE_DEV_API_TARGET || 'http://127.0.0.1:8000'

const proxy = {
  '/api': { target: API_TARGET, changeOrigin: true },
  '/ws': { target: API_TARGET, changeOrigin: true, ws: true },
}

export default defineConfig({
  plugins: [react()],
  server: { proxy },
  preview: { proxy },
})
