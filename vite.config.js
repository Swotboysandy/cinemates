import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { nodePolyfills } from 'vite-plugin-node-polyfills'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    nodePolyfills(),
  ],
  server: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: true, // Fail if port is busy, don't auto-switch
    allowedHosts: true, // Allow tunneling
  }
})
