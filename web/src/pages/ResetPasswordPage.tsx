import { useState, type FormEvent } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '../api'
import { PulseIcon } from '../components/Icons'
import { useAuth } from '../useAuth'

export default function ResetPasswordPage() {
  const [params] = useSearchParams()
  const token = params.get('token') ?? ''
  const { acceptSession } = useAuth()
  const navigate = useNavigate()
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    if (password !== confirm) {
      setError("The passwords don't match")
      return
    }
    setBusy(true)
    try {
      acceptSession(await api.resetPassword(token, password))
      navigate('/', { replace: true })
    } catch (err) {
      setError((err as Error).message)
      setBusy(false)
    }
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
        <h1 style={{ fontSize: '1.2rem', textAlign: 'center', margin: '8px 0 20px' }}>Choose a new password</h1>
        {!token ? (
          <div className="alert alert-danger">This link is missing its reset code. Request a new link from the sign-in page.</div>
        ) : (
          <form className="stack" onSubmit={submit}>
            <div className="field">
              <label className="field">
                <span>New password</span>
                <input
                  className="input"
                  type="password"
                  autoComplete="new-password"
                  minLength={8}
                  aria-describedby="new-password-hint"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </label>
              <small id="new-password-hint" className="muted">
                At least 8 characters.
              </small>
            </div>
            <label className="field">
              <span>Confirm new password</span>
              <input
                className="input"
                type="password"
                autoComplete="new-password"
                minLength={8}
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                required
              />
            </label>
            {error && <div className="alert alert-danger">{error}</div>}
            <button className="btn btn-primary" disabled={busy}>
              {busy ? 'Saving…' : 'Save password & sign in'}
            </button>
          </form>
        )}
        <a href="/" className="small" style={{ display: 'block', textAlign: 'center', marginTop: 16 }}>
          Back to FitAI
        </a>
      </div>
    </div>
  )
}
