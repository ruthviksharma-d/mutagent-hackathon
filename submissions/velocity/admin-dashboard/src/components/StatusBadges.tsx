import { Badge } from "@/components/ui/Badge"
import type { Action, Risk } from "@/types/admin"

const ACTION_TONE: Record<Action, "success" | "warning" | "default" | "danger"> = {
  ALLOW: "success",
  WARN: "warning",
  REDACT: "default",
  BLOCK: "danger",
}

export function ActionBadge({ action }: { action: Action }) {
  return <Badge tone={ACTION_TONE[action]}>{action}</Badge>
}

const RISK_TONE: Record<Risk, "success" | "warning" | "default" | "danger" | "muted"> = {
  NONE: "muted",
  LOW: "success",
  MEDIUM: "warning",
  HIGH: "danger",
  CRITICAL: "danger",
}

export function RiskBadge({ risk }: { risk: Risk }) {
  return <Badge tone={RISK_TONE[risk]}>{risk}</Badge>
}

export function ExtensionStatusBadge({ status }: { status: "active" | "inactive" | "not_installed" }) {
  const tone = status === "active" ? "success" : status === "inactive" ? "warning" : "muted"
  const label = status === "active" ? "Active" : status === "inactive" ? "Inactive" : "Not Installed"
  return <Badge tone={tone}>{label}</Badge>
}
