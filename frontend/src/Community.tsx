import { useCallback, useEffect, useRef, useState, type FormEvent } from "react"
import { ArrowLeft, ArrowUpRight, Heart, MessageCircle, RefreshCw, Trophy, Users } from "lucide-react"
import { Link } from "react-router-dom"
import { requestError, useAuthenticatedApi } from "./authenticatedApi"
import { Button } from "./components/ui/button"
import {
  communityDate, profilePath, submission, type Comment, type LikeState, type Page, type Post, type PostType, type Profile,
} from "./community"

type CommunityCall = ReturnType<typeof useAuthenticatedApi>

export function Community({ token, onExpired, viewer, username }: {
  token: string
  onExpired: () => void
  viewer: string
  username?: string
}) {
  const call = useAuthenticatedApi(token, onExpired)
  const [profile, setProfile] = useState<Profile>()
  const [feed, setFeed] = useState<Page<Post>>()
  const [pending, setPending] = useState(true)
  const [error, setError] = useState("")
  const [editing, setEditing] = useState(false)
  const [relatedVersion, setRelatedVersion] = useState(0)
  const ownedProfile = username === viewer

  const fetchPosts = useCallback((before?: number, signal?: AbortSignal) => {
    const params = new URLSearchParams()
    if (username) params.set("author", username)
    if (before !== undefined) params.set("before_id", String(before))
    return call<Page<Post>>(`/community/posts?${params}`, { signal })
  }, [call, username])

  const refresh = useCallback(async (signal?: AbortSignal) => {
    setPending(true)
    setError("")
    try {
      const [posts, member] = await Promise.all([
        fetchPosts(undefined, signal),
        username ? call<Profile>(`/community/profiles/${encodeURIComponent(username)}`, { signal }) : undefined,
      ])
      if (!signal?.aborted) {
        setFeed(posts)
        setProfile(member)
        setRelatedVersion((previous) => previous + 1)
      }
    } catch (failure) {
      if (!signal?.aborted) setError(requestError(failure))
    } finally {
      if (!signal?.aborted) setPending(false)
    }
  }, [call, fetchPosts, username])

  useEffect(() => {
    const controller = new AbortController()
    void refresh(controller.signal)
    return () => controller.abort()
  }, [refresh])

  async function loadMore() {
    if (pending || feed?.before_id == null) return
    setPending(true)
    setError("")
    try {
      const page = await fetchPosts(feed.before_id)
      setFeed((previous) => previous ? { items: [...previous.items, ...page.items], before_id: page.before_id } : page)
    } catch (failure) {
      setError(requestError(failure))
    } finally {
      setPending(false)
    }
  }

  function updatePost(id: number, values: Partial<Post>) {
    setFeed((previous) => previous && {
      ...previous, items: previous.items.map((item) => item.id === id ? { ...item, ...values } : item),
    })
  }

  function updateProfile(saved: Profile) {
    setProfile(saved)
    setEditing(false)
    setFeed((previous) => previous && { ...previous, items: previous.items.map((item) => ({ ...item, author: saved })) })
    setRelatedVersion((previous) => previous + 1)
  }

  return (
    <div className="banking community">
      <section className="bank-hero">
        <div>
          <p className="bank-eyebrow"><Users size={16} aria-hidden /> {username ? "Community profile" : "Tandem community"}</p>
          <h1>{profile?.display_name ?? (username ? `@${username}` : "Community")}</h1>
          <p>{username ? `@${username}` : "Share savings wins, ask questions, and learn from other members."}</p>
        </div>
        {!username && <Link className="community-profile-link" to={profilePath(viewer)}>My profile <ArrowUpRight size={17} aria-hidden /></Link>}
      </section>

      {username && <Link to="/community" className="intelligence-back"><ArrowLeft size={17} aria-hidden /> Back to Community</Link>}
      {profile && ownedProfile && <section className="card">
        <div className="intelligence-row">
          <h2>Your public profile</h2>
          <Button className="bank-secondary" disabled={pending} onClick={() => setEditing(!editing)}>{editing ? "Cancel" : "Edit display name"}</Button>
        </div>
        <p>Community members see your username and display name.</p>
        {editing && <ProfileForm profile={profile} call={call} onSaved={updateProfile} />}
      </section>}

      {!username && feed && <PostComposer call={call} disabled={pending} onAdded={(post) => {
        setFeed((previous) => previous && {
          ...previous, items: [post, ...previous.items.filter((entry) => entry.id !== post.id)],
        })
      }} />}

      <section className="community-feed" aria-labelledby="community-feed-heading">
        <div className="intelligence-row">
          <h2 id="community-feed-heading">{username ? "Shared posts" : "Community feed"}</h2>
          <Button className="bank-secondary" disabled={pending} onClick={() => void refresh()}><RefreshCw size={16} aria-hidden /> Refresh feed</Button>
        </div>
        {pending && !feed && <p className="bank-feedback" role="status">Loading community posts…</p>}
        {error && <p className="bank-feedback bank-error" role="alert">{error}</p>}
        {feed && feed.items.length === 0 && !error && <p className="bank-empty">{username ? "This member hasn’t shared any posts yet." : "The feed is empty. Start a discussion or share a savings achievement."}</p>}
        {feed?.items.map((post) => (
          <PostCard key={`${post.id}:${relatedVersion}`} post={post} call={call} disabled={pending}
            onUpdate={(values) => updatePost(post.id, values)} />
        ))}
        {feed && feed.before_id !== null &&
          <Button className="bank-secondary" disabled={pending} onClick={() => void loadMore()}>Load more posts</Button>}
      </section>
    </div>
  )
}

