const apiBase = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "")

export type User = { id: number; email: string; username: string }
export type Credentials = { email: string; password: string }

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
  }
}

export async function api<T>(path: string, options: RequestInit = {}, token?: string): Promise<T> {
  const headers = new Headers(options.headers)
  if (options.body) headers.set("Content-Type", "application/json")
  if (token) headers.set("Authorization", `Bearer ${token}`)
  const response = await fetch(`${apiBase}/api${path}`, { ...options, headers })
  if (!response.ok) {
    const { detail } = await response.json().catch(() => ({}))
    const message = Array.isArray(detail)
      ? detail.map(({ field, message }) => `${field}: ${message}`).join(". ")
      : detail
    throw new ApiError(response.status, message || "The request failed. Please try again.")
  }
  return response.json()
}
