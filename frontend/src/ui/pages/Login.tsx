import React, { FormEvent, useCallback, useState } from 'react'
import { useNavigate } from 'react-router-dom'

const apiBase = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000'

export function Login() {
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()

  const login = useCallback(async () => {
    const trimmed = email.trim().toLowerCase()
    if (!trimmed) return
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(`${apiBase}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: trimmed })
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || 'We could not complete your login request.')
      localStorage.setItem('token', data.token)
      localStorage.setItem('userId', data.user_id)
      navigate('/chat')
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [email, navigate])

  const onSubmit = useCallback((event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!loading) login()
  }, [login, loading])

  return (
    <div className="login-layout">
      <section className="login-hero">
        <span className="chip">Enterprise-ready</span>
        <h1>Solid infrastructure for conversational copilots.</h1>
        <p className="muted-text">
          Spin up curated chat sessions, manage secure tokens, and keep your team aligned with a workspace designed
          for clarity and speed.
        </p>
        <ul className="login-bullets">
          <li className="login-bullet">Real-time orchestration with deterministic session control</li>
          <li className="login-bullet">Role-based access aligned with your governance requirements</li>
          <li className="login-bullet">One dashboard to monitor usage, transcripts, and health checks</li>
        </ul>
      </section>

      <section className="surface-card login-card" aria-labelledby="login-title">
        <div>
          <span className="eyebrow">Start a session</span>
          <h2 id="login-title" style={{ margin: '8px 0 6px' }}>Sign in to continue</h2>
          <p className="muted-text">Use your work email to receive access to the MCP chat workspace.</p>
        </div>
        <form className="form-block" onSubmit={onSubmit} noValidate>
          <label className="form-label" htmlFor="login-email">Work email</label>
          <input
            id="login-email"
            className="input-field"
            placeholder="you@company.com"
            value={email}
            onChange={event => setEmail(event.target.value)}
            type="email"
            autoComplete="email"
            disabled={loading}
            required
          />
          <span className="helper-text">We&apos;ll generate a short-lived token and start a dedicated chat session.</span>
          {error && <span className="error-text" role="alert">{error}</span>}
          <div className="login-actions">
            <button type="submit" className="accent-btn" disabled={loading || !email.trim()}>
              {loading ? 'Connecting...' : 'Access workspace'}
            </button>
            <button
              type="button"
              className="ghost-btn"
              onClick={() => setEmail('analyst@example.com')}
              disabled={loading}
            >
              Use sample email
            </button>
          </div>
        </form>
        <div className="muted-text" style={{ fontSize: '0.78rem' }}>
          By continuing you agree to our acceptable use policy and confirm you understand how we store session
          transcripts for quality review.
        </div>
      </section>
    </div>
  )
}
