import { Link } from "react-router-dom"
import { useCallback, useEffect, useRef, useState, type FormEvent } from "react"
import { ArrowLeftRight, CalendarDays, PiggyBank, Target } from "lucide-react"
import { api, ApiError } from "./api"
import { money, readAmount } from "./banking"
import { Button } from "./components/ui/button"

type GoalPlan = {
  name: string
  target_minor: number
  monthly_minor: number
  target_date: string | null
}
type Goal = GoalPlan & { id: number; allocated_minor: number }
type Goals = { goals: Goal[]; savings_minor: number; unallocated_minor: number }
type Timeline = { starting_minor: number; periods: number | null; estimated_date: string | null }
type Projection = { baseline: Timeline; with_purchase: Timeline; delay_days: number | null; period_days: number }
type Funding = "allocated" | "contributions"

const dateFormat = new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeZone: "UTC" })
const showDate = (value: string) => dateFormat.format(new Date(`${value}T00:00:00Z`))
const inputMoney = (value: number | undefined) => value === undefined ? "" : (value / 100).toFixed(2)
const message = (error: unknown) => error instanceof ApiError ? error.message : "The server could not be reached. Please try again."

export function SavingsSimulator({ token, onExpired }: { token: string; onExpired: () => void }) {
  const [data, setData] = useState<Goals>()
  const [selected, setSelected] = useState<number>()
  const [edit, setEdit] = useState(false)
  const [loading, setLoading] = useState(true)
  const [pending, setPending] = useState(false)
  const [loadError, setLoadError] = useState("")
  const [error, setError] = useState("")
  const [notice, setNotice] = useState("")
  const [projection, setProjection] = useState<Projection>()
  const active = useRef(false)
  const expired = useRef(onExpired)
  expired.current = onExpired

  const call = useCallback(async <T,>(path: string, options?: RequestInit) => {
    try {
      return await api<T>(`/goals${path}`, options, token)
    } catch (failure) {
      if (failure instanceof ApiError && failure.status === 401) expired.current()
      throw failure
    }
  }, [token])

  const refresh = useCallback(async (signal?: AbortSignal) => {
    setLoading(true)
    setLoadError("")
    try {
      const goals = await call<Goals>("", { signal })
      if (!signal?.aborted) setData(goals)
    } catch (failure) {
      if (!signal?.aborted) setLoadError(message(failure))
    } finally {
      if (!signal?.aborted) setLoading(false)
    }
  }, [call])

  useEffect(() => {
    const controller = new AbortController()
    void refresh(controller.signal)
    return () => controller.abort()
  }, [refresh])

  async function run(task: () => Promise<void>) {
    if (active.current) return false
    active.current = true
    setPending(true)
    setError("")
    setNotice("")
    setProjection(undefined)
    try {
      await task()
      return true
    } catch (failure) {
      setError(message(failure))
      return false
    } finally {
      active.current = false
      setPending(false)
    }
  }

  const goal = data?.goals.find(({ id }) => id === selected) ?? data?.goals[0]
  const disabled = loading || pending || Boolean(loadError)
  const choose = (id: number) => {
    setSelected(id)
    setEdit(false)
    setError("")
    setNotice("")
    setProjection(undefined)
  }

  async function savePlan(plan: GoalPlan, id?: number) {
    return run(async () => {
      const saved = await call<Goal>(id === undefined ? "" : `/${id}`, {
        method: id === undefined ? "POST" : "PUT", body: JSON.stringify(plan),
      })
      choose(saved.id)
      setNotice(id === undefined ? "Savings goal created." : "Goal plan updated.")
      await refresh()
    })
  }

  async function allocate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const amount = readAmount(String(new FormData(event.currentTarget).get("allocation")), true)
    if (amount === null || !goal) {
      setError("Enter a valid allocation in CAD. Use 0 to release all funds.")
      return
    }
    await run(async () => {
      await call<Goal>(`/${goal.id}/allocation`, {
        method: "PUT", body: JSON.stringify({ allocated_minor: amount }),
      })
      setNotice("Goal allocation updated.")
      await refresh()
    })
  }

  async function simulate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const fields = new FormData(event.currentTarget)
    const amount = readAmount(String(fields.get("purchase")))
    if (amount === null || !goal) {
      setProjection(undefined)
      setError("Enter a valid purchase amount in CAD.")
      return
    }
    await run(async () => {
      const result = await call<Projection>(`/${goal.id}/projection`, {
        method: "POST", body: JSON.stringify({ amount_minor: amount, funding: fields.get("funding") as Funding }),
      })
      setProjection(result)
    })
  }

  return (
    <div className="banking">
      <section className="bank-hero">
        <div>
          <p className="bank-eyebrow"><Target size={16} aria-hidden /> Savings goals · Simulated CAD</p>
          <h1>New Savings</h1>
          <p>Set a savings target and see how buying something today could change your timeline.</p>
        </div>
        {data && <div className="bank-total"><span>Unallocated savings</span><strong>{money(data.unallocated_minor)}</strong><span>of {money(data.savings_minor)} in savings</span></div>}
      </section>

      {loadError && <div className="bank-feedback bank-error" role="alert">{loadError} <Button onClick={() => void refresh()}>Retry</Button></div>}
      {!data && loading && <p className="bank-feedback" role="status">Loading your savings goals…</p>}
      {notice && <p role="status" className="bank-feedback bank-success">{notice}</p>}
      {error && <p role="alert" className="bank-feedback bank-error">{error}</p>}

      {data && (
        <div className="goal-layout">
          <div className="goal-column">
            <section className="card">
              <h2>Your savings goals</h2>
              {data.goals.length === 0 && <p>Create your first goal to begin comparing timelines.</p>}
              <ul className="goal-list">
                {data.goals.map((item) => (
                  <li key={item.id}>
                    <button type="button" aria-pressed={goal?.id === item.id} disabled={disabled} onClick={() => choose(item.id)}>
                      <span><Target size={16} aria-hidden /> {item.name}</span>
                      <small>{money(item.allocated_minor)} of {money(item.target_minor)}</small>
                    </button>
                  </li>
                ))}
              </ul>
            </section>

            <section className="card">
              <h2>New savings goal</h2>
              <PlanForm disabled={disabled} onSave={savePlan} />
            </section>
          </div>

          {goal && (
            <div className="goal-column">
              <section className="card">
                <div className="goal-heading">
                  <div><h2>{goal.name}</h2><p>{goal.target_date ? `Target date ${showDate(goal.target_date)}` : "No target date set"}</p></div>
                  <div className="bank-actions">
                    <Button className="bank-secondary" disabled={disabled} onClick={() => setEdit(!edit)}>{edit ? "Cancel edit" : "Edit plan"}</Button>
                    <Link to="/community" state={{ goalDraft: `I’ve reached ${Math.floor(goal.allocated_minor * 100 / goal.target_minor)}% of my savings goal: ${goal.name}!` }}>Share goal</Link>
                  </div>
                </div>
                <div className="goal-progress">
                  <label htmlFor="goal-progress">Allocated progress</label>
                  <strong>{money(goal.allocated_minor)} / {money(goal.target_minor)}</strong>
                  <progress id="goal-progress" max={goal.target_minor} value={goal.allocated_minor} />
                </div>
                <p>Planned contribution of <strong>{money(goal.monthly_minor)}</strong> every 30 days.</p>
                {edit ? <PlanForm key={goal.id} goal={goal} disabled={disabled} onSave={savePlan} /> : (
                  <form className="bank-form" onSubmit={(event) => void allocate(event)}>
                    <fieldset disabled={disabled}>
                      <label>Total allocated (CAD)<input key={`${goal.id}:${goal.allocated_minor}`} name="allocation" inputMode="decimal" defaultValue={inputMoney(goal.allocated_minor)} required /></label>
                      <p>Set the total reserved for this goal. Lower it to release funds back to unallocated savings.</p>
                      <Button className="bank-secondary" type="submit"><PiggyBank size={17} aria-hidden /> Update allocation</Button>
                    </fieldset>
                  </form>
                )}
              </section>

              <section className="card">
                <h2>Compare a purchase</h2>
                <form key={goal.id} className="bank-form" onSubmit={(event) => void simulate(event)} onChange={() => setProjection(undefined)}>
                  <fieldset disabled={disabled}>
                    <div className="bank-fields">
                      <label>Purchase amount (CAD)<input name="purchase" inputMode="decimal" placeholder="0.00" required /></label>
                      <label><span id="purchase-funding-label">Fund the purchase from</span>
                        <select aria-labelledby="purchase-funding-label" name="funding" defaultValue="contributions">
                          <option value="contributions">Upcoming contributions</option>
                          <option value="allocated">This goal’s allocated savings</option>
                        </select>
                      </label>
                    </div>
                    <Button type="submit"><ArrowLeftRight size={17} aria-hidden /> Compare timelines</Button>
                  </fieldset>
                </form>
                <p>The estimate applies contributions every 30 days. A purchase can reduce today’s allocation or divert upcoming contributions until its cost is covered.</p>
                {projection && <TimelineComparison projection={projection} targetDate={goal.target_date} />}
              </section>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function PlanForm({ goal, disabled, onSave }: {
  goal?: Goal
  disabled: boolean
  onSave: (plan: GoalPlan, id?: number) => Promise<boolean>
}) {
  const [error, setError] = useState("")
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    const fields = new FormData(form)
    const target = readAmount(String(fields.get("target")))
    const monthly = readAmount(String(fields.get("monthly")), true)
    if (target === null || monthly === null) {
      setError("Enter a positive target and a valid contribution. Use 0 to pause contributions.")
      return
    }
    setError("")
    const saved = await onSave({
      name: String(fields.get("name")),
      target_minor: target,
      monthly_minor: monthly,
      target_date: String(fields.get("date")) || null,
    }, goal?.id)
    if (saved && !goal) form.reset()
  }
  return (
    <form className="bank-form" onSubmit={(event) => void submit(event)}>
      <fieldset disabled={disabled}>
        <label>Goal name<input name="name" maxLength={80} defaultValue={goal?.name} required /></label>
        <div className="bank-fields">
          <label>Target (CAD)<input name="target" inputMode="decimal" defaultValue={inputMoney(goal?.target_minor)} required /></label>
          <label>Monthly contribution (CAD)<input name="monthly" inputMode="decimal" defaultValue={inputMoney(goal?.monthly_minor) || "0.00"} required /></label>
        </div>
        <label>Target date (optional)<input name="date" type="date" min="0001-01-01" max="9999-12-31" defaultValue={goal?.target_date ?? ""} /></label>
        {error && <p role="alert" className="bank-error">{error}</p>}
        <Button type="submit">{goal ? "Save plan" : "Create goal"}</Button>
      </fieldset>
    </form>
  )
}

function TimelineComparison({ projection, targetDate }: { projection: Projection; targetDate: string | null }) {
  const scenarios = [
    { label: "Without purchase", timeline: projection.baseline, style: "goal-baseline" },
    { label: "With purchase", timeline: projection.with_purchase, style: "goal-alternative" },
  ]
  const scale = Math.max(1, ...scenarios.map(({ timeline }) => timeline.periods ?? 0))
  const delay = projection.delay_days
  return (
    <section className="goal-comparison" aria-label="Estimated timelines" aria-live="polite">
      <h3><CalendarDays size={17} aria-hidden /> {delay === null ? "Delay unavailable at the current contribution" : delay === 0 ? "No estimated delay" : `About ${delay.toLocaleString()} days later`}</h3>
      {scenarios.map(({ label, timeline, style }) => (
        <div className="goal-scenario" key={label}>
          <span>{label}</span>
          <strong>{timeline.estimated_date ? showDate(timeline.estimated_date) : timeline.periods === null ? "No estimated date" : "Beyond calendar range"}</strong>
          {timeline.periods !== null && <div className="goal-track" aria-hidden="true"><span className={style} style={{ width: `${timeline.periods / scale * 100}%` }} /></div>}
          <small>{money(timeline.starting_minor)} starting allocation{timeline.periods === null ? " · Add a contribution to estimate a date" : ` · ${(timeline.periods * projection.period_days).toLocaleString()} days`}{targetDate && timeline.estimated_date ? (timeline.estimated_date <= targetDate ? " · Meets target date" : " · After target date") : ""}</small>
        </div>
      ))}
    </section>
  )
}
