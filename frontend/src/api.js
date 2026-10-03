const TOKEN = 'dm_token'
const USER = 'dm_user'

export const getSession = () => {
  try {
    const token = localStorage.getItem(TOKEN)
    const user = JSON.parse(localStorage.getItem(USER) || 'null')
    return token && user ? { token, user } : null
  } catch {
    return null
  }
}
export const saveSession = (token, user) => {
  localStorage.setItem(TOKEN, token)
  localStorage.setItem(USER, JSON.stringify(user))
}
export const clearSession = () => {
  localStorage.removeItem(TOKEN)
  localStorage.removeItem(USER)
}

function errorText(data) {
  if (!data) return 'Something went wrong. Please try again.'
  if (typeof data.detail === 'string') return data.detail
  const first = Object.values(data)[0]
  if (Array.isArray(first)) return String(first[0])
  return typeof first === 'string' ? first : 'Something went wrong. Please try again.'
}

export async function api(path, { method = 'GET', body } = {}) {
  const token = localStorage.getItem(TOKEN)
  let res
  try {
    res = await fetch('/api' + path, {
      method,
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: 'Token ' + token } : {}),
      },
      body: body ? JSON.stringify(body) : undefined,
    })
  } catch {
    throw new Error('Cannot reach the server. Check your internet and try again.')
  }
  if (res.status === 401 && token) {
    clearSession()
    window.dispatchEvent(new Event('dm-signout'))
    throw new Error('Please sign in again.')
  }
  const data = res.status === 204 ? null : await res.json().catch(() => null)
  if (!res.ok) throw new Error(errorText(data))
  return data
}

export const money = (currency, n) => `${currency}${Number(n || 0).toFixed(2)}`
export const when = (iso) =>
  iso ? new Date(iso).toLocaleString([], { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) : '-'
export const timeOnly = (iso) =>
  new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
export const todayISO = () => new Date().toLocaleDateString('en-CA')
export const durationLabel = (m) => {
  if (m % 1440 === 0) return m === 1440 ? '24 hours' : `${m / 1440} days`
  if (m % 60 === 0) return m === 60 ? '1 hour' : `${m / 60} hours`
  return `${m} minutes`
}
