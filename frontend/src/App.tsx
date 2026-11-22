import { useState, type FormEvent } from "react"
import {
  ArrowRight, ArrowUpRight, Compass, House, LogOut, ScanSearch, Sprout, Target, Users, Wallet,
} from "lucide-react"
import { Link, Navigate, NavLink, Outlet, Route, Routes, useLocation, useNavigate } from "react-router-dom"
import { api, ApiError, type User } from "./api"
import { useAuth } from "./auth"
import { Button } from "./components/ui/button"

const brand = "Tandem"

const sections = [
  { name: "Home", path: "/", icon: House },
  {
    name: "Simulator", path: "/simulator", icon: Target,
    description: "See how a purchase could change the timeline for a savings goal.",
    features: ["Set a savings goal", "Compare purchase scenarios", "Track your progress"],
  },
  {
    name: "MoneyLeaks", path: "/moneyleaks", icon: ScanSearch,
    description: "Review recurring expenses and find opportunities to keep more of your money.",
    features: ["Review subscriptions", "Spot duplicate charges", "Audit past purchases"],
  },
  {
    name: "Explore", path: "/explore", icon: Compass,
    description: "Find local deals that fit what you already planned to buy.",
    features: ["Discover nearby offers", "Browse food and clothing deals"],
  },
  {
    name: "Community", path: "/community", icon: Users,
    description: "Share savings milestones and learn from the habits that work for others.",
    features: ["Share an achievement", "Follow banknote stories"],
  },
]

function Brand() {
  return <span className="brand"><span className="brand-icon"><Sprout size={22} aria-hidden /></span>{brand}</span>
}

function SessionStatus() {
  const { state, retry, signOut } = useAuth()
  if (state.status === "unavailable") {
    return (
      <main className="status-screen">
        <p role="alert">We couldn’t connect to verify your session.</p>
        <Button onClick={retry}>Retry</Button>
        <Button className="bg-white text-foreground" onClick={signOut}>Log out</Button>
      </main>
    )
  }
  return <main className="status-screen" role="status">Checking your session…</main>
}

function AuthPage({ registration = false }: { registration?: boolean }) {
  const { state, signIn } = useAuth()
  const [error, setError] = useState("")
  const [pending, setPending] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  const returnTo = location.state?.from
  const destination = sections.some(({ path }) => path === returnTo) ? returnTo : "/"

  if (state.status === "signed-in") return <Navigate to={destination} replace />
  if (state.status !== "signed-out") return <SessionStatus />

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError("")
    setPending(true)
    const form = new FormData(event.currentTarget)
    const credentials = { email: String(form.get("email")).trim(), password: String(form.get("password")) }
    try {
      if (registration) {
        await api<User>("/auth/register", {
          method: "POST",
          body: JSON.stringify({ ...credentials, username: String(form.get("username")).trim() }),
        })
        navigate("/login", { replace: true, state: { from: destination, registered: true } })
      } else {
        await signIn(credentials)
      }
    } catch (failure) {
      setError(failure instanceof ApiError ? failure.message : "We couldn’t connect. Please try again.")
    } finally {
      setPending(false)
    }
  }

  return (
    <main className="auth-shell">
      <aside className="auth-intro">
        <Brand />
        <div>
          <h2>Make room for what matters.</h2>
          <p>See where your money goes and plan for what’s next.</p>
        </div>
        <span className="simulation"><Sprout size={16} aria-hidden /> Simulated finances</span>
      </aside>
      <section className="auth-form-area">
        <div className="auth-form">
          <h1>{registration ? "Create your account" : "Welcome back"}</h1>
          <p>{registration ? "Set up your private Tandem workspace." : "Sign in to your Tandem account."}</p>
          {location.state?.registered && <p className="success" role="status">Account created. Sign in to continue.</p>}
          <form onSubmit={submit}>
            {registration && (
              <label>Username
                <input name="username" autoComplete="username" minLength={3} maxLength={32} pattern="[a-zA-Z0-9_]{3,32}" aria-describedby="username-hint" required />
                <small id="username-hint">3–32 letters, numbers, or underscores.</small>
              </label>
            )}
            <label>Email<input name="email" type="email" autoComplete="email" maxLength={254} required /></label>
            <label>Password
              <input name="password" type="password" autoComplete={registration ? "new-password" : "current-password"} minLength={registration ? 8 : 1} maxLength={128} aria-describedby={registration ? "password-hint" : undefined} required />
              {registration && <small id="password-hint">Use at least 8 characters.</small>}
            </label>
            {error && <p role="alert" className="form-error">{error}</p>}
            <Button type="submit" disabled={pending}>
              {pending ? "Please wait…" : registration ? "Create account" : "Sign in"}<ArrowRight size={17} aria-hidden />
            </Button>
          </form>
          <p className="auth-switch">
            {registration ? "Already have an account? " : "New to Tandem? "}
            <Link to={registration ? "/login" : "/register"} state={{ from: destination }}>
              {registration ? "Sign in" : "Create an account"}
            </Link>
          </p>
        </div>
      </section>
    </main>
  )
}

