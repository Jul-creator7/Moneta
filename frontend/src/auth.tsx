import { createContext, useContext, useEffect, useState, type ReactNode } from "react"
import { api, ApiError, type Credentials, type User } from "./api"

const tokenKey = "tandem.access_token"
type AuthState =
  | { status: "loading" | "signed-out" | "unavailable" }
  | { status: "signed-in"; user: User; token: string }

const AuthContext = createContext<{
  state: AuthState
  signIn: (credentials: Credentials) => Promise<void>
  signOut: () => void
  retry: () => void
} | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({ status: "loading" })
  const [attempt, setAttempt] = useState(0)

  function signOut() {
    localStorage.removeItem(tokenKey)
    setState({ status: "signed-out" })
  }

  useEffect(() => {
    const token = localStorage.getItem(tokenKey)
    if (!token) {
      setState({ status: "signed-out" })
      return
    }
    const controller = new AbortController()
    api<User>("/users/me", { signal: controller.signal }, token)
      .then((user) => {
        if (!controller.signal.aborted) setState({ status: "signed-in", user, token })
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return
        if (error instanceof ApiError && error.status === 401) signOut()
        else setState({ status: "unavailable" })
      })
    return () => controller.abort()
  }, [attempt])

  async function signIn(credentials: Credentials) {
    const { access_token } = await api<{ access_token: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify(credentials),
    })
    const user = await api<User>("/users/me", {}, access_token)
    localStorage.setItem(tokenKey, access_token)
    setState({ status: "signed-in", user, token: access_token })
  }

  function retry() {
    setState({ status: "loading" })
    setAttempt((previous) => previous + 1)
  }

  return <AuthContext.Provider value={{ state, signIn, signOut, retry }}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const auth = useContext(AuthContext)
  if (!auth) throw new Error("AuthProvider is required")
  return auth
}
