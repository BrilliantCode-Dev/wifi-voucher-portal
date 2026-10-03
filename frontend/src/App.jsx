import { useEffect, useState } from 'react'
import { api, clearSession, getSession, saveSession } from './api.js'
import Sell from './pages/Sell.jsx'
import Vouchers from './pages/Vouchers.jsx'
import Cards from './pages/Cards.jsx'
import Reports from './pages/Reports.jsx'
import Packages from './pages/Packages.jsx'

function Login({ onDone }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(e) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      const data = await api('/auth/login/', { method: 'POST', body: { username, password } })
      const { token, ...user } = data
      saveSession(token, user)
      onDone({ token, user })
    } catch (err) {
      setError(err.message.includes('credentials') ? 'Wrong username or password.' : err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="login-wrap">
      <form className="login" onSubmit={submit}>
        <h1>Staff sign in</h1>
        {error && <div className="alert" role="alert">{error}</div>}
        <label>Username<input value={username} onChange={(e) => setUsername(e.target.value)} autoCapitalize="none" autoFocus required /></label>
        <label>Password<input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required /></label>
        <button className="btn primary big" disabled={busy}>{busy ? 'Signing in...' : 'Sign in'}</button>
      </form>
    </div>
  )
}

export default function App() {
  const [session, setSession] = useState(getSession())
  const [tab, setTab] = useState('sell')

  useEffect(() => {
    const out = () => setSession(null)
    window.addEventListener('dm-signout', out)
    return () => window.removeEventListener('dm-signout', out)
  }, [])

  if (!session) return <Login onDone={setSession} />
  const { user } = session

  const tabs = [
    ['sell', 'Sell'],
    ['vouchers', 'Vouchers'],
    ...(user.is_owner ? [['cards', 'Print cards'], ['reports', 'Reports'], ['packages', 'Packages']] : []),
  ]

  async function signOut() {
    try { await api('/auth/logout/', { method: 'POST' }) } catch { /* ignore */ }
    clearSession()
    setSession(null)
  }

  return (
    <>
      <header className="bar no-print">
        <strong className="brand">{user.cafe_name}</strong>
        <nav aria-label="Dashboard">
          {tabs.map(([id, label]) => (
            <button key={id} className={tab === id ? 'tab on' : 'tab'} onClick={() => setTab(id)} aria-current={tab === id ? 'page' : undefined}>{label}</button>
          ))}
        </nav>
        <span className="who">{user.username}{user.is_owner ? ' (owner)' : ''} <button className="link" onClick={signOut}>Sign out</button></span>
      </header>
      <main className="page">
        {tab === 'sell' && <Sell user={user} />}
        {tab === 'vouchers' && <Vouchers user={user} />}
        {tab === 'cards' && user.is_owner && <Cards user={user} />}
        {tab === 'reports' && user.is_owner && <Reports user={user} />}
        {tab === 'packages' && user.is_owner && <Packages user={user} />}
      </main>
    </>
  )
}
