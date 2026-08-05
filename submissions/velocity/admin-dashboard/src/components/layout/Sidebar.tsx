import { NavLink } from "react-router-dom"
import {
  LayoutDashboard,
  ScrollText,
  ShieldCheck,
  Users,
  BarChart3,
  Settings,
  SearchCode,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { Logo } from "@/components/Logo"

const NAV_ITEMS = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/prompt-logs", label: "Prompt Logs", icon: ScrollText },
  { to: "/investigations", label: "Investigations", icon: SearchCode },
  { to: "/policies", label: "Policies", icon: ShieldCheck },
  { to: "/employees", label: "Employees", icon: Users },
  { to: "/analytics", label: "Analytics", icon: BarChart3 },
  { to: "/settings", label: "Settings", icon: Settings },
]

export function Sidebar() {
  return (
    <aside className="hidden w-64 shrink-0 flex-col border-r border-border bg-sidebar text-sidebar-foreground md:flex">
      <div className="flex h-14 items-center gap-2 border-b border-border px-5">
        <Logo className="h-6 w-6" />
        <span className="text-sm font-semibold tracking-tight">PromptShield AI</span>
      </div>
      <nav className="flex-1 space-y-1 px-3 py-4">
        {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              )
            }
          >
            <Icon className="h-4 w-4" />
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="border-t border-border p-4 text-xs text-muted-foreground">
        PromptShield AI v2.0.0 · Mutagent
      </div>
    </aside>
  )
}