function ProfileForm({ profile, call, onSaved }: { profile: Profile; call: CommunityCall; onSaved: (profile: Profile) => void }) {
  const [pending, setPending] = useState(false)
  const [error, setError] = useState("")
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const name = String(new FormData(event.currentTarget).get("name")).trim()
    setPending(true)
    setError("")
    try {
      const updated = await call<Profile>("/community/profile", { method: "PUT", body: JSON.stringify({ display_name: name || null }) })
      onSaved(updated)
    } catch (failure) {
      setError(requestError(failure))
    } finally {
      setPending(false)
    }
  }
  return (
    <form className="bank-form" onSubmit={(event) => void save(event)}>
      <fieldset disabled={pending}>
        <label>Display name<input name="name" defaultValue={profile.display_name} maxLength={80} /></label>
        <p>Leave it blank to use your username.</p>
        <Button type="submit">Save display name</Button>
      </fieldset>
      {error && <p role="alert" className="bank-error">{error}</p>}
    </form>
  )
}

function PostComposer({ call, disabled, onAdded }: { call: CommunityCall; disabled: boolean; onAdded: (post: Post) => void }) {
  const [pending, setPending] = useState(false)
  const [error, setError] = useState("")
  const [notice, setNotice] = useState("")
  const attempt = useRef<{ key: string; id: string } | undefined>(undefined)

  async function publish(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    const fields = new FormData(form)
    const content = String(fields.get("post")).trim()
    const type = fields.get("type") as PostType
    setNotice("")
    if (!content) {
      setError("Write something before publishing.")
      return
    }
    setPending(true)
    setError("")
    const request = submission(attempt.current, JSON.stringify([type, content]))
    attempt.current = request
    try {
      const post = await call<Post>("/community/posts", {
        method: "POST", body: JSON.stringify({ request_id: request.id, post_type: type, content }),
      })
      attempt.current = undefined
      onAdded(post)
      form.reset()
      setNotice("Post published.")
    } catch (failure) {
      setError(requestError(failure))
    } finally {
      setPending(false)
    }
  }

  return (
    <section className="card">
      <h2>Share with the community</h2>
      <form className="bank-form" onSubmit={(event) => void publish(event)}>
        <fieldset disabled={pending || disabled}>
          <label><span id="community-post-type">Post type</span>
            <select aria-labelledby="community-post-type" name="type">
              <option value="discussion">Discussion</option>
              <option value="achievement">Savings achievement</option>
            </select>
          </label>
          <label>Your post<textarea name="post" maxLength={1500} rows={3} required /></label>
          <p>Members can read what you publish. Share only the details you want others to see.</p>
          <Button type="submit">{pending ? "Publishing…" : "Publish post"}</Button>
        </fieldset>
      </form>
      {notice && <p role="status" className="bank-success">{notice}</p>}
      {error && <p role="alert" className="bank-error">{error}</p>}
    </section>
  )
}

