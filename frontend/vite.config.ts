/// <reference types="vitest/config" />
/**
 * Vite and Vitest config. The dev server proxies /api and /media to the Django backend so the browser sees one origin.
 *
 * Miesign · Author: Mihir Kapildev Tiwari
 */

import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

const BACKEND = 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react()],
  server: { proxy: { '/api': BACKEND, '/media': BACKEND } },
  test: { environment: 'node' },
})
