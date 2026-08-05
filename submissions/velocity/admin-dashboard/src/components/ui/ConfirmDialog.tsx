import { AlertTriangle } from "lucide-react"
import { Button } from "./Button"
import { useDialogA11y } from "@/hooks/useDialogA11y"

interface ConfirmDialogProps {
  open: boolean
  title: string
  description: string
  confirmLabel?: string
  onConfirm: () => void
  onCancel: () => void
  isLoading?: boolean
}

export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel = "Delete",
  onConfirm,
  onCancel,
  isLoading,
}: ConfirmDialogProps) {
  const containerRef = useDialogA11y(open, onCancel)

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onCancel}>
      <div
        ref={containerRef}
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirm-dialog-title"
        tabIndex={-1}
        className="w-full max-w-sm rounded-xl border border-border bg-card p-5 shadow-2xl focus:outline-none"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-3 flex items-center gap-2 text-danger">
          <AlertTriangle className="h-5 w-5" />
          <h3 id="confirm-dialog-title" className="text-sm font-semibold text-foreground">{title}</h3>
        </div>
        <p className="mb-5 text-sm text-muted-foreground">{description}</p>
        <div className="flex justify-end gap-2">
          <Button variant="outline" size="sm" onClick={onCancel} disabled={isLoading}>
            Cancel
          </Button>
          <Button variant="destructive" size="sm" onClick={onConfirm} disabled={isLoading}>
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  )
}
