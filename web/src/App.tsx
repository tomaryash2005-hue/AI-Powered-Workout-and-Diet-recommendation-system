import type { ReactNode } from 'react'
import { Navigate, NavLink, Route, Routes, useLocation } from 'react-router-dom'
import { useAuth } from './useAuth'
import {
  ChartIcon,
  DumbbellIcon,
  HomeIcon,
  JournalIcon,
  LogoutIcon,
  PulseIcon,
  SaladIcon,
  SettingsIcon,
  UserIcon,
} from './components/Icons'
import AuthPage from './pages/AuthPage'
import Dashboard from './pages/Dashboard'
import DietPage from './pages/DietPage'
import MealsPage from './pages/MealsPage'
import ProfilePage from './pages/ProfilePage'
import ProgressPage from './pages/ProgressPage'
import ResetPasswordPage from './pages/ResetPasswordPage'
import SettingsPage from './pages/SettingsPage'
import WorkoutPage from './pages/WorkoutPage'

const NAV = [
  { to: '/', label: 'Home', icon: <HomeIcon /> },
  { to: '/diet', label: 'Diet', icon: <SaladIcon /> },
  { to: '/workout', label: 'Workout', icon: <DumbbellIcon /> },
  { to: '/meals', label: 'Food log', icon: <JournalIcon /> },
  { to: '/progress', label: 'Progress', icon: <ChartIcon /> },
  { to: '/profile', label: 'Profile', icon: <UserIcon /> },
]

function Shell({ children, showNav }: { children: ReactNode; showNav: boolean }) {
  const { user, logout } = useAuth()
  return (
    <div className="shell">
      <header className="topbar">
        <div className="topbar-inner">
          <NavLink to="/" className="brand">
            <span className="brand-mark">
              <PulseIcon />
            </span>
            FitAI
          </NavLink>
          {showNav && (
            <nav className="nav" aria-label="Main">
              {NAV.map((n) => (
                <NavLink key={n.to} to={n.to} end={n.to === '/'}>
                  {n.icon}
                  {n.label}
                </NavLink>
              ))}
            </nav>
          )}
          <div className="user-menu" style={{ marginLeft: 'auto' }}>
            <span className="user-name small muted">{user?.name}</span>
            <NavLink to="/settings" className="btn btn-ghost btn-icon" aria-label="Settings" title="Settings">
              <SettingsIcon />
            </NavLink>
            <button type="button" className="btn btn-ghost btn-sm" onClick={logout}>
              <LogoutIcon />
              Sign out
            </button>
          </div>
        </div>
      </header>
      <main>{children}</main>
    </div>
  )
}

export default function App() {
  const { user, loading } = useAuth()
  const { pathname } = useLocation()

  if (pathname === '/reset-password') return <ResetPasswordPage />
  if (loading) return <div className="loading">Loading…</div>
  if (!user) return <AuthPage />

  if (!user.has_profile) {
    return (
      <Shell showNav={false}>
        <ProfilePage />
      </Shell>
    )
  }

  return (
    <Shell showNav>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/diet" element={<DietPage />} />
        <Route path="/workout" element={<WorkoutPage />} />
        <Route path="/meals" element={<MealsPage />} />
        <Route path="/progress" element={<ProgressPage />} />
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Shell>
  )
}
