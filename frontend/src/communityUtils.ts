export type Profile = { username: string; display_name: string }
export type PostType = "discussion" | "achievement"
export type LikeState = { liked: boolean; like_count: number }
export type Post = LikeState & {
  id: number
  author: Profile
  post_type: PostType
  content: string
  image: string | null
  created_at: string
  comment_count: number
}
export type Comment = { id: number; author: Profile; content: string; created_at: string }
export type Page<T> = { items: T[]; before_id: number | null }

const dates = new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" })
export const communityDate = (value: string) => dates.format(new Date(value))
export const profilePath = (username: string) => `/community/profiles/${encodeURIComponent(username)}`

export function submission(previous: { key: string; id: string } | undefined, key: string) {
  return previous?.key === key ? previous : { key, id: crypto.randomUUID() }
}
