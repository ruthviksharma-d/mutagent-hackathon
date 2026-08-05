/**
 * InvestigationDetailPage — full multi-panel view of one investigation trace.
 *
 * Five panels:
 *   1. Summary Card       — scan ID, user, target AI, decision, timing
 *   2. Agent Flow Graph   — SVG execution DAG with status-colored nodes
 *   3. Timeline           — rich event log with all event types
 *   4. Evidence Panel ⭐   — per-agent expandable evidence items
 *   5. Risk Score Gauge   — animated 0–100 dial
 */
import { useState } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import {
  ArrowLeft, CheckCircle2, XCircle, Activity,
  ChevronDown, ChevronRight, Shield, Zap,
  SearchCode, AlertCircle, SkipForward, RefreshCw, Timer, Bot,
} from "lucide-react"
import { getInvestigation } from "@/lib/adminApi"
import type { AgentExecution, Evidence, TimelineEvent, InvestigationDetail } from "@/types/admin"
import { formatDateTime } from "@/lib/format"

// ---------------------------------------------------------------------------
// Colour helpers
// ---------------------------------------------------------------------------

const DECISION_COLOR: Record<string, string> = {
  ALLOW:  "#22c55e",
  WARN:   "#f59e0b",
  REDACT: "#60a5fa",
  BLOCK:  "#ef4444",
}

const SEVERITY_COLOR: Record<string, string> = {
  NONE:     "#6b7280",
  LOW:      "#22c55e",
  MEDIUM:   "#f59e0b",
  HIGH:     "#f97316",
  CRITICAL: "#ef4444",
}

const STATUS_COLOR: Record<string, { node: string; label: string }> = {
  SUCCESS: { node: "#22c55e", label: "text-emerald-400" },
  FAILED:  { node: "#ef4444", label: "text-red-400" },
  SKIPPED: { node: "#6b7280", label: "text-gray-400" },
  TIMEOUT: { node: "#f59e0b", label: "text-amber-400" },
  PENDING: { node: "#6b7280", label: "text-gray-400" },
  RUNNING: { node: "#60a5fa", label: "text-blue-400" },
}

const EVENT_ICON: Record<string, typeof CheckCircle2> = {
  investigation_start:  Activity,
  investigation_end:    CheckCircle2,
  analyzer_started:     Zap,
  analyzer_finished:    CheckCircle2,
  analyzer_failed:      XCircle,
  analyzer_skipped:     SkipForward,
  analyzer_timeout:     Timer,
  analyzer_recovered:   RefreshCw,
  decision_made:        Shield,
}

const EVENT_COLOR: Record<string, string> = {
  investigation_start:  "text-blue-400",
  investigation_end:    "text-emerald-400",
  analyzer_started:     "text-blue-400",
  analyzer_finished:    "text-emerald-400",
  analyzer_failed:      "text-red-400",
  analyzer_skipped:     "text-gray-400",
  analyzer_timeout:     "text-amber-400",
  analyzer_recovered:   "text-amber-400",
  decision_made:        "text-purple-400",
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function SummaryCard({ inv }: { inv: InvestigationDetail | undefined }) {
  if (!inv) return null
  const decisionColor = DECISION_COLOR[inv.decision] ?? "#6b7280"
  const summary = (inv.summary || {}) as Record<string, unknown>

  return (
    <div className="rounded-xl border border-border bg-card p-5 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold text-sm">Investigation Summary</h2>
        <span className="font-mono text-xs text-muted-foreground">{inv.id}</span>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "Employee", value: inv.user_name || inv.user_email || "System User" },
          { label: "Target AI", value: inv.target_ai },
          { label: "Files Scanned", value: String(inv.file_count) },
          {
            label: "Decision",
            value: inv.decision,
            style: `font-bold`,
            color: decisionColor,
          },
          { label: "Risk Score", value: `${inv.overall_score}/100` },
          { label: "Severity", value: inv.overall_severity, color: SEVERITY_COLOR[inv.overall_severity] },
          { label: "Analyzers", value: `${inv.analyzers_succeeded}✓ ${inv.analyzers_failed > 0 ? `${inv.analyzers_failed}✗` : ""} ${inv.analyzers_skipped > 0 ? `${inv.analyzers_skipped}⊘` : ""}`.trim() },
          { label: "Duration", value: `${Math.round(inv.total_execution_ms)}ms` },
        ].map(({ label, value, color, style }) => (
          <div key={label}>
            <p className="text-xs text-muted-foreground mb-0.5">{label}</p>
            <p className={`text-sm font-semibold ${style ?? ""}`} style={color ? { color } : undefined}>
              {value}
            </p>
          </div>
        ))}
      </div>

      {typeof summary.reasoning === "string" && summary.reasoning.length > 0 && (
        <div className="rounded-lg bg-muted/40 px-3 py-2">
          <p className="text-xs text-muted-foreground mb-0.5">Reasoning</p>
          <p className="text-sm">{summary.reasoning}</p>
        </div>
      )}
    </div>
  )
}

