import { useCallback, useEffect, useState, type FormEvent } from "react"
import { ArrowLeft, ClipboardCheck, Target } from "lucide-react"
import { Link } from "react-router-dom"
import { requestError, useAuthenticatedApi } from "./authenticatedApi"
import { money } from "./banking"
import { CoachPanel } from "./CoachPanel"
import { Button } from "./components/ui/button"
import {
  financialDate, type AuditedPurchase, type AuditProjection, type GoalOption,
} from "./intelligence"

export function PurchaseAudit({ token, onExpired, transactionId }: {
  token: string; onExpired: () => void; transactionId: string
}) {
  const call = useAuthenticatedApi(token, onExpired)
  const [detail, setDetail] = useState<AuditedPurchase>()
  const [goals, setGoals] = useState<GoalOption[]>([])
  const [goalId, setGoalId] = useState("")
  const [projection, setProjection] = useState<AuditProjection>()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [projecting, setProjecting] = useState(false)
  const [loadError, setLoadError] = useState("")
  const [saveError, setSaveError] = useState("")
  const [projectionError, setProjectionError] = useState("")
  const [notice, setNotice] = useState("")
  const path = `/audits/${transactionId}`

  const load = useCallback(async (signal?: AbortSignal) => {
    setLoading(true)
    setLoadError("")
    try {
      const [data, options] = await Promise.all([
        call<AuditedPurchase>(path, { signal }),
        call<{ goals: GoalOption[] }>("/goals", { signal }),
      ])
      if (!signal?.aborted) {
        setDetail(data)
        setGoals(options.goals)
      }
    } catch (error) {
      if (!signal?.aborted) setLoadError(requestError(error))
    } finally {
      if (!signal?.aborted) setLoading(false)
    }
  }, [call, path])

  useEffect(() => {
    const controller = new AbortController()
    void load(controller.signal)
    return () => controller.abort()
  }, [load])

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (saving) return
    const fields = new FormData(event.currentTarget)
    setSaving(true)
    setSaveError("")
    setNotice("")
    try {
      const data = await call<AuditedPurchase>(path, {
        method: "PUT",
        body: JSON.stringify({
          necessity_rating: Number(fields.get("rating")),
          reflection: String(fields.get("reflection")).trim() || null,
        }),
      })
      setDetail(data)
      setNotice("Purchase audit saved.")
    } catch (error) {
      setSaveError(requestError(error))
    } finally {
      setSaving(false)
    }
  }

  async function estimate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!goalId || projecting) return
    setProjecting(true)
    setProjectionError("")
    setProjection(undefined)
    try {
      const result = await call<AuditProjection>(`${path}/projection/${goalId}`)
      setProjection(result)
    } catch (error) {
      setProjectionError(requestError(error))
    } finally {
      setProjecting(false)
    }
  }

  const purchase = detail?.purchase
  return (
    <div className="banking">
      <section className="bank-hero">
        <div>
          <p className="bank-eyebrow"><ClipboardCheck size={16} aria-hidden /> Private purchase audit</p>
          <h1>{purchase?.merchant_name || purchase?.description || "Review purchase"}</h1>
          {purchase && <p>{purchase.category} · {financialDate(purchase.created_at)} · Simulated CAD</p>}
        </div>
        {purchase && <div className="bank-total"><span>Purchase amount</span><strong>{money(-purchase.amount_minor)}</strong></div>}
      </section>
      <Link to="/moneyleaks" className="intelligence-back"><ArrowLeft size={17} aria-hidden /> Back to MoneyLeaks</Link>
      {loading && <p className="bank-feedback" role="status">Loading purchase…</p>}
      {loadError && <div className="bank-feedback bank-error" role="alert">{loadError} <Button onClick={() => void load()}>Retry</Button></div>}
      {detail && <div className="bank-grid intelligence-grid">
        <section className="card">
          <h2>How necessary was this purchase?</h2>
          <form className="bank-form" onSubmit={(event) => void save(event)}>
            <fieldset disabled={saving || loading}>
              <label>
                <span id="audit-rating-label">Necessity rating</span>
                <select name="rating" aria-labelledby="audit-rating-label" defaultValue={detail.audit?.necessity_rating ?? ""} required>
                  <option value="" disabled>Select a rating</option>
                  {Array.from({ length: 10 }, (_, index) => index + 1).map((rating) => (
                    <option key={rating} value={rating}>{rating}{rating === 1 ? " · Not necessary" : rating === 5 ? " · Somewhat necessary" : rating === 10 ? " · Essential" : ""}</option>
                  ))}
                </select>
              </label>
              <label>Reflection (optional)<textarea name="reflection" rows={4} maxLength={2000} defaultValue={detail.audit?.reflection ?? ""} /></label>
              <Button type="submit">{saving ? "Saving…" : "Save audit"}</Button>
            </fieldset>
          </form>
          {notice && <p className="bank-feedback bank-success" role="status">{notice}</p>}
          {saveError && <p className="bank-feedback bank-error" role="alert">{saveError}</p>}
          {detail.audit && <div>
            <h3>Lower-cost options for next time</h3>
            <ul className="intelligence-alternatives">{detail.alternatives.map((item) => <li key={item}>{item}</li>)}</ul>
          </div>}
        </section>

        <section className="card">
          <Target size={23} aria-hidden />
          <h2>Estimated effect on a savings goal</h2>
          <p>Compare your current plan with a scenario where this purchase diverts the same amount from upcoming contributions. The estimate leaves your balances and goal unchanged.</p>
          {goals.length === 0 ? <Link to="/simulator">Create a savings goal</Link> : (
            <form className="bank-form" onSubmit={(event) => void estimate(event)}>
              <fieldset disabled={projecting || loading}>
                <label>
                  <span id="audit-goal-label">Savings goal</span>
                  <select aria-labelledby="audit-goal-label" value={goalId} onChange={(event) => {
                    setGoalId(event.target.value)
                    setProjection(undefined)
                    setProjectionError("")
                  }} required>
                    <option value="" disabled>Choose a goal</option>
                    {goals.map((goal) => <option value={goal.id} key={goal.id}>{goal.name}</option>)}
                  </select>
                </label>
                <Button className="bank-secondary" type="submit">Estimate delay</Button>
              </fieldset>
            </form>
          )}
          {projectionError && <p role="alert" className="bank-feedback bank-error">{projectionError}</p>}
          {projection && <div className="goal-comparison" role="status">
            <h3>{projection.delay_days === null ? "Delay unavailable at the current contribution" : projection.delay_days === 0 ? "No estimated delay" : `About ${projection.delay_days.toLocaleString()} days later`}</h3>
            <div className="intelligence-row"><span>Without purchase</span><strong>{projection.baseline.estimated_date ? financialDate(projection.baseline.estimated_date) : "No estimated date"}</strong></div>
            <div className="intelligence-row"><span>With purchase</span><strong>{projection.with_purchase.estimated_date ? financialDate(projection.with_purchase.estimated_date) : "No estimated date"}</strong></div>
          </div>}
        </section>
      </div>}
      {detail?.audit && <CoachPanel token={token} onExpired={onExpired} topic={`purchases/${transactionId}`}
        title="Explore more alternatives" label="Get alternative ideas" contextKey={String(detail.audit.necessity_rating)} />}
    </div>
  )
}