function PostCard({ post, call, onUpdate, disabled }: {
  post: Post; call: CommunityCall; onUpdate: (values: Partial<Post>) => void; disabled: boolean
}) {
  const [replyOpen, setReplyOpen] = useState(false)
  const [likePending, setLikePending] = useState(false)
  const [error, setError] = useState("")

  async function like() {
    setError("")
    setLikePending(true)
    try {
      const state = await call<LikeState>(`/community/posts/${post.id}/like`, {
        method: "PUT", body: JSON.stringify({ liked: !post.liked }),
      })
      onUpdate(state)
    } catch (failure) {
      setError(requestError(failure))
    } finally {
      setLikePending(false)
    }
  }

  return (
    <article className="card community-post">
      <div className="intelligence-row community-post-heading">
        <div className="community-author">
          <span className="avatar" aria-hidden="true">{Array.from(post.author.display_name).slice(0, 2).join("").toUpperCase()}</span>
          <div>
            <Link to={profilePath(post.author.username)}>{post.author.display_name}</Link>
            <p><time dateTime={post.created_at}>{communityDate(post.created_at)}</time></p>
          </div>
        </div>
        {post.post_type === "achievement" && <span className="community-achievement"><Trophy size={15} aria-hidden /> Savings achievement</span>}
      </div>
      <p className="community-copy">{post.content}</p>
      <div className="community-controls">
        <Button className="bank-secondary" aria-pressed={post.liked} disabled={likePending || disabled} onClick={() => void like()}>
          <Heart size={17} fill={post.liked ? "currentColor" : "none"} aria-hidden /> Likes ({post.like_count})
        </Button>
        <Button className="bank-secondary" aria-expanded={replyOpen} aria-controls={replyOpen ? `post-comments-${post.id}` : undefined} onClick={() => setReplyOpen(!replyOpen)}>
          <MessageCircle size={17} aria-hidden /> Comments ({post.comment_count})
        </Button>
      </div>
      {error && <p role="alert" className="bank-error">{error}</p>}
      {replyOpen && <Comments postId={post.id} call={call} disabled={disabled} onAdded={(count) => onUpdate({ comment_count: count })} />}
    </article>
  )
}

function Comments({ postId, call, onAdded, disabled }: {
  postId: number; call: CommunityCall; onAdded: (count: number) => void; disabled: boolean
}) {
  const path = `/community/posts/${postId}/comments`
  const [comments, setComments] = useState<Page<Comment>>()
  const [pending, setPending] = useState(true)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState("")
  const [sendError, setSendError] = useState("")
  const attempt = useRef<{ key: string; id: string } | undefined>(undefined)

  const load = useCallback(async (before?: number, signal?: AbortSignal) => {
    setPending(true)
    setError("")
    try {
      const page = await call<Page<Comment>>(before ? `${path}?before_id=${before}` : path, { signal })
      if (!signal?.aborted) setComments((previous) => before && previous ? { items: [...previous.items, ...page.items], before_id: page.before_id } : page)
    } catch (failure) {
      if (!signal?.aborted) setError(requestError(failure))
    } finally {
      if (!signal?.aborted) setPending(false)
    }
  }, [call, path])

  useEffect(() => {
    const controller = new AbortController()
    void load(undefined, controller.signal)
    return () => controller.abort()
  }, [load])

  async function send(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    const content = String(new FormData(form).get("comment")).trim()
    if (!content) {
      setSendError("Write a comment before posting.")
      return
    }
    setSendError("")
    setSending(true)
    const request = submission(attempt.current, content)
    attempt.current = request
    try {
      const { comment, comment_count } = await call<{ comment: Comment; comment_count: number }>(path, {
        method: "POST", body: JSON.stringify({ request_id: request.id, content }),
      })
      attempt.current = undefined
      onAdded(comment_count)
      setComments((previous) => previous && {
        ...previous, items: [comment, ...previous.items.filter((entry) => entry.id !== comment.id)],
      })
      form.reset()
    } catch (failure) {
      setSendError(requestError(failure))
    } finally {
      setSending(false)
    }
  }

  return (
    <section id={`post-comments-${postId}`} className="community-comments" aria-label="Post comments">
      {pending && !comments && <p role="status">Loading comments…</p>}
      {error && <div role="alert"><p className="bank-error">{error}</p><Button className="bank-secondary" disabled={pending || sending} onClick={() => void load()}>Retry comments</Button></div>}
      {comments && <>
        {comments.items.length === 0 && <p>Be the first to comment.</p>}
        <ul className="intelligence-list">
          {comments.items.map((item) => <li key={item.id}>
            <div className="intelligence-row">
              <Link to={profilePath(item.author.username)}>{item.author.display_name}</Link>
              <time dateTime={item.created_at}>{communityDate(item.created_at)}</time>
            </div>
            <p className="community-copy">{item.content}</p>
          </li>)}
        </ul>
        {comments.before_id !== null && <Button className="bank-secondary" disabled={pending || sending} onClick={() => void load(comments.before_id ?? undefined)}>Load older comments</Button>}
        <form className="bank-form" onSubmit={(event) => void send(event)}>
          <fieldset disabled={pending || sending || disabled}>
            <label>Write a comment<textarea name="comment" maxLength={500} rows={2} required /></label>
            <Button type="submit" className="bank-secondary">{sending ? "Posting…" : "Post comment"}</Button>
          </fieldset>
        </form>
      </>}
      {sendError && <p role="alert" className="bank-error">{sendError}</p>}
    </section>
  )
}
