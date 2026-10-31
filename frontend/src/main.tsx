/**
 * Browser entry point: loads the design tokens and styles and mounts the app.
 *
 * Miesign · Author: Mihir Kapildev Tiwari
 */

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import './tokens.css'
import './styles.css'

const root = document.getElementById('root')
if (root) {
  createRoot(root).render(
    <StrictMode>
      <App />
    </StrictMode>,
  )
}
