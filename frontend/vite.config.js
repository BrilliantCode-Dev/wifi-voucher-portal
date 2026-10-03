import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// `npm run build` writes straight into Django's static folder,
// so Django serves the dashboard at /dashboard/
export default defineConfig({
  plugins: [react()],
  base: '/static/dashboard/',
  build: {
    outDir: '../dashboard/static/dashboard',
    emptyOutDir: true,
    rollupOptions: {
      output: {
        entryFileNames: 'assets/app.js',
        chunkFileNames: 'assets/[name].js',
        assetFileNames: 'assets/app[extname]',
      },
    },
  },
  // `npm run dev`: run Django on :8000 too, and the dashboard on :5173 talks to it
  server: { proxy: { '/api': 'http://127.0.0.1:8000' } },
})
