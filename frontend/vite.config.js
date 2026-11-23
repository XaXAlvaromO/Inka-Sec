import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,
  },
  // Pruebas del frontend (Vitest + Testing Library). "npm run test:coverage" deja el reporte en coverage/.
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.js'],
    restoreMocks: true,
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'lcov'],
      include: ['src/**/*.{js,jsx}'],
      // main.jsx solo monta la app; ParticleNetwork es el fondo animado en canvas (jsdom no dibuja).
      exclude: ['src/main.jsx', 'src/ParticleNetwork.jsx', 'src/test/**', 'src/**/*.test.{js,jsx}'],
      // Si la cobertura baja de estos mínimos, "npm run test:coverage" falla (y el CI también).
      thresholds: { lines: 90, statements: 90, functions: 85, branches: 75 },
    },
  },
})
