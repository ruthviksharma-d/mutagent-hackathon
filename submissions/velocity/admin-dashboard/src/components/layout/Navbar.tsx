import { useLocation } from "react-router-dom"
import { Moon, Sun, LogOut, Search } from "lucide-react"
import { useTheme } from "@/context/ThemeContext"
import { useAuth } from "@/context/AuthContext"
import { Button } from "@/components/ui/Button"
import { Input } from "@/components/ui/Input"

const TITLES: Record<string, string> = {
  "/dashboard": "Dashboard",
  "/prompt-logs": "Prompt Logs",
  "/policies": "Policies",
  "/employees": "Employees",
  "/analytics": "Analytics",
  "/settings": "Settings",
}

export function Navbar() {
  const { pathname } = useLocation()
  const { theme, toggleTheme } = useTheme()
  const { user, logout } = useAuth()

  const crumbs = pathname.split("/").filter(Boolean)
  const title = TITLES[pathname] ?? "PromptShield"

  return (
    <header className="flex h-14 items-center justify-between border-b border-border bg-background px-6">
      <div>
        <h1 className="text-sm font-semibold">{title}</h1>
        <p className="text-xs text-muted-foreground">
          Home {crumbs.map((c) => `/ ${c.replace(/-/g, " ")}`).join(" ")}
        </p>
      </div>

      <div className="flex items-center gap-3">
        <div className="relative hidden sm:block">
          <Search className="pointer-events-none absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input placeholder="Search..." className="w-56 pl-8" />
        </div>

        <Button variant="ghost" size="icon" onClick={toggleTheme} aria-label="Toggle theme">
          {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </Button>

        <div className="hidden text-right sm:block">
          <p className="text-sm font-medium leading-none">{user?.full_name ?? "—"}</p>
          <p className="text-xs capitalize text-muted-foreground">
            {user?.role.replace("_", " ") ?? ""}
          </p>
        </div>

        <Button variant="ghost" size="icon" onClick={logout} aria-label="Log out">
          <LogOut className="h-4 w-4" />
        </Button>
      </div>
    </header>
  )
}
