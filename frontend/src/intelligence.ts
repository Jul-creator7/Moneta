import { useCallback, useRef } from "react"
import { api, ApiError } from "./api"
import type { Entry } from "./banking"

export type AuditInput = { necessity_rating: number; reflection: string | null }
export type AuditedPurchase = { purchase: Entry; audit: AuditInput | null; alternatives: string[] }
export type AuditHistory = { items: AuditedPurchase[]; before_id: number | null }
type RecurringCharge = {
  merchant: string
  category: string
  cadence: "Weekly" | "Monthly"
  last_charged: string
  amount_minor: number
  annual_minor: number
  active: boolean
  previous_amount_minor: number | null
  annual_increase_minor: number
}
type PossibleDuplicate = { merchant: string; charged_on: string; amount_minor: number; count: number }
export type Report = {
  recurring: RecurringCharge[]
  duplicates: PossibleDuplicate[]
  potential_annual_savings_minor: number
  potential_annual_increase_minor: number
}
type Timeline = { estimated_date: string | null }
export type AuditProjection = { baseline: Timeline; with_purchase: Timeline; delay_days: number | null }
export type GoalOption = { id: number; name: string }

const dates = new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeZone: "UTC" })
export function financialDate(value: string) {
  return dates.format(new Date(value.length === 10 ? `${value}T00:00:00Z` : value))
}

export function requestError(error: unknown) {
  return error instanceof ApiError ? error.message : "The server could not be reached. Please try again."
}

export function useIntelligenceApi(token: string, onExpired: () => void) {
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
