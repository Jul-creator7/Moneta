import { useCallback, useRef } from "react"
import { api, ApiError } from "./api"

export function requestError(error: unknown) {
  return error instanceof ApiError ? error.message : "The server could not be reached. Please try again."
}

export function useAuthenticatedApi(token: string, onExpired: () => void) {
  const expired = useRef(onExpired)
  expired.current = onExpired
  return useCallback(async <T,>(path: string, options?: RequestInit) => {
    try {
      return await api<T>(path, options, token)
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) expired.current()
      throw error
    }
  }, [token])
}
