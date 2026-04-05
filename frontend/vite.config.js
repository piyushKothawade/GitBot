import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    // Dev proxy — routes /chat and /health to local FastAPI backend
    proxy: {
      '/chat':   'http://localhost:8000',
      '/health': 'http://localhost:8000',
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    // Chunk splitting for better caching
    rollupOptions: {
      output: {
        manualChunks: {
          vendor:   ['react', 'react-dom'],
          markdown: ['react-markdown', 'remark-gfm'],
        }
      }
    }
  },
  // In production, API calls go to /chat/... which Vercel rewrites
  // to the HF Space backend — no CORS needed since same-origin
  define: {
    __API_BASE__: JSON.stringify(''),
  }
})
