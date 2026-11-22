import { lazy, Suspense, useCallback, useEffect, useRef, useState, type FormEvent } from "react"
import { ArrowDownLeft, ArrowLeftRight, ArrowUpRight, CircleDollarSign, Landmark, PiggyBank } from "lucide-react"
import { Link } from "react-router-dom"
import { api, ApiError, apiResponse } from "./api"
import {
  expenseCategories, money, operations, readAmount,
  type Account, type Dashboard, type Entry, type History, type OperationType,
} from "./banking"
import { Button } from "./components/ui/button"

const SpendingChart = lazy(() => import("./SpendingChart"))
const dates = new Intl.DateTimeFormat(undefined, { dateStyle: "medium" })

function errorText(error: unknown) {
  return error instanceof ApiError ? error.message : "The server could not be reached. Please try again."
}

export function BankingDashboard({ username, token, onExpired }: {
  username: string
  token: string
  onExpired: () => void
}) {
  const [dashboard, setDashboard] = useState<Dashboard>()
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState("")
  const [notice, setNotice] = useState("")
  const [auditId, setAuditId] = useState<string | null>(null)
  const [actionError, setActionError] = useState("")
  const [pending, setPending] = useState(false)
  const [history, setHistory] = useState<History>()
  const [historyPending, setHistoryPending] = useState(false)
  const [confirmReset, setConfirmReset] = useState(false)
  const request = useRef<{ body: string; id: string } | undefined>(undefined)
  const mutation = useRef(false)
  const expired = useRef(onExpired)
  expired.current = onExpired

  const call = useCallback(async <T,>(path: string, options?: RequestInit) => {
    try {
      return await api<T>(`/banking${path}`, options, token)
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) expired.current()
      throw error
    }
  }, [token])

  const refresh = useCallback(async (signal?: AbortSignal) => {
    setLoading(true)
    setLoadError("")
    try {
      const data = await call<Dashboard>("/dashboard", { signal })
      if (!signal?.aborted) setDashboard(data)
    } catch (error) {
      if (!signal?.aborted) setLoadError(errorText(error))
    } finally {
      if (!signal?.aborted) setLoading(false)
    }
  }, [call])

  useEffect(() => {
    const controller = new AbortController()
    void refresh(controller.signal)
    return () => controller.abort()
  }, [refresh])

  async function perform(path: string, message: string, body?: string, offerAudit = false) {
    if (mutation.current) return false
    mutation.current = true
    setPending(true)
    setNotice("")
    setAuditId(null)
    setActionError("")
    try {
      const response = await apiResponse(`/banking${path}`, { method: "POST", body }, token)
      if (offerAudit) setAuditId(response.headers.get("X-Transaction-Id"))
      setConfirmReset(false)
      setHistory(undefined)
      setNotice(message)
      await refresh()
      return true
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) expired.current()
      setActionError(errorText(error))
      return false
    } finally {
      mutation.current = false
      setPending(false)
    }
  }

  async function submit(payload: Record<string, unknown>) {
    const body = JSON.stringify(payload)
    const previous = request.current
    const id = previous?.body === body ? previous.id : crypto.randomUUID()
    request.current = { body, id }
    const saved = await perform("/operations", "Simulated transaction recorded.", JSON.stringify({
      ...payload, operation_id: id,
    }), payload.transaction_type === "purchase")
    if (saved) request.current = undefined
    return saved
  }

  async function loadHistory() {
    setHistoryPending(true)
    setActionError("")
    try {
      const page = await call<History>(`/transactions?offset=${history?.next_offset ?? 0}`)
      setHistory({
        transactions: [...(history?.transactions ?? []), ...page.transactions],
        next_offset: page.next_offset,
      })
    } catch (error) {
      setActionError(errorText(error))
    } finally {
      setHistoryPending(false)
    }
  }

  const disabled = pending || historyPending || loading || Boolean(loadError)

  return (
    <div className="banking">
      <section className="bank-hero">
        <div>
          <p className="bank-eyebrow"><Landmark size={16} aria-hidden /> Simulated banking · CAD</p>
          <h1>Welcome, {username}.</h1>
          <p>Review your balances, track spending, and move simulated money.</p>
        </div>
        {dashboard && <div className="bank-total"><span>Total virtual balance</span><strong>{money(dashboard.total_balance_minor)}</strong></div>}
      </section>

      {loadError && <div className="bank-feedback" role="alert">{loadError} <Button onClick={() => void refresh()}>Retry</Button></div>}
      {!dashboard && loading && <p className="bank-feedback" role="status">Loading your dashboard…</p>}
      {dashboard && (
        <>
          <section className="bank-metrics" aria-label="Account balances and monthly totals">
            {dashboard.accounts.map((account) => (
              <article className="card" key={account.id}>
                {account.account_type === "savings" ? <PiggyBank size={23} aria-hidden /> : <Landmark size={23} aria-hidden />}
                <h2>{account.name}</h2><strong>{money(account.balance_minor)}</strong>
              </article>
            ))}
            <article className="card"><ArrowDownLeft size={23} aria-hidden /><h2>Income this month</h2><strong>{money(dashboard.monthly_income_minor)}</strong></article>
            <article className="card"><ArrowUpRight size={23} aria-hidden /><h2>Spending this month</h2><strong>{money(dashboard.monthly_spending_minor)}</strong></article>
          </section>

          <section className="card bank-demo">
            <div><h2>Savings goals</h2><p>Allocate money from savings and see how a purchase could change your timeline.</p></div>
            <Link to="/simulator">Open savings simulator <ArrowUpRight size={17} aria-hidden /></Link>
          </section>

          <div className="bank-grid">
            <OperationForm accounts={dashboard.accounts} disabled={disabled || confirmReset} onSubmit={submit} />
            <section className="card bank-chart" aria-labelledby="spending-title">
              <div>
                <h2 id="spending-title">Spending by category</h2>
                <p>This month (UTC) · Savings rate {dashboard.monthly_savings_rate === null ? "available after recording income" : `${dashboard.monthly_savings_rate}%`}</p>
              </div>
              {dashboard.spending_by_category.length ? (
                <>
                  <Suspense fallback={<p className="bank-empty">Loading spending chart…</p>}>
                    <SpendingChart totals={dashboard.spending_by_category} />
                  </Suspense>
                  <ul className="bank-category-list" aria-label="Category totals">
                    {dashboard.spending_by_category.map(({ category, total_minor }) => <li key={category}>{category} <strong>{money(total_minor)}</strong></li>)}
                  </ul>
                </>
              ) : <p className="bank-empty">Record a simulated purchase or bill to see spending here.</p>}
            </section>
          </div>

          {notice && <div className="bank-feedback bank-success intelligence-feedback">
            <p role="status">{notice}</p>
            {auditId && <Link to={`/moneyleaks/audit/${auditId}`}>Audit this purchase</Link>}
          </div>}
          {actionError && <p role="alert" className="bank-feedback bank-error">{actionError}</p>}

          <section className="card bank-history" aria-labelledby="history-title">
            <h2 id="history-title">{history ? "Transaction history" : "Recent transactions"}</h2>
            <TransactionList accounts={dashboard.accounts} entries={history?.transactions ?? dashboard.recent_transactions} />
            {!history && dashboard.recent_transactions.length > 0 && (
              <Button className="bank-secondary" disabled={disabled} onClick={() => void loadHistory()}>View history</Button>
            )}
            {history && history.next_offset !== null && (
              <Button className="bank-secondary" disabled={disabled} onClick={() => void loadHistory()}>Load more transactions</Button>
            )}
          </section>

          <section className="card bank-demo">
            <div><h2>Demo data</h2><p>Load sample activity into empty accounts, or clear your simulated balances and transactions.</p></div>
            <div className="bank-actions">
              {confirmReset ? (
                <>
                  <span>Clear simulated balances, activity, and goal allocations?</span>
                  <Button className="bank-danger" disabled={disabled} onClick={() => void perform("/reset", "Simulation reset.")}>Confirm reset</Button>
                  <Button className="bank-secondary" disabled={pending} onClick={() => setConfirmReset(false)}>Cancel</Button>
                </>
              ) : (
                <>
                  <Button className="bank-secondary" onClick={() => void perform("/demo", "Demo transactions loaded.")} disabled={disabled || dashboard.recent_transactions.length > 0 || dashboard.total_balance_minor !== 0}>Load demo data</Button>
                  <Button className="bank-secondary" disabled={disabled} onClick={() => setConfirmReset(true)}>Reset simulation</Button>
                </>
              )}
            </div>
          </section>
        </>
      )}
    </div>
  )
}

