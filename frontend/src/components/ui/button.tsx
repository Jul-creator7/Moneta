import type { ComponentProps } from "react"
import { cn } from "@/lib/utils"

export function Button({ className, type = "button", ...props }: ComponentProps<"button">) {
  return (
    <button
      type={type}
      className={cn("inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-primary px-5 font-semibold text-primary-foreground transition hover:brightness-110 disabled:opacity-60", className)}
      {...props}
    />
  )
}
