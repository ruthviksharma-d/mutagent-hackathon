import { AlertTriangle, RotateCw } from "lucide-react"
import { Button } from "./Button"

interface ErrorStateProps {
  message?: string
  onRetry?: () => void
}

export function ErrorState({ message = "Something went wrong loading this data.", onRetry }: ErrorStateProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
      <div className="rounded-full bg-danger/10 p-3">
        <AlertTriangle className="h-6 w-6 text-danger" />
      </div>
      <p className="max-w-sm text-sm text-muted-foreground">{message}</p>
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry}>
          <RotateCw className="h-3.5 w-3.5" />
          Retry
        </Button>
      )}
    </div>
  )
}
