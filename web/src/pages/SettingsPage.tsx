import { useEffect, useState, type FormEvent } from 'react'
import { api, type ReminderSettings } from '../api'
import { AlertIcon } from '../components/Icons'
import { currentSubscription, disablePush, enablePush, needsInstallForPush, pushSupported } from '../push'
import { useAuth } from '../useAuth'
import { useAsync } from '../utils'

const WEEKDAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
const localTimezone = () => Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC'

function Toggle({
  label,
  hint,
  checked,
  onChange,
}: {
  label: string
  hint: string
  checked: boolean
  onChange: (v: boolean) => void
}) {
  return (
    <label className="toggle-row">
      <span>
        <strong>{label}</strong>
        <span className="small muted">{hint}</span>
      </span>
      <input type="checkbox" className="switch" checked={checked} onChange={(e) => onChange(e.target.checked)} />
    </label>
  )
}

function TimeField({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <label className="field">
      <span>{label}</span>
      <input className="input" type="time" value={value} onChange={(e) => onChange(e.target.value)} required />
    </label>
  )
}

function Reminders({ publicKey }: { publicKey: string | null }) {
  const { data: loaded, error: loadError } = useAsync(api.reminderSettings)
  const [form, setForm] = useState<ReminderSettings | null>(null)
  const [deviceOn, setDeviceOn] = useState(false)
  const [message, setMessage] = useState<{ kind: 'info' | 'danger'; text: string } | null>(null)
  const [busy, setBusy] = useState(false)
  const settings = form ?? loaded

  useEffect(() => {
    currentSubscription()
      .then((sub) => setDeviceOn(sub !== null))
      .catch(() => setDeviceOn(false))
  }, [])

  const set = <K extends keyof ReminderSettings>(key: K, value: ReminderSettings[K]) =>
    setForm({ ...(settings as ReminderSettings), [key]: value })

  const run = async (action: () => Promise<string>) => {
    setBusy(true)
    setMessage(null)
    try {
      setMessage({ kind: 'info', text: await action() })
    } catch (e) {
      setMessage({ kind: 'danger', text: (e as Error).message })
    } finally {
      setBusy(false)
    }
  }

  const toggleDevice = () =>
    run(async () => {
      if (deviceOn) {
        await disablePush()
        setDeviceOn(false)
        return 'Notifications turned off on this device.'
      }
      await enablePush(publicKey!)
      setDeviceOn(true)
      return 'Notifications are on for this device.'
    })

  const save = (e: FormEvent) => {
    e.preventDefault()
    run(async () => {
      await api.saveReminderSettings({ ...(settings as ReminderSettings), timezone: localTimezone() })
      return 'Reminder settings saved.'
    })
  }

  if (!publicKey) {
    return (
      <section className="card stack">
        <h2>Reminders</h2>
        <p className="small muted">Reminders aren't set up on this server yet (the owner needs to add a VAPID key).</p>
      </section>
    )
  }

  return (
    <form className="card stack" onSubmit={save}>
      <div>
        <h2>Reminders</h2>
        <p className="small muted">
          Get a notification when it's time to log a meal, weigh in or work out. Reminders skip anything you've
          already done.
        </p>
      </div>

      {!pushSupported() ? (
        <div className="alert alert-warn">
          <AlertIcon />
          <span>This browser doesn't support notifications.</span>
        </div>
      ) : needsInstallForPush() ? (
        <div className="alert alert-warn">
          <AlertIcon />
          <span>
            On iPhone, add FitAI to your Home Screen first (Share → Add to Home Screen), then open it from there to
            turn on notifications.
          </span>
        </div>
      ) : (
        <div className="spread" style={{ flexWrap: 'wrap' }}>
          <span className="small">
            This device: <strong>{deviceOn ? 'notifications on' : 'notifications off'}</strong>
          </span>
          <div className="row">
            <button type="button" className="btn btn-sm" disabled={busy} onClick={toggleDevice}>
              {deviceOn ? 'Turn off on this device' : 'Turn on notifications'}
            </button>
            {deviceOn && (
              <button
                type="button"
                className="btn btn-sm btn-ghost"
                disabled={busy}
                onClick={() => run(async () => ((await api.testNotification()).sent ? 'Test notification sent.' : 'No devices reached.'))}
              >
                Send a test
              </button>
            )}
          </div>
        </div>
      )}

      {loadError && <div className="alert alert-danger">{loadError}</div>}
      {settings && (
        <>
          <Toggle
            label="Meal reminders"
            hint="A nudge to log each meal"
            checked={settings.meals_enabled}
            onChange={(v) => set('meals_enabled', v)}
          />
          {settings.meals_enabled && (
            <div className="form-grid">
              <TimeField label="Breakfast" value={settings.breakfast_time} onChange={(v) => set('breakfast_time', v)} />
              <TimeField label="Lunch" value={settings.lunch_time} onChange={(v) => set('lunch_time', v)} />
              <TimeField label="Dinner" value={settings.dinner_time} onChange={(v) => set('dinner_time', v)} />
            </div>
          )}
          <Toggle
            label="Weekly weigh-in"
            hint="Once a week, to keep your plan accurate"
            checked={settings.weigh_in_enabled}
            onChange={(v) => set('weigh_in_enabled', v)}
          />
          {settings.weigh_in_enabled && (
            <div className="form-grid">
              <label className="field">
                <span>Day</span>
                <select
                  className="input"
                  value={settings.weigh_in_weekday}
                  onChange={(e) => set('weigh_in_weekday', Number(e.target.value))}
                >
                  {WEEKDAYS.map((d, i) => (
                    <option key={d} value={i}>
                      {d}
                    </option>
                  ))}
                </select>
              </label>
              <TimeField label="Time" value={settings.weigh_in_time} onChange={(v) => set('weigh_in_time', v)} />
            </div>
          )}
          <Toggle
            label="Workout reminders"
            hint="On training days only"
            checked={settings.workout_enabled}
            onChange={(v) => set('workout_enabled', v)}
          />
          {settings.workout_enabled && (
            <div className="form-grid">
              <TimeField label="Time" value={settings.workout_time} onChange={(v) => set('workout_time', v)} />
            </div>
          )}
          <p className="small muted">Times use your device's time zone ({localTimezone()}).</p>
          <button className="btn btn-primary" disabled={busy}>
            Save reminders
          </button>
        </>
      )}
      {message && <div className={`alert alert-${message.kind}`}>{message.text}</div>}
    </form>
  )
}

