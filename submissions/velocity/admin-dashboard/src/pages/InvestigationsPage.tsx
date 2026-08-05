/**
 * InvestigationsPage — paginated list of all Mutagent investigations.
 *
 * Displays each investigation's scan ID, user, target AI, risk score,
 * decision badge, analyzer stats, and execution time. Clicking a row
 * navigates to the InvestigationDetailPage.
 */
import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { useNavigate } from "react-router-dom"
import {
  SearchCode,
  ChevronLeft,
  ChevronRight,
  Filter,
  ExternalLink,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
} from "lucide-react"
import { listInvestigations, type InvestigationFilters } from "@/lib/adminApi"
import type { InvestigationListItem } from "@/types/admin"
import { formatDateTime } from "@/lib/format"

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const DECISION_STYLES: Record<string, { bg: string; text: string; icon: typeof CheckCircle2 }> = {
  ALLOW:  { bg: "bg-emerald-500/15 text-emerald-400", text: "ALLOW",  icon: CheckCircle2 },
  WARN:   { bg: "bg-amber-500/15 text-amber-400",     text: "WARN",   icon: AlertTriangle },
  REDACT: { bg: "bg-blue-500/15 text-blue-400",       text: "REDACT", icon: AlertTriangle },
  BLOCK:  { bg: "bg-red-500/15 text-red-400",         text: "BLOCK",  icon: XCircle },
}

const SEVERITY_STYLES: Record<string, string> = {
  NONE:     "bg-gray-500/10 text-gray-400",
  LOW:      "bg-green-500/15 text-green-400",
  MEDIUM:   "bg-amber-500/15 text-amber-400",
  HIGH:     "bg-orange-500/15 text-orange-400",
  CRITICAL: "bg-red-500/15 text-red-400",
}

function ScoreMeter({ score }: { score: number }) {
  const color =
    score >= 75 ? "#ef4444" :
    score >= 50 ? "#f97316" :
    score >= 25 ? "#f59e0b" :
    "#22c55e"
  return (
    <div className="flex items-center gap-2">
      <div className="relative h-1.5 w-16 rounded-full bg-muted overflow-hidden">
        <div
          className="absolute inset-y-0 left-0 rounded-full transition-all"
          style={{ width: `${score}%`, background: color }}
        />
      </div>
      <span className="text-xs tabular-nums font-mono" style={{ color }}>{score}</span>
    </div>
  )
}

