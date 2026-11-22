export type AccountType = "chequing" | "savings"

export const operations = {
  deposit: "Add simulated money",
  income: "Record income",
  purchase: "Make a purchase",
  bill: "Pay a bill",
  transfer: "Transfer money",
} as const

export type OperationType = keyof typeof operations

export const expenseCategories = ["Food", "Shopping", "Transport", "Housing", "Utilities", "Entertainment", "Other"]

export type Account = {
  id: number
  account_type: AccountType
  name: string
  currency: string
  balance_minor: number
}

export type Entry = {
  id: number
  account_id: number
  amount_minor: number
  transaction_type: OperationType
  merchant_name: string | null
  category: string
  description: string
  created_at: string
}

export type Dashboard = {
  accounts: Account[]
  total_balance_minor: number
  savings_balance_minor: number
  monthly_income_minor: number
  monthly_spending_minor: number
  monthly_savings_rate: number | null
  spending_by_category: { category: string; total_minor: number }[]
  recent_transactions: Entry[]
}

export type History = { transactions: Entry[]; next_offset: number | null }

const currency = new Intl.NumberFormat("en-CA", { style: "currency", currency: "CAD" })
export const money = (minor: number) => currency.format(minor / 100)

export function readAmount(value: string) {
  const parts = /^(\d{1,7})(?:\.(\d{1,2}))?$/.exec(value.trim())
  if (!parts) return null
  const amount = Number(parts[1]) * 100 + Number((parts[2] ?? "").padEnd(2, "0"))
  return amount > 0 && amount <= 100_000_000 ? amount : null
}