function ChangePassword() {
  const { acceptSession } = useAuth()
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [message, setMessage] = useState<{ kind: 'info' | 'danger'; text: string } | null>(null)
  const [busy, setBusy] = useState(false)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setMessage(null)
    try {
      acceptSession(await api.changePassword(current, next))
      setCurrent('')
      setNext('')
      setMessage({ kind: 'info', text: 'Password changed. You were signed out on your other devices.' })
    } catch (err) {
      setMessage({ kind: 'danger', text: (err as Error).message })
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="card stack" onSubmit={submit}>
      <h2>Change password</h2>
      <div className="form-grid">
        <label className="field">
          <span>Current password</span>
          <input
            className="input"
            type="password"
            autoComplete="current-password"
            value={current}
            onChange={(e) => setCurrent(e.target.value)}
            required
          />
        </label>
        <label className="field">
          <span>New password</span>
          <input
            className="input"
            type="password"
            autoComplete="new-password"
            minLength={8}
            value={next}
            onChange={(e) => setNext(e.target.value)}
            required
          />
        </label>
      </div>
      {message && <div className={`alert alert-${message.kind}`}>{message.text}</div>}
      <button className="btn" disabled={busy}>
        {busy ? 'Saving…' : 'Change password'}
      </button>
    </form>
  )
}

function YourData() {
  const { logout } = useAuth()
  const [confirming, setConfirming] = useState(false)
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const exportData = async () => {
    setError(null)
    try {
      await api.exportData()
    } catch (e) {
      setError((e as Error).message)
    }
  }

  const remove = async (e: FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await disablePush().catch(() => {})
      await api.deleteAccount(password)
      logout()
    } catch (err) {
      setError((err as Error).message)
      setBusy(false)
    }
  }

  return (
    <section className="card stack">
      <h2>Your data</h2>
      <div className="spread" style={{ flexWrap: 'wrap' }}>
        <p className="small muted">Download everything FitAI stores about you as a JSON file.</p>
        <button type="button" className="btn btn-sm" onClick={exportData}>
          Export my data
        </button>
      </div>
      <div className="danger-zone stack">
        <div>
          <strong>Delete account</strong>
          <p className="small muted">
            Permanently deletes your account, profile, food log, weigh-ins, workouts and reminders. This can't be
            undone.
          </p>
        </div>
        {!confirming ? (
          <button type="button" className="btn btn-danger btn-sm" onClick={() => setConfirming(true)}>
            Delete my account…
          </button>
        ) : (
          <form className="row" style={{ alignItems: 'flex-end' }} onSubmit={remove}>
            <label className="field" style={{ flex: '1 1 200px' }}>
              <span>Enter your password to confirm</span>
              <input
                className="input"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </label>
            <button className="btn btn-danger" disabled={busy}>
              {busy ? 'Deleting…' : 'Delete permanently'}
            </button>
            <button type="button" className="btn btn-ghost" onClick={() => setConfirming(false)}>
              Cancel
            </button>
          </form>
        )}
      </div>
      {error && <div className="alert alert-danger">{error}</div>}
    </section>
  )
}

export default function SettingsPage() {
  const { user } = useAuth()
  const { data: options } = useAsync(api.options)

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <h1>Settings</h1>
          <p className="muted">Signed in as {user?.email}</p>
        </div>
      </div>
      <div className="grid grid-2" style={{ alignItems: 'start' }}>
        <div className="stack">{options && <Reminders publicKey={options.push_public_key} />}</div>
        <div className="stack">
          <ChangePassword />
          <YourData />
        </div>
      </div>
    </div>
  )
}
