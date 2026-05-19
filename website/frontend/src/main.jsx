import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import App from './App.jsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: '#12121A',
            color: '#E2E8F0',
            border: '1px solid #1E1E2E',
            borderRadius: '12px',
          },
          success: {
            iconTheme: { primary: '#10B981', secondary: '#12121A' },
          },
          error: {
            iconTheme: { primary: '#EF4444', secondary: '#12121A' },
          },
        }}
      />
    </BrowserRouter>
  </React.StrictMode>
)
