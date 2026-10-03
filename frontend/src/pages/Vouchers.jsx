import { useCallback, useEffect, useState } from 'react'
import { api, when } from '../api.js'

const FILTERS = [
  ['active', 'In use now'],
  ['unused', 'Sold, not used yet'],
  ['expired', 'Finished'],
  ['void', 'Cancelled'],
  ['unsold', 'Printed, not sold'],
  ['', 'All'],
]
const LABEL = { unused: 'Not used yet', active: 'In use', expired: 'Finished', void: 'Cancelled' }

export default function Vouchers({ user }) {
  const [filter, setFilter] = useState('active')
  const [q, setQ] = useState('')
  const [rows, setRows] = useState([])
  const [error, setError] = useState('')

  const load = useCallback(() => {
    const params = new URLSearchParams()
    if (filter) params.set('status', filter)
    if (q.trim()) params.set('q', q.trim())
    api('/vouchers/?' + params).then(setRows).catch((e) => setError(e.message))
  }, [filter, q])
  useEffect(() => { const t = setTimeout(load, 200); return () => clearTimeout(t) }, [load])

  async function cancel(v) {
    if (!window.confirm(`Cancel voucher ${v.code}? The customer will be disconnected.`)) return
    try { await api(`/vouchers/${v.id}/void/`, { method: 'POST' }); load() } catch (e) { setError(e.message) }
  }

  return (
    <section className="panel">
      <h2>Vouchers</h2>
      {error && <div className="alert" role="alert">{error}</div>}
      <div className="row wrap">
        <select value={filter} onChange={(e) => setFilter(e.target.value)} aria-label="Show">
          {FILTERS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
        <input className="search" placeholder="Find a code" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Find a code" />
      </div>
      {rows.length === 0 ? <p className="muted">No vouchers match. Try another filter.</p> : (
        <div className="scroll"><table>
          <thead><tr><th>Code</th><th>Package</th><th>Status</th><th>Sold</th><th>Started</th><th>Ends</th>{user.is_owner && <th></th>}</tr></thead>
          <tbody>{rows.map((v) => (
            <tr key={v.id}>
              <td className="mono">{v.code}</td><td>{v.package_name}</td>
              <td><span className={'pill ' + v.status}>{v.sold_at || v.status !== 'unused' ? LABEL[v.status] : 'Not sold'}</span></td>
              <td>{when(v.sold_at)}</td><td>{when(v.activated_at)}</td><td>{when(v.expires_at)}</td>
              {user.is_owner && <td>{(v.status === 'active' || v.status === 'unused') && <button className="link danger" onClick={() => cancel(v)}>Cancel</button>}</td>}
            </tr>
          ))}</tbody>
        </table></div>
      )}
      <p className="muted">Showing up to 200 vouchers.</p>
    </section>
  )
}
