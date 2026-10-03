import { useEffect, useState } from 'react'
import { api, money, todayISO } from '../api.js'

function Bars({ data, value, label, format, tall }) {
  const max = Math.max(...data.map(value), 0.0001)
  return (
    <div className={tall ? 'bars tall' : 'bars'} role="img" aria-label="Bar chart">
      {data.map((d, i) => (
        <div className="bar" key={i} title={format(d)}>
          <div className="fill" style={{ height: `${(value(d) / max) * 100}%` }} />
          <span>{label(d, i)}</span>
        </div>
      ))}
    </div>
  )
}

function Breakdown({ title, rows, currency }) {
  return (
    <div>
      <h3>{title}</h3>
      {rows.length === 0 ? <p className="muted">Nothing sold yet.</p> : (
        <table><tbody>{rows.map((r) => (
          <tr key={r.label}><td>{r.label}</td><td className="num muted">{r.count} sold</td><td className="num">{money(currency, r.total)}</td></tr>
        ))}</tbody></table>
      )}
    </div>
  )
}

export default function Reports({ user }) {
  const c = user.currency
  const [date, setDate] = useState(todayISO())
  const [day, setDay] = useState(null)
  const [trend, setTrend] = useState([])
  const [error, setError] = useState('')

  useEffect(() => {
    setError('')
    api('/reports/daily/?date=' + date).then(setDay).catch((e) => setError(e.message))
  }, [date])
  useEffect(() => { api('/reports/trend/?days=14').then(setTrend).catch(() => {}) }, [])

  const peak = day && day.count > 0 ? day.hourly.reduce((a, b) => (b.count > a.count ? b : a)) : null
  const hourName = (h) => `${h % 12 === 0 ? 12 : h % 12}${h < 12 ? 'am' : 'pm'}`

  return (
    <>
      <section className="panel">
        <div className="row wrap">
          <h2>Daily report</h2>
          <input type="date" value={date} max={todayISO()} onChange={(e) => e.target.value && setDate(e.target.value)} aria-label="Report date" />
        </div>
        {error && <div className="alert" role="alert">{error}</div>}
        {day && (
          <>
            <div className="stats">
              <div className="stat"><span>Money taken</span><strong>{money(c, day.total)}</strong></div>
              <div className="stat"><span>Vouchers sold</span><strong>{day.count}</strong></div>
              <div className="stat"><span>Online right now</span><strong>{day.active_now}</strong></div>
              <div className="stat"><span>Sold, not used yet</span><strong>{day.unused_sold}</strong></div>
            </div>
            <div className="cols">
              <Breakdown title="By package" rows={day.by_package} currency={c} />
              <Breakdown title="By payment method" rows={day.by_method} currency={c} />
              <Breakdown title="By staff member" rows={day.by_staff} currency={c} />
            </div>
          </>
        )}
      </section>

      {day && (
        <section className="panel">
          <h2>Busy times</h2>
          <p className="muted">{peak ? `Busiest hour: ${hourName(peak.hour)} with ${peak.count} sold.` : 'No sales on this day.'}</p>
          <Bars data={day.hourly} value={(d) => d.count} label={(d) => (d.hour % 3 === 0 ? d.hour : '')}
            format={(d) => `${hourName(d.hour)}: ${d.count} sold, ${money(c, d.total)}`} />
        </section>
      )}

      <section className="panel">
        <h2>Last 14 days</h2>
        <Bars tall data={trend} value={(d) => d.total} label={(d) => d.date.slice(8)}
          format={(d) => `${d.date}: ${money(c, d.total)} (${d.count} sold)`} />
        <p className="muted">Each bar is one day's takings. Point at a bar to see the amount.</p>
      </section>
    </>
  )
}
