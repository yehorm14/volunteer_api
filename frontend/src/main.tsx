import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App'
import { AuthProvider } from './context/AuthContext'
import { API_CONFIG_ERROR } from './services/api'

const root = createRoot(document.getElementById('root')!)

if (API_CONFIG_ERROR) {
  root.render(
    <div className="min-h-screen flex items-center justify-center p-6">
      <div role="alert" className="max-w-md p-5 border border-red-500/30 bg-red-500/10 rounded-xl">
        <h1 className="text-lg font-semibold text-slate-100">Configuration error</h1>
        <p className="mt-2 text-sm text-red-300">{API_CONFIG_ERROR}</p>
      </div>
    </div>
  )
} else {
  root.render(
    <StrictMode>
      <AuthProvider>
        <App />
      </AuthProvider>
    </StrictMode>
  )
}
