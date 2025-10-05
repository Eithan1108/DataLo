import React, { KeyboardEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'

type Message = { role: 'user' | 'assistant', text: string }

const apiBase = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000'
const promptLibrary = [
  'Summarise the latest deployment checklist and flag missing approvals.',
  'Draft a release announcement using the current sprint highlights.',
  'List pending MCP actions for the customer onboarding workspace.',
  'Generate a troubleshooting guide for the most common support issue this week.'
]

export function Chat() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const messagesRef = useRef<HTMLDivElement | null>(null)
  const textareaRef = useRef<HTMLTextAreaElement | null>(null)
  const navigate = useNavigate()

  const token = useMemo(() => localStorage.getItem('token'), [])
  const userId = useMemo(() => localStorage.getItem('userId'), [])

  useEffect(() => {
    if (!token || !userId) {
      navigate('/')
      return
    }
    ;(async () => {
      const response = await fetch(`${apiBase}/api/init`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId })
      })
      const data = await response.json()
      if (response.ok) setSessionId(data.session_id)
    })()
  }, [navigate, token, userId])

  const appendMessage = useCallback((message: Message) => {
    setMessages(previous => [...previous, message])
  }, [])

  const send = useCallback(async () => {
    if (!token || !sessionId) return
    const trimmed = input.trim()
    if (!trimmed) return
    appendMessage({ role: 'user', text: trimmed })
    setInput('')
    setLoading(true)
    try {
      const response = await fetch(`${apiBase}/api/message`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ session_id: sessionId, message: trimmed })
      })
      const data = await response.json()
      appendMessage({ role: 'assistant', text: response.ok ? (data.reply || '') : (data.detail || 'Request failed') })
    } catch (error: any) {
      appendMessage({ role: 'assistant', text: `There was a problem sending your message: ${error.message}` })
    } finally {
      setLoading(false)
      requestAnimationFrame(() => {
        messagesRef.current?.scrollTo({ top: messagesRef.current.scrollHeight, behavior: 'smooth' })
      })
    }
  }, [appendMessage, input, sessionId, token])

  const handleKey = useCallback((event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) {
      event.preventDefault()
      send()
    }
  }, [send])

  const handlePromptClick = useCallback((prompt: string) => {
    setInput(prompt)
    textareaRef.current?.focus()
  }, [])

  return (
    <div className="chat-page">
      <section className="chat-intro surface-card">
        <div>
          <span className="eyebrow">Assistant workspace</span>
          <h1>Ask anything, stay in control.</h1>
          <p className="muted-text">
            Start a conversation or pick a suggested task to continue within your secured MCP session.
          </p>
        </div>
        <div className="session-inline" aria-label="Session status">
          <div className="session-pill">
            <span className="session-label">Session</span>
            <span className="session-value">{sessionId ?? 'Initializing'}</span>
          </div>
          <div className="session-pill">
            <span className="session-label">User</span>
            <span className="session-value">{userId ?? 'Unknown user'}</span>
          </div>
          <div className="session-pill">
            <span className="session-label">Status</span>
            <span className="session-value">{loading ? 'Waiting on assistant' : 'Ready to chat'}</span>
          </div>
        </div>
      </section>

      <section className="chat-flow">
        <div className="conversation-shell">
          <div className="conversation-meta">
            <div className="status-pill">
              <span className="status-dot" aria-hidden="true" />
              <span>{loading ? 'Responding...' : 'Live conversation'}</span>
            </div>
            <span className="muted-text">Backend: {apiBase}</span>
          </div>
          <div ref={messagesRef} className="message-rail" aria-live="polite">
            {messages.length === 0 ? (
              <div className="message-block assistant">
                <strong>Hello!</strong> How can I support your team today? Try one of the prompts below to explore the workspace.
              </div>
            ) : (
              messages.map((message, index) => (
                <div key={index} className={`message-block ${message.role}`}>
                  {message.text}
                </div>
              ))
            )}
          </div>
        </div>

        <div className="prompt-rail" aria-label="Suggested prompts">
          {promptLibrary.map(prompt => (
            <button
              key={prompt}
              type="button"
              className="prompt-pill"
              onClick={() => handlePromptClick(prompt)}
              disabled={!sessionId || loading}
            >
              {prompt}
            </button>
          ))}
        </div>

        <div className="composer-card">
          <textarea
            ref={textareaRef}
            className="composer-textarea"
            placeholder="Message MCP Chat..."
            value={input}
            onChange={event => setInput(event.target.value)}
            onKeyDown={handleKey}
            disabled={!sessionId || loading}
          />
          <div className="composer-footer">
            <span className="composer-hint">Press Cmd/Ctrl + Enter to send | Shift + Enter for a new line</span>
            <div className="composer-actions">
              <button
                type="button"
                className="secondary-btn"
                onClick={() => setInput('Can you outline the next best action for our MCP implementation?')}
                disabled={!sessionId || loading}
              >
                Insert suggestion
              </button>
              <button
                type="button"
                className="accent-btn"
                onClick={send}
                disabled={!sessionId || !input.trim() || loading}
              >
                {loading ? 'Sending...' : 'Send'}
              </button>
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}
