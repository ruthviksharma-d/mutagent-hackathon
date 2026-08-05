import { useNavigate } from "react-router-dom"
import { ArrowLeft, Home } from "lucide-react"
import { Logo } from "@/components/Logo"
import { Button } from "@/components/ui/Button"

export function NotFoundPage() {
  const navigate = useNavigate()

  return (
    <div className="flex min-h-screen w-full flex-col items-center justify-center gap-6 bg-background px-6 text-center">
      <Logo className="h-14 w-14" />
      <div className="space-y-2">
        <p className="text-7xl font-bold tracking-tight text-primary/90">404</p>
        <h1 className="text-xl font-semibold text-foreground">This page went unscanned.</h1>
        <p className="mx-auto max-w-sm text-sm text-muted-foreground">
          The page you're looking for doesn't exist, was moved, or never made it
          past PromptShield's policy engine.
        </p>
      </div>
      <div className="flex items-center gap-3">
        <Button variant="outline" onClick={() => navigate("/")}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to home
        </Button>
        <Button onClick={() => navigate("/dashboard")}>
          <Home className="mr-2 h-4 w-4" />
          Go to dashboard
        </Button>
      </div>
    </div>
  )
}