function RiskGauge({ score }: { score: number }) {
  const pct = Math.min(Math.max(score, 0), 100)
  const angle = -135 + (pct / 100) * 270
  const color = pct >= 75 ? "#ef4444" : pct >= 50 ? "#f97316" : pct >= 25 ? "#f59e0b" : "#22c55e"
  const cx = 90, cy = 60, r = 52

  function polarToCart(angleDeg: number, radius: number = r) {
    const a = angleDeg * (Math.PI / 180)
    return { x: cx + radius * Math.cos(a), y: cy + radius * Math.sin(a) }
  }
  const trackStart = polarToCart(-135)
  const trackEnd = polarToCart(135)
  const fillEnd = polarToCart(-135 + (pct / 100) * 270)

  // Outer indicator tick (confined between radius 40 and 52, zero overlap with center score text)
  const needleInner = polarToCart(angle, 38)
  const needleOuter = polarToCart(angle, 52)

  return (
    <div className="flex flex-col items-center shrink-0">
      <svg width="180" height="125" viewBox="0 0 180 125" className="select-none">
        {/* Track */}
        <path
          d={`M ${trackStart.x} ${trackStart.y} A ${r} ${r} 0 1 1 ${trackEnd.x} ${trackEnd.y}`}
          fill="none" stroke="#374151" strokeWidth="8" strokeLinecap="round"
        />
        {/* Fill */}
        <path
          d={`M ${trackStart.x} ${trackStart.y} A ${r} ${r} 0 ${pct > 50 ? 1 : 0} 1 ${fillEnd.x} ${fillEnd.y}`}
          fill="none" stroke={color} strokeWidth="8" strokeLinecap="round"
          style={{ transition: "stroke 0.5s" }}
        />
        {/* Outer Ring Tick Indicator */}
        <line
          x1={needleInner.x} y1={needleInner.y}
          x2={needleOuter.x} y2={needleOuter.y}
          stroke="#ffffff" strokeWidth="3" strokeLinecap="round"
        />
        <line
          x1={needleInner.x} y1={needleInner.y}
          x2={needleOuter.x} y2={needleOuter.y}
          stroke={color} strokeWidth="2" strokeLinecap="round"
        />

        {/* Center Score Typography — Completely Clear of Needle */}
        <text x={cx} y={cy + 6} textAnchor="middle" fontSize="28" fontWeight="800" fill={color}>
          {score}
        </text>
        <text x={cx} y={cy + 22} textAnchor="middle" fontSize="9" fontWeight="700" fill="#9ca3af" letterSpacing="0.08em">
          RISK SCORE
        </text>
      </svg>
    </div>
  )
}

