import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { Toaster } from 'sonner'
import { CheckCircle, AlertCircle, X } from 'lucide-react'
import './styles/globals.css'
import App from './App.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
    <Toaster 
      position="top-right"
      toastOptions={{
        style: {
          background: '#0F1635',
          border: '1px solid rgba(123, 97, 255, 0.25)',
          color: '#ffffff',
          fontSize: '14px',
          fontWeight: '500',
        },
        success: {
          icon: <CheckCircle className="w-4 h-4 text-green-500" />,
          style: {
            background: '#10b981',
            border: '1px solid rgba(16, 185, 129, 0.25)',
            color: '#ffffff',
          },
        },
        error: {
          icon: <AlertCircle className="w-4 h-4 text-red-500" />,
          style: {
            background: '#dc2626',
            border: '1px solid rgba(220, 38, 38, 0.25)',
            color: '#ffffff',
          },
        },
        action: {
          icon: <X className="w-3 h-3 text-white" />,
          style: {
            background: 'rgba(255, 255, 255, 0.1)',
          },
        },
      }}
    />
  </StrictMode>
)
