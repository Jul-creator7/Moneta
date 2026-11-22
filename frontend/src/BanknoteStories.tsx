import { useRef, useState, type FormEvent } from "react"
import { Banknote, LockKeyhole, MapPin, Search } from "lucide-react"
import { Link } from "react-router-dom"
import { ApiError } from "./api"
import { requestError, useAuthenticatedApi } from "./authenticatedApi"
import { communityDate, submission } from "./communityUtils"
import { imageTypes, readPostImage } from "./postImage"
import { Button } from "./components/ui/button"

type Identity = { currency: string; denomination: number; serial_number: string; series: string }
type StoryEvent = { id: number; city: string; message: string; image: string | null; is_hidden: boolean; created_at: string }
type Story = { note: Identity; events: StoryEvent[]; before_id: number | null }

export function BanknoteStories({ token, onExpired }: { token: string; onExpired: () => void }) {
  const call = useAuthenticatedApi(token, onExpired)
  const [story, setStory] = useState<Story>()
  const [missing, setMissing] = useState<Identity>()
  const [pending, setPending] = useState(false)
  const [error, setError] = useState("")
  const [status, setStatus] = useState("")
  const attempt = useRef<{ key: string; id: string } | undefined>(undefined)

  async function run(task: () => Promise<void>) {
    setPending(true)
    setError("")
    setStatus("")
    try {
      await task()
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : requestError(failure))
    } finally {
      setPending(false)
    }
  }

  async function find(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const fields = new FormData(event.currentTarget)
    const identity = {
      currency: String(fields.get("currency")).trim(),
      denomination: Number(fields.get("denomination")),
      serial_number: String(fields.get("serial")),
      series: String(fields.get("series")),
    }
    setStory(undefined)
    setMissing(undefined)
    await run(async () => {
      try {
        setStory(await call<Story>("/banknotes/lookup", { method: "POST", body: JSON.stringify(identity) }))
        setStatus("Banknote found.")
      } catch (failure) {
        if (failure instanceof ApiError && failure.status === 404) setMissing(identity)
        else throw failure
      }
    })
  }

  async function register() {
    if (!missing) return
    await run(async () => {
      setStory(await call<Story>("/banknotes/register", { method: "POST", body: JSON.stringify(missing) }))
      setMissing(undefined)
      setStatus("Banknote registered.")
    })
  }

  async function loadOlder() {
    if (!story?.before_id) return
    await run(async () => {
      const page = await call<Story>(`/banknotes/lookup?before_id=${story.before_id}`, {
        method: "POST", body: JSON.stringify(story.note),
      })
      setStory({ ...page, events: [...story.events, ...page.events] })
    })
  }

  async function contribute(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!story) return
    const form = event.currentTarget
    const fields = new FormData(form)
    await run(async () => {
      const values = {
        city: String(fields.get("city")).trim(),
        message: String(fields.get("message")).trim(),
        is_hidden: fields.has("hidden"),
        image: await readPostImage(fields.get("image")),
      }
      if (!values.message && !values.image) {
        setError("Add text or an image to the story.")
        return
      }
      const key = submission(attempt.current, JSON.stringify([story.note, values]))
      attempt.current = key
      const created = await call<StoryEvent>("/banknotes/events", {
        method: "POST", body: JSON.stringify({ note: story.note, event: { ...values, request_id: key.id } }),
      })
      setStory({ ...story, events: [created, ...story.events.filter((item) => item.id !== created.id)] })
      attempt.current = undefined
      form.reset()
      setStatus(values.is_hidden ? "Hidden message added." : "Story added.")
    })
  }

  return (
    <div className="banking">
      <section className="bank-hero">
        <div>
          <p className="bank-eyebrow"><Banknote size={17} aria-hidden /> Community stories</p>
          <h1>Banknote stories</h1>
          <p>Look up a note by its printed details or add a city and a message for the next person who finds it.</p>
        </div>
      </section>
      <Link to="/community" className="intelligence-back">Back to Community</Link>
      <div className="bank-grid">
        <section className="card">
          <h2>Find a banknote</h2>
          <p>Use the same currency, denomination, serial number, and series for each lookup. Leave the series blank if it was omitted when registering the note.</p>
          <form className="bank-form" onSubmit={(event) => void find(event)} onChange={() => {
            setStory(undefined)
            setMissing(undefined)
            setStatus("")
            setError("")
          }}>
            <fieldset disabled={pending}>
              <div className="bank-fields">
                <label>Currency code<input name="currency" defaultValue="CAD" minLength={3} maxLength={3} pattern="[A-Za-z]{3}" required /></label>
                <label>Denomination<input name="denomination" type="number" min="1" max="1000000" step="1" placeholder="20" required /></label>
              </div>
              <label>Serial number<input name="serial" autoComplete="off" maxLength={64} required /></label>
              <label>Series (optional)<input name="series" maxLength={40} /></label>
              <Button type="submit"><Search size={17} aria-hidden /> Look up banknote</Button>
            </fieldset>
          </form>
          {missing && <div className="bank-feedback">
            <p>No story matches those details yet.</p>
            <Button disabled={pending} onClick={() => void register()}>Register this banknote</Button>
          </div>}
        </section>
        <section className="card">
          <h2>How stories work</h2>
          <p>Each entry is a community report. A lookup does not verify the note’s journey or establish who holds it.</p>
          <p>Hidden messages are revealed after a lookup with matching note details. Share only information you want other members to read, and use a city in place of an address.</p>
        </section>
      </div>
      {pending && <p role="status" className="bank-feedback">Working…</p>}
      {error && <p role="alert" className="bank-feedback bank-error">{error}</p>}
      {!pending && status && <p role="status" className="bank-feedback bank-success">{status}</p>}

      {story && <div className="bank-grid">
        <section className="card">
          <h2>{story.note.currency} {story.note.denomination} banknote timeline</h2>
          <p className="note-identity">{story.note.serial_number}{story.note.series ? ` · Series ${story.note.series}` : ""}</p>
          {story.events.length === 0 ? <p className="bank-empty">This note has no stories yet.</p> : (
            <ol className="intelligence-list note-timeline">
              {story.events.map((item) => (
                <li key={item.id}>
                  <div className="intelligence-row">
                    <h3><MapPin size={16} aria-hidden /> {item.city}</h3>
                    <time dateTime={item.created_at}>{communityDate(item.created_at)}</time>
                  </div>
                  {item.is_hidden && <span className="note-revealed"><LockKeyhole size={15} aria-hidden /> Hidden message revealed</span>}
                  {item.message && <p className="community-copy">{item.message}</p>}
                  {item.image && <img className="post-attachment" src={item.image} alt="Image shared with this banknote story" loading="lazy" />}
                </li>
              ))}
            </ol>
          )}
          {story.before_id !== null && <Button className="bank-secondary" disabled={pending} onClick={() => void loadOlder()}>Load older stories</Button>}
        </section>

        <section className="card">
          <h2>Add to this note’s story</h2>
          <form className="bank-form" onSubmit={(event) => void contribute(event)}>
            <fieldset disabled={pending}>
              <label>City<input name="city" maxLength={80} required /></label>
              <label>Your message<textarea name="message" rows={4} maxLength={1000} /></label>
              <label>Attach an image<input type="file" name="image" accept={imageTypes} /></label>
              <label className="note-checkbox"><input name="hidden" type="checkbox" /> Mark as a hidden message</label>
              <Button type="submit">Add story</Button>
            </fieldset>
          </form>
        </section>
      </div>}
    </div>
  )
}
