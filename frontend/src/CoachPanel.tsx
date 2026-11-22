import { useEffect, useRef, useState } from "react"
import { Sparkles } from "lucide-react"
import { requestError, useAuthenticatedApi } from "./authenticatedApi"
import { Button } from "./components/ui/button"

type CoachReply = { source: "ai" | "local"; tips: string[] }

export function CoachPanel({ token, onExpired, topic, label, title, contextKey }: {
  token: string
  onExpired: () => void
  topic: string
  label: string
  title: string
  contextKey?: string
}) {
  const call = useAuthenticatedApi(token, onExpired)
  const [pending, setPending] = useState(false)
  const [reply, setReply] = useState<CoachReply>()
  const [error, setError] = useState("")
  const request = useRef<AbortController | null>(null)

  useEffect(() => {
    setReply(undefined)
    setError("")
    setPending(false)
    return () => {
      request.current?.abort()
      request.current = null
    }
  }, [topic, contextKey, token])

  async function getTips() {
    if (request.current) return
    const controller = new AbortController()
    request.current = controller
    setPending(true)
    setError("")
    setReply(undefined)
    try {
      const result = await call<CoachReply>(`/coach/${topic}`, { method: "POST", signal: controller.signal })
      if (!controller.signal.aborted) setReply(result)
    } catch (failure) {
      if (!controller.signal.aborted) setError(requestError(failure))
    } finally {
      if (!controller.signal.aborted) {
        request.current = null
        setPending(false)
      }
    }
  }

  return (
    <section className="card">
      <div className="intelligence-row">
        <h2>{title}</h2>
        <Button className="bank-secondary" disabled={pending} onClick={() => void getTips()}>
          <Sparkles size={17} aria-hidden /> {pending ? "Getting tips…" : label}
        </Button>
      </div>
      <p>Request informational budgeting tips. When AI is enabled, the coach sends a limited summary for this topic to OpenAI.</p>
      {error && <p className="bank-feedback bank-error" role="alert">{error}</p>}
      {reply && <div className="coach-reply" role="status">
        <strong>{reply.source === "ai" ? "AI-generated suggestions" : "Local suggestions"}</strong>
        <ul className="intelligence-alternatives">{reply.tips.map((tip, index) => <li key={index}>{tip}</li>)}</ul>
      </div>}
    </section>
  )
}
