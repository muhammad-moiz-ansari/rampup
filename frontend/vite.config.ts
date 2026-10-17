import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '.', 'RAMPUP_')
  return {
    plugins: [react(), tailwindcss()],
    server: {
      proxy: {
        '/api': {
          target: env.RAMPUP_API_PROXY || 'http://localhost:8000',
          changeOrigin: true,
          headers: { Connection: 'close' },
        },
      },
    },
  }
})