function AgentFlowGraph({
  agentExecutions,
}: {
  agentExecutions: AgentExecution[]
}) {
  const statusMap: Record<string, string> = {}
  for (const ae of agentExecutions) {
    statusMap[ae.agent_name] = ae.status
  }

  const NODE_W = 130
  const NODE_H = 34
  const GAP_X = 20
  const GAP_Y = 28
  const MARGIN_X = 20
  const MARGIN_Y = 15

  // 4 parallel columns: Total parallel width = 4*130 + 3*20 = 580px
  const PARALLEL_WIDTH = 4 * NODE_W + 3 * GAP_X
  const SVG_W = MARGIN_X * 2 + PARALLEL_WIDTH // 620px
  const CENTER_X = MARGIN_X + PARALLEL_WIDTH / 2 // 310px
  const CENTER_NODE_X = CENTER_X - NODE_W / 2 // 245px

  type GraphNode = { key: string; label: string; x: number; y: number; color: string }

  // Y levels
  const y0 = MARGIN_Y                              // Prompt
  const y1 = y0 + NODE_H + GAP_Y                  // Context
  const y2 = y1 + NODE_H + GAP_Y                  // File Intel
  const y3 = y2 + NODE_H + GAP_Y                  // Parallel Stage
  const y4 = y3 + NODE_H + GAP_Y                  // Risk Fusion
  const y5 = y4 + NODE_H + GAP_Y                  // Decision
  const SVG_H = y5 + NODE_H + MARGIN_Y             // Total height ~365px

  const singleNodes: GraphNode[] = [
    { key: "_input", label: "Prompt", x: CENTER_NODE_X, y: y0, color: "#818cf8" },
    { key: "ContextAnalyzer", label: "Context Agent", x: CENTER_NODE_X, y: y1, color: STATUS_COLOR[statusMap["ContextAnalyzer"] ?? "SKIPPED"].node },
    { key: "FileIntelAnalyzer", label: "File Intel Agent", x: CENTER_NODE_X, y: y2, color: STATUS_COLOR[statusMap["FileIntelAnalyzer"] ?? "SKIPPED"].node },
  ]

  const parallelKeys = [
    { key: "PiiAnalyzer", label: "PII" },
    { key: "SecretsAnalyzer", label: "Secrets" },
    { key: "InjectionAnalyzer", label: "Injection" },
    { key: "ComplianceAnalyzer", label: "Compliance" },
  ]

  const parallelNodes: GraphNode[] = parallelKeys.map((p, i) => ({
    key: p.key,
    label: p.label,
    x: MARGIN_X + i * (NODE_W + GAP_X),
    y: y3,
    color: STATUS_COLOR[statusMap[p.key] ?? "SKIPPED"].node,
  }))

  const endNodes: GraphNode[] = [
    { key: "RiskFusionAnalyzer", label: "Risk Fusion", x: CENTER_NODE_X, y: y4, color: STATUS_COLOR[statusMap["RiskFusionAnalyzer"] ?? "SKIPPED"].node },
    { key: "DecisionAnalyzer", label: "Decision", x: CENTER_NODE_X, y: y5, color: STATUS_COLOR[statusMap["DecisionAnalyzer"] ?? "SKIPPED"].node },
  ]

  const allNodes = [...singleNodes, ...parallelNodes, ...endNodes]

  return (
    <div className="overflow-x-auto flex justify-center py-2">
      <svg width={SVG_W} height={SVG_H} className="text-xs select-none">
        <defs>
          <marker id="arrow" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 1 L 10 5 L 0 9 z" fill="#4b5563" />
          </marker>
        </defs>

        {/* Straight edges: Prompt -> Context -> File Intel */}
        <line x1={CENTER_X} y1={y0 + NODE_H} x2={CENTER_X} y2={y1} stroke="#4b5563" strokeWidth="1.5" markerEnd="url(#arrow)" />
        <line x1={CENTER_X} y1={y1 + NODE_H} x2={CENTER_X} y2={y2} stroke="#4b5563" strokeWidth="1.5" markerEnd="url(#arrow)" />

        {/* Fan out: File Intel -> Parallel Stage (PII, Secrets, Injection, Compliance) */}
        {parallelNodes.map((pn) => {
          const targetX = pn.x + NODE_W / 2
          return (
            <path
              key={`fan-out-${pn.key}`}
              d={`M ${CENTER_X} ${y2 + NODE_H} C ${CENTER_X} ${y2 + NODE_H + 14}, ${targetX} ${y3 - 14}, ${targetX} ${y3}`}
              stroke="#4b5563"
              strokeWidth="1.5"
              fill="none"
              strokeDasharray="4 2"
              markerEnd="url(#arrow)"
            />
          )
        })}

        {/* Fan in: Parallel Stage -> Risk Fusion */}
        {parallelNodes.map((pn) => {
          const sourceX = pn.x + NODE_W / 2
          return (
            <path
              key={`fan-in-${pn.key}`}
              d={`M ${sourceX} ${y3 + NODE_H} C ${sourceX} ${y3 + NODE_H + 14}, ${CENTER_X} ${y4 - 14}, ${CENTER_X} ${y4}`}
              stroke="#4b5563"
              strokeWidth="1.5"
              fill="none"
              strokeDasharray="4 2"
              markerEnd="url(#arrow)"
            />
          )
        })}

        {/* Straight edge: Risk Fusion -> Decision */}
        <line x1={CENTER_X} y1={y4 + NODE_H} x2={CENTER_X} y2={y5} stroke="#4b5563" strokeWidth="1.5" markerEnd="url(#arrow)" />

        {/* Render all nodes */}
        {allNodes.map((node) => (
          <g key={node.key}>
            <rect
              x={node.x}
              y={node.y}
              width={NODE_W}
              height={NODE_H}
              rx="6"
              ry="6"
              fill={node.color + "20"}
              stroke={node.color}
              strokeWidth="1.5"
            />
            <text
              x={node.x + NODE_W / 2}
              y={node.y + NODE_H / 2 + 4}
              textAnchor="middle"
              fontSize="11"
              fill={node.color}
              fontWeight="600"
            >
              {node.label}
            </text>
          </g>
        ))}
      </svg>
    </div>
  )
}


