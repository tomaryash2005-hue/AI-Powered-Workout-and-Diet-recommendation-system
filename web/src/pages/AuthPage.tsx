import { useState, type FormEvent } from 'react'
import { api } from '../api'
import { PulseIcon } from '../components/Icons'
import { useAuth } from '../useAuth'
import { useAsync } from '../utils'

export default function AuthPage() {
  const { login, register } = useAuth()
  const [mode, setMode] = useState<'login' | 'register' | 'forgot'>('login')
  const [notice, setNotice] = useState<string | null>(null)
  const { data: options } = useAsync(api.options)
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setNotice(null)
    setBusy(true)
    try {
      if (mode === 'forgot') {
        setNotice((await api.forgotPassword(email)).detail)
        setBusy(false)
      } else if (mode === 'login') await login(email, password)
      else await register(name, email, password)
    } catch (err) {
      setError((err as Error).message)
      setBusy(false)
    }
  }

  const switchMode = (m: typeof mode) => {
    setMode(m)
    setError(null)
    setNotice(null)
  }

  return (
    <div className="auth-wrap">
      <div className="card auth-card">
        <div className="brand">
          <span className="brand-mark">
            <PulseIcon />
          </span>
          FitAI
        </div>
        <p className="muted small" style={{ textAlign: 'center' }}>
          Personalised workout and diet plans based on your body, goals and allergies.
        </p>

        <div className="tabs" role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={mode !== 'register'}
            className={mode !== 'register' ? 'active' : ''}
            onClick={() => switchMode('login')}
          >
            Sign in
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={mode === 'register'}
            className={mode === 'register' ? 'active' : ''}
            onClick={() => switchMode('register')}
          >
            Create account
          </button>
        </div>

        <form className="stack" onSubmit={submit}>
          {mode === 'register' && (
            <label className="field">
              <span>Name</span>
              <input
                className="input"
                value={name}
                onChange={(e) => setName(e.target.value)}
                autoComplete="name"
                required
              />
            </label>
          )}
          <label className="field">
            <span>Email</span>
            <input
              className="input"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              required
            />
          </label>
          {mode !== 'forgot' && (
            <label className="field">
              <span>Password</span>
              <input
                className="input"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                minLength={mode === 'register' ? 8 : undefined}
                aria-describedby={mode === 'register' ? 'password-hint' : undefined}
                required
              />
            </label>
          )}
          {mode === 'register' && (
            <small id="password-hint" className="muted" style={{ marginTop: -10 }}>
              At least 8 characters.
            </small>
          )}
          {mode === 'forgot' && (
            <p className="small muted">Enter your account email and we'll send you a link to choose a new password.</p>
          )}
          {error && <div className="alert alert-danger">{error}</div>}
          {notice && <div className="alert alert-info">{notice}</div>}
          <button className="btn btn-primary" disabled={busy}>
            {busy
              ? 'Please wait…'
              : mode === 'login'
                ? 'Sign in'
                : mode === 'forgot'
                  ? 'Send reset link'
                  : 'Create account'}
          </button>
          {mode === 'login' && options?.password_reset && (
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => switchMode('forgot')}>
              Forgot password?
            </button>
          )}
          {mode === 'forgot' && (
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => switchMode('login')}>
              Back to sign in
            </button>
          )}
        </form>
      </div>
    </div>
  )
}
