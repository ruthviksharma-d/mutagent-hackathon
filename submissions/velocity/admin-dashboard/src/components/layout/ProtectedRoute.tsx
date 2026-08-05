import { Navigate, Outlet } from "react-router-dom"
import { useAuth } from "@/context/AuthContext"
import { Logo } from "@/components/Logo"

export function ProtectedRoute() {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="flex h-screen w-full flex-col items-center justify-center gap-4 bg-background">
        <div className="relative flex h-16 w-16 items-center justify-center">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary/20" />
          <Logo className="relative h-10 w-10 animate-pulse" />
        </div>
        <div className="text-center">
          <p className="text-sm font-medium text-foreground">PromptShield AI</p>
          <p className="text-xs text-muted-foreground">Securing your session…</p>
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return <Outlet />
}
