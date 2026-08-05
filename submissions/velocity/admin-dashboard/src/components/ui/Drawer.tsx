import { type ReactNode } from "react"
import { X } from "lucide-react"
import { useDialogA11y } from "@/hooks/useDialogA11y"

interface DrawerProps {
  open: boolean
  onClose: () => void
  title: string
  subtitle?: string
  children: ReactNode
}

export function Drawer({ open, onClose, title, subtitle, children }: DrawerProps) {
  const containerRef = useDialogA11y(open, onClose)

  if (!open) return null

  return (
    <div className="fixed inset-0 z-40 flex justify-end">
      <div className="absolute inset-0 animate-[fadeIn_150ms_ease-out] bg-black/40" onClick={onClose} />
      <div
        ref={containerRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="drawer-title"
        tabIndex={-1}
        className="relative flex h-full w-full max-w-lg animate-[slideIn_200ms_cubic-bezier(0.16,1,0.3,1)] flex-col border-l border-border bg-card shadow-2xl focus:outline-none"
      >
        <div className="flex items-start justify-between border-b border-border p-5">
          <div>
            <h2 id="drawer-title" className="text-base font-semibold">{title}</h2>
            {subtitle && <p className="mt-0.5 text-sm text-muted-foreground">{subtitle}</p>}
          </div>
          <button onClick={onClose} aria-label="Close panel" className="rounded-md p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground">
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-5">{children}</div>
      </div>
    </div>
  )
}
