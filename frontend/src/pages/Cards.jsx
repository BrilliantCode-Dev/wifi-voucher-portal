import { useEffect, useState } from 'react'
import { api, durationLabel, money, when } from '../api.js'

export default function Cards({ user }) {
  const [packages, setPackages] = useState([])
  const [pkgId, setPkgId] = useState('')
  const [qty, setQty] = useState(20)
  const [batch, setBatch] = useState(null)
  const [batches, setBatches] = useState([])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const loadBatches = () => api('/batches/').then(setBatches).catch(() => {})
  useEffect(() => {
    api('/packages/').then((p) => {
      const active = p.filter((x) => x.is_active)
      setPackages(active)
      if (active[0]) setPkgId(String(active[0].id))
    })
    loadBatches()
  }, [])

  async function create() {
    setBusy(true)
    setError('')
    try {
      setBatch(await api('/batches/', { method: 'POST', body: { package: Number(pkgId), quantity: Number(qty) } }))
      loadBatches()
    } catch (e) { setError(e.message) } finally { setBusy(false) }
  }
  const reprint = (id) => api(`/batches/${id}/`).then(setBatch).catch((e) => setError(e.message))

  return (
    <>
      <section className="panel no-print">
        <h2>Print voucher cards</h2>
        <p className="muted">Make a batch of cards ahead of time. A card only works after you sell it: use "Selling a card that is already printed?" on the Sell page.</p>
        {error && <div className="alert" role="alert">{error}</div>}
        <div className="row wrap">
          <label className="field">Package
            <select value={pkgId} onChange={(e) => setPkgId(e.target.value)}>
              {packages.map((p) => <option key={p.id} value={p.id}>{p.name} ({money(user.currency, p.price)})</option>)}
            </select>
          </label>
          <label className="field">How many (1 to 200)
            <input type="number" min="1" max="200" value={qty} onChange={(e) => setQty(e.target.value)} />
          </label>
          <button className="btn primary" disabled={busy || !pkgId} onClick={create}>{busy ? 'Making cards...' : 'Make cards'}</button>
        </div>
      </section>

      {batch && (
        <section className="panel">
          <div className="row wrap no-print">
            <h2>{batch.codes.length} cards: {batch.package_name}</h2>
            <button className="btn primary" onClick={() => window.print()}>Print cards</button>
          </div>
          <div className="cardsheet">
            {batch.codes.map((c) => (
              <div className="vcard" key={c}>
                <strong>{user.cafe_name}</strong>
                <span className="vcode">{c}</span>
                <span>{batch.package_name}: {durationLabel(batch.duration_minutes)} of Wi-Fi</span>
                <small>Connect to our Wi-Fi and type this code.</small>
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="panel no-print">
        <h2>Earlier batches</h2>
        {batches.length === 0 ? <p className="muted">No batches yet. Make your first set of cards above.</p> : (
          <div className="scroll"><table>
            <thead><tr><th>Made</th><th>Package</th><th className="num">Cards</th><th>By</th><th></th></tr></thead>
            <tbody>{batches.map((b) => (
              <tr key={b.id}><td>{when(b.created_at)}</td><td>{b.package_name}</td><td className="num">{b.quantity}</td><td>{b.created_by}</td>
                <td><button className="link" onClick={() => reprint(b.id)}>Show to print again</button></td></tr>
            ))}</tbody>
          </table></div>
        )}
      </section>
    </>
  )
}