function TimelinePanel({ events }: { events: TimelineEvent[] }) {
  return (
    <div className="space-y-0">
      {events.map((event, idx) => {
        const Icon = EVENT_ICON[event.event_type] ?? Activity
        const colorCls = EVENT_COLOR[event.event_type] ?? "text-muted-foreground"
        const isLast = idx === events.length - 1
        return (
          <div key={event.id} className="flex gap-3">
            <div className="flex flex-col items-center">
              <div className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-muted/50 ${colorCls}`}>
                <Icon className="h-3.5 w-3.5" />
              </div>
              {!isLast && <div className="w-px flex-1 bg-border my-1" />}
            </div>
            <div className={`pb-4 ${isLast ? "" : ""}`}>
              <p className={`text-xs font-medium ${colorCls}`}>{event.event_type.replace(/_/g, " ").toUpperCase()}</p>
              <p className="text-xs text-foreground mt-0.5">{event.message}</p>
              <div className="flex items-center gap-3 mt-0.5">
                <span className="text-[10px] text-muted-foreground">
                  {formatDateTime(event.timestamp)}
                </span>
                {event.duration_ms != null && (
                  <span className="text-[10px] text-muted-foreground">
                    {Math.round(event.duration_ms)}ms
                  </span>
                )}
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}

function EvidenceItem({ ev }: { ev: Evidence }) {
  const color = SEVERITY_COLOR[ev.severity] ?? "#6b7280"
  const confPct = Math.round(ev.confidence * 100)
  return (
    <div className="flex items-start gap-3 rounded-lg border border-border/50 bg-muted/20 px-3 py-2.5 hover:bg-muted/40 transition-colors">
      <div
        className="mt-0.5 h-2 w-2 shrink-0 rounded-full"
        style={{ background: color }}
      />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs font-mono font-bold text-foreground">{ev.label}</span>
          <span
            className="rounded px-1.5 py-0.5 text-[10px] font-semibold"
            style={{ background: color + "26", color }}
          >
            {ev.severity}
          </span>
          <span className="text-[10px] text-muted-foreground">conf: {confPct}%</span>
          <span className="text-[10px] text-muted-foreground">via {ev.detector}</span>
        </div>
        <p className="text-xs font-mono text-muted-foreground mt-0.5 truncate">{ev.value_preview}</p>
        <p className="text-[10px] text-muted-foreground mt-0.5">📍 {ev.location}</p>
      </div>
    </div>
  )
}

function AgentCard({ agent }: { agent: AgentExecution }) {
  const [expanded, setExpanded] = useState(false)
  const statusStyle = STATUS_COLOR[agent.status] ?? STATUS_COLOR.PENDING
  const hasEvidence = agent.evidence.length > 0

  return (
    <div className="rounded-xl border border-border bg-card overflow-hidden">
      <button
        className="w-full flex items-center gap-3 px-4 py-3 hover:bg-muted/30 transition-colors text-left"
        onClick={() => setExpanded(!expanded)}
      >
        <div
          className="h-2 w-2 rounded-full shrink-0"
          style={{ background: statusStyle.node }}
        />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-semibold">{agent.display_name}</span>
            <span className={`text-xs font-medium ${statusStyle.label}`}>{agent.status}</span>
            {agent.severity !== "NONE" && (
              <span
                className="text-[10px] rounded px-1.5 py-0.5"
                style={{
                  background: (SEVERITY_COLOR[agent.severity] ?? "#6b7280") + "26",
                  color: SEVERITY_COLOR[agent.severity] ?? "#6b7280",
                }}
              >
                {agent.severity}
              </span>
            )}
          </div>
          <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">{agent.summary}</p>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <span className="text-xs text-muted-foreground">{Math.round(agent.execution_time_ms)}ms</span>
          {hasEvidence && (
            <span className="text-xs font-medium text-primary">{agent.evidence.length} evidence</span>
          )}
          {expanded ? (
            <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
          ) : (
            <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
          )}
        </div>
      </button>

      {expanded && (
        <div className="border-t border-border px-4 py-3 space-y-2">
          {agent.error && (
            <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-400">
              Error: {agent.error}
            </div>
          )}
          {hasEvidence ? (
            <div className="space-y-1.5">
              {agent.evidence.map((ev, i) => (
                <EvidenceItem key={i} ev={ev} />
              ))}
            </div>
          ) : (
            <p className="text-xs text-muted-foreground italic">No evidence items — no issues detected by this agent.</p>
          )}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function InvestigationDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState<"graph" | "timeline" | "evidence">("graph")

  const { data: inv, isLoading } = useQuery({
    queryKey: ["investigation", id],
    queryFn: () => getInvestigation(id!),
    enabled: !!id,
  })

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center gap-2 text-muted-foreground">
        <div className="h-5 w-5 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        Loading investigation trace…
      </div>
    )
  }

  if (!inv) {
    return (
      <div className="flex h-64 flex-col items-center justify-center gap-3">
        <AlertCircle className="h-10 w-10 text-muted-foreground/30" />
        <p className="text-muted-foreground">Investigation not found.</p>
        <button
          onClick={() => navigate("/investigations")}
          className="text-sm text-primary hover:underline"
        >
          ← Back to Investigations
        </button>
      </div>
    )
  }

  const tabs = [
    { id: "graph",    label: "Agent Flow Graph", icon: Bot },
    { id: "timeline", label: "Timeline",         icon: Activity },
    { id: "evidence", label: `Evidence (${inv.agent_executions.reduce((acc, a) => acc + a.evidence.length, 0)})`, icon: SearchCode },
  ] as const

  return (
    <div className="flex flex-col gap-5 p-6 max-w-5xl">
      {/* Back nav */}
      <button
        onClick={() => navigate("/investigations")}
        className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors self-start"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        All Investigations
      </button>

      {/* Panel 1 — Summary */}
      <SummaryCard inv={inv} />

      {/* Panels 2–4 — Tabbed */}
      <div className="rounded-xl border border-border bg-card overflow-hidden">
        {/* Tab bar */}
        <div className="flex border-b border-border">
          {tabs.map(({ id: tabId, label, icon: Icon }) => (
            <button
              key={tabId}
              onClick={() => setActiveTab(tabId)}
              className={`flex items-center gap-2 px-4 py-3 text-sm font-medium transition-colors border-b-2 ${
                activeTab === tabId
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              <Icon className="h-3.5 w-3.5" />
              {label}
            </button>
          ))}
        </div>

        <div className="p-5">
          {activeTab === "graph" && (
            <div className="space-y-4">
              <p className="text-xs text-muted-foreground">
                Execution graph — node color indicates analyzer status.
                <span className="ml-3 inline-flex gap-2">
                  {Object.entries({ SUCCESS: "#22c55e", FAILED: "#ef4444", SKIPPED: "#6b7280", TIMEOUT: "#f59e0b" }).map(([status, color]) => (
                    <span key={status} className="inline-flex items-center gap-1 text-[10px]">
                      <span className="h-2 w-2 rounded-full inline-block" style={{ background: color }} />
                      {status}
                    </span>
                  ))}
                </span>
              </p>
              <AgentFlowGraph agentExecutions={inv.agent_executions} />
            </div>
          )}

          {activeTab === "timeline" && (
            <div className="max-h-[520px] overflow-y-auto pr-1">
              {inv.timeline.length === 0 ? (
                <p className="text-sm text-muted-foreground italic">No timeline events recorded.</p>
              ) : (
                <TimelinePanel events={inv.timeline} />
              )}
            </div>
          )}

          {activeTab === "evidence" && (
            <div className="space-y-3">
              {inv.agent_executions.filter(a => a.evidence.length > 0).length === 0 ? (
                <p className="text-sm text-muted-foreground italic">No evidence items — investigation found no issues.</p>
              ) : (
                inv.agent_executions
                  .filter(a => a.evidence.length > 0 || a.status === "FAILED")
                  .map(agent => <AgentCard key={agent.id} agent={agent} />)
              )}
            </div>
          )}
        </div>
      </div>

      {/* Panel 5 — Risk Gauge */}
      <div className="rounded-xl border border-border bg-card p-5">
        <h3 className="text-sm font-semibold mb-3">Risk Score</h3>
        <div className="flex items-center gap-8">
          <RiskGauge score={inv.overall_score} />
          <div className="space-y-2">
            <div>
              <p className="text-xs text-muted-foreground">Severity Band</p>
              <p
                className="text-sm font-bold"
                style={{ color: SEVERITY_COLOR[inv.overall_severity] ?? "#6b7280" }}
              >
                {inv.overall_severity}
              </p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Confidence</p>
              <p className="text-sm font-medium">
                {(() => {
                  const summary = (inv.summary || {}) as Record<string, unknown>
                  const conf = summary.overall_confidence as number | undefined
                  return conf != null ? `${Math.round(conf * 100)}%` : "—"
                })()}
              </p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Execution Time</p>
              <p className="text-sm font-medium">{Math.round(inv.total_execution_ms)}ms total</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
