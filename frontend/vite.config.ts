import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

const backend = `127.0.0.1:${process.env.AIGORA_BACKEND_PORT ?? '8765'}`

export default defineConfig({
  plugins: [vue()],
  // App icon and favicons come from assets/brand (ticket 15); served at the site root.
  publicDir: '../assets/brand',
  server: {
    host: '127.0.0.1',
    port: 5173,
    proxy: {
      '/api': { target: `http://${backend}` },
      '/ws': { target: `ws://${backend}`, ws: true },
    },
  },
})
