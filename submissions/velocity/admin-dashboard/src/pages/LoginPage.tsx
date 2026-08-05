import { type FormEvent, useState } from "react"
import { Navigate, useNavigate } from "react-router-dom"
import { ShieldHalf, Loader2 } from "lucide-react"
import { useAuth } from "@/context/AuthContext"
import { Button } from "@/components/ui/Button"
import { Input } from "@/components/ui/Input"

export function LoginPage() {
  const { login, isAuthenticated } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState("admin@promptshield.ai")
  const [password, setPassword] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  if (isAuthenticated) return <Navigate to="/dashboard" replace />

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setIsSubmitting(true)
    try {
      await login(email, password)
      navigate("/dashboard")
    } catch {
      setError("Incorrect email or password.")
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted px-4">
      <div className="w-full max-w-sm rounded-xl border border-border bg-card p-8 shadow-sm">
        <div className="mb-6 flex items-center gap-2">
          <ShieldHalf className="h-6 w-6 text-primary" />
          <span className="text-lg font-semibold tracking-tight">PromptShield AI</span>
        </div>
        <h2 className="mb-1 text-xl font-semibold">Sign in to your workspace</h2>
        <p className="mb-6 text-sm text-muted-foreground">
          Admin and Security Analyst accounts only.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <label className="text-sm font-medium" htmlFor="email">
              Work email
            </label>
            <Input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@company.com"
            />
          </div>
          <div className="space-y-1.5">
            <label className="text-sm font-medium" htmlFor="password">
              Password
            </label>
            <Input
              id="password"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
            />
          </div>

          {error && <p className="text-sm text-danger">{error}</p>}

          <Button type="submit" className="w-full" disabled={isSubmitting}>
            {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
            Sign in
          </Button>
        </form>

        <p className="mt-6 text-center text-xs text-muted-foreground">
          Default seeded admin: admin@promptshield.ai / Admin@12345
        </p>
      </div>
    </div>
  )
}
