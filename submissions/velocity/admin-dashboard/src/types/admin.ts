/** TypeScript mirrors of the Milestone 4 backend Pydantic schemas. */

export type Action = "ALLOW" | "WARN" | "REDACT" | "BLOCK"
export type Risk = "NONE" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"

export interface DailyActivityPoint {
  date: string
  ALLOW: number
  WARN: number
  REDACT: number
  BLOCK: number
}

export interface RiskDistributionPoint {
  risk: Risk
  count: number
}

export interface DetectorCount {
  detector: string
  count: number
}

export interface WebsiteUsagePoint {
  website: string
  count: number
}

export interface DepartmentUsagePoint {
  department: string
  count: number
}

export interface RecentActivityItem {
  id: string
  employee_name: string
  employee_email: string
  website: string
  action: Action
  risk: Risk
  score: number
  created_at: string
}

export interface FileTypeBreakdownPoint {
  extension: string
  count: number
}

export interface FileCategoryPoint {
  category: string
  count: number
}

export interface FileScanStats {
  total_files_scanned: number
  blocked_uploads: number
  file_type_breakdown: FileTypeBreakdownPoint[]
  top_sensitive_categories: FileCategoryPoint[]
}

export interface DashboardSummary {
  security_score: number
  total_prompts: number
  allowed: number
  warned: number
  redacted: number
  blocked: number
  active_employees: number
  protected_websites: number
  daily_activity: DailyActivityPoint[]
  risk_distribution: RiskDistributionPoint[]
  top_violations: DetectorCount[]
  website_usage: WebsiteUsagePoint[]
  department_usage: DepartmentUsagePoint[]
  recent_activity: RecentActivityItem[]
  file_stats: FileScanStats
}

export interface RiskTrendPoint {
  date: string
  average_risk_score: number
}

export interface TopEmployeeViolation {
  full_name: string
  email: string
  department: string | null
  violation_count: number
}

export interface AnalyticsSummary {
  daily_activity: DailyActivityPoint[]
  blocked_vs_allowed: Record<string, number>
  risk_trend: RiskTrendPoint[]
  top_triggered_rules: DetectorCount[]
  website_usage: WebsiteUsagePoint[]
  department_usage: DepartmentUsagePoint[]
  top_employees_by_violations: TopEmployeeViolation[]
  file_stats: FileScanStats
}

export interface PromptLogListItem {
  id: string
  employee_name: string
  employee_email: string
  website: string
  risk: Risk
  score: number
  action: Action
  status: "Clean" | "Flagged"
  created_at: string
  has_files: boolean
  file_count: number
}

export interface FileFinding {
  filename: string
  extension: string
  category: string
  size_bytes: number | null
  mime_type: string | null
  risk: Risk
  score: number
  extracted: boolean
  extraction_note: string | null
}

export interface PromptLogListResponse {
  items: PromptLogListItem[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface TriggeredRuleDetail {
  detector: string
  severity: Risk
  score: number
  reason: string
}

export interface PromptLogDetail {
  id: string
  employee_name: string
  employee_email: string
  department: string | null
  website: string
  risk: Risk
  score: number
  action: Action
  reason: string
  triggered_policy: string | null
  original_prompt: string
  sanitized_prompt: string
  triggered_rules: TriggeredRuleDetail[]
  created_at: string
  files: FileFinding[]
}

export interface Policy {
  id: string
  name: string
  description: string
  priority: number
  detection_type: string
  action: Action
  enabled: boolean
  created_at: string
  updated_at: string
}

export interface PolicyInput {
  name: string
  description: string
  priority: number
  detection_type: string
  action: Action
  enabled: boolean
}

export interface EmployeeListItem {
  id: string
  full_name: string
  email: string
  department: string | null
  role: string
  prompt_count: number
  violation_count: number
  last_active: string | null
  extension_status: "active" | "inactive" | "not_installed"
}

export interface EmployeeListResponse {
  items: EmployeeListItem[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface OrgSettings {
  organization_name: string
  risk_threshold: number
  supported_websites: string[]
  allowed_file_types: string[]
  theme_default: "light" | "dark"
  // Mutagent: configurable per-analyzer risk weights and enabled analyzers
  risk_weights: Record<string, number> | null
  enabled_analyzers: string[] | null
}

export interface CompanyKeyword {
  id: string
  keyword: string
  enabled: boolean
}

// ---------------------------------------------------------------------------
// Investigation (Mutagent trace) types
// ---------------------------------------------------------------------------

export interface Evidence {
  label: string
  value_preview: string
  confidence: number
  location: string
  detector: string
  severity: Risk
  start: number | null
  end: number | null
  metadata: Record<string, unknown>
}

export interface AgentExecution {
  id: string
  agent_name: string
  display_name: string
  status: "SUCCESS" | "FAILED" | "SKIPPED" | "TIMEOUT" | "PENDING" | "RUNNING"
  execution_time_ms: number
  confidence: number
  severity: Risk
  recommendation: Action
  summary: string
  error: string | null
  findings: Record<string, unknown>[]
  evidence: Evidence[]
  created_at: string
}

export interface TimelineEvent {
  id: string
  event_type: string
  analyzer_name: string | null
  message: string
  timestamp: string
  duration_ms: number | null
  metadata: Record<string, unknown>
}

export interface InvestigationListItem {
  id: string
  user_id: string
  user_email?: string
  user_name?: string
  user_department?: string
  target_ai: string
  file_count: number
  total_analyzers: number
  analyzers_succeeded: number
  analyzers_failed: number
  analyzers_skipped: number
  overall_score: number
  overall_severity: Risk
  decision: Action
  total_execution_ms: number
  created_at: string
}

export interface InvestigationDetail extends InvestigationListItem {
  prompt_length: number
  summary: Record<string, unknown>
  agent_executions: AgentExecution[]
  timeline: TimelineEvent[]
}

export interface InvestigationListResponse {
  items: InvestigationListItem[]
  total: number
  page: number
  page_size: number
  total_pages: number
}