function Layout() {
  const { state, signOut } = useAuth()
  const location = useLocation()
  if (state.status === "signed-out") return <Navigate to="/login" replace state={{ from: location.pathname }} />
  if (state.status !== "signed-in") return <SessionStatus />
  const { user } = state

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Link to="/" aria-label="Tandem home"><Brand /></Link>
        <nav aria-label="Main navigation">
          {sections.map(({ name, path, icon: Icon }) => (
            <NavLink key={path} to={path} end><Icon size={21} aria-hidden /><span>{name}</span></NavLink>
          ))}
        </nav>
        <span className="simulation"><Sprout size={16} aria-hidden /> Simulated finances</span>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <span className="topbar-title">Personal workspace</span>
          <Link to="/" className="mobile-brand" aria-label="Tandem home"><Brand /></Link>
          <details className="profile">
            <summary aria-label={`Account menu for ${user.username}`}>
              <span className="avatar">{user.username.slice(0, 2).toUpperCase()}</span>
              <span className="profile-name">{user.username}</span>
            </summary>
            <div className="profile-panel">
              <p>{user.email}</p>
              <Button className="w-full justify-start bg-transparent px-2 text-foreground hover:bg-muted" onClick={signOut}>
                <LogOut size={17} aria-hidden /> Log out
              </Button>
            </div>
          </details>
        </header>
        <main className="content"><Outlet /></main>
      </div>
    </div>
  )
}

function Home() {
  const { state } = useAuth()
  if (state.status !== "signed-in") return null

  return (
    <>
      <section className="hero">
        <div className="section-icon"><Sprout size={25} aria-hidden /></div>
        <h1>Welcome, {state.user.username}.</h1>
        <p>Your private space for tracking spending and growing savings.</p>
      </section>
      <section className="dashboard-grid" aria-label="Financial overview">
        <article className="card">
          <Wallet size={23} aria-hidden />
          <h2>Virtual banking</h2>
          <p>Balances and recent activity will appear here once virtual banking is available.</p>
        </article>
        <article className="card">
          <Target size={23} aria-hidden />
          <h2>Savings goals</h2>
          <p>See what’s planned for setting goals and estimating purchase impact.</p>
          <Link to="/simulator">Open Simulator <ArrowUpRight size={17} aria-hidden /></Link>
        </article>
      </section>
    </>
  )
}

function SectionPage({ section }: { section: (typeof sections)[number] }) {
  const Icon = section.icon
  return (
    <>
      <section className="hero">
        <div className="section-icon"><Icon size={25} aria-hidden /></div>
        <h1>{section.name}</h1>
        <p>{section.description}</p>
      </section>
      <section className="card roadmap">
        <h2>Planned features</h2>
        <ul>{section.features?.map((feature) => <li key={feature}>{feature}</li>)}</ul>
      </section>
    </>
  )
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<AuthPage key="login" />} />
      <Route path="/register" element={<AuthPage key="register" registration />} />
      <Route element={<Layout />}>
        <Route index element={<Home />} />
        {sections.slice(1).map((section) => (
          <Route key={section.path} path={section.path} element={<SectionPage section={section} />} />
        ))}
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
