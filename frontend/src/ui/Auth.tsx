import React, { useCallback, useState } from 'react'

type Props = {
  onLoggedIn: (token: string, userId: string) => void
  apiBase: string
}

export function Auth({ onLoggedIn, apiBase }: Props) {
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const login = useCallback(async () => {
    if (!email.trim()) return
    setLoading(true)
    setError(null)
    try {
      const r = await fetch(`${apiBase}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim() })
      })
      const data = await r.json()
      if (!r.ok) throw new Error(data.detail || 'Login failed')
      onLoggedIn(data.token, data.user_id)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [email, apiBase, onLoggedIn])

  return (
    <div style={{ display: 'grid', gap: 10 }}>
      <input placeholder="Email" value={email} onChange={e => setEmail(e.target.value)} style={{ padding: 12, borderRadius: 10, border: '1px solid #ccc' }} />
      <button onClick={login} disabled={loading || !email.trim()} className="btn">Login</button>
      {error && <div className="muted">{error}</div>}
    </div>
  )
}


