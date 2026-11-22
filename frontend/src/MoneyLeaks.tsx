import { useCallback, useEffect, useState } from "react"
import { ArrowUpRight, CalendarClock, Copy, ScanSearch } from "lucide-react"
import { Link } from "react-router-dom"
import { requestError, useAuthenticatedApi } from "./authenticatedApi"
import { money } from "./banking"
import { CoachPanel } from "./CoachPanel"
import { Button } from "./components/ui/button"
import { financialDate, type AuditHistory, type Report } from "./intelligence"

export function MoneyLeaks({ token, onExpired }: { token: string; onExpired: () => void }) {
  const call = useAuthenticatedApi(token, onExpired)
  const [report, setReport] = useState<Report>()
  const [history, setHistory] = useState<AuditHistory>()
  const [error, setError] = useState("")
  const [pending, setPending] = useState(true)

  const load = useCallback(async (signal?: AbortSignal) => {
    setError("")
    setPending(true)
    try {
      const [summary, audits] = await Promise.all([
        call<Report>("/money-leaks", { signal }),
        call<AuditHistory>("/audits", { signal }),
      ])
      if (!signal?.aborted) {
        setReport(summary)
        setHistory(audits)
      }
    } catch (failure) {
      if (!signal?.aborted) setError(requestError(failure))
    } finally {
      if (!signal?.aborted) setPending(false)
    }
  }, [call])

  useEffect(() => {
    const controller = new AbortController()
    void load(controller.signal)
    return () => controller.abort()
  }, [load])

  async function loadMore() {
    if (!history?.before_id || pending) return
    setError("")
    setPending(true)
    try {
      const page = await call<AuditHistory>(`/audits?before_id=${history.before_id}`)
      setHistory({ items: [...history.items, ...page.items], before_id: page.before_id })
    } catch (failure) {
      setError(requestError(failure))
    } finally {
      setPending(false)
    }
  }

  return (
    <div className="banking">
      <section className="bank-hero">
        <div>
          <p className="bank-eyebrow"><ScanSearch size={16} aria-hidden /> Simulated spending · CAD</p>
          <h1>MoneyLeaks</h1>
          <p>Review recurring charges, changes in price, and possible duplicates.</p>
        </div>
        {report && <div className="bank-total"><span>Potential annual savings</span><strong>{money(report.potential_annual_savings_minor)}</strong><span>If you cancel every active pattern below</span></div>}
      </section>

      {pending && !report && <p className="bank-feedback" role="status">Analyzing your simulated transactions…</p>}
      {error && <div className="bank-feedback bank-error" role="alert">{error} <Button disabled={pending} onClick={() => void load()}>Retry</Button></div>}
      {report && <>
        <div className="bank-grid intelligence-grid">
          <section className="card">
            <CalendarClock size={23} aria-hidden />
            <h2>Recurring charges</h2>
            <p>Potential matches from the last 365 days. Confirm the charges and keep the services you use. Check cancellation terms and lower tiers before making changes.</p>
            {report.potential_annual_increase_minor > 0 &&
              <p className="bank-feedback">{money(report.potential_annual_increase_minor)} in estimated annual price increases across active patterns.</p>}
            {report.recurring.length === 0 ? (
              <p className="bank-empty">No recurring charges detected. Patterns need at least three similar charges on separate dates.</p>
            ) : (
              <ul className="intelligence-list">
                {report.recurring.map((charge) => (
                  <li key={`${charge.merchant}:${charge.category}`}>
                    <div className="intelligence-row">
                      <h3>{charge.merchant}</h3><strong>{money(charge.amount_minor)} {charge.cadence.toLowerCase()}</strong>
                    </div>
                    <p>{charge.category} · Last charged {financialDate(charge.last_charged)}{charge.active ? "" : " · No recent charge"}</p>
                    <p>{money(charge.annual_minor)} per year at this rate</p>
                    {charge.previous_amount_minor !== null &&
                      <p className="intelligence-flag">Possible price increase from {money(charge.previous_amount_minor)}. About {money(charge.annual_increase_minor)} more per year if the new price continues.</p>}
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="card">
            <Copy size={23} aria-hidden />
            <h2>Possible duplicates</h2>
            <p>Matching merchant, date, and amount can be legitimate. Compare receipts or statements before treating a charge as a duplicate.</p>
            {report.duplicates.length === 0 ? <p className="bank-empty">No possible duplicates detected.</p> : (
              <ul className="intelligence-list">
                {report.duplicates.map((item) => (
                  <li key={`${item.merchant}:${item.charged_on}:${item.amount_minor}`}>
                    <div className="intelligence-row"><h3>{item.merchant}</h3><strong>{item.count} × {money(item.amount_minor)}</strong></div>
                    <p>{financialDate(item.charged_on)}</p>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>

        <CoachPanel token={token} onExpired={onExpired} topic="recurring" title="Review recurring spending" label="Get review tips"
          contextKey={JSON.stringify([report.potential_annual_savings_minor, report.potential_annual_increase_minor, report.duplicates.length])} />

        <section className="card">
          <div className="intelligence-row">
            <h2>Purchase audit history</h2>
            <Link to="/">Find purchases on Home <ArrowUpRight size={17} aria-hidden /></Link>
          </div>
          {!history?.items.length ? <p className="bank-empty">Audits you save from your purchase history will appear here.</p> : (
            <ul className="intelligence-list">
              {history.items.map(({ purchase, audit }) => (
                <li key={purchase.id}>
                  <div className="intelligence-row">
                    <Link to={`/moneyleaks/audit/${purchase.id}`}>{purchase.merchant_name || purchase.description}</Link>
                    <strong>{audit?.necessity_rating}/10 · {money(-purchase.amount_minor)}</strong>
                  </div>
                  <p>{purchase.category} · {financialDate(purchase.created_at)}</p>
                  {audit?.reflection && <p className="intelligence-reflection">{audit.reflection}</p>}
                </li>
              ))}
            </ul>
          )}
          {history?.before_id !== null && history?.before_id !== undefined &&
            <Button className="bank-secondary" disabled={pending} onClick={() => void loadMore()}>Load more audits</Button>}
        </section>
      </>}
    </div>
  )
}
