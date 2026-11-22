import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import { money, type Dashboard } from "./banking"

export default function SpendingChart({ totals }: { totals: Dashboard["spending_by_category"] }) {
  return (
  <div className="bank-chart-area" aria-hidden="true">
    <ResponsiveContainer width="100%" height={210}>
      <BarChart data={totals} margin={{ left: -12, right: 8, bottom: 4 }}>
        <CartesianGrid vertical={false} stroke="#e1e7dd" />
        <XAxis dataKey="category" tickLine={false} axisLine={false} tick={{ fontSize: 10 }} />
        <YAxis tickFormatter={(value: number) => `$${value / 100}`} tickLine={false} axisLine={false} tick={{ fontSize: 10 }} />
        <Tooltip formatter={(value) => [money(Number(value)), "Spent"]} />
        <Bar dataKey="total_minor" fill="#398159" radius={[6, 6, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  </div>
  )
}