function OperationForm({ accounts, disabled, onSubmit }: {
  accounts: Account[]
  disabled: boolean
  onSubmit: (payload: Record<string, unknown>) => Promise<boolean>
}) {
  const [kind, setKind] = useState<OperationType>("deposit")
  const [account, setAccount] = useState<Account["account_type"]>("chequing")
  const [error, setError] = useState("")
  const expense = kind === "purchase" || kind === "bill"
  const destination = account === "chequing" ? "savings" : "chequing"

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    const fields = new FormData(form)
    const amount = readAmount(String(fields.get("amount")))
    if (amount === null) {
      setError("Enter an amount from $0.01 to $1,000,000 with up to two decimal places.")
      return
    }
    setError("")
    const saved = await onSubmit({
      transaction_type: kind,
      account_type: account,
      amount_minor: amount,
      destination: kind === "transfer" ? destination : undefined,
      merchant_name: expense ? String(fields.get("merchant")) : undefined,
      category: expense ? String(fields.get("category")) : undefined,
      description: String(fields.get("description")).trim() || undefined,
    })
    if (saved) form.reset()
  }

  return (
    <section className="card">
      <h2>Simulate a transaction</h2>
      <form className="bank-form" onSubmit={(event) => void submit(event)}>
        <fieldset disabled={disabled}>
          <label><span id="bank-action-label">Action</span><select aria-labelledby="bank-action-label" value={kind} onChange={(event) => setKind(event.target.value as OperationType)}>
            {Object.entries(operations).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select></label>
          <div className="bank-fields">
            <label><span id="bank-account-label">{kind === "transfer" ? "From account" : "Account"}</span><select aria-labelledby="bank-account-label" value={account} onChange={(event) => setAccount(event.target.value as Account["account_type"])}>
              {accounts.map((item) => <option key={item.id} value={item.account_type}>{item.name}</option>)}
            </select></label>
            <label>Amount (CAD)<input name="amount" inputMode="decimal" placeholder="0.00" required /></label>
          </div>
          {kind === "transfer" && <p>To {accounts.find((item) => item.account_type === destination)?.name}</p>}
          {expense && <div className="bank-fields">
            <label>Merchant<input name="merchant" maxLength={80} required /></label>
            <label><span id="bank-category-label">Category</span><select aria-labelledby="bank-category-label" name="category" defaultValue="" required>
              <option value="" disabled>Choose category</option>
              {expenseCategories.map((category) => <option key={category}>{category}</option>)}
            </select></label>
          </div>}
          <label>Description (optional)<input name="description" maxLength={160} /></label>
          {error && <p className="bank-error" role="alert">{error}</p>}
          <Button type="submit"><CircleDollarSign size={17} aria-hidden /> {operations[kind]}</Button>
        </fieldset>
      </form>
    </section>
  )
}

function TransactionList({ accounts, entries }: { accounts: Account[]; entries: Entry[] }) {
  if (!entries.length) return <p className="bank-empty">Your simulated transactions will appear here.</p>
  return (
    <ul className="bank-transactions">
      {entries.map((entry) => {
        const Icon = entry.transaction_type === "transfer" ? ArrowLeftRight : entry.amount_minor > 0 ? ArrowDownLeft : ArrowUpRight
        return (
          <li key={entry.id}>
            <span className="bank-entry-icon"><Icon size={18} aria-hidden /></span>
            <div><strong>{entry.merchant_name || entry.description}</strong>
              <p>{accounts.find((account) => account.id === entry.account_id)?.name} · {entry.category} · {dates.format(new Date(entry.created_at))}</p>
              {entry.transaction_type === "purchase" && <Link to={`/moneyleaks/audit/${entry.id}`}>Audit purchase<span className="sr-only"> from {entry.merchant_name || entry.description}</span></Link>}
            </div>
            <strong className={entry.amount_minor > 0 ? "bank-positive" : ""}>{entry.amount_minor > 0 ? "+" : ""}{money(entry.amount_minor)}</strong>
          </li>
        )
      })}
    </ul>
  )
}
