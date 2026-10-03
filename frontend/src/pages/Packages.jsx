import { useEffect, useState } from 'react'
import { api, durationLabel, money } from '../api.js'

const UNITS = { minutes: 1, hours: 60, days: 1440 }
function split(minutes) {
  if (minutes % 1440 === 0) return [minutes / 1440, 'days']
  if (minutes % 60 === 0) return [minutes / 60, 'hours']
  return [minutes, 'minutes']
}

function Editor({ pkg, onSaved, onCancel }) {
  const [amount, unit0] = split(pkg.duration_minutes || 60)
  const [f, setF] = useState({ name: pkg.name || '', price: pkg.price || '', amount, unit: unit0,
    valid_days: pkg.valid_days ?? 30, speed_limit: pkg.speed_limit || '', is_active: pkg.is_active ?? true })
  const [error, setError] = useState('')
  const set = (k) => (e) => setF({ ...f, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value })

  async function save(e) {
    e.preventDefault()
    setError('')
    const body = { name: f.name, price: f.price, duration_minutes: Math.round(Number(f.amount) * UNITS[f.unit]),
      valid_days: Number(f.valid_days), speed_limit: f.speed_limit.trim(), is_active: f.is_active }
    try {
      await api(pkg.id ? `/packages/${pkg.id}/` : '/packages/', { method: pkg.id ? 'PUT' : 'POST', body })
      onSaved()
    } catch (err) { setError(err.message) }
  }

  return (
    <form className="editor" onSubmit={save}>
      {error && <div className="alert" role="alert">{error}</div>}
      <div className="row wrap">
        <label className="field">Name<input value={f.name} onChange={set('name')} required /></label>
        <label className="field">Price<input type="number" step="0.01" min="0" value={f.price} onChange={set('price')} required /></label>
        <label className="field">Internet time
          <span className="row"><input type="number" min="1" step="any" value={f.amount} onChange={set('amount')} required />
            <select value={f.unit} onChange={set('unit')}>{Object.keys(UNITS).map((u) => <option key={u}>{u}</option>)}</select></span>
        </label>
        <label className="field">Must be used within (days)<input type="number" min="1" value={f.valid_days} onChange={set('valid_days')} required /></label>
        <label className="field">Speed cap (optional)<input value={f.speed_limit} onChange={set('speed_limit')} placeholder="e.g. 3M/3M" /></label>
      </div>
      <label className="chip on"><input type="checkbox" checked={f.is_active} onChange={set('is_active')} /> On sale</label>
      <div className="row">
        <button className="btn primary">Save package</button>
        <button type="button" className="btn" onClick={onCancel}>Cancel</button>
      </div>
    </form>
  )
}

export default function Packages({ user }) {
  const [list, setList] = useState([])
  const [editing, setEditing] = useState(null) // package object, {} for new, or null
  const load = () => api('/packages/').then(setList)
  useEffect(() => { load() }, [])

  return (
    <section className="panel">
      <div className="row wrap"><h2>Packages and prices</h2>
        {!editing && <button className="btn primary" onClick={() => setEditing({})}>Add a package</button>}</div>
      <p className="muted">Changes show on the Sell page and the public website straight away. Vouchers already sold keep the price they were sold at.</p>
      {editing && <Editor key={editing.id || 'new'} pkg={editing} onCancel={() => setEditing(null)} onSaved={() => { setEditing(null); load() }} />}
      <div className="scroll"><table>
        <thead><tr><th>Name</th><th>Internet time</th><th className="num">Price</th><th>Status</th><th></th></tr></thead>
        <tbody>{list.map((p) => (
          <tr key={p.id}><td>{p.name}</td><td>{durationLabel(p.duration_minutes)}</td><td className="num">{money(user.currency, p.price)}</td>
            <td>{p.is_active ? 'On sale' : 'Not on sale'}</td><td><button className="link" onClick={() => setEditing(p)}>Edit</button></td></tr>
        ))}</tbody>
      </table></div>
    </section>
  )
}
