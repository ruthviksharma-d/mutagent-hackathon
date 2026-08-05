/**
 * Typed client functions for the PromptShield admin APIs.
 * Includes Mutagent investigation trace endpoints (v2).
 */
import { api } from "./api"
import type {
  AgentExecution,
  AnalyticsSummary,
  CompanyKeyword,
  DashboardSummary,
  EmployeeListResponse,
  InvestigationDetail,
  InvestigationListResponse,
  OrgSettings,
  Policy,
  PolicyInput,
  PromptLogDetail,
  PromptLogListResponse,
  TimelineEvent,
} from "@/types/admin"

export async function getDashboardSummary(): Promise<DashboardSummary> {
  const { data } = await api.get<DashboardSummary>("/api/dashboard/summary")
  return data
}

export async function getAnalyticsSummary(): Promise<AnalyticsSummary> {
  const { data } = await api.get<AnalyticsSummary>("/api/analytics/summary")
  return data
}

export interface PromptLogFilters {
  page?: number
  page_size?: number
  search?: string
  action?: string
  risk?: string
  website?: string
  sort_by?: "created_at" | "score"
  sort_dir?: "asc" | "desc"
}

export async function getPromptLogs(filters: PromptLogFilters): Promise<PromptLogListResponse> {
  const { data } = await api.get<PromptLogListResponse>("/api/prompt-logs", { params: filters })
  return data
}

export async function getPromptLogDetail(id: string): Promise<PromptLogDetail> {
  const { data } = await api.get<PromptLogDetail>(`/api/prompt-logs/${id}`)
  return data
}

export async function getPolicies(): Promise<Policy[]> {
  const { data } = await api.get<Policy[]>("/api/policies")
  return data
}

export async function createPolicy(payload: PolicyInput): Promise<Policy> {
  const { data } = await api.post<Policy>("/api/policies", payload)
  return data
}

export async function updatePolicy(id: string, payload: Partial<PolicyInput>): Promise<Policy> {
  const { data } = await api.patch<Policy>(`/api/policies/${id}`, payload)
  return data
}

export async function deletePolicy(id: string): Promise<void> {
  await api.delete(`/api/policies/${id}`)
}

export interface EmployeeFilters {
  page?: number
  page_size?: number
  search?: string
  department?: string
  role?: string
}

export async function getEmployees(filters: EmployeeFilters): Promise<EmployeeListResponse> {
  const { data } = await api.get<EmployeeListResponse>("/api/employees", { params: filters })
  return data
}

export async function getSettings(): Promise<OrgSettings> {
  const { data } = await api.get<OrgSettings>("/api/settings")
  return data
}

export async function updateSettings(payload: Partial<OrgSettings>): Promise<OrgSettings> {
  const { data } = await api.put<OrgSettings>("/api/settings", payload)
  return data
}

export async function getKeywords(): Promise<CompanyKeyword[]> {
  const { data } = await api.get<CompanyKeyword[]>("/api/settings/keywords")
  return data
}

export async function createKeyword(keyword: string): Promise<CompanyKeyword> {
  const { data } = await api.post<CompanyKeyword>("/api/settings/keywords", { keyword })
  return data
}

export async function updateKeyword(id: string, enabled: boolean): Promise<CompanyKeyword> {
  const { data } = await api.patch<CompanyKeyword>(`/api/settings/keywords/${id}`, { enabled })
  return data
}

export async function deleteKeyword(id: string): Promise<void> {
  await api.delete(`/api/settings/keywords/${id}`)
}

// ---------------------------------------------------------------------------
// Investigations API (Mutagent v2)
// ---------------------------------------------------------------------------

export interface InvestigationFilters {
  page?: number
  page_size?: number
  decision?: string
  severity?: string
}

export async function listInvestigations(
  filters: InvestigationFilters = {},
): Promise<InvestigationListResponse> {
  const { data } = await api.get<InvestigationListResponse>("/api/investigations", {
    params: filters,
  })
  return data
}

export async function getInvestigation(scanId: string): Promise<InvestigationDetail> {
  const { data } = await api.get<InvestigationDetail>(`/api/investigations/${scanId}`)
  return data
}

export async function getInvestigationTimeline(scanId: string): Promise<TimelineEvent[]> {
  const { data } = await api.get<TimelineEvent[]>(`/api/investigations/${scanId}/timeline`)
  return data
}

export async function getInvestigationAgents(scanId: string): Promise<AgentExecution[]> {
  const { data } = await api.get<AgentExecution[]>(`/api/investigations/${scanId}/agents`)
  return data
}
