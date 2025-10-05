import React from 'react'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import './App.css'

export function App() {
  const location = useLocation()
  const navigate = useNavigate()

  const isChatRoute = location.pathname.startsWith('/chat')
  const isAuthenticated = Boolean(localStorage.getItem('token'))

  const handleLogout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('userId')
    navigate('/')
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-container app-header-content">
          <div className="brand-mark" role="banner">
            <div className="brand-icon" aria-hidden="true">MC</div>
            <div className="brand-copy">
              <span className="brand-name">MCP Chat</span>
              <span className="brand-tagline">Conversational copilots for teams</span>
            </div>
          </div>
          <div className="header-actions">
            {isChatRoute && isAuthenticated ? (
              <button type="button" className="ghost-btn" onClick={handleLogout}>Logout</button>
            ) : (
              <button type="button" className="ghost-btn" onClick={() => navigate('/')}>Back to login</button>
            )}
            <button
              type="button"
              className="accent-btn"
              onClick={() => navigate('/chat')}
              disabled={!isAuthenticated}
            >
              Open workspace
            </button>
          </div>
        </div>
      </header>
      <main className="app-main">
        <div className="app-container">
          <Outlet />
        </div>
      </main>
      <footer className="app-footer">
        <div className="app-container">
          <span className="footer-note">© {new Date().getFullYear()} MCP Chat · Secure copilots for your organisation</span>
        </div>
      </footer>
    </div>
  )
}