function DecisionBadge({ decision }: { decision: string }) {
  const style = DECISION_STYLES[decision] ?? { bg: "bg-muted text-muted-foreground", text: decision, icon: CheckCircle2 }
  const Icon = style.icon
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold ${style.bg}`}>
      <Icon className="h-3 w-3" />
      {style.text}
    </span>
  )
}

function SeverityBadge({ severity }: { severity: string }) {
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${SEVERITY_STYLES[severity] ?? "bg-muted text-muted-foreground"}`}>
      {severity}
    </span>
  )
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function InvestigationsPage() {
  const navigate = useNavigate()
  const [page, setPage] = useState(1)
  const [filters, setFilters] = useState<InvestigationFilters>({})

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ["investigations", page, filters],
    queryFn: () => listInvestigations({ page, page_size: 20, ...filters }),
    placeholderData: (prev) => prev,
  })

  const items = data?.items ?? []
  const totalPages = data?.total_pages ?? 1

  return (
    <div className="flex flex-col gap-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10">
            <SearchCode className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight">Security Investigations</h1>
            <p className="text-sm text-muted-foreground">
              {data ? `${data.total.toLocaleString()} investigation${data.total !== 1 ? "s" : ""}` : "—"} ·
              Mutagent multi-analyzer traces
            </p>
          </div>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1 text-sm text-muted-foreground">
            <Filter className="h-3.5 w-3.5" />
            <span className="text-xs">Filter:</span>
          </div>
          <select
            className="h-8 rounded-md border border-border bg-background px-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            value={filters.decision ?? ""}
            onChange={(e) => { setFilters(f => ({ ...f, decision: e.target.value || undefined })); setPage(1) }}
          >
            <option value="">All Decisions</option>
            <option value="ALLOW">Allow</option>
            <option value="WARN">Warn</option>
            <option value="REDACT">Redact</option>
            <option value="BLOCK">Block</option>
          </select>
          <select
            className="h-8 rounded-md border border-border bg-background px-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            value={filters.severity ?? ""}
            onChange={(e) => { setFilters(f => ({ ...f, severity: e.target.value || undefined })); setPage(1) }}
          >
            <option value="">All Severities</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
            <option value="NONE">None</option>
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="rounded-xl border border-border bg-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-muted/40">
                <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wide">Scan ID</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wide">Employee</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wide">Target AI</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wide">Decision</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wide">Severity</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wide">Risk Score</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wide">Agents</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wide">Duration</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wide">When</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wide"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {isLoading ? (
                <tr>
                  <td colSpan={10} className="px-4 py-12 text-center text-muted-foreground text-sm">
                    <div className="flex items-center justify-center gap-2">
                      <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                      Loading investigations…
                    </div>
                  </td>
                </tr>
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan={10} className="px-4 py-16 text-center">
                    <div className="flex flex-col items-center gap-3">
                      <SearchCode className="h-10 w-10 text-muted-foreground/30" />
                      <p className="text-sm text-muted-foreground">No investigations yet. Scan a prompt to generate the first trace.</p>
                    </div>
                  </td>
                </tr>
              ) : (
                items.map((inv) => (
                  <InvestigationRow
                    key={inv.id}
                    inv={inv}
                    onClick={() => navigate(`/investigations/${inv.id}`)}
                  />
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between border-t border-border px-4 py-3">
            <p className="text-xs text-muted-foreground">
              Page {page} of {totalPages} · {data?.total ?? 0} total
            </p>
            <div className="flex items-center gap-1">
              <button
                className="flex h-7 w-7 items-center justify-center rounded-md border border-border bg-background text-xs hover:bg-muted disabled:opacity-40 disabled:cursor-not-allowed"
                disabled={page <= 1}
                onClick={() => setPage(p => p - 1)}
              >
                <ChevronLeft className="h-3.5 w-3.5" />
              </button>
              <span className="px-2 text-xs tabular-nums">{page}</span>
              <button
                className="flex h-7 w-7 items-center justify-center rounded-md border border-border bg-background text-xs hover:bg-muted disabled:opacity-40 disabled:cursor-not-allowed"
                disabled={page >= totalPages || isFetching}
                onClick={() => setPage(p => p + 1)}
              >
                <ChevronRight className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function InvestigationRow({
  inv,
  onClick,
}: {
  inv: InvestigationListItem
  onClick: () => void
}) {
  const failed = inv.analyzers_failed > 0
  const skipped = inv.analyzers_skipped > 0

  return (
    <tr
      className="group cursor-pointer transition-colors hover:bg-muted/40"
      onClick={onClick}
    >
      <td className="px-4 py-3">
        <span className="font-mono text-xs text-muted-foreground">{inv.id.slice(0, 8)}…</span>
      </td>
      <td className="px-4 py-3">
        <div className="flex flex-col">
          <span className="font-medium text-foreground text-xs">{inv.user_name || inv.user_email || "System User"}</span>
          {inv.user_email && inv.user_name && (
            <span className="text-[10px] text-muted-foreground">{inv.user_email}</span>
          )}
          {inv.user_department && (
            <span className="mt-0.5 inline-self-start rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground w-fit">
              {inv.user_department}
            </span>
          )}
        </div>
      </td>

      <td className="px-4 py-3">
        <span className="font-medium text-foreground">{inv.target_ai}</span>
        {inv.file_count > 0 && (
          <span className="ml-1.5 text-xs text-muted-foreground">+{inv.file_count} file{inv.file_count !== 1 ? "s" : ""}</span>
        )}
      </td>
      <td className="px-4 py-3">
        <DecisionBadge decision={inv.decision} />
      </td>
      <td className="px-4 py-3">
        <SeverityBadge severity={inv.overall_severity} />
      </td>
      <td className="px-4 py-3">
        <ScoreMeter score={inv.overall_score} />
      </td>
      <td className="px-4 py-3">
        <div className="flex items-center gap-1.5 text-xs">
          <span className="text-emerald-400">{inv.analyzers_succeeded}✓</span>
          {failed && <span className="text-red-400">{inv.analyzers_failed}✗</span>}
          {skipped && <span className="text-muted-foreground">{inv.analyzers_skipped}⊘</span>}
        </div>
      </td>
      <td className="px-4 py-3">
        <div className="flex items-center gap-1 text-xs text-muted-foreground">
          <Clock className="h-3 w-3" />
          {Math.round(inv.total_execution_ms)}ms
        </div>
      </td>
      <td className="px-4 py-3 text-xs text-muted-foreground">
        {formatDateTime(inv.created_at)}
      </td>
      <td className="px-4 py-3">
        <ExternalLink className="h-3.5 w-3.5 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
      </td>
    </tr>
  )
}
