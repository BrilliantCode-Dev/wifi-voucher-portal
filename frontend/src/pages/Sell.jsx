import { useCallback, useEffect, useState } from 'react'
import { api, durationLabel, money, timeOnly, when } from '../api.js'

export default function Sell({ user }) {
  const [packages, setPackages] = useState([])
  const [pkg, setPkg] = useState(null)
  const [method, setMethod] = useState('cash')
  const [card, setCard] = useState('')
  const [useCard, setUseCard] = useState(false)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [done, setDone] = useState(null)
  const [today, setToday] = useState({ total: 0, count: 0, sales: [] })

  const refresh = useCallback(() => api('/sales/').then(setToday).catch(() => {}), [])
  useEffect(() => {
    api('/packages/').then((p) => setPackages(p.filter((x) => x.is_active))).catch((e) => setError(e.message))
    refresh()
  }, [refresh])

  async function sell() {
    setBusy(true)
    setError('')
    try {
      const sale = await api('/sell/', { method: 'POST', body: { package: useCard ? null : pkg?.id, method, code: useCard ? card : '' } })
      setDone(sale)
      setCard('')
      refresh()
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  if (done) {
    return (
      <>
        <section className="panel done no-print">
          <p>Sold. Give the customer this code:</p>
          <div className="code">{done.code}</div>
          <p className="muted">{done.package_name}, {money(user.currency, done.amount)} ({done.method === 'cash' ? 'cash' : 'EcoCash'}). Their time starts when they first enter the code.</p>
          <div className="row">
            <button className="btn" onClick={() => window.print()}>Print slip</button>
            <button className="btn primary" onClick={() => setDone(null)}>Next customer</button>
          </div>
        </section>
        <div className="print-only slip">
          <h2>{user.cafe_name}</h2>
          <p>Wi-Fi voucher: {done.package_name} ({durationLabel(done.duration_minutes)})</p>
          <div className="code">{done.code}</div>
          <p>Connect to our Wi-Fi and type this code on the page that opens. Your time starts when you first enter it.</p>
          <p className="muted">{when(done.sold_at)}</p>
        </div>
      </>
    )
  }

  const ready = useCard ? card.trim().length > 0 : !!pkg
  return (
    <>
      <section className="panel no-print">
        <h2>Sell a voucher</h2>
        {error && <div className="alert" role="alert">{error}</div>}
        {!useCard && (
          <div className="grid pkgs">
            {packages.map((p) => (
              <button key={p.id} className={pkg?.id === p.id ? 'pkg on' : 'pkg'} onClick={() => setPkg(p)}>
                <span className="pname">{p.name}</span>
                <span className="pprice">{money(user.currency, p.price)}</span>
                <span className="muted">{durationLabel(p.duration_minutes)}</span>
              </button>
            ))}
          </div>
        )}
        {useCard && (
          <label className="field">Code printed on the card
            <input className="codein" value={card} onChange={(e) => setCard(e.target.value.toUpperCase())} placeholder="K7M2-9QXA" maxLength={12} autoFocus />
          </label>
        )}
        <button className="link" onClick={() => { setUseCard(!useCard); setError('') }}>
          {useCard ? 'Sell a new voucher instead' : 'Selling a card that is already printed?'}
        </button>
        <fieldset className="methods">
          <legend>How did the customer pay?</legend>
          {[['cash', 'Cash'], ['ecocash', 'EcoCash']].map(([v, l]) => (
            <label key={v} className={method === v ? 'chip on' : 'chip'}>
              <input type="radio" name="method" checked={method === v} onChange={() => setMethod(v)} /> {l}
            </label>
          ))}
        </fieldset>
        <button className="btn primary big" disabled={!ready || busy} onClick={sell}>
          {busy ? 'Selling...' : useCard ? 'Sell this card' : pkg ? `Sell ${pkg.name} for ${money(user.currency, pkg.price)}` : 'Choose a package'}
        </button>
      </section>

      <section className="panel no-print">
        <h2>Today's sales: {money(user.currency, today.total)} <span className="muted">({today.count} sold)</span></h2>
        {today.sales.length === 0 ? <p className="muted">No sales yet today. Your first sale will appear here.</p> : (
          <div className="scroll"><table>
            <thead><tr><th>Time</th><th>Code</th><th>Package</th><th>Paid</th>{user.is_owner && <th>Sold by</th>}<th className="num">Amount</th></tr></thead>
            <tbody>{today.sales.map((s) => (
              <tr key={s.id}><td>{timeOnly(s.sold_at)}</td><td className="mono">{s.code}</td><td>{s.package_name}</td>
                <td>{s.method === 'cash' ? 'Cash' : 'EcoCash'}</td>{user.is_owner && <td>{s.sold_by_name}</td>}
                <td className="num">{money(user.currency, s.amount)}</td></tr>
            ))}</tbody>
          </table></div>
        )}
      </section>
    </>
  )
}
